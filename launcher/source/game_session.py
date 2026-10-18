from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time


SECRET_PATTERNS = (
    re.compile(r"eyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]{8,}"),
    re.compile(r"(?i)((?:access|refresh|xbl|xsts|mc)[_-]?token[\"'=: ]+)[^\s\"',]+"),
    re.compile(r"(?i)(--accessToken\s+)\S+"),
)


def mask_secrets(text):
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(lambda match: (match.group(1) if match.groups() else '') + '***', text)
    return text


def write_status(path, data):
    temporary = path.with_suffix('.new')
    with temporary.open('w', encoding='utf-8') as output:
        json.dump(data, output, ensure_ascii=False)
        output.flush()
        os.fsync(output.fileno())
    for attempt in range(30):
        try:
            os.replace(temporary, path)
            break
        except PermissionError:
            if attempt == 29:
                raise
            time.sleep(0.05)


class GameLogTail:
    def __init__(self, path):
        self.path = Path(path)
        self.position = 0
        self.identity = None
        self.prefix = b''
        try:
            with self.path.open('rb') as source:
                metadata = os.fstat(source.fileno())
                self.identity = (metadata.st_dev, metadata.st_ino)
                self.prefix = source.read(512)
                self.position = metadata.st_size
        except OSError:
            pass

    def read_lines(self):
        lines = []
        try:
            with self.path.open('rb') as source:
                metadata = os.fstat(source.fileno())
                identity = (metadata.st_dev, metadata.st_ino)
                if (identity != self.identity or metadata.st_size < self.position
                        or source.read(len(self.prefix)) != self.prefix):
                    self.position = 0
                self.identity = identity
                source.seek(0)
                self.prefix = source.read(512)
                source.seek(self.position)
                for _ in range(4096):
                    line = source.readline()
                    if not line or not line.endswith(b'\n'):
                        break
                    self.position = source.tell()
                    lines.append(line.decode('utf-8', errors='replace').rstrip('\r\n'))
        except OSError:
            pass
        return lines


class StartupState:
    def __init__(self, grace=3):
        self.grace = grace
        self.pid = None
        self.candidate = None
        self.exit_code = None
        self.error = ''

    def observe(self, parts, now):
        if not parts:
            return
        code = parts[0]
        if code == 'launched':
            try:
                self.pid = int(parts[1])
                if self.pid <= 0:
                    raise ValueError('Invalid process ID')
            except (IndexError, ValueError):
                self.error = 'PortableMC не сообщил процесс Minecraft.'
        elif code == 'terminated':
            try:
                self.exit_code = int(parts[1])
            except (IndexError, ValueError):
                self.exit_code = 1
        elif code.startswith('error_'):
            self.error = ' | '.join(parts)
        elif code in ('log_raw', 'log_xml'):
            message = parts[5] if code == 'log_xml' and len(parts) >= 6 else ' '.join(parts[1:])
            render_thread = (code == 'log_xml' and len(parts) >= 6 and parts[4] == 'Render thread') or '[Render thread/' in message
            if (code == 'log_xml' and len(parts) > 1 and parts[1] == 'fatal') or any(
                marker in message for marker in ('Reported exception thrown!', 'Mod loading has failed',
                                                  'Failed to load mods', 'A detailed walkthrough of the error')):
                self.error = message
            ready = 'ScreenCustomizationLayer registered: title_screen' in message or (
                re.search(r'Game took [\d.,]+ seconds to start', message) is not None)
            if render_thread and ready and self.pid and self.candidate is None:
                self.candidate = now

    def can_close(self, now):
        return (bool(self.pid) and self.candidate is not None and not self.error
                and self.exit_code is None and now - self.candidate >= self.grace)


