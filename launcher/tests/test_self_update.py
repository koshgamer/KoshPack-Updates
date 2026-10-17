from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'source'))
try: import self_update as U
except ImportError: U = None

class SelfUpdateTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(U, 'Self update is not implemented')
        self.t = tempfile.TemporaryDirectory(); self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.old = self.root/'Launcher with spaces.exe'; self.old.write_bytes(b'old')
        self.new = self.root/'new.exe'; self.new.write_bytes(b'new')
    def test_verified_replacement_and_restart(self):
        launches=[]
        U.replace_and_restart(self.new, self.old, U.sha256(self.new), launches.append)
        self.assertEqual(self.old.read_bytes(), b'new')
        self.assertEqual(launches, [[str(self.old)]])
        self.assertEqual(self.old.with_suffix('.previous.exe').read_bytes(), b'old')
    def test_bad_hash_never_replaces(self):
        with self.assertRaises(ValueError): U.replace_and_restart(self.new,self.old,'0'*64,lambda _:None)
        self.assertEqual(self.old.read_bytes(), b'old')
    def test_restart_failure_restores_old_executable(self):
        def fail(_): raise OSError('cannot start')
        with self.assertRaises(OSError): U.replace_and_restart(self.new,self.old,U.sha256(self.new),fail)
        self.assertEqual(self.old.read_bytes(), b'old')

if __name__ == '__main__': unittest.main()
