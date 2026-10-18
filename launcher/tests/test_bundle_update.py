import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
import self_update as updater
from incremental import sha256


class BundleUpdateTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.installed = self.root / 'Launcher with spaces'
        self.installed.mkdir()
        (self.installed / 'Project-Meridian-Launcher.exe').write_bytes(b'old executable')
        (self.installed / '_internal').mkdir()
        (self.installed / '_internal/runtime.dll').write_bytes(b'old runtime')
        (self.installed / 'unins000.dat').write_bytes(b'uninstall data')
        self.archive = self.root / 'update.zip'
        self.payload = {'Project-Meridian-Launcher.exe': b'new executable',
                        '_internal/runtime.dll': b'new runtime'}
        self.write_archive()

    def write_archive(self, extra=None):
        import hashlib
        metadata = {'schema': 1, 'product': 'Project Meridian Launcher', 'version': '2.0.0',
                    'files': {name: hashlib.sha256(data).hexdigest() for name, data in self.payload.items()}}
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for name, data in self.payload.items():
                archive.writestr(name, data)
            archive.writestr('bundle.json', json.dumps(metadata))
            for name, data in (extra or {}).items():
                archive.writestr(name, data)

    def replace(self, launch=None, probe=None):
        self.assertTrue(hasattr(updater, 'replace_bundle'), 'Whole-folder updates are missing')
        return updater.replace_bundle(self.archive, self.installed, sha256(self.archive),
                                      launch=launch or (lambda command: None),
                                      probe=probe or (lambda executable: None))

    def test_replaces_complete_bundle_and_preserves_uninstaller(self):
        launches = []
        self.replace(launch=launches.append)
        self.assertEqual((self.installed / '_internal/runtime.dll').read_bytes(), b'new runtime')
        self.assertEqual((self.installed / 'unins000.dat').read_bytes(), b'uninstall data')
        self.assertEqual(launches, [[str(self.installed / 'Project-Meridian-Launcher.exe')]])
        self.assertEqual((self.installed.with_name(self.installed.name + '.previous') /
                          '_internal/runtime.dll').read_bytes(), b'old runtime')

    def test_wrapped_distribution_reads_its_own_metadata(self):
        with zipfile.ZipFile(self.archive) as archive:
            entries = {name: archive.read(name) for name in archive.namelist()}
        with zipfile.ZipFile(self.archive, 'w') as archive:
            archive.writestr('Project-Meridian-Launcher.exe', b'stable bootstrap')
            for name, data in entries.items():
                archive.writestr('app/' + name, data)
        try:
            self.replace()
        except KeyError as error:
            self.fail(f'Wrapped payload metadata was not read: {error}')
        self.assertEqual((self.installed / '_internal/runtime.dll').read_bytes(), b'new runtime')

    def test_failed_startup_restores_executable_and_dependencies(self):
        def fail(executable):
            raise OSError('new application cannot start')
        with self.assertRaises(OSError):
            self.replace(probe=fail)
        self.assertEqual((self.installed / 'Project-Meridian-Launcher.exe').read_bytes(), b'old executable')
        self.assertEqual((self.installed / '_internal/runtime.dll').read_bytes(), b'old runtime')

    def test_bad_bundle_hash_never_touches_installation(self):
        self.assertTrue(hasattr(updater, 'replace_bundle'), 'Whole-folder updates are missing')
        with self.assertRaises(ValueError):
            updater.replace_bundle(self.archive, self.installed, '0' * 64)
        self.assertEqual((self.installed / '_internal/runtime.dll').read_bytes(), b'old runtime')

    def test_unlisted_payload_and_traversal_are_rejected(self):
        for name in ('../outside', 'extra.dll', '_internal/CON.dll'):
            with self.subTest(name=name):
                self.write_archive({name: b'untrusted'})
                with self.assertRaises(ValueError):
                    self.replace()
                self.assertEqual((self.installed / '_internal/runtime.dll').read_bytes(), b'old runtime')

    def test_game_data_directory_is_never_swapped(self):
        (self.installed / 'instance').mkdir()
        (self.installed / 'instance/world').write_bytes(b'player world')
        with self.assertRaises(ValueError):
            self.replace()
        self.assertEqual((self.installed / 'instance/world').read_bytes(), b'player world')

    def test_interrupted_swap_leaves_a_durable_recovery_marker(self):
        script = self.root / 'interrupted_update.py'
        script.write_text("import os,sys\nfrom pathlib import Path\n"
                          f"sys.path.insert(0, {str(Path(updater.__file__).parent)!r})\nimport self_update\n"
                          "original=os.replace\n"
                          "def interrupted(source,destination):\n    original(source,destination)\n"
                          f"    if str(source)=={str(self.installed.resolve())!r}: os._exit(77)\n"
                          "os.replace=interrupted\n"
                          f"self_update.replace_bundle({str(self.archive)!r}, {str(self.installed)!r}, {sha256(self.archive)!r}, launch=lambda command:None, probe=lambda executable:None)\n")
        result = subprocess.run([sys.executable, str(script)], timeout=10)
        self.assertEqual(result.returncode, 77)
        self.assertFalse(self.installed.exists())
        self.assertTrue(self.installed.with_name(self.installed.name + '.update-pending').exists(),
                        'A power interruption leaves no recovery marker')

    def test_interrupted_launch_failure_rollback_remains_recoverable(self):
        script = self.root / 'interrupted_rollback.py'
        script.write_text("import os,sys\n"
                          f"sys.path.insert(0, {str(Path(updater.__file__).parent)!r})\nimport self_update\n"
                          "original=os.replace\n"
                          "def interrupted(source,destination):\n    original(source,destination)\n"
                          "    if str(destination).endswith('failed'): os._exit(77)\n"
                          "def failed_launch(command):\n    raise OSError('cannot start new app')\n"
                          "os.replace=interrupted\n"
                          f"self_update.replace_bundle({str(self.archive)!r}, {str(self.installed)!r}, {sha256(self.archive)!r}, launch=failed_launch, probe=lambda executable:None)\n")
        result = subprocess.run([sys.executable, str(script)], timeout=10)
        self.assertEqual(result.returncode, 77)
        self.assertFalse(self.installed.exists())
        self.assertTrue(self.installed.with_name(self.installed.name + '.update-pending').exists(),
                        'Interrupted rollback lost its recovery marker')


if __name__ == '__main__':
    unittest.main()
