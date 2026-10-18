import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
from incremental import sha256


def merge_release(manifest, metadata):
    version = metadata.get('version', '')
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Invalid launcher version')
    base = f'https://github.com/koshgamer/KoshPack-Updates/releases/download/launcher-{version}/'
    artifacts = {}
    for kind, suffix in (('installer', '.exe'), ('bundle', '.zip')):
        artifact = metadata.get(kind, {})
        name = artifact.get('file', '')
        if not name.endswith(suffix) or '/' in name or '\\' in name or not re.fullmatch(r'[A-Za-z0-9_.-]+', name):
            raise ValueError(f'Missing or invalid {kind}')
        if not re.fullmatch('[0-9a-f]{64}', str(artifact.get('sha256', ''))) or type(artifact.get('size')) is not int or artifact['size'] <= 0:
            raise ValueError(f'Invalid {kind} digest/size')
        artifacts[kind] = {'url': base + name, 'sha256': artifact['sha256'], 'size': artifact['size']}
    result = copy.deepcopy(manifest)
    result['launcher'] = dict(artifacts['installer'], version=version, format='installer',
                              bundle=dict(artifacts['bundle'], format='onedir-zip'))
    return result


def verify_remote(artifact):
    digest = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(artifact['url'], timeout=120) as response:
        while block := response.read(1024 * 1024):
            size += len(block)
            if size > artifact['size']:
                raise ValueError('Published artifact exceeds declared size')
            digest.update(block)
    if size != artifact['size'] or digest.hexdigest() != artifact['sha256']:
        raise ValueError('Published artifact does not match the tested build')


def main():
    metadata = json.loads(Path('.out/launcher-build.json').read_text('utf-8'))
    inputs = metadata.get('buildInputs')
    if not inputs:
        raise ValueError('Build inputs are missing')
    for name, expected in inputs.items():
        if sha256(Path(name)) != expected:
            raise ValueError(f'Source changed during build: {name}')
    path = Path('launcher/manifest.json')
    manifest = merge_release(json.loads(path.read_text('utf-8')), metadata)
    verify_remote(manifest['launcher'])
    verify_remote(manifest['launcher']['bundle'])
    temporary = path.with_suffix('.new')
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


if __name__ == '__main__':
    main()
