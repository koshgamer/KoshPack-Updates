"""Verified per-file updates using HTTP ranges of an immutable release ZIP.

The small index is pinned by SHA-256 in the public manifest. File payloads remain
in the ordinary ZIP, keeping old launchers compatible with the same release.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import time
import urllib.request
import zipfile
import zlib


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def safe_path(name):
    if not isinstance(name, str) or not name: raise ValueError('Empty file path')
    parts = name.split('/')
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{p}{i}' for p in ('COM', 'LPT') for i in range(1,10)}
    if any(p in ('', '.', '..') or p.rstrip('. ') != p or
           any(ord(c) < 32 or c in '\\:*?"<>|' for c in p) or
           p.split('.')[0].upper() in reserved for p in parts):
        raise ValueError(f'Unsafe file path: {name}')
    return name


def target(root, name):
    path = root / safe_path(name)
    # Reject reparse/symlink escapes before reading, writing or deleting.
    if not path.resolve().is_relative_to(root.resolve()): raise ValueError(f'Path escapes game folder: {name}')
    for p in (path, *path.parents):
        if p == root.parent: break
        if p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()):
            raise ValueError(f'Linked game path: {name}')
    return path


def validate_index(data):
    if data.get('schema') != 1 or not re.fullmatch('[0-9a-f]{64}', str(data.get('packageSha256', ''))):
        raise ValueError('Invalid file index')
    if not isinstance(data.get('packageSize'), int) or data['packageSize'] <= 0:
        raise ValueError('Invalid package size')
    if not str(data.get('url', '')).startswith('https://'): raise ValueError('HTTPS required')
    if not isinstance(data.get('files'), list) or not data['files']: raise ValueError('Empty file index')
    seen = set()
    for entry in data['files']:
        path = safe_path(entry['path'])
        if path.casefold() in seen: raise ValueError(f'Duplicate file: {path}')
        seen.add(path.casefold())
        if not re.fullmatch('[0-9a-f]{64}', str(entry.get('sha256', ''))): raise ValueError('Invalid file hash')
        if any(type(entry.get(k)) is not int or entry[k] < 0 for k in ('offset', 'length', 'size')):
            raise ValueError('Invalid file range')
        if entry['offset'] + entry['length'] > data['packageSize'] or entry['method'] not in (0, 8):
            raise ValueError('Invalid compression/range')
    return data


def build_index(archive, url):
    archive = Path(archive)
    entries = []
    with zipfile.ZipFile(archive) as z, archive.open('rb') as raw:
        infos = [i for i in z.infolist() if not i.is_dir() and not i.filename.startswith('__MACOSX/')]
        prefix = next((p for p in ('.minecraft/', 'minecraft/') if infos and all(i.filename.startswith(p) for i in infos)), '')
        for i in infos:
            if i.flag_bits & 1: raise ValueError('Encrypted ZIP is unsupported')
            raw.seek(i.header_offset)
            header = raw.read(30)
            if header[:4] != b'PK\x03\x04': raise ValueError('Invalid ZIP local header')
            name_len, extra_len = struct.unpack_from('<HH', header, 26)
            h = hashlib.sha256()
            with z.open(i) as f:
                for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
            entries.append(dict(path=i.filename[len(prefix):], size=i.file_size, sha256=h.hexdigest(),
                                offset=i.header_offset+30+name_len+extra_len, length=i.compress_size,
                                method=i.compress_type))
    return validate_index(dict(schema=1, url=url, packageSha256=sha256(archive),
                               packageSize=archive.stat().st_size, files=entries))


def fetch_range(url, offset, length, total):
    if not length: return b''
    end = offset + length - 1
    request = urllib.request.Request(url, headers={'Range': f'bytes={offset}-{end}',
                                      'Accept-Encoding': 'identity', 'User-Agent': 'ProjectMeridianLauncher/1.1'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=90) as r:
                if r.status != 206 or r.headers.get('Content-Range') != f'bytes {offset}-{end}/{total}':
                    raise ValueError('Сервер не поддержал выборочную загрузку. Полный архив автоматически не скачивается.')
                data = r.read(length + 1)
                if len(data) != length: raise OSError('Incomplete file download')
                return data
        except (OSError, TimeoutError):
            if attempt == 2: raise
            time.sleep(attempt + 1)


def atomic_copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + '.meridian-new')
    try:
        with Path(src).open('rb') as inp, tmp.open('wb') as out:
            shutil.copyfileobj(inp, out, 1024*1024)
            out.flush()
            os.fsync(out.fileno())
        if dst.exists(): dst.chmod(0o666)
        os.replace(tmp, dst)
    finally: tmp.unlink(missing_ok=True)


def recover(root, cache):
    tx = cache / 'transaction'
    journal = tx / 'journal.json'
    if journal.exists():
        data = json.loads(journal.read_text('utf-8'))
        if data['root'] != str(root.resolve()): raise ValueError('Wrong transaction root')
        for name, existed in data['files'].items():
            dst = target(root, name)
            if existed: atomic_copy(tx/'backup'/safe_path(name), dst)
            elif dst.exists():
                dst.chmod(0o666)
                dst.unlink()
    journal.unlink(missing_ok=True)
    if tx.exists(): shutil.rmtree(tx)


def sync_pack(index, root, previous, cache, preserved, fetch=fetch_range, progress=lambda a,b: None):
    validate_index(index)
    root, cache = Path(root), Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    recover(root, cache)
    entries = index['files']
    managed = {e['path']:e['sha256'] for e in entries if not preserved(e['path'])}
    needed = []
    for e in entries:
        dst = target(root, e['path'])
        if preserved(e['path']) and dst.exists(): continue
        if dst.is_file() and sha256(dst) == e['sha256']: continue
        needed.append(e)
    obsolete = [p for p in previous if p not in managed and not preserved(p)]
    for p in obsolete: target(root, p)
    affected = sorted(set([e['path'] for e in needed] + obsolete))
    required = sum(e['size']*2 for e in needed) + sum(target(root,p).stat().st_size for p in affected if target(root,p).is_file())
    if shutil.disk_usage(cache).free < required + 64*1024*1024:
        raise OSError('Недостаточно места для обновления и резервной копии.')
    total = sum(e['length'] for e in needed)
    done = 0
    progress(done, total)
    # All downloads complete and pass hashes before any game file changes.
    for e in needed:
        blob = cache / (e['sha256'] + '.blob')
        if not blob.is_file() or sha256(blob) != e['sha256']:
            raw = fetch(index['url'], e['offset'], e['length'], index['packageSize'])
            if e['method'] == 8:
                dec = zlib.decompressobj(-15)
                data = dec.decompress(raw, e['size']+1)
                if not dec.eof or dec.unused_data or dec.unconsumed_tail:
                    raise ValueError('Invalid compressed file')
            else: data = raw
            if len(data) != e['size'] or hashlib.sha256(data).hexdigest() != e['sha256']:
                raise ValueError(f"Файл повреждён: {e['path']}")
            tmp = blob.with_suffix('.part')
            with tmp.open('wb') as f:
                f.write(data); f.flush(); os.fsync(f.fileno())
            os.replace(tmp, blob)
        done += e['length']
        progress(done, total)
    if not affected: return sorted(managed), managed
    tx = cache/'transaction'
    tx.mkdir()
    existed = {}
    for name in affected:
        dst = target(root, name)
        existed[name] = dst.is_file()
        if dst.exists() and not dst.is_file(): raise ValueError(f'Expected file: {name}')
        if existed[name]: atomic_copy(dst, tx/'backup'/name)
    # Backups are durable before the journal makes the transaction recoverable.
    with (tx/'journal.new').open('w', encoding='utf-8') as f:
        json.dump({'root':str(root.resolve()), 'files':existed}, f)
        f.flush(); os.fsync(f.fileno())
    os.replace(tx/'journal.new', tx/'journal.json')
    try:
        for e in needed: atomic_copy(cache/(e['sha256']+'.blob'), target(root,e['path']))
        for name in obsolete:
            dst = target(root,name)
            if dst.exists(): dst.chmod(0o666); dst.unlink()
    except BaseException:
        recover(root, cache)
        raise
    # Unlink journal first: interruption during cleanup must not restore a partial backup.
    (tx/'journal.json').unlink()
    shutil.rmtree(tx)
    # Successfully applied payloads are no longer needed; interrupted downloads remain reusable.
    for blob in cache.glob('*.blob'): blob.unlink(missing_ok=True)
    return sorted(managed), managed
