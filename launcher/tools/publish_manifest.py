"""Merge only this release's fields into the latest manifest, refusing stale packs."""
import json
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from incremental import sha256
p=Path('launcher/manifest.json')
manifest=json.loads(p.read_text('utf-8'))
fields=json.loads(Path('.out/pack-fields.json').read_text('utf-8'))
assert manifest['package']['sha256'] in (Path('.out/base-sha.txt').read_text().strip(),fields['package']['sha256']), 'Pack changed during build; refusing to overwrite'
version=re.search(r'APP_VERSION = "([^"]+)"',Path('launcher/source/launcher.py').read_text('utf-8')).group(1)
exe=Path('dist/Project-Meridian-Launcher.exe')
manifest.update(fields)
manifest['launcher']={'version':version,'url':f'https://github.com/koshgamer/KoshPack-Updates/releases/download/launcher-{version}/Project-Meridian-Launcher.exe', 'sha256':sha256(exe),'size':exe.stat().st_size}
# Old launchers can still install the full ZIP. Do not lock them out of the game.
p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