def supervise(command, cwd, log_path, events_path, status_path, grace=3, game_log=None):
    state = StartupState(grace)
    game_output = GameLogTail(game_log) if game_log is not None else None
    write_status(status_path, {'state': 'starting'})
    process = subprocess.Popen(command, cwd=str(cwd), stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding='utf-8', errors='replace', bufsize=1,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    incoming = queue.Queue()

    def read_output():
        try:
            for line in process.stdout:
                incoming.put(line)
        finally:
            incoming.put(None)

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    ended = False
    confirmed = False
    reported_error = False
    with Path(log_path).open('a', encoding='utf-8') as log, Path(events_path).open('w', encoding='utf-8') as events:
        log.write('\n===== Project Meridian game session =====\n')
        while not ended or process.poll() is None:
            try:
                line = incoming.get(timeout=0.05)
            except queue.Empty:
                line = ''
            if line is None:
                ended = True
            elif line:
                clean = mask_secrets(line.rstrip('\r\n'))
                log.write(clean + '\n')
                log.flush()
                parts = clean.split('\t')
                state.observe(parts, time.monotonic())
                if not confirmed:
                    events.write(json.dumps(parts, ensure_ascii=False) + '\n')
                    events.flush()
            if not confirmed and game_output is not None and state.pid:
                for message in game_output.read_lines():
                    clean = mask_secrets(message)
                    parts = ['log_raw', clean]
                    state.observe(parts, time.monotonic())
                    log.write(clean + '\n')
                    events.write(json.dumps(parts, ensure_ascii=False) + '\n')
                log.flush()
                events.flush()
            if not confirmed and state.error and not reported_error:
                write_status(status_path, {'state': 'error', 'message': state.error, 'exit_code': state.exit_code})
                reported_error = True
            if not confirmed and state.can_close(time.monotonic()) and process.poll() is None:
                confirmed = True
                write_status(status_path, {'state': 'ready', 'pid': state.pid})
    reader.join()
    process.stdout.close()
    portable_code = process.wait()
    exit_code = state.exit_code if state.exit_code is not None else portable_code
    failed = bool(state.error) or exit_code != 0
    write_status(status_path, {'state': 'error' if failed else 'exited', 'exit_code': exit_code,
                              'message': state.error or (f'Minecraft завершился с кодом {exit_code}.' if failed else '')})
    return 1 if failed else 0


def start(command, cwd, log_path, game_log=None):
    root = Path(cwd) / 'sessions'
    root.mkdir(exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix='game-', dir=root))
    job = folder / 'job.json'
    job.write_text(json.dumps({'command': command, 'cwd': str(cwd), 'log': str(log_path),
                               'game_log': str(game_log) if game_log is not None else None}), encoding='utf-8')
    if getattr(sys, 'frozen', False):
        helper = [sys.executable, '--game-session', str(job)]
    else:
        helper = [sys.executable, str(Path(__file__).resolve()), str(job)]
    environment = dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT='1')
    with (folder / 'helper-error.log').open('w', encoding='utf-8') as errors:
        process = subprocess.Popen(helper, cwd=str(cwd), stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=errors, env=environment,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                                   start_new_session=os.name != 'nt', close_fds=True)
    return process, folder


def wait_for_start(process, folder, on_event):
    position = 0
    error_reported = False
    while True:
        events_path = folder / 'events.jsonl'
        if events_path.exists():
            with events_path.open('r', encoding='utf-8') as events:
                events.seek(position)
                while True:
                    line = events.readline()
                    if not line or not line.endswith('\n'):
                        break
                    on_event(json.loads(line))
                    position = events.tell()
        status_path = folder / 'status.json'
        if status_path.exists():
            status = json.loads(status_path.read_text('utf-8'))
            if status['state'] == 'ready' and process.poll() is None:
                return True
            if status['state'] == 'error':
                message = status.get('message') or f"Minecraft завершился с кодом {status.get('exit_code')}."
                if status.get('exit_code') is not None or process.poll() is not None:
                    raise RuntimeError(message)
                if not error_reported:
                    on_event(['error_session', message])
                    error_reported = True
            if status['state'] == 'exited':
                return False
        if process.poll() is not None:
            raise RuntimeError('Не удалось запустить наблюдение за Minecraft. Откройте журнал диагностики.')
        time.sleep(0.1)


def main(job_path):
    job_path = Path(job_path)
    status_path = job_path.parent / 'status.json'
    try:
        job = json.loads(job_path.read_text('utf-8'))
        return supervise(job['command'], Path(job['cwd']), Path(job['log']),
                         job_path.parent / 'events.jsonl', status_path, grace=job.get('grace', 3),
                         game_log=job.get('game_log'))
    except Exception as error:
        write_status(status_path, {'state': 'error', 'message': mask_secrets(str(error))})
        return 1
    finally:
        job_path.unlink(missing_ok=True)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
