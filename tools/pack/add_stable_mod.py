"""Add one new mod JAR to the public Stable client pack and build its per-file index.

Every existing ZIP entry is copied unchanged; exactly one new file (mods/<jar>) is added. A new immutable
release (pack-<version>) gets the ZIP and the index, and the public manifest is updated with
packVersion + package + fileIndex together, as required by docs/launcher-updates.md.
Existing players then fetch only the new JAR.

  patch    <manifest.json> <current.zip> <current-index.json> <new-jar> <expected-sha256> <base-pack> <suffix> <out-dir>
  verify   <out-dir>      (after upload: the new JAR must be fetchable through an exact HTTP range)
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


def mod_id(jar_bytes_path):
    with zipfile.ZipFile(jar_bytes_path) as z:
        toml = z.read('META-INF/neoforge.mods.toml').decode('utf-8')
    for line in toml.splitlines():
        line = line.strip()
        if line.startswith('modId=') or line.startswith('modId ='):
            return line.split('=', 1)[1].strip().strip('"')
    raise AssertionError('modId not found in the new JAR')


def patch(manifest_path, archive, current_index_path, jar, expected_sha, base_pack, suffix, out,
          downloads=REPO_DOWNLOADS):
    manifest = json.loads(Path(manifest_path).read_text('utf-8'))
    assert manifest['packVersion'] == base_pack, f"Public pack is {manifest['packVersion']}, expected {base_pack}; refusing."
    assert archive.stat().st_size == manifest['package']['size'], 'Base pack size mismatch'
    assert sha256(archive) == manifest['package']['sha256'], 'Base pack hash mismatch'
    assert sha256(jar) == expected_sha, 'New mod JAR hash mismatch'
    assert sha256(current_index_path) == manifest['fileIndex']['sha256'], 'Current index hash mismatch'
    current_index = validate_index(json.loads(Path(current_index_path).read_text('utf-8')))
    assert current_index['packageSha256'] == manifest['package']['sha256'], 'Current index is for another pack'
    new_mod_id = mod_id(jar)

    version = f'{base_pack}-{suffix}'
    tag = f'pack-{version}'
    rel = 'mods/' + jar.name
    out.mkdir(parents=True, exist_ok=True)
    package = out / f'Project-Meridian-{version}-client.zip'
    with zipfile.ZipFile(archive) as src:
        infos = src.infolist()
        names = [i.filename for i in infos if not i.is_dir()]
        prefix = next((p for p in ('.minecraft/', 'minecraft/') if all(n.startswith(p) for n in names)), '')
        new = prefix + rel
        assert new not in names, f'{new} is already in the pack'
        # no other JAR of the pack may carry the same mod id (two copies would crash the game)
        for n in names:
            if n.startswith(prefix + 'mods/') and n.lower().endswith('.jar'):
                with src.open(n) as f, zipfile.ZipFile(f) as inner:
                    try:
                        toml = inner.read('META-INF/neoforge.mods.toml').decode('utf-8', 'replace')
                    except KeyError:
                        continue
                assert f'modId="{new_mod_id}"' not in toml.replace(' ', ''), f'{n} already provides {new_mod_id}'
        with zipfile.ZipFile(package, 'w', allowZip64=True) as dst:
            for info in infos:
                if info.is_dir():
                    dst.writestr(info, b'')
                    continue
                with src.open(info) as fin, dst.open(info, 'w', force_zip64=True) as fout:
                    shutil.copyfileobj(fin, fout, 4 * 1024 * 1024)
            entry = zipfile.ZipInfo(new, date_time=(2026, 10, 19, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            dst.writestr(entry, jar.read_bytes(), compresslevel=6)
    with zipfile.ZipFile(package) as check:
        assert check.testzip() is None, 'Patched ZIP is corrupt'

    url = downloads + tag + '/' + package.name
    index = build_index(package, url)
    before = {e['path']: e['sha256'] for e in current_index['files']}
    after = {e['path']: e['sha256'] for e in index['files']}
    removed = sorted(set(before) - set(after))
    added = sorted(set(after) - set(before))
    changed = sorted(p for p in set(before) & set(after) if before[p] != after[p])
    assert removed == [] and added == [rel] and not changed, (removed, added, changed)
    assert after[rel] == expected_sha

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
    (out / 'added.txt').write_text(f'{rel}\n{expected_sha}\n')
    print(f'{version}: {len(index["files"])} files; added {added}; unchanged {len(before)}; '
          f'package {package.stat().st_size} bytes, sha256 {index["packageSha256"]}')
    return manifest, index


def verify(out):
    manifest = json.loads((out / 'manifest.json').read_text('utf-8'))
    index_path = Path((out / 'assets.txt').read_text().split()[1])
    rel, expected = (out / 'added.txt').read_text().split()
    assert sha256(index_path) == manifest['fileIndex']['sha256']
    index = validate_index(json.loads(index_path.read_text('utf-8')))
    entry = next(e for e in index['files'] if e['path'] == rel)
    raw = fetch_range(index['url'], entry['offset'], entry['length'], index['packageSize'])
    data = zlib.decompress(raw, -15) if entry['method'] == 8 else raw
    assert hashlib.sha256(data).hexdigest() == expected, 'Live range returned different bytes'
    assert manifest['package']['url'] == index['url']
    print('Live HTTP range verified for', rel)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'patch':
        patch(sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5]), sys.argv[6], sys.argv[7],
              sys.argv[8], Path(sys.argv[9]))
    elif len(sys.argv) > 1 and sys.argv[1] == 'verify':
        verify(Path(sys.argv[2]))
    else:
        raise SystemExit(__doc__)
