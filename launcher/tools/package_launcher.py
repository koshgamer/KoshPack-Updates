import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
from incremental import sha256


def build_inputs():
    paths = []
    for directory in ('launcher/source', 'launcher/build', 'launcher/tools'):
        paths.extend(path for path in Path(directory).rglob('*')
                     if path.is_file() and path.suffix in ('.py', '.txt', '.iss', '.ps1', '.cs', '.spec'))
    paths.extend(Path(name) for name in ('.github/workflows/publish-meridian-launcher.yml',
                                        'launcher/meridian.ico', 'launcher/meridian.png', 'launcher/meridian-keygen.wav'))
    return {path.as_posix(): sha256(path) for path in sorted(paths)}


def artifact(path):
    return {'file': path.name, 'sha256': sha256(path), 'size': path.stat().st_size}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--installer', action='store_true')
    arguments = parser.parse_args()
    output = Path('.out')
    output.mkdir(exist_ok=True)
    metadata_path = output / 'launcher-build.json'
    if arguments.installer:
        metadata = json.loads(metadata_path.read_text('utf-8'))
        metadata['installer'] = artifact(Path('dist/Project-Meridian-Launcher.exe'))
    else:
        version = re.search(r'APP_VERSION = "([^\"]+)"', Path('launcher/source/launcher.py').read_text('utf-8')).group(1)
        bundle = Path('dist/Project-Meridian-Launcher')
        application = bundle / 'app'
        files = {path.relative_to(application).as_posix(): sha256(path)
                 for path in sorted(application.rglob('*')) if path.is_file() and path.name != 'bundle.json'}
        marker = {'schema': 1, 'product': 'Project Meridian Launcher', 'version': version, 'files': files}
        (application / 'bundle.json').write_text(json.dumps(marker, sort_keys=True, indent=2) + '\n', encoding='utf-8')
        archive = Path('dist') / f'Project-Meridian-Launcher-{version}-win64.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as package:
            for path in sorted(bundle.rglob('*')):
                if path.is_file():
                    package.write(path, path.relative_to(bundle).as_posix())
        try:
            revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True, stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            revision = None
        metadata = {'version': version, 'bundle': artifact(archive), 'buildInputs': build_inputs(),
                    'sourceCommit': revision}
    metadata_path.write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    checksums = [f"{metadata[kind]['sha256']}  {metadata[kind]['file']}"
                 for kind in ('bundle', 'installer') if kind in metadata]
    Path('dist/SHA256SUMS.txt').write_text('\n'.join(checksums) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in metadata.items() if key != 'buildInputs'}, indent=2))


if __name__ == '__main__':
    main()
