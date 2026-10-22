"""Add new non-mod files (configs, kubejs data, ...) to the public Stable client pack and build its per-file index.

Every existing ZIP entry is copied unchanged; every file under <files-dir> is added at the same relative path
inside the pack (e.g. files/steel-casting1/kubejs/data/x.json -> kubejs/data/x.json). None of them may exist in
the pack yet. A new immutable release (pack-<version>) gets the ZIP and the index, and the public manifest is
updated with packVersion + package + fileIndex together, as required by docs/launcher-updates.md.
Existing players then fetch only the new files.

  patch    <manifest.json> <current.zip> <current-index.json> <files-dir> <base-pack> <suffix> <out-dir>
  verify   <out-dir>      (after upload: every new file must be fetchable through an exact HTTP range)
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'launcher' / 'source'))
from incremental import build_index, fetch_range, sha256, validate_index  # noqa: E402

REPO_DOWNLOADS = 'https://github.com/koshgamer/KoshPack-Updates/releases/download/'


def patch(manifest_path, archive, current_index_path, files_dir, base_pack, suffix, out, downloads=REPO_DOWNLOADS):
    manifest = json.loads(Path(manifest_path).read_text('utf-8'))
    assert manifest['packVersion'] == base_pack, f"Public pack is {manifest['packVersion']}, expected {base_pack}; refusing."
    assert archive.stat().st_size == manifest['package']['size'], 'Base pack size mismatch'
    assert sha256(archive) == manifest['package']['sha256'], 'Base pack hash mismatch'
    assert sha256(current_index_path) == manifest['fileIndex']['sha256'], 'Current index hash mismatch'
    current_index = validate_index(json.loads(Path(current_index_path).read_text('utf-8')))
    assert current_index['packageSha256'] == manifest['package']['sha256'], 'Current index is for another pack'

    new_files = {p.relative_to(files_dir).as_posix(): p for p in sorted(files_dir.rglob('*')) if p.is_file()}
    assert new_files, f'No files under {files_dir}'
    assert not any(rel.startswith('mods/') for rel in new_files), 'Use add_stable_mod.py for mod JARs'

    version = f'{base_pack}-{suffix}'
    tag = f'pack-{version}'
    out.mkdir(parents=True, exist_ok=True)
    package = out / f'Project-Meridian-{version}-client.zip'
    with zipfile.ZipFile(archive) as src:
        infos = src.infolist()
        names = [i.filename for i in infos if not i.is_dir()]
        prefix = next((p for p in ('.minecraft/', 'minecraft/') if all(n.startswith(p) for n in names)), '')
        for rel in new_files:
            assert prefix + rel not in names, f'{prefix + rel} is already in the pack'
        with zipfile.ZipFile(package, 'w', allowZip64=True) as dst:
            for info in infos:
                if info.is_dir():
                    dst.writestr(info, b'')
                    continue
                with src.open(info) as fin, dst.open(info, 'w', force_zip64=True) as fout:
                    shutil.copyfileobj(fin, fout, 4 * 1024 * 1024)
            for rel, path in new_files.items():
                entry = zipfile.ZipInfo(prefix + rel, date_time=(2026, 10, 22, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                dst.writestr(entry, path.read_bytes(), compresslevel=6)
    with zipfile.ZipFile(package) as check:
        assert check.testzip() is None, 'Patched ZIP is corrupt'

    url = downloads + tag + '/' + package.name
    index = build_index(package, url)
    before = {e['path']: e['sha256'] for e in current_index['files']}
    after = {e['path']: e['sha256'] for e in index['files']}
    removed = sorted(set(before) - set(after))
    added = sorted(set(after) - set(before))
    changed = sorted(p for p in set(before) & set(after) if before[p] != after[p])
    assert removed == [] and added == sorted(new_files) and not changed, (removed, added, changed)
    expected = {rel: sha256(path) for rel, path in new_files.items()}
    assert all(after[rel] == sha for rel, sha in expected.items())

    index_path = out / f'files-{index["packageSha256"][:16]}.json'
    index_path.write_text(json.dumps(index, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    manifest['packVersion'] = version
    manifest['package'] = {'file': package.name, 'url': url, 'sha256': index['packageSha256'],
                           'size': package.stat().st_size}
    manifest['fileIndex'] = {'url': downloads + tag + '/' + index_path.name,
                             'sha256': sha256(index_path), 'size': index_path.stat().st_size}
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (out / 'tag.txt').write_text(tag)
    (out / 'assets.txt').write_text(f'{package}\n{index_path}\n')
    (out / 'added.json').write_text(json.dumps(expected, indent=2))
    print(f'{version}: {len(index["files"])} files; added {added}; unchanged {len(before)}; '
          f'package {package.stat().st_size} bytes, sha256 {index["packageSha256"]}')
    return manifest, index


def verify(out):
    manifest = json.loads((out / 'manifest.json').read_text('utf-8'))
    index_path = Path((out / 'assets.txt').read_text().split()[1])
    expected = json.loads((out / 'added.json').read_text())
    assert sha256(index_path) == manifest['fileIndex']['sha256']
    index = validate_index(json.loads(index_path.read_text('utf-8')))
    assert manifest['package']['url'] == index['url']
    for rel, sha in expected.items():
        entry = next(e for e in index['files'] if e['path'] == rel)
        raw = fetch_range(index['url'], entry['offset'], entry['length'], index['packageSize'])
        data = zlib.decompress(raw, -15) if entry['method'] == 8 else raw
        assert hashlib.sha256(data).hexdigest() == sha, f'Live range returned different bytes for {rel}'
        print('Live HTTP range verified for', rel)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'patch':
        patch(sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5]), sys.argv[6], sys.argv[7],
              Path(sys.argv[8]))
    elif len(sys.argv) > 1 and sys.argv[1] == 'verify':
        verify(Path(sys.argv[2]))
    else:
        raise SystemExit(__doc__)
