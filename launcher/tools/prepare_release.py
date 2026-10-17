"""Build a backwards-compatible pack and pinned per-file index for publication."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import urllib.request
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'source'))
from incremental import build_index, sha256

ZUME_URL = 'https://cdn.modrinth.com/data/o6qsdrrQ/versions/Rh2ImJ86/zume-1.2.2.jar'
ZUME_SHA512 = '9803fcf070327ed40316f8323ad7de83977a4ff8dc928c892836c8f49a9be3da6e9282aa85bf8bcf3467c4339f3d16dad5ec92d1a2e9bc9fc10bddba1ffc1190'


def download(url, path):
    req = urllib.request.Request(url, headers={'User-Agent':'ProjectMeridian-Release/1.1'})
    with urllib.request.urlopen(req, timeout=180) as r, path.open('wb') as f:
        shutil.copyfileobj(r, f, 1024*1024)


def prepare(manifest, archive, mod, out):
    assert sha256(archive) == manifest['package']['sha256'], 'Base pack hash mismatch'
    assert archive.stat().st_size == manifest['package']['size'], 'Base pack size mismatch'
    assert hashlib.sha512(mod.read_bytes()).hexdigest() == ZUME_SHA512, 'Zoom mod hash mismatch'
    version = manifest['packVersion']
    with zipfile.ZipFile(archive) as z:
        names = [i.filename for i in z.infolist() if not i.is_dir()]
        prefix = next((p for p in ('.minecraft/','minecraft/') if all(n.startswith(p) for n in names)), '')
        present = [n for n in names if n.startswith(prefix+'mods/') and Path(n).name.lower().startswith('zume-')]
        if present:
            assert len(present)==1 and hashlib.sha512(z.read(present[0])).hexdigest()==ZUME_SHA512, 'Different Zume already present'
    if not present:
        version += '-zoom1'
        package = out / f'Project-Meridian-{version}-client.zip'
        shutil.copy2(archive, package)
        with zipfile.ZipFile(package,'a',zipfile.ZIP_DEFLATED) as z:
            info=zipfile.ZipInfo(prefix+'mods/zume-1.2.2.jar', date_time=(2026,4,25,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,mod.read_bytes())
    else:
        package = out/manifest['package']['file']
        if archive.resolve()!=package.resolve(): shutil.copy2(archive,package)
    tag = 'pack-'+version
    base = f'https://github.com/koshgamer/KoshPack-Updates/releases/download/{tag}/'
    index = build_index(package, base+package.name)
    index_path = out/f'files-{index["packageSha256"][:16]}.json'
    index_path.write_text(json.dumps(index, ensure_ascii=False, separators=(',',':')), encoding='utf-8')
    fields = {'packVersion':version, 'package':{'file':package.name,'url':base+package.name,
              'sha256':index['packageSha256'],'size':package.stat().st_size},
              'fileIndex':{'url':base+index_path.name,'sha256':sha256(index_path),'size':index_path.stat().st_size}}
    (out/'pack-fields.json').write_text(json.dumps(fields, indent=2),encoding='utf-8')
    (out/'base-sha.txt').write_text(manifest['package']['sha256'])
    (out/'tag.txt').write_text(tag)
    print(f'{len(index["files"])} indexed files; {version}; zoom payload {mod.stat().st_size} bytes')
    return index

if __name__=='__main__':
    out=Path('.out'); out.mkdir(exist_ok=True)
    manifest=json.loads(Path('launcher/manifest.json').read_text('utf-8'))
    archive=out/'original.zip'; mod=out/'zume-1.2.2.jar'
    if not archive.exists(): download(manifest['package']['url'], archive)
    if not mod.exists(): download(ZUME_URL,mod)
    prepare(manifest,archive,mod,out)
