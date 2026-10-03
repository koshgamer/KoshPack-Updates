import hashlib
import importlib.util
import json
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile


spec = importlib.util.spec_from_file_location("launcher_restore_test", Path(__file__).with_name("launcher.py"))
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class DevExtraRestoreTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        launcher.INSTANCE_DIR = root / "instance"
        launcher.CACHE_DIR = root / "cache"
        launcher.DEV_EXTRA_BACKUP_DIR = root / "backup"
        launcher.DEV_EXTRA_TRACK_FILE = root / "tracked.json"
        launcher.CACHE_DIR.mkdir()

    def install(self, rel, data):
        digest = hashlib.sha256(data).hexdigest()
        (launcher.CACHE_DIR / f"dev-extra-{digest[:16]}-{Path(rel).name}").write_bytes(data)
        return launcher.install_dev_extras({"extras": [{"path": rel, "url": "https://unused.invalid/fixture",
                                                       "sha256": digest, "size": len(data)}]})

    def test_update_of_introduced_dev_file_does_not_become_a_stable_backup(self):
        rel = "kubejs/client_scripts/test_dev_only.js"
        self.install(rel, b"dev-v1")
        self.install(rel, b"dev-v2")
        self.assertFalse((launcher.DEV_EXTRA_BACKUP_DIR / rel).exists())
        launcher.restore_stable_dev_extras()
        self.assertFalse((launcher.INSTANCE_DIR / rel).exists())

    def test_existing_stable_script_is_restored_after_multiple_dev_updates(self):
        rel = "kubejs/server_scripts/test_stable.js"
        target = launcher.INSTANCE_DIR / rel
        target.parent.mkdir(parents=True)
        target.write_bytes(b"stable-original")
        self.install(rel, b"dev-v1")
        self.install(rel, b"dev-v2")
        launcher.restore_stable_dev_extras()
        self.assertEqual(target.read_bytes(), b"stable-original")

    def test_unchanged_introduced_file_keeps_its_cleanup_tracking(self):
        rel = "mods/test_dev_only.jar"
        self.install(rel, b"dev-v1")
        self.assertEqual(self.install(rel, b"dev-v1"), [rel])
        self.assertEqual(json.loads(launcher.DEV_EXTRA_TRACK_FILE.read_text())["paths"], [rel])
        launcher.restore_stable_dev_extras()
        self.assertFalse((launcher.INSTANCE_DIR / rel).exists())

    def mod_jar(self, filename, mod_id):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as jar:
            jar.writestr('META-INF/neoforge.mods.toml', f'[[mods]]\nmodId="{mod_id}"\nversion="1.0"\n')
        target = launcher.INSTANCE_DIR / 'mods' / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data.getvalue())
        return target, data.getvalue()

    def test_removed_mod_restores_exact_original_after_repeated_dev_updates(self):
        target, original = self.mod_jar('enchant-custom-version.jar', 'enchantmentlibrary')
        manifest = {'removedModIds': ['enchantmentlibrary']}
        self.assertEqual(launcher.install_dev_extras(manifest), ['mods/enchant-custom-version.jar'])
        self.assertFalse(target.exists())
        self.assertEqual(launcher.install_dev_extras(manifest), ['mods/enchant-custom-version.jar'])
        launcher.restore_stable_dev_extras()
        self.assertEqual(target.read_bytes(), original)

    def test_only_removed_mod_ids_are_affected_not_other_create_dependencies(self):
        removed, _ = self.mod_jar('different-name.jar', 'create_enchantment_industry')
        kept, original = self.mod_jar('CreateDragonsPlus.jar', 'create_dragons_plus')
        launcher.install_dev_extras({'removedModIds': ['create_enchantment_industry']})
        self.assertFalse(removed.exists())
        self.assertEqual(kept.read_bytes(), original)

    def test_manifest_reader_preserves_removed_mod_policy(self):
        manifest = {'armor': {'version': 'test', 'sha256': 'a' * 64},
                    'removedModIds': ['create_enchantment_industry', 'enchantmentlibrary']}
        with patch.object(launcher, 'request_json', return_value=manifest):
            self.assertEqual(launcher.get_dev_armor_manifest()['removedModIds'], manifest['removedModIds'])

    def test_invalid_removal_policy_fails_before_touching_files(self):
        target, original = self.mod_jar('test.jar', 'enchantmentlibrary')
        for invalid in ('../saves', 'minecraft', 'neoforge', ['../saves'], ['minecraft'], ['neoforge']):
            with self.assertRaises(RuntimeError):
                launcher.install_dev_extras({'removedModIds': invalid})
            self.assertEqual(target.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
