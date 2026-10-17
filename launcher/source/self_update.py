"""Windows frozen-executable updater. No shell scripts, elevation or shell quoting."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from incremental import sha256, atomic_copy


def replace_and_restart(staged, target, digest, launch=subprocess.Popen):
    staged, target = Path(staged), Path(target)
    if sha256(staged) != digest: raise ValueError('Новая версия лаунчера повреждена.')
    backup = target.with_suffix('.previous.exe')
    sibling = target.with_suffix('.update.exe')
    atomic_copy(staged, sibling)
    atomic_copy(target, backup)
    try:
        for attempt in range(30):
            try:
                os.replace(sibling, target)
                break
            except PermissionError:
                if attempt == 29: raise
                time.sleep(1)
        try: launch([str(target)])
        except BaseException:
            atomic_copy(backup, target)
            raise
    finally: sibling.unlink(missing_ok=True)


def prepare(staged, digest):
    if os.name != 'nt' or not getattr(sys, 'frozen', False):
        raise RuntimeError('Самообновление доступно в Windows EXE лаунчера.')
    target = Path(sys.executable).resolve()
    if sha256(staged) != digest: raise ValueError('Новая версия лаунчера повреждена.')
    # Check target-directory write access before the running launcher exits.
    with tempfile.TemporaryFile(dir=target.parent): pass
    folder = Path(tempfile.mkdtemp(prefix='MeridianUpdater-'))
    helper = folder/'helper.exe'
    payload = folder/'new.exe'
    shutil.copy2(target, helper)
    shutil.copy2(staged, payload)
    job = folder/'job.json'
    job.write_text(json.dumps({'target':str(target), 'staged':str(payload),
                               'sha256':digest, 'pid':os.getpid()}), encoding='utf-8')
    subprocess.Popen([str(helper), '--apply-self-update', str(job)],
                     creationflags=subprocess.CREATE_NO_WINDOW, close_fds=True)


def apply_job(job_path):
    job_path = Path(job_path)
    try:
        data = json.loads(job_path.read_text('utf-8'))
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x00100000, False, data['pid'])
        if handle:
            try:
                if kernel.WaitForSingleObject(handle, 120000) != 0:
                    raise RuntimeError('Лаунчер не закрылся за две минуты. Повторите обновление.')
            finally: kernel.CloseHandle(handle)
        replace_and_restart(data['staged'], data['target'], data['sha256'])
        Path(data['staged']).unlink(missing_ok=True)
        job_path.unlink(missing_ok=True)
    except Exception as exc:
        (job_path.parent/'error.txt').write_text(str(exc), encoding='utf-8')
        ctypes.windll.user32.MessageBoxW(None, f'Не удалось обновить лаунчер: {exc}\nПрежний EXE сохранён.',
                                        'Project Meridian', 0x10)
        raise
