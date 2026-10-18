from pathlib import Path

repository = Path(SPECPATH).resolve().parents[1]
analysis = Analysis(
    [str(repository / 'launcher/source/launcher.py')],
    pathex=[str(repository / 'launcher/source')],
    binaries=[],
    datas=[(str(repository / 'launcher' / name), '.')
           for name in ('meridian.ico', 'meridian.png', 'meridian-keygen.wav')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
archive = PYZ(analysis.pure)
executable = EXE(
    archive, analysis.scripts, [],
    exclude_binaries=True,
    name='Project-Meridian-Launcher',
    console=False,
    debug=False,
    strip=False,
    upx=False,
    icon=str(repository / 'launcher/meridian.ico'),
    version=str(repository / 'launcher/build/version_info.txt'),
)
bundle = COLLECT(executable, analysis.binaries, analysis.datas, strip=False, upx=False, name='app')
