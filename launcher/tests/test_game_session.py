import json
import os
import queue
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
try:
    import game_session as session
except ImportError:
    session = None


class GameSessionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(session, 'Independent game-session monitoring is missing')
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)

    def test_process_creation_does_not_confirm_startup(self):
        state = session.StartupState(grace=0.1)
        state.observe(['launched', '123'], 0)
        self.assertFalse(state.can_close(20))
        state.observe(['log_xml', 'info', '', 'Window', 'Render thread', 'OpenGL ready'], 1)
        self.assertFalse(state.can_close(20))

    def test_title_screen_requires_stable_startup(self):
        state = session.StartupState(grace=3)
        state.observe(['launched', '123'], 0)
        state.observe(['log_xml', 'info', '', 'FancyMenu', 'Render thread',
                       '[FANCYMENU] ScreenCustomizationLayer registered: title_screen'], 1)
        self.assertFalse(state.can_close(3))
        self.assertTrue(state.can_close(4))

    def test_early_crash_cancels_pending_close(self):
        state = session.StartupState(grace=3)
        state.observe(['launched', '123'], 0)
        state.observe(['log_raw', '[Render thread/WARN] [ModernFix]: Game took 55.1 seconds to start'], 1)
        state.observe(['terminated', '42'], 2)
        self.assertFalse(state.can_close(30))
        self.assertEqual(state.exit_code, 42)

    def test_portablemc_error_cancels_pending_close(self):
        state = session.StartupState(grace=0)
        state.observe(['launched', '123'], 0)
        state.observe(['log_raw', '[Render thread/WARN] [ModernFix]: Game took 55.1 seconds to start'], 1)
        state.observe(['error_launch', 'missing java'], 1)
        self.assertFalse(state.can_close(30))

    def test_wrapped_stdout_preserves_render_thread_readiness(self):
        state = session.StartupState(grace=3)
        state.observe(['launched', '123'], 0)
        state.observe(['log_xml', 'info', '', '', '_stdout_',
                       '[11:24:36] [Render thread/INFO] [FancyMenu]: '
                       'ScreenCustomizationLayer registered: title_screen'], 1)
        self.assertTrue(state.can_close(4))

    def test_current_game_log_confirms_readiness_without_console_marker(self):
        game_log = self.root / 'latest.log'
        game_log.write_text('[old] [Render thread/INFO] ScreenCustomizationLayer registered: title_screen\n')
        status_path = self.root / 'status.json'
        confirmed = self.root / 'confirmed'
        premature = self.root / 'premature'
        game = self.root / 'file_logging_game.py'
        game.write_text(
            'import json,pathlib,time\n'
            f'status=pathlib.Path({str(status_path)!r})\n'
            f'game_log=pathlib.Path({str(game_log)!r})\n'
            "print('launched\\t123', flush=True)\n"
            'deadline=time.monotonic()+0.3\n'
            'while time.monotonic()<deadline:\n'
            "    if json.loads(status.read_text())['state']=='ready':\n"
            f'        pathlib.Path({str(premature)!r}).touch()\n'
            '    time.sleep(0.01)\n'
            "game_log.write_text('[new] [Render thread/INFO] ScreenCustomizationLayer registered: title_screen\\n')\n"
            'deadline=time.monotonic()+0.8\n'
            'while time.monotonic()<deadline:\n'
            "    if json.loads(status.read_text())['state']=='ready':\n"
            f'        pathlib.Path({str(confirmed)!r}).touch()\n'
            '        break\n'
            '    time.sleep(0.01)\n'
            "print('terminated\\t0', flush=True)\n")
        job = self.root / 'job.json'
        job.write_text(json.dumps({'command': [sys.executable, str(game)], 'cwd': str(self.root),
                                   'log': str(self.root / 'game.log'), 'game_log': str(game_log),
                                   'grace': 0.05}))
        self.assertEqual(session.main(job), 0)
        self.assertFalse(premature.exists(), 'An old menu log closed the launcher before the current game loaded')
        self.assertTrue(confirmed.exists(), 'The current game reached its menu but readiness was not detected')

    def test_log_tail_skips_old_lines_and_waits_for_complete_records(self):
        path = self.root / 'latest.log'
        path.write_text('old menu\n')
        tail = session.GameLogTail(path)
        self.assertEqual(tail.read_lines(), [])
        with path.open('a') as output:
            output.write('current\npartial')
        self.assertEqual(tail.read_lines(), ['current'])
        self.assertEqual(tail.read_lines(), [])
        with path.open('a') as output:
            output.write(' record\n')
        self.assertEqual(tail.read_lines(), ['partial record'])

    def test_log_tail_handles_creation_replacement_and_truncation(self):
        path = self.root / 'latest.log'
        tail = session.GameLogTail(path)
        self.assertEqual(tail.read_lines(), [])
        path.write_text('first game\n')
        self.assertEqual(tail.read_lines(), ['first game'])
        path.rename(self.root / 'previous.log')
        path.write_text('replacement\n')
        self.assertEqual(tail.read_lines(), ['replacement'])
        path.write_text('new game with a longer first line\n')
        self.assertEqual(tail.read_lines(), ['new game with a longer first line'])
        path.write_text('short\n')
        self.assertEqual(tail.read_lines(), ['short'])

    def test_game_exit_code_is_not_hidden_by_portablemc_success(self):
        result = session.supervise(
            [sys.executable, '-c', "print('launched\\t123'); print('terminated\\t42')"],
            self.root, self.root / 'game.log', self.root / 'events.jsonl', self.root / 'status.json',
            grace=0.05)
        self.assertNotEqual(result, 0)
        status = json.loads((self.root / 'status.json').read_text())
        self.assertEqual(status['state'], 'error')
        self.assertEqual(status['exit_code'], 42)

    def test_supervisor_confirms_readiness_and_masks_logs(self):
        script = self.root / 'fake_game.py'
        script.write_text("import time\nprint('launched\\t123', flush=True)\n"
                          "print('log_raw\\t[Render thread/WARN] [ModernFix]: Game took 1 seconds to start', flush=True)\n"
                          "time.sleep(0.8)\nprint('log_raw\\tstill alive accessToken=secret', flush=True)\n"
                          "print('terminated\\t0', flush=True)\n")
        job = self.root / 'job.json'
        job.write_text(json.dumps({'command': [sys.executable, str(script)], 'cwd': str(self.root),
                                   'log': str(self.root / 'game.log'), 'grace': 0.05}))
        process = subprocess.Popen([sys.executable, str(Path(session.__file__)), str(job)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        self.addCleanup(lambda: process.poll() is None and process.kill())
        deadline = time.monotonic() + 10
        observed = None
        while time.monotonic() < deadline:
            status_path = self.root / 'status.json'
            if status_path.exists():
                observed = json.loads(status_path.read_text())
                if observed['state'] == 'ready':
                    break
            if process.poll() is not None:
                break
            time.sleep(0.01)
        self.assertEqual(observed['state'], 'ready')
        self.assertEqual(process.wait(timeout=10), 0)
        process.stderr.close()
        log = (self.root / 'game.log').read_text()
        self.assertIn('still alive', log)
        self.assertNotIn('accessToken=secret', log)
        self.assertIn('accessToken=***', log)

    def test_game_survives_actual_launcher_process_exit(self):
        game = self.root / 'game.py'
        exited = self.root / 'parent-exited'
        game.write_text("import pathlib,time\nprint('launched\\t123', flush=True)\n"
                        "print('log_raw\\t[Render thread/WARN] [ModernFix]: Game took 1 seconds to start', flush=True)\n"
                        f"deadline=time.monotonic()+12\nwhile not pathlib.Path({str(exited)!r}).exists() and time.monotonic()<deadline: time.sleep(0.01)\n"
                        "time.sleep(0.3)\nprint('log_raw\\tsurvived parent exit', flush=True)\nprint('terminated\\t0', flush=True)\n")
        parent = self.root / 'parent.py'
        parent.write_text("import sys,pathlib\n"
                          f"sys.path.insert(0, {str(Path(session.__file__).parent)!r})\nimport game_session\n"
                          f"root=pathlib.Path({str(self.root)!r})\n"
                          f"process,folder=game_session.start([sys.executable, {str(game)!r}], root, root/'game.log')\n"
                          "assert game_session.wait_for_start(process, folder, lambda parts:None)\n"
                          "(root/'parent-exited').touch()\n")
        result = subprocess.run([sys.executable, str(parent)], timeout=15, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if 'survived parent exit' in (self.root / 'game.log').read_text('utf-8'):
                break
            time.sleep(0.05)
        self.assertIn('survived parent exit', (self.root / 'game.log').read_text('utf-8'))
        time.sleep(0.2)

    def test_window_closes_only_for_confirmed_ready_event(self):
        import launcher
        for event, expected in (('game_ready', True), ('error', False)):
            with self.subTest(event=event):
                closed = []
                app = SimpleNamespace(events=queue.Queue(), _log=lambda text: None,
                                      destroy=lambda: closed.append(True), after=lambda *args: None)
                app._drain_events = lambda: None
                app.events.put((event, 'startup failed'))
                with patch.object(launcher.messagebox, 'showerror'):
                    launcher.MeridianLauncher._drain_events(app)
                self.assertEqual(bool(closed), expected)

    def test_failed_game_finishes_before_retry_is_enabled(self):
        game = self.root / 'failed_game.py'
        acknowledged = self.root / 'error-seen'
        ended = self.root / 'game-ended'
        game.write_text("import pathlib,time\nprint('launched\\t123', flush=True)\n"
                        "print('error_launch\\tbroken mod screen', flush=True)\n"
                        f"deadline=time.monotonic()+5\nwhile not pathlib.Path({str(acknowledged)!r}).exists() and time.monotonic()<deadline: time.sleep(0.01)\n"
                        f"time.sleep(0.2)\npathlib.Path({str(ended)!r}).touch()\nprint('terminated\\t1', flush=True)\n")
        process, folder = session.start([sys.executable, str(game)], self.root, self.root / 'game.log')
        def observe(parts):
            if parts[0] == 'error_session':
                acknowledged.touch()
        try:
            with self.assertRaises(RuntimeError):
                session.wait_for_start(process, folder, observe)
            self.assertTrue(ended.exists(), 'Retry was enabled while the failed game was still running')
        finally:
            process.wait(timeout=10)


if __name__ == '__main__':
    unittest.main()
