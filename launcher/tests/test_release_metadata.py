import copy
import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))


class ReleaseMetadataTests(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).resolve().parents[1] / 'tools/publish_manifest.py'
        self.assertIn('def merge_release(', source.read_text('utf-8'), 'Safe release metadata merging is missing')
        spec = importlib.util.spec_from_file_location('publish_manifest', source)
        self.publisher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.publisher)

    def test_launcher_release_preserves_latest_modpack_and_partial_update_index(self):
        manifest = {'packVersion': 'new-pack', 'package': {'sha256': 'a' * 64},
                    'fileIndex': {'sha256': 'b' * 64}, 'launcherMinVersion': '1.0.2',
                    'launcher': {'version': '1.1.0'}}
        original = copy.deepcopy(manifest)
        metadata = {'version': '2.0.0',
                    'installer': {'file': 'Project-Meridian-Launcher.exe', 'sha256': 'c' * 64, 'size': 10},
                    'bundle': {'file': 'Project-Meridian-Launcher-2.0.0-win64.zip', 'sha256': 'd' * 64, 'size': 20}}
        result = self.publisher.merge_release(manifest, metadata)
        self.assertEqual(manifest, original)
        for key in ('packVersion', 'package', 'fileIndex', 'launcherMinVersion'):
            self.assertEqual(result[key], original[key])
        self.assertEqual(result['launcher']['version'], '2.0.0')
        self.assertIn('/launcher-2.0.0/', result['launcher']['bundle']['url'])
        self.assertTrue(result['launcher']['url'].endswith('.exe'))

    def test_incomplete_release_does_not_change_manifest(self):
        with self.assertRaises(ValueError):
            self.publisher.merge_release({'launcher': {'version': '1.1.0'}}, {'version': '2.0.0'})


if __name__ == '__main__':
    unittest.main()
