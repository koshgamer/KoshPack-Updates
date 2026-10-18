import hashlib
import http.server
import threading
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
try:
    import incremental as U
except ImportError:
    U = None

class IncrementalTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(U, 'Incremental updater is not implemented')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'instance'
        self.root.mkdir()
        self.cache = self.base / 'cache'
        self.zip = self.base / 'pack.zip'
        self.data = {'mods/same.jar': b'same', 'mods/new.jar': b'new' * 100,
                     'config/test.txt': b'new config', 'options.txt': b'default'}
        with zipfile.ZipFile(self.zip, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, data in self.data.items():
                z.writestr('.minecraft/' + name, data)
        self.index = U.build_index(self.zip, 'https://example.com/pack.zip')
        self.downloads = []
    def write(self, name, data):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    def fetch(self, url, offset, length, total):
        self.downloads.append((offset, length))
        with self.zip.open('rb') as f:
            f.seek(offset)
            return f.read(length)
    def sync(self, previous=()):
        return U.sync_pack(self.index, self.root, list(previous), self.cache,
                           lambda p: p == 'options.txt', self.fetch)
    def test_only_changed_bytes_and_preserve_unknown(self):
        self.write('mods/same.jar', b'same')
        self.write('mods/old.jar', b'old')
        self.write('mods/personal.jar', b'personal')
        self.write('options.txt', b'my settings')
        managed, hashes = self.sync(['mods/same.jar', 'mods/old.jar'])
        self.assertEqual(len(self.downloads), 2)
        self.assertLess(sum(n for _, n in self.downloads), self.zip.stat().st_size)
        self.assertEqual((self.root/'options.txt').read_bytes(), b'my settings')
        self.assertEqual((self.root/'mods/personal.jar').read_bytes(), b'personal')
        self.assertFalse((self.root/'mods/old.jar').exists())
        self.assertEqual((self.root/'mods/new.jar').read_bytes(), self.data['mods/new.jar'])
        self.assertNotIn('options.txt', hashes)
        self.downloads.clear()
        self.sync(managed)
        self.assertEqual(self.downloads, [])
    def test_corrupt_download_keeps_previous_install(self):
        self.write('config/test.txt', b'old')
        self.write('mods/old.jar', b'old')
        self.fetch = lambda *args: b'bad'
        with self.assertRaises(Exception):
            self.sync(['mods/old.jar'])
        self.assertEqual((self.root/'config/test.txt').read_bytes(), b'old')
        self.assertTrue((self.root/'mods/old.jar').exists())
    def test_path_and_case_collisions_rejected(self):
        for path in ('../escape', 'C:/x', 'mods/a:stream', 'mods/CON.jar', 'mods/a.'): 
            with self.subTest(path=path):
                index = json.loads(json.dumps(self.index))
                index['files'][0]['path'] = path
                with self.assertRaises(ValueError):
                    U.validate_index(index)
        index = json.loads(json.dumps(self.index))
        index['files'].append(dict(index['files'][0], path=index['files'][0]['path'].upper()))
        with self.assertRaises(ValueError): U.validate_index(index)
    def test_failed_apply_rolls_back(self):
        self.write('config/test.txt', b'old')
        original = U.atomic_copy
        def fail(src, dst):
            if str(src).endswith('.blob') and Path(dst).as_posix().endswith('mods/new.jar'):
                raise OSError('simulated disk failure')
            return original(src, dst)
        with patch.object(U, 'atomic_copy', side_effect=fail):
            with self.assertRaises(OSError): self.sync()
        self.assertEqual((self.root/'config/test.txt').read_bytes(), b'old')
        self.assertFalse((self.root/'mods/new.jar').exists())

    def test_resume_space_check_uses_remaining_download_bytes(self):
        self.assertTrue(hasattr(U, 'range_cache_path'), 'Reusable download space is not accounted for')
        self.cache.mkdir()
        entry = self.index['files'][0]
        partial = U.range_cache_path(self.index, entry, self.cache)
        with self.zip.open('rb') as archive:
            archive.seek(entry['offset'])
            compressed = archive.read(entry['length'])
        partial.write_bytes(compressed[:-1])
        required = sum(item['size'] * 2 + item['length'] for item in self.index['files'])
        free = 64 * 1024 * 1024 + required - len(compressed[:-1])
        def complete(url, offset, length, total, destination):
            destination.write_bytes(self.fetch(url, offset, length, total))
        with patch.object(U.shutil, 'disk_usage', return_value=type('Usage', (), {'free': free})()), \
             patch.object(U, 'download_range', side_effect=complete):
            U.sync_pack(self.index, self.root, [], self.cache, lambda name: False)
        self.assertEqual((self.root / 'mods/new.jar').read_bytes(), self.data['mods/new.jar'])
    def test_pending_transaction_recovered_before_retry(self):
        self.write('config/test.txt', b'partial')
        tx = self.cache / 'transaction'
        (tx/'backup/config').mkdir(parents=True)
        (tx/'backup/config/test.txt').write_bytes(b'old')
        (tx/'journal.json').write_text(json.dumps({'root':str(self.root.resolve()),
            'files': {'config/test.txt': True, 'mods/new.jar': False}}))
        self.write('mods/new.jar', b'partial')
        U.recover(self.root, self.cache)
        self.assertEqual((self.root/'config/test.txt').read_bytes(), b'old')
        self.assertFalse((self.root/'mods/new.jar').exists())
    def test_symlink_escape_rejected(self):
        outside = self.base / 'outside'
        outside.mkdir()
        try: (self.root/'mods').symlink_to(outside, target_is_directory=True)
        except OSError: self.skipTest('symlinks unavailable')
        with self.assertRaises(ValueError): self.sync()
        self.assertEqual(list(outside.iterdir()), [])


class RangeTests(unittest.TestCase):
    def test_interrupted_file_resumes_from_saved_bytes(self):
        self.assertTrue(hasattr(U, 'download_range'), 'Persistent per-file downloads are missing')
        payload = b'0123456789'
        requests = []
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                requested = self.headers['Range']
                requests.append(requested)
                start, end = map(int, requested[6:].split('-'))
                self.send_response(206)
                self.send_header('Content-Range', f'bytes {start}-{end}/{len(payload)}')
                self.send_header('Content-Length', str(end - start + 1))
                self.end_headers()
                self.wfile.write(payload[start:start + 3] if len(requests) == 1 else payload[start:end + 1])
                self.wfile.flush()
                self.close_connection = True
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as folder:
                partial = Path(folder) / 'range.part'
                url = f'http://127.0.0.1:{server.server_port}'
                with self.assertRaises(OSError):
                    U.download_range(url, 2, 6, 10, partial, attempts=1)
                self.assertEqual(partial.read_bytes(), b'234')
                U.download_range(url, 2, 6, 10, partial, attempts=1)
                self.assertEqual(partial.read_bytes(), b'234567')
                self.assertEqual(requests, ['bytes=2-7', 'bytes=5-7'])
        finally:
            server.shutdown()
            server.server_close()

    def test_bounded_range_and_refusal_to_download_full_archive(self):
        self.assertIsNotNone(U)
        payload=b'0123456789'
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                if self.path=='/ignore':
                    self.send_response(200); self.end_headers(); self.wfile.write(payload); return
                self.send_response(206)
                self.send_header('Content-Range','bytes 2-4/10')
                self.end_headers(); self.wfile.write(payload[2:5])
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            url=f'http://127.0.0.1:{server.server_port}'
            self.assertEqual(U.fetch_range(url,2,3,10),b'234')
            with self.assertRaises(ValueError): U.fetch_range(url+'/ignore',2,3,10)
        finally: server.shutdown();server.server_close()

if __name__ == '__main__': unittest.main()
