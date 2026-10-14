"""Starts the launcher (source or EXE) in a sandbox at several interface scales, collects the built-in layout report
and a picture of the launcher window only (PrintWindow, no screen capture).

    python launcher/tests/gui_layout_check.py OUT_DIR [--exe PATH] [--scales auto,100,125,150,175,200] [--dialogs]
"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path

from PIL import Image

u = ctypes.windll.user32
g = ctypes.windll.gdi32
u.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
SOURCE = Path(__file__).resolve().parents[1] / "source" / "launcher.py"


def windows_of(pid: int) -> list[int]:
    found: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _):
        p = wintypes.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u.IsWindowVisible(h) and u.GetWindowTextLengthW(h) > 0:
            found.append(h)
        return True

    u.EnumWindows(cb, 0)
    return found


def capture(hwnd: int, path: Path) -> None:
    rc = wintypes.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(rc))
    w, h = rc.right - rc.left, rc.bottom - rc.top
    hdc = u.GetWindowDC(hwnd)
    mem = g.CreateCompatibleDC(hdc)
    bmp = g.CreateCompatibleBitmap(hdc, w, h)
    g.SelectObject(mem, bmp)
    u.PrintWindow(hwnd, mem, 2)
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
                    ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long), ("biYPelsPerMeter", ctypes.c_long),
                    ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]
    bi = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    g.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bi), 0)
    Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB").save(path)
    g.DeleteObject(bmp); g.DeleteDC(mem); u.ReleaseDC(hwnd, hdc)


def run(out: Path, scale: str, exe: str | None, extra: list[str], mode: str = "offline") -> dict:
    sandbox = Path(tempfile.mkdtemp(prefix="meridian-gui-"))
    root = sandbox / "ProjectMeridianLauncher"
    root.mkdir(parents=True)
    (root / "state.json").write_text(json.dumps({"ui_scale": scale, "auth_mode": mode, "username": "Tester_01"}), "utf-8")
    report = out / f"layout-{scale}.json"
    env = dict(os.environ, LOCALAPPDATA=str(sandbox))
    cmd = ([exe] if exe else [sys.executable, str(SOURCE)]) + [f"--layout-report={report}"] + extra
    proc = subprocess.Popen(cmd, env=env)
    try:
        time.sleep(5)
        wins = windows_of(proc.pid)
        if not wins:  # one-file EXE: the window belongs to the unpacked child process
            out_ps = subprocess.run(["powershell", "-NoProfile", "-Command",
                                     f"(Get-CimInstance Win32_Process -Filter 'ParentProcessId={proc.pid}').ProcessId"],
                                    capture_output=True, text=True).stdout.split()
            for child in out_ps:
                wins += windows_of(int(child))
        for i, h in enumerate(wins):
            capture(h, out / f"window-{scale}{'-' + str(i) if i else ''}.png")
        time.sleep(3)
    finally:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    data = json.loads(report.read_text("utf-8")) if report.exists() else {"error": "no report"}
    bad = {k: v for k, v in data.get("widgets", {}).items() if not (v.get("mapped") and v.get("inside") and not v.get("squeezed"))}
    return {"scale": scale, "ok": data.get("ok"), "layout": data.get("layout"), "problems": bad}


def main() -> None:
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    exe = sys.argv[sys.argv.index("--exe") + 1] if "--exe" in sys.argv else None
    scales = (sys.argv[sys.argv.index("--scales") + 1] if "--scales" in sys.argv else "auto,100,125,150,175,200").split(",")
    results = [run(out, s, exe, []) for s in scales]
    if "--dialogs" in sys.argv:
        for preview in ("skin", "log", "auth"):
            sub = out / f"dialog-{preview}"
            sub.mkdir(exist_ok=True)
            results.append(dict(run(sub, "100", exe, [f"--ui-preview={preview}"]), scale=f"100+{preview}"))
    (out / "gui-layout-summary.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), "utf-8")
    for r in results:
        lay = r["layout"] or {}
        print(r["scale"], "OK" if r["ok"] else "ISSUES", lay.get("effective_scale"), lay.get("columns"), lay.get("size"),
              list(r["problems"])[:6])


if __name__ == "__main__":
    main()
