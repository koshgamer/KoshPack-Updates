"""Windows frozen-executable updater. No shell scripts, elevation or shell quoting."""
import ctypes
from contextlib import contextmanager
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from incremental import sha256, atomic_copy, safe_path, target

EXECUTABLE = 'Project-Meridian-Launcher.exe'
PRODUCT = 'Project Meridian Launcher'


@contextmanager
def update_lock():
    if os.name != 'nt':
        yield
        return
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.ReleaseMutex.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateMutexW(None, False, 'Local\\ProjectMeridianLauncherUpdate')
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    acquired = False
    try:
        acquired = kernel.WaitForSingleObject(handle, 10000) in (0, 0x80)
        if not acquired:
            raise RuntimeError('Другое обновление ещё выполняется.')
        yield
    finally:
        if acquired:
            kernel.ReleaseMutex(handle)
        kernel.CloseHandle(handle)


def launch_application(command):
    return subprocess.Popen(command, env=dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT='1'),
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                            close_fds=True)


def probe_application(executable):
    with tempfile.TemporaryDirectory(prefix='MeridianUpdateProbe-') as folder:
        environment = dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT='1', LOCALAPPDATA=folder, XDG_DATA_HOME=folder)
        subprocess.run([str(executable), '--smoke-ui'], env=environment, check=True, timeout=60,
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)


def extract_bundle(archive, destination, digest):
    archive, destination = Path(archive), Path(destination)
    if sha256(archive) != digest:
        raise ValueError('Архив лаунчера повреждён.')
    with zipfile.ZipFile(archive) as package:
        members = {}
        seen = set()
        for entry in package.infolist():
            name = safe_path(entry.filename.rstrip('/'))
            if name.casefold() in seen or entry.flag_bits & 1 or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Некорректный файл в архиве лаунчера.')
            seen.add(name.casefold())
            if not entry.is_dir():
                members[name] = entry
        if 'app/bundle.json' in members:
            if {name for name in members if not name.startswith('app/')} != {EXECUTABLE}:
                raise ValueError('Некорректная оболочка комплекта лаунчера.')
            members = {name[4:]: entry for name, entry in members.items() if name.startswith('app/')}
        if 'bundle.json' not in members or members['bundle.json'].file_size > 1024 * 1024:
            raise ValueError('В архиве нет описания комплекта лаунчера.')
        metadata = json.loads(package.read(members['bundle.json']))
        if not isinstance(metadata, dict) or metadata.get('schema') != 1 or metadata.get('product') != PRODUCT:
            raise ValueError('Неверный комплект лаунчера.')
        files = metadata.get('files')
        if not isinstance(files, dict) or EXECUTABLE not in files or not any(name.startswith('_internal/') for name in files):
            raise ValueError('В архиве отсутствуют EXE или зависимости.')
        if set(members) != set(files) | {'bundle.json'}:
            raise ValueError('Состав архива не совпадает с описанием.')
        for name, expected in files.items():
            safe_path(name)
            if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
                raise ValueError('Некорректная контрольная сумма файла.')
        required = sum(entry.file_size for entry in members.values())
        if required > 1024 * 1024 * 1024:
            raise ValueError('Комплект лаунчера слишком велик.')
        destination.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(destination).free < required + 64 * 1024 * 1024:
            raise OSError('Недостаточно места для нового лаунчера.')
        for name, entry in members.items():
            output_path = target(destination, name)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with package.open(entry) as source, output_path.open('wb') as output:
                shutil.copyfileobj(source, output, 1024 * 1024)
            if name != 'bundle.json' and sha256(output_path) != files[name]:
                raise ValueError(f'Файл лаунчера повреждён: {name}')
    return metadata


def replace_bundle(staged, directory, digest, launch=launch_application, probe=probe_application):
    with update_lock():
        _replace_bundle(staged, directory, digest, launch, probe)


def _replace_bundle(staged, directory, digest, launch, probe):
    directory = Path(directory).resolve()
    if directory.parent == directory or not (directory / EXECUTABLE).is_file() or not (directory / '_internal').is_dir():
        raise ValueError('Не найден каталог установленного лаунчера.')
    if (directory / 'instance').exists() or (directory / 'state.json').exists():
        raise ValueError('Каталог программы совпадает с данными игры. Установите лаунчер в отдельную папку.')
    backup = directory.with_name(directory.name + '.previous')
    pending = directory.with_name(directory.name + '.update-pending')
    if pending.exists():
        raise RuntimeError('Запустите лаунчер через основной ярлык для восстановления прерванного обновления.')
    with tempfile.TemporaryDirectory(prefix=directory.name + '-update-', dir=directory.parent) as temporary:
        container = Path(temporary)
        prepared = container / 'new'
        extract_bundle(staged, prepared, digest)
        for uninstaller in directory.glob('unins*'):
            if uninstaller.is_file() and not uninstaller.is_symlink():
                shutil.copy2(uninstaller, prepared / uninstaller.name)
        if backup.exists():
            marker = backup / 'bundle.json'
            if backup.is_symlink() or (hasattr(backup, 'is_junction') and backup.is_junction()) or not marker.is_file() or json.loads(marker.read_text('utf-8')).get('product') != PRODUCT:
                raise ValueError('Каталог резервной копии занят посторонними файлами.')
            shutil.rmtree(backup)
        temporary_marker = pending.with_suffix('.new')
        with temporary_marker.open('w', encoding='utf-8') as marker:
            marker.write(PRODUCT)
            marker.flush()
            os.fsync(marker.fileno())
        os.replace(temporary_marker, pending)
        for attempt in range(30):
            try:
                os.replace(directory, backup)
                break
            except PermissionError:
                if attempt == 29:
                    raise
                time.sleep(1)
        try:
            os.replace(prepared, directory)
            probe(directory / EXECUTABLE)
            launch([str(directory / EXECUTABLE)])
            pending.unlink()
        except BaseException:
            if directory.exists():
                os.replace(directory, container / 'failed')
            os.replace(backup, directory)
            pending.unlink(missing_ok=True)
            raise


def prepare_bundle(staged, digest):
    if os.name != 'nt' or not getattr(sys, 'frozen', False):
        raise RuntimeError('Самообновление доступно в Windows EXE лаунчера.')
    directory = Path(sys.executable).resolve().parent
    if (directory / 'instance').exists() or (directory / 'state.json').exists():
        raise RuntimeError('Каталог программы совпадает с данными игры. Запустите установщик повторно.')
    metadata = json.loads((directory / 'bundle.json').read_text('utf-8'))
    if metadata.get('product') != PRODUCT or not (directory / '_internal').is_dir():
        raise RuntimeError('Используйте установленную версию лаунчера.')
    with tempfile.TemporaryFile(dir=directory.parent):
        pass
    folder = Path(tempfile.mkdtemp(prefix='MeridianUpdater-'))
    extract_bundle(staged, folder / 'verified', digest)
    shutil.rmtree(folder / 'verified')
    helper_folder = folder / 'helper'
    helper_folder.mkdir()
    for name, expected in metadata['files'].items():
        source = target(directory, name)
        if sha256(source) != expected:
            raise ValueError(f'Текущий лаунчер повреждён: {name}. Запустите установщик повторно.')
        atomic_copy(source, target(helper_folder, name))
    atomic_copy(directory / 'bundle.json', helper_folder / 'bundle.json')
    payload = folder / 'update.zip'
    atomic_copy(staged, payload)
    job = folder / 'job.json'
    job.write_text(json.dumps({'kind': 'bundle', 'target': str(directory), 'staged': str(payload),
                               'sha256': digest, 'pid': os.getpid()}), encoding='utf-8')
    helper = launch_application([str(helper_folder / EXECUTABLE), '--apply-self-update', str(job)])
    deadline = time.monotonic() + 15
    while not job.with_suffix('.ready').exists():
        if helper.poll() is not None or time.monotonic() >= deadline:
            if helper.poll() is None:
                helper.terminate()
                helper.wait(timeout=5)
            raise RuntimeError('Помощник обновления не запустился. Лаунчер оставлен открытым.')
        time.sleep(0.05)


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
    with update_lock():
        _apply_job(job_path)


def _apply_job(job_path):
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
        if not handle and ctypes.get_last_error() != 87:
            raise ctypes.WinError(ctypes.get_last_error())
        job_path.with_suffix('.ready').touch()
        if handle:
            try:
                if kernel.WaitForSingleObject(handle, 120000) != 0:
                    raise RuntimeError('Лаунчер не закрылся за две минуты. Повторите обновление.')
            finally: kernel.CloseHandle(handle)
        if data.get('kind') == 'bundle':
            replace_bundle(data['staged'], data['target'], data['sha256'])
        else:
            replace_and_restart(data['staged'], data['target'], data['sha256'])
        Path(data['staged']).unlink(missing_ok=True)
        job_path.unlink(missing_ok=True)
    except Exception as exc:
        (job_path.parent/'error.txt').write_text(str(exc), encoding='utf-8')
        if 'data' in locals() and data.get('kind') == 'bundle':
            executable = Path(data['target']) / EXECUTABLE
            if executable.is_file():
                launch_application([str(executable)])
        ctypes.windll.user32.MessageBoxW(None, f'Не удалось обновить лаунчер: {exc}\nПодробности: {job_path.parent / "error.txt"}',
                                        'Project Meridian', 0x10)
        raise
