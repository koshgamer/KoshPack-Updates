from __future__ import annotations

import base64
import incremental
import self_update
import ctypes
import hashlib
import io
import math
import json
import os
import queue
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import zipfile
from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageDraw, ImageTk

import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk

APP_NAME = "Project Meridian Launcher"
APP_VERSION = "1.1.0"
REPO = "koshgamer/KoshPack-Updates"
RELEASE_TAG = "current"
# The public launcher reads only the Stable manifest; there is no other channel in this build.
UPDATE_MANIFEST_URL = "https://raw.githubusercontent.com/koshgamer/KoshPack-Updates/main/launcher/manifest.json"
MC_VERSION = "1.21.1"
NEOFORGE_VERSION = "21.1.249"
LAUNCH_SPEC = f"neoforge::{NEOFORGE_VERSION}"
PMC_VERSION = "5.0.5"
PMC_ARCHIVE_URL = "https://github.com/theorzr/portablemc/releases/download/v5.0.5/portablemc-5.0.5-windows-x86_64-msvc.zip"
PMC_ARCHIVE_SHA256 = "c1ad577e9441040e65a55b521c6ab0fc4c32ec0c6f114d169ae6eee7d3d9fda6"
PROJECT_SITE_URL = "https://projectmeridian-minecraft.lovable.app/"
LAUNCHER_DOWNLOAD_PAGE = PROJECT_SITE_URL + "download"
SERVER_HOST = ""
SERVER_PORT = 25565

# Visual language taken directly from the live Project Meridian site.
C_BG = "#030607"
C_PANEL = "#070c0e"
C_PANEL_2 = "#0d1416"
C_INK = "#dfdacf"
C_MUTED = "#72888a"
C_COPPER = "#d07940"
C_TELEMETRY = "#52bcaf"
C_LINE = "#29383a"
C_DANGER = "#ff4d2e"
C_OK = "#9ecb6b"
C_FIELD = "#10191b"

C_TEXT_OUTLINE = "#010304"  # dark outline around texts drawn over the background
C_HINT = "#93a8aa"          # secondary text over the background (a little brighter than C_MUTED)

# Backward-compatible aliases used by the existing UI code.
C_AMBER = C_COPPER
C_AMBER_2 = C_TELEMETRY

# Launcher interface scale (independent of Minecraft's GUI Scale). "auto" follows the Windows display scale;
# a fixed value (relative to a 100 % / 96 DPI display) is only used for layout tests via --ui-scale=.
UI_SCALE_CHOICES: tuple[str, ...] = ("auto", "100", "125", "150", "175", "200")
UI_SCALE = 1.0


def enable_dpi_awareness() -> None:
    """Per-system DPI awareness: Windows stops bitmap-stretching the window and the launcher scales itself."""
    if os.name != "nt":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def system_dpi_scale() -> float:
    if os.name != "nt":
        return 1.0
    dpi = 0
    try:
        dpi = int(ctypes.windll.user32.GetDpiForSystem())
    except Exception:
        try:
            hdc = ctypes.windll.user32.GetDC(0)
            dpi = int(ctypes.windll.gdi32.GetDeviceCaps(hdc, 88))  # LOGPIXELSX
            ctypes.windll.user32.ReleaseDC(0, hdc)
        except Exception:
            dpi = 0
    return dpi / 96.0 if dpi > 0 else 1.0


APP_USER_MODEL_ID = "KoshPack.ProjectMeridianLauncher"
ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def set_app_user_model_id() -> None:
    """Own taskbar identity: the taskbar button uses this window's icon, not python.exe / the Tk host."""
    if os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


def resource_file(name: str) -> Path | None:
    """A file shipped with the launcher: inside the PyInstaller bundle, next to the exe, or in the source tree."""
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / name)
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / name)
    here = Path(__file__).resolve().parent
    candidates += [here / name, here.parent / name]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def meridian_emblem(size: int) -> Image.Image:
    """The Project Meridian mark (same geometry as make_icon.py) when the bundled image cannot be read."""
    from PIL import ImageDraw

    k = 4
    canvas = size * k
    img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = canvas / 256.0
    c = 128 * f
    copper, telemetry = (208, 121, 64, 255), (82, 188, 175, 255)
    for r, color, width in ((69, copper, 8), (31, telemetry, 8)):
        pts = [(c, c - r * f), (c + r * f, c), (c, c + r * f), (c - r * f, c)]
        d.line(pts + [pts[0]], fill=color, width=max(1, round(width * f)), joint="curve")
    e = 91 * f
    d.line((c - e, c - e, c + e, c + e), fill=copper, width=max(1, round(5 * f)))
    d.line((c + e, c - e, c - e, c + e), fill=copper, width=max(1, round(5 * f)))
    return img.resize((size, size), Image.Resampling.LANCZOS)


def apply_window_icon(window: tk.Misc, keep: list[Any]) -> str:
    """Sets the emblem on a Tk window: the .ico (all sizes) for the Windows title bar/taskbar/Alt+Tab and photo images
    for Tk itself. Returns a short description of what was used."""
    used = []
    ico = resource_file("meridian.ico")
    if ico is not None and os.name == "nt":
        try:
            if isinstance(window, tk.Tk):
                window.iconbitmap(default=str(ico))
            else:
                window.iconbitmap(str(ico))
            used.append("ico")
        except tk.TclError:
            pass
    try:
        png = resource_file("meridian.png")
        base = Image.open(png).convert("RGBA") if png is not None else meridian_emblem(256)
        photos = [ImageTk.PhotoImage(base.resize((size, size), Image.Resampling.LANCZOS), master=window) for size in (256, 64, 48, 32, 16)]
        keep.extend(photos)
        if isinstance(window, tk.Tk):
            window.iconphoto(True, *photos)   # default for the dialogs created later
        window.iconphoto(False, *photos)      # WM_SETICON on this window itself: title bar, taskbar, Alt+Tab
        used.append("png" if png is not None else "drawn")
    except Exception:
        pass
    if dark_title_bar(window):
        used.append("dark-titlebar")
    return "+".join(used) or "none"


def dark_title_bar(window: tk.Misc) -> bool:
    """Dark Windows title bar (Windows 10 20H1+ / 11); older systems simply keep the default one. Called again after
    a dialog is shown, because a window that was hidden while the attribute was set keeps its light frame."""
    if os.name != "nt":
        return False
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        dark = ctypes.c_int(1)
        ok = ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark)) == 0
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020)
        return ok
    except Exception:
        return False


class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class _MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_ulong), ("rcMonitor", _RECT), ("rcWork", _RECT), ("dwFlags", ctypes.c_ulong)]


def work_area(window: tk.Misc | None = None) -> tuple[int, int, int, int]:
    """(left, top, width, height) of the usable area (taskbar excluded) of the monitor holding the window, or the one
    under the mouse pointer for a window not shown yet."""
    if os.name == "nt":
        try:
            user32 = ctypes.windll.user32
            user32.MonitorFromWindow.restype = ctypes.c_void_p
            user32.MonitorFromWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            user32.MonitorFromPoint.restype = ctypes.c_void_p
            user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            monitor = None
            if window is not None and window.winfo_viewable():
                monitor = user32.MonitorFromWindow(int(window.wm_frame(), 16), 2)
            if not monitor:
                class _POINT(ctypes.Structure):
                    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
                pt = _POINT()
                user32.GetCursorPos(ctypes.byref(pt))
                user32.MonitorFromPoint.argtypes = [_POINT, ctypes.c_ulong]
                monitor = user32.MonitorFromPoint(pt, 2)
            info = _MONITORINFO()
            info.cbSize = ctypes.sizeof(info)
            if monitor and user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                r = info.rcWork
                return r.left, r.top, r.right - r.left, r.bottom - r.top
        except Exception:
            pass
    if window is not None:
        return 0, 0, window.winfo_screenwidth(), window.winfo_screenheight() - 48
    return 0, 0, 1280, 720


def frame_extra(resizable: bool = True) -> tuple[int, int]:
    """Width and height the Windows frame and title bar add around the client area (at the process DPI)."""
    if os.name == "nt":
        try:
            r = _RECT(0, 0, 100, 100)
            style = 0x00CF0000 if resizable else 0x00C80000  # WS_OVERLAPPEDWINDOW / caption + sysmenu
            if ctypes.windll.user32.AdjustWindowRectEx(ctypes.byref(r), style, False, 0):
                return (r.right - r.left) - 100, (r.bottom - r.top) - 100
        except Exception:
            pass
    return 16, 39


def normalize_ui_scale_choice(value: Any) -> str:
    text = str(value if value is not None else "auto").strip().lower().rstrip("%").strip()
    return text if text in UI_SCALE_CHOICES else "auto"


def resolve_ui_scale(choice: Any) -> float:
    choice = normalize_ui_scale_choice(choice)
    if choice == "auto":
        return max(0.5, min(4.0, system_dpi_scale()))
    return int(choice) / 100.0


def px(value: float) -> int:
    """Pixel distance at the current launcher UI scale (never rounds a non-zero distance to zero)."""
    if value == 0:
        return 0
    scaled = int(round(value * UI_SCALE))
    if scaled == 0:
        return 1 if value > 0 else -1
    return scaled

USER_AGENT = f"ProjectMeridianLauncher/{APP_VERSION} (+https://github.com/{REPO})"
PRESERVE_PREFIXES = (
    "saves/",
    "screenshots/",
    "crash-reports/",
    "logs/",
    "config/voicechat/",
)
PRESERVE_FILES = {
    "options.txt",
    "servers.dat",
    "servers.dat_old",
    "usercache.json",
}


def _app_root() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "ProjectMeridianLauncher"


APP_ROOT = _app_root()
INSTANCE_DIR = APP_ROOT / "instance"
CACHE_DIR = APP_ROOT / "cache"
LOG_DIR = APP_ROOT / "logs"
STATE_FILE = APP_ROOT / "state.json"
LAUNCH_LOG = LOG_DIR / "minecraft-launch.log"
TOOLS_DIR = APP_ROOT / "tools"
PMC_EXE = TOOLS_DIR / f"portablemc-{PMC_VERSION}.exe"
FILE_INDEX = APP_ROOT / "installed-files.json"
INSTALL_JOURNAL = APP_ROOT / "install-journal.json"
# Left behind by DEV builds of the old launcher; only used to clean up once during migration.
LEGACY_DEV_BACKUP_DIR = APP_ROOT / "dev-extra-backup"
LEGACY_DEV_TRACK_FILE = APP_ROOT / "dev-extra-paths.json"
LEGACY_DEV_ARMOR_JAR = "koshpack-armor-specialties-DEV.jar"
FREE_SPACE_MARGIN = 512 * 1024 * 1024


def ensure_dirs() -> None:
    for path in (APP_ROOT, INSTANCE_DIR, CACHE_DIR, LOG_DIR, TOOLS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def hide_console_if_needed() -> None:
    if os.name != "nt":
        return
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_state() -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "username": "Player",
        "email": "",
        "auth_mode": "offline",
        "msa_uuid": "",
        "msa_username": "",
        "ram_gb": 8,
        "ui_scale": "auto",
        "skin_source": "",
        "skin_nick": "",
        "skin_slim": False,
        "pack_digest": "",
        "pack_identity": "",
        "managed_files": [],
    }
    try:
        if STATE_FILE.is_file():
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                defaults.update(data)
    except Exception:
        pass
    return defaults


def request_json(url: str, timeout: int = 45, max_attempts: int = 5) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code not in (408, 429, 500, 502, 503, 504) or attempt >= max_attempts:
                raise
        except (urllib.error.URLError, ConnectionResetError, TimeoutError, OSError) as e:
            last_error = e
            if attempt >= max_attempts:
                break
        time.sleep(min(2 ** attempt, 10))
    raise RuntimeError(
        f"GitHub не ответил после {max_attempts} попыток. "
        f"Попробуй ещё раз через несколько секунд. Последняя ошибка: {last_error}"
    )


def get_release_asset() -> dict[str, Any]:
    manifest = request_json(UPDATE_MANIFEST_URL)
    package = manifest.get("package") or {}
    url = str(package.get("url") or "")
    sha256 = str(package.get("sha256") or "").lower()
    size = int(package.get("size") or 0)
    if not url:
        raise RuntimeError("В публичном манифесте Project Meridian не указан URL сборки.")
    if not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise RuntimeError("В публичном манифесте Project Meridian не указан SHA-256 сборки.")
    if urllib.parse.urlsplit(url).scheme != "https":
        raise RuntimeError("Адрес сборки в манифесте должен быть HTTPS.")
    launcher = manifest.get("launcher") or {}
    pack_version = str(manifest.get("packVersion") or "")
    return {
        "url": url,
        "size": size,
        "digest": f"sha256:{sha256}",
        "identity": f"{pack_version or 'unknown'}:{sha256}",
        "updated_at": pack_version,
        "release_name": pack_version_label(pack_version),
        "launcher_version": str(launcher.get("version") or ""),
        "launcher_min": str(manifest.get("launcherMinVersion") or ""),
        "launcher_asset": launcher,
        "file_index": manifest.get("fileIndex"),
    }


def pack_version_label(pack_version: str) -> str:
    """Public name of a pack version: 'stable-r2h' / 'r2h' -> 'Stable r2h'."""
    value = str(pack_version or "").strip()
    if not value:
        return "Stable"
    value = value.removeprefix("stable-").removeprefix("Stable-")
    return f"Stable {value}"


def offline_uuid(nick: str) -> str:
    """Standard offline-mode UUID (same as Java UUID.nameUUIDFromBytes("OfflinePlayer:" + nick))."""
    raw = bytearray(hashlib.md5(f"OfflinePlayer:{nick}".encode("utf-8")).digest())
    raw[6] = (raw[6] & 0x0F) | 0x30
    raw[8] = (raw[8] & 0x3F) | 0x80
    h = raw.hex()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


_SECRET_PATTERNS = (
    re.compile(r"eyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]{8,}"),
    re.compile(r"(?i)((?:access|refresh|xbl|xsts|mc)[_-]?token[\"'=: ]+)[^\s\"',]+"),
    re.compile(r"(?i)(--accessToken\s+)\S+"),
)


def mask_secrets(text: str) -> str:
    """Logs never contain sign-in tokens, even if a component prints one."""
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(lambda m: (m.group(1) if m.groups() else "") + "***", text)
    return text


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def expected_sha256(asset: dict[str, Any]) -> str:
    digest = str(asset.get("digest") or "")
    if digest.lower().startswith("sha256:"):
        return digest.split(":", 1)[1].lower()
    return ""


def cached_pack_path(asset: dict[str, Any]) -> Path:
    key = expected_sha256(asset)[:16]
    if not key:
        key = hashlib.sha1(asset["identity"].encode("utf-8")).hexdigest()[:16]
    return CACHE_DIR / f"minecraft-{key}.zip"


def download_file(
    url: str,
    dest: Path,
    expected_size: int,
    on_progress: Callable[[int, int], None],
    timeout: int = 180,
    max_attempts: int = 8,
) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        done = tmp.stat().st_size if tmp.exists() else 0
        if expected_size and done > expected_size:
            tmp.unlink(missing_ok=True)
            done = 0

        headers = {"User-Agent": USER_AGENT}
        if done:
            headers["Range"] = f"bytes={done}-"

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status = getattr(response, "status", response.getcode())
                content_range = response.headers.get("Content-Range") or ""
                content_length = int(response.headers.get("Content-Length") or 0)

                if done and status != 206:
                    tmp.unlink(missing_ok=True)
                    done = 0
                    mode = "wb"
                else:
                    mode = "ab" if done else "wb"

                total = expected_size
                if "/" in content_range:
                    try:
                        total = int(content_range.rsplit("/", 1)[1])
                    except ValueError:
                        pass
                elif not total and content_length:
                    total = done + content_length

                with tmp.open(mode) as out:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        out.write(chunk)
                        done += len(chunk)
                        on_progress(done, total)

            final_size = tmp.stat().st_size if tmp.exists() else 0
            if expected_size and final_size < expected_size:
                raise OSError(f"Скачано только {final_size} из {expected_size} байт")
            tmp.replace(dest)
            return
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, ConnectionResetError, TimeoutError, OSError) as e:
            last_error = e
            if attempt >= max_attempts:
                break
            time.sleep(min(2 ** attempt, 10))

    raise RuntimeError(
        f"Скачивание оборвалось после {max_attempts} попыток. "
        f"Лаунчер сохранит .part и попробует докачать файл при следующем запуске. Последняя ошибка: {last_error}"
    )


def format_bytes(value: float | int) -> str:
    size = float(max(0, value))
    units = ("Б", "КБ", "МБ", "ГБ")
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            if unit == "Б":
                return f"{size:.0f} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} ГБ"


def request_json_public(url: str, timeout: int = 30) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def minecraft_skin_path(uuid_value: str) -> Path | None:
    uuid_clean = uuid_value.replace("-", "").strip()
    if not uuid_clean:
        return None

    target = CACHE_DIR / f"skin-{uuid_clean}.png"
    if target.is_file():
        return target

    try:
        profile = request_json_public(
            f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid_clean}",
            timeout=20,
        )
        properties = profile.get("properties") or []
        encoded = next(
            (str(p.get("value") or "") for p in properties if p.get("name") == "textures"),
            "",
        )
        if not encoded:
            return None
        payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
        skin_url = str((((payload.get("textures") or {}).get("SKIN") or {}).get("url")) or "")
        if not skin_url:
            return None

        req = urllib.request.Request(skin_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as response:
            target.write_bytes(response.read())
        return target
    except Exception:
        return None


def skin_head_rgba(path: Path, size: int = 104) -> Image.Image:
    with Image.open(path) as raw:
        skin = raw.convert("RGBA")
        face = skin.crop((8, 8, 16, 16)).resize((size, size), Image.Resampling.NEAREST)
        if skin.width >= 48 and skin.height >= 16:
            hat = skin.crop((40, 8, 48, 16)).resize((size, size), Image.Resampling.NEAREST)
            face.alpha_composite(hat)
        return face.copy()


def safe_extract(zip_path: Path, dest: Path) -> None:
    root = dest.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            candidate = (dest / info.filename).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                raise RuntimeError(f"Небезопасный путь в архиве: {info.filename}")
        zf.extractall(dest)


def is_preserved(rel: str) -> bool:
    normalized = rel.replace("\\", "/")
    return normalized in PRESERVE_FILES or any(normalized.startswith(prefix) for prefix in PRESERVE_PREFIXES)


def safe_rel_path(name: str) -> str | None:
    """Relative instance path for a ZIP member, or None for directories. Rejects path traversal and absolute paths."""
    rel = name.replace("\\", "/")
    if not rel or rel.endswith("/"):
        return None
    parts = rel.split("/")
    if rel.startswith("/") or any(p in ("", ".", "..") for p in parts) or ":" in parts[0]:
        raise RuntimeError(f"Небезопасный путь в архиве: {name}")
    if any(p.rstrip(". ") != p for p in parts):
        raise RuntimeError(f"Небезопасное имя файла в архиве: {name}")
    return rel


def pack_members(zf: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    """Maps instance-relative paths to ZIP entries. Every entry name is validated as a whole first; a common
    .minecraft/ or minecraft/ top folder is then stripped."""
    files = [i for i in zf.infolist() if not i.is_dir() and not i.filename.startswith("__MACOSX/")]
    names = {i.filename: safe_rel_path(i.filename) for i in files}
    prefix = ""
    for top in (".minecraft/", "minecraft/"):
        if files and all(str(n).startswith(top) for n in names.values()):
            prefix = top
    members: dict[str, zipfile.ZipInfo] = {}
    for info in files:
        rel = names[info.filename]
        if rel is not None:
            rel = safe_rel_path(rel[len(prefix):])
        if rel is not None:
            members[rel] = info
    if not members:
        raise RuntimeError("Архив сборки пуст.")
    return members


def ensure_free_space(where: Path, needed: int, purpose: str) -> None:
    probe = where
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    free = shutil.disk_usage(probe).free
    required = needed + FREE_SPACE_MARGIN
    if free < required:
        raise RuntimeError(
            f"Недостаточно места на диске {probe.anchor or probe}: для {purpose} нужно ещё "
            f"{format_bytes(required - free)}. Освободи место и повтори — уже установленные файлы не тронуты."
        )


def _make_writable(path: Path) -> None:
    try:
        path.chmod(0o666)
    except OSError:
        pass


def _write_member(zf: zipfile.ZipFile, info: zipfile.ZipInfo, dst: Path) -> str:
    """Writes one ZIP entry next to its target, then atomically replaces the target. Returns the SHA-256."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".meridian-new")
    if tmp.exists():
        _make_writable(tmp)
        tmp.unlink()
    h = hashlib.sha256()
    try:
        with zf.open(info) as src, tmp.open("wb") as out:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
                out.write(chunk)
            out.flush()
            os.fsync(out.fileno())
        if dst.exists():
            _make_writable(dst)
        os.replace(tmp, dst)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return h.hexdigest()


def load_file_index() -> dict[str, str]:
    try:
        data = json.loads(FILE_INDEX.read_text(encoding="utf-8"))
        files = data.get("files") if isinstance(data, dict) else None
        if isinstance(files, dict):
            return {str(k): str(v).lower() for k, v in files.items() if not is_preserved(str(k))}
    except (OSError, ValueError):
        pass
    return {}


def install_from_zip(
    zip_path: Path,
    previous_managed: list[str],
    on_progress: Callable[[int, int], None] | None = None,
) -> tuple[list[str], dict[str, str]]:
    """Installs a verified pack ZIP into the instance without deleting anything first.

    Every file is written to a temporary name and swapped in atomically; files of the previous version that are
    no longer part of the pack are removed only after all new files are in place. User data (saves, screenshots,
    options, servers, ...) is never overwritten or removed, and unknown files the launcher did not install stay."""
    with zipfile.ZipFile(zip_path) as zf:
        members = pack_members(zf)
        ensure_free_space(INSTANCE_DIR, sum(i.file_size for i in members.values()), "установки сборки")
        managed: list[str] = []
        index: dict[str, str] = {}
        total = len(members)
        for done, (rel, info) in enumerate(sorted(members.items()), start=1):
            dst = INSTANCE_DIR / rel
            if is_preserved(rel):
                if not dst.exists():
                    _write_member(zf, info, dst)
                continue
            index[rel] = _write_member(zf, info, dst)
            managed.append(rel)
            if on_progress is not None and (done % 25 == 0 or done == total):
                on_progress(done, total)
    remove_obsolete_files(previous_managed, set(managed))
    return sorted(managed), index


def remove_obsolete_files(previous_managed: list[str], keep: set[str]) -> list[str]:
    removed: list[str] = []
    parents: set[Path] = set()
    for rel in previous_managed:
        if rel in keep or is_preserved(rel):
            continue
        try:
            safe = safe_rel_path(rel)
        except RuntimeError:
            continue
        if safe is None:
            continue
        target = INSTANCE_DIR / safe
        try:
            if target.is_file() or target.is_symlink():
                _make_writable(target)
                target.unlink()
                removed.append(safe)
                parents.add(target.parent)
        except OSError:
            pass
    root = INSTANCE_DIR.resolve()
    for parent in sorted(parents, key=lambda p: len(p.parts), reverse=True):
        p = parent
        while p.resolve() != root:
            try:
                p.rmdir()
            except OSError:
                break
            p = p.parent
    return removed


def verify_installed_files(index: dict[str, str]) -> list[str]:
    """Managed files that are missing or whose SHA-256 differs from the installed pack."""
    broken: list[str] = []
    for rel, expected in sorted(index.items()):
        target = INSTANCE_DIR / rel
        try:
            if not target.is_file() or sha256_file(target) != expected:
                broken.append(rel)
        except OSError:
            broken.append(rel)
    return broken


def restore_files_from_zip(zip_path: Path, rels: list[str]) -> dict[str, str]:
    with zipfile.ZipFile(zip_path) as zf:
        members = pack_members(zf)
        wanted = [rel for rel in rels if rel in members and not is_preserved(rel)]
        ensure_free_space(INSTANCE_DIR, sum(members[rel].file_size for rel in wanted), "восстановления файлов")
        return {rel: _write_member(zf, members[rel], INSTANCE_DIR / rel) for rel in wanted}


def unknown_mod_files(index: dict[str, str]) -> list[str]:
    """Mods in the instance that the launcher did not install (reported, never deleted automatically)."""
    mods = INSTANCE_DIR / "mods"
    if not mods.is_dir():
        return []
    return sorted(f"mods/{p.name}" for p in mods.iterdir() if p.is_file() and f"mods/{p.name}" not in index)


def cleanup_legacy_dev_files() -> list[str]:
    """One-time migration from DEV builds of the old launcher: removes the DEV armor JAR, its stable backups and the
    DEV extras the old launcher tracked. The following Stable install puts the stable files back."""
    removed: list[str] = []
    mods = INSTANCE_DIR / "mods"
    candidates: list[Path] = []
    if mods.is_dir():
        candidates += [mods / LEGACY_DEV_ARMOR_JAR]
        candidates += list(mods.glob("*.meridian-stable-bak"))
    try:
        if LEGACY_DEV_TRACK_FILE.is_file():
            data = json.loads(LEGACY_DEV_TRACK_FILE.read_text(encoding="utf-8"))
            for rel in (data.get("paths", []) if isinstance(data, dict) else []):
                safe = safe_rel_path(str(rel))
                if safe and safe.startswith(("kubejs/", "mods/", "config/ftbquests/quests/")):
                    candidates.append(INSTANCE_DIR / safe)
    except (OSError, ValueError, RuntimeError):
        pass
    for target in candidates:
        try:
            if target.is_file():
                _make_writable(target)
                target.unlink()
                removed.append(target.relative_to(INSTANCE_DIR).as_posix())
        except OSError:
            pass
    return removed


def finish_legacy_dev_cleanup() -> None:
    """After a successful Stable install the old launcher's DEV bookkeeping is no longer needed."""
    LEGACY_DEV_TRACK_FILE.unlink(missing_ok=True)
    shutil.rmtree(LEGACY_DEV_BACKUP_DIR, ignore_errors=True)


def legacy_dev_state_present(state: dict[str, Any]) -> bool:
    mods = INSTANCE_DIR / "mods"
    return (
        str(state.get("channel") or "stable") != "stable"
        or LEGACY_DEV_TRACK_FILE.exists()
        or LEGACY_DEV_BACKUP_DIR.exists()
        or (mods / LEGACY_DEV_ARMOR_JAR).exists()
        or (mods.is_dir() and any(mods.glob("*.meridian-stable-bak")))
    )


def version_tuple(value: str) -> tuple[int, ...]:
    """'1.2.3' -> (1, 2, 3); pre-release suffixes ('-dev5') sort before the release."""
    main, _, suffix = str(value).strip().lstrip("v").partition("-")
    nums = tuple(int(p) if p.isdigit() else 0 for p in main.split("."))
    nums = (nums + (0, 0, 0))[:3]
    return nums + ((0,) if suffix else (1,))

# ---------- Skins ("МОЙ СКИН") ----------
# The launcher only previews skins and prepares the in-game command for the server mod SkinRestorer, which applies
# the skin to the player's profile so that every player on the server sees it. Remote images are fetched only from
# the fixed hosts below (redirects included), with a size limit, and are validated before they are decoded.
SKIN_SOURCES: tuple[tuple[str, str], ...] = (
    ("official", "Официальный (Microsoft)"),
    ("elyby", "Ely.by — по нику"),
    ("tlauncher", "TLauncher — по нику"),
    ("file", "Свой PNG-файл"),
    ("default", "Стандартный скин"),
)
SKIN_ALLOWED_HOSTS = ("textures.minecraft.net", "ely.by", ".ely.by", "auth.tlauncher.org")
SKIN_MAX_BYTES = 256 * 1024
SKIN_SIZES = ((64, 64), (64, 32))
ELYBY_SKIN_URL = "https://skinsystem.ely.by/skins/{}.png"
TLAUNCHER_TEXTURES_URL = "https://auth.tlauncher.org/skin/profile/texture/login/{}"
MINESKIN_API = "https://api.mineskin.org"
NICK_RE = re.compile(r"^[A-Za-z0-9_]{3,16}$")


def skin_host_allowed(url: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(url)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("http", "https") or not host or parsed.username or parsed.password:
        return False
    if parsed.port not in (None, 80, 443):
        return False
    return any(host == h or (h.startswith(".") and host.endswith(h)) for h in SKIN_ALLOWED_HOSTS)


class _AllowlistRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        if not skin_host_allowed(newurl):
            raise RuntimeError("Источник скина перенаправил на неразрешённый адрес.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_limited(url: str, limit: int = SKIN_MAX_BYTES, timeout: int = 20) -> tuple[bytes, str]:
    """GET from an allow-listed skin host. Returns (body, final URL)."""
    if not skin_host_allowed(url):
        raise RuntimeError("Адрес скина не входит в список разрешённых источников.")
    opener = urllib.request.build_opener(_AllowlistRedirect())
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with opener.open(req, timeout=timeout) as response:
        final_url = response.geturl()
        if not skin_host_allowed(final_url):
            raise RuntimeError("Источник скина ответил с неразрешённого адреса.")
        declared = int(response.headers.get("Content-Length") or 0)
        if declared > limit:
            raise RuntimeError("Файл скина слишком большой.")
        body = response.read(limit + 1)
    if len(body) > limit:
        raise RuntimeError("Файл скина слишком большой.")
    return body, final_url


def validate_skin_png(data: bytes) -> dict[str, Any]:
    """Checks a skin before use: PNG signature, size, dimensions (read from the header, before decoding),
    integrity and pixel format. Returns facts used for the preview and the Steve/Alex suggestion."""
    if len(data) > SKIN_MAX_BYTES:
        raise ValueError(f"Файл больше {SKIN_MAX_BYTES // 1024} КБ — это не похоже на скин Minecraft.")
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) < 33 or data[12:16] != b"IHDR":
        raise ValueError("Это не PNG-файл.")
    width, height = int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if (width, height) not in SKIN_SIZES:
        raise ValueError(f"Размер {width}×{height}: скин Minecraft должен быть 64×64 (или старый 64×32).")
    try:
        with Image.open(io.BytesIO(data)) as probe:
            if probe.format != "PNG":
                raise ValueError("Это не PNG-файл.")
            probe.verify()
        with Image.open(io.BytesIO(data)) as img:
            img.load()
            rgba = img.convert("RGBA")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"PNG повреждён или не читается: {type(e).__name__}.") from e
    alpha = rgba.getchannel("A")
    has_transparency = alpha.getextrema()[0] < 255
    slim_guess = height == 64 and rgba.getpixel((54, 20))[3] == 0 and rgba.getpixel((55, 31))[3] == 0
    return {"width": width, "height": height, "has_transparency": has_transparency, "slim": slim_guess, "image": rgba}


def resolve_external_skin(source: str, nick: str) -> tuple[bytes, str]:
    """Downloads a public skin by nickname from Ely.by or TLauncher (no sign-in, no password)."""
    if not NICK_RE.match(nick):
        raise ValueError("Ник: 3–16 символов, латиница, цифры и «_».")
    quoted = urllib.parse.quote(nick)
    if source == "elyby":
        return fetch_limited(ELYBY_SKIN_URL.format(quoted))
    if source == "tlauncher":
        body, _ = fetch_limited(TLAUNCHER_TEXTURES_URL.format(quoted), limit=16 * 1024)
        try:
            url = str(((json.loads(body.decode("utf-8")).get("SKIN") or {}).get("url")) or "")
        except ValueError as e:
            raise RuntimeError("TLauncher вернул неожиданный ответ.") from e
        if not url:
            raise RuntimeError("У этого ника нет скина TLauncher.")
        return fetch_limited(url)
    raise ValueError(source)


def skin_preview_image(skin: Image.Image, scale: int) -> Image.Image:
    """Front view (head, body, arms, legs with overlay layers) of a 64×64 or 64×32 skin."""
    w = 16 * scale
    out = Image.new("RGBA", (16, 32), (0, 0, 0, 0))
    legacy = skin.height == 32

    def part(box: tuple[int, int, int, int], at: tuple[int, int], mirror: bool = False) -> None:
        piece = skin.crop(box)
        if mirror:
            piece = piece.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        out.alpha_composite(piece, at)

    part((8, 8, 16, 16), (4, 0))
    part((20, 20, 28, 32), (4, 8))
    part((44, 20, 48, 32), (0, 8))
    part((4, 20, 8, 32), (4, 20))
    if legacy:
        part((44, 20, 48, 32), (12, 8), mirror=True)
        part((4, 20, 8, 32), (8, 20), mirror=True)
    else:
        part((36, 52, 40, 64), (12, 8))
        part((20, 52, 24, 64), (8, 20))
        for box, at in (((20, 36, 28, 48), (4, 8)), ((44, 36, 48, 48), (0, 8)), ((52, 52, 56, 64), (12, 8)),
                        ((4, 36, 8, 48), (4, 20)), ((4, 52, 8, 64), (8, 20))):
            part(box, at)
    part((40, 8, 48, 16), (4, 0))
    return out.resize((w, 2 * w), Image.Resampling.NEAREST)


def mineskin_sign_png(data: bytes, variant: str) -> str:
    """Uploads the player's own PNG to MineSkin (unlisted) to obtain a Mojang-signed texture URL on
    textures.minecraft.net. Only called after the player confirmed the upload."""
    boundary = "----meridian" + hashlib.sha1(data).hexdigest()[:16]
    fields = {"variant": variant, "visibility": "unlisted", "name": "project-meridian"}
    body = b"".join(
        f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items()
    ) + (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="skin.png"\r\n'
        "Content-Type: image/png\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    req = urllib.request.Request(f"{MINESKIN_API}/v2/queue", data=body, method="POST",
                                 headers={**headers, "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=40) as response:
            answer = json.load(response)
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            errors = json.loads(e.read(4096).decode("utf-8")).get("errors") or []
            detail = "; ".join(str(x.get("message") or x.get("code")) for x in errors if isinstance(x, dict))
        except Exception:
            pass
        raise RuntimeError(f"MineSkin отклонил загрузку (HTTP {e.code}){': ' + detail if detail else ''}.") from e
    def skin_url(skin_id: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{32}", skin_id):
            raise RuntimeError("MineSkin вернул неожиданный ответ.")
        with urllib.request.urlopen(urllib.request.Request(f"{MINESKIN_API}/v2/skins/{skin_id}", headers=headers),
                                    timeout=30) as response:
            skin = json.load(response).get("skin") or {}
        texture = skin.get("texture") or {}
        url_field = texture.get("url")
        url = str((url_field.get("skin") if isinstance(url_field, dict) else url_field) or "")
        if not url:
            try:  # the URL inside the Mojang-signed textures property
                packed = json.loads(base64.b64decode(str((texture.get("data") or {}).get("value") or "")))
                url = str(((packed.get("textures") or {}).get("SKIN") or {}).get("url") or "")
            except (ValueError, TypeError):
                url = ""
        if urllib.parse.urlsplit(url).hostname != "textures.minecraft.net":
            raise RuntimeError("MineSkin вернул текстуру не с серверов Mojang.")
        return url

    job = answer.get("job") or {}
    job_id = str(job.get("id") or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,64}", job_id):
        raise RuntimeError("MineSkin вернул неожиданный ответ.")
    deadline = time.monotonic() + 120
    while True:
        if job.get("status") == "failed":
            raise RuntimeError("MineSkin не смог обработать скин.")
        if job.get("status") == "completed" and job.get("result"):
            return skin_url(str(job["result"]))
        if time.monotonic() > deadline:
            break
        time.sleep(3)
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{MINESKIN_API}/v2/queue/{job_id}", headers=headers),
                                        timeout=30) as response:
                job = json.load(response).get("job") or {}
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
    raise RuntimeError("MineSkin не ответил за 2 минуты. Попробуй позже.")


def skin_command(source: str, url: str = "", slim: bool = False) -> str:
    """In-game command for SkinRestorer. Ely.by, TLauncher and own PNG skins are first signed by Mojang through
    MineSkin (textures.minecraft.net), the only address the server accepts, so every player's client shows them."""
    if source == "official":
        return "/skin reset"
    if source == "default":
        return "/skin clear"
    if urllib.parse.urlsplit(url).hostname != "textures.minecraft.net" or not skin_host_allowed(url):
        raise ValueError("Сначала подготовьте скин для сервера (подпись Mojang).")
    return f"/skin set web {'slim' if slim else 'classic'} \"{url}\""


def ensure_portablemc() -> Path:
    if PMC_EXE.is_file():
        return PMC_EXE

    archive = CACHE_DIR / f"portablemc-{PMC_VERSION}-windows-x86_64.zip"
    valid = archive.is_file() and sha256_file(archive) == PMC_ARCHIVE_SHA256
    if not valid:
        archive.unlink(missing_ok=True)
        download_file(PMC_ARCHIVE_URL, archive, 0, lambda _done, _total: None)

    actual = sha256_file(archive)
    if actual != PMC_ARCHIVE_SHA256:
        archive.unlink(missing_ok=True)
        raise RuntimeError(
            f"Не удалось проверить ядро PortableMC {PMC_VERSION}: SHA-256 не совпал."
        )

    temp_dir = Path(tempfile.mkdtemp(prefix="portablemc-", dir=str(APP_ROOT)))
    try:
        safe_extract(archive, temp_dir)
        candidates = list(temp_dir.rglob("portablemc.exe"))
        if not candidates:
            candidates = [p for p in temp_dir.rglob("*.exe") if "portablemc" in p.name.lower()]
        if not candidates:
            raise RuntimeError("В официальном архиве PortableMC не найден portablemc.exe.")
        PMC_EXE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(candidates[0], PMC_EXE)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return PMC_EXE


def build_pmc_command(pmc_args: list[str]) -> list[str]:
    return [str(ensure_portablemc()), *pmc_args]


def run_pmc(
    pmc_args: list[str],
    log_path: Path,
    on_event: Callable[[list[str]], None] | None = None,
) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with log_path.open("a", encoding="utf-8", errors="replace") as log:
        log.write("\n\n===== Project Meridian Launcher =====\n")
        log.write(f"PortableMC core: {PMC_VERSION}\n")
        log.write("PortableMC args: " + mask_secrets(" ".join(pmc_args)) + "\n")
        log.flush()
        proc = subprocess.Popen(
            build_pmc_command(pmc_args),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(APP_ROOT),
            creationflags=creationflags,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        assert proc.stdout is not None
        for raw_line in proc.stdout:
            line = raw_line.rstrip("\r\n")
            log.write(mask_secrets(line) + "\n")
            log.flush()
            if on_event is not None:
                try:
                    on_event(line.split("\t"))
                except Exception as callback_error:
                    log.write(f"[launcher progress parser] {callback_error}\n")
                    log.flush()
        return proc.wait()


MS_HINT = "Вход на официальной странице Microsoft. Пароль лаунчер не видит и не хранит."
OFFLINE_HINT = ("Ник: 3–16 символов (A–Z, 0–9, _). При первом входе на сервер придумайте пароль: "
                "/register пароль пароль, потом /login пароль. Не используйте пароли от других сайтов.")

# Title brightness per frame (70 ms) when the launcher starts: a short flicker, like an old game menu powering on.
BOOT_FLICKER: tuple[float, ...] = (0.0, 0.15, 0.05, 0.5, 0.2, 0.75, 0.35, 0.9, 0.6, 1.0, 0.8, 1.0)

# Layout densities, tried in order until the whole window fits the work area of the monitor without scrolling.
# Values are pixels / points at 100 % and are scaled by the effective interface scale.
DENSITY: tuple[dict[str, Any], ...] = (
    {"outer": (28, 20), "gap": 14, "sep": (10, 14), "pad": 20, "sec": (18, 10), "btn_pady": 10, "play_pady": 13,
     "play_font": 14, "title_font": 24, "subtitle": True, "icon": 48, "skin": 96, "skin_font": 15, "hints": True,
     "log_lines": 6, "status_font": 23, "entry_ipady": 7, "item_gap": 10},
    {"outer": (20, 14), "gap": 12, "sep": (8, 10), "pad": 16, "sec": (12, 7), "btn_pady": 7, "play_pady": 9,
     "play_font": 13, "title_font": 19, "subtitle": True, "icon": 40, "skin": 72, "skin_font": 12, "hints": False,
     "log_lines": 4, "status_font": 19, "entry_ipady": 5, "item_gap": 7},
    {"outer": (14, 9), "gap": 9, "sep": (6, 7), "pad": 12, "sec": (8, 5), "btn_pady": 5, "play_pady": 6,
     "play_font": 12, "title_font": 15, "subtitle": False, "icon": 32, "skin": 56, "skin_font": 10, "hints": False,
     "log_lines": 3, "status_font": 16, "entry_ipady": 3, "item_gap": 5},
)
# (columns, density): three columns first (shortest window), then two columns for narrow screens.
LAYOUTS: tuple[tuple[int, int], ...] = ((3, 0), (3, 1), (3, 2), (2, 1), (2, 2))
MIN_EFFECTIVE_SCALE = 0.75
PREFERRED_SIZE = (1180, 720)


class Tooltip:
    """Hint shown on hover; used for explanations moved out of the compact layout."""

    def __init__(self, widget: tk.Misc, text: Callable[[], str]) -> None:
        self.widget, self.text, self.tip = widget, text, None
        widget.bind("<Enter>", self.show, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")

    def show(self, _event: tk.Event | None = None) -> None:
        text = self.text()
        if not text or self.tip is not None:
            return
        tip = tk.Toplevel(self.widget)
        tip.wm_overrideredirect(True)
        tip.configure(bg=C_LINE)
        tk.Label(tip, text=text, bg=C_PANEL_2, fg=C_INK, font=("Segoe UI", 9), justify="left",
                 wraplength=px(320), padx=px(8), pady=px(5)).pack(padx=1, pady=1)
        tip.update_idletasks()
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + px(4)
        left, top, ww, wh = work_area(self.widget.winfo_toplevel())
        x = max(left, min(x, left + ww - tip.winfo_reqwidth()))
        if y + tip.winfo_reqheight() > top + wh:
            y = self.widget.winfo_rooty() - tip.winfo_reqheight() - px(4)
        tip.geometry(f"+{x}+{y}")
        self.tip = tip

    def hide(self, _event: tk.Event | None = None) -> None:
        if self.tip is not None:
            try:
                self.tip.destroy()
            except tk.TclError:
                pass
            self.tip = None


class RamSlider(tk.Canvas):
    """Small custom slider so the handle is always visible on Windows."""

    def __init__(self, parent: tk.Misc, variable: tk.IntVar, from_: int = 4, to: int = 16) -> None:
        super().__init__(
            parent,
            width=px(120),
            height=px(30),
            bg=C_PANEL_2,
            bd=0,
            highlightthickness=1,
            highlightbackground=C_LINE,
            cursor="hand2",
        )
        self.variable = variable
        self.minimum = from_
        self.maximum = to
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Button-1>", self._pointer)
        self.bind("<B1-Motion>", self._pointer)
        self.variable.trace_add("write", lambda *_args: self._draw())
        self.after_idle(self._draw)

    def _pointer(self, event: tk.Event) -> None:
        width = max(1, self.winfo_width())
        left, right = px(9), max(px(10), width - px(9))
        ratio = max(0.0, min(1.0, (event.x - left) / max(1, right - left)))
        value = round(self.minimum + ratio * (self.maximum - self.minimum))
        self.variable.set(max(self.minimum, min(self.maximum, value)))

    def _draw(self) -> None:
        self.delete("all")
        width = max(1, self.winfo_width())
        left, right, y = px(9), max(px(10), width - px(9)), px(15)
        value = max(self.minimum, min(self.maximum, int(self.variable.get())))
        ratio = (value - self.minimum) / max(1, self.maximum - self.minimum)
        x = left + (right - left) * ratio

        self.create_line(left, y, right, y, fill=C_LINE, width=px(2))
        self.create_line(left, y, x, y, fill=C_COPPER, width=px(3))

        for step in range(self.minimum, self.maximum + 1, 2):
            r = (step - self.minimum) / max(1, self.maximum - self.minimum)
            tick_x = left + (right - left) * r
            self.create_line(tick_x, y - px(4), tick_x, y + px(4), fill="#314346", width=px(1))

        # Permanent high-contrast handle; no hover required.
        self.create_rectangle(
            x - px(9), y - px(9), x + px(9), y + px(9),
            fill=C_COPPER,
            outline=C_TELEMETRY,
            width=px(2),
        )
        self.create_rectangle(
            x - px(3), y - px(3), x + px(3), y + px(3),
            fill=C_TELEMETRY,
            outline="",
        )


def _hex(c: str) -> tuple[int, int, int]:
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


def blend_hex(a: str, b: str, t: float) -> str:
    """Colour a -> b at t (0..1): canvas items cannot be translucent, so faint layers are pre-blended."""
    av, bv = _hex(a), _hex(b)
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(av, bv))


def windows_animations_enabled() -> bool:
    """Respects Windows 'Show animations' (Accessibility > Visual effects)."""
    if os.name != "nt":
        return True
    try:
        value = ctypes.c_int(1)
        ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(value), 0)  # SPI_GETCLIENTAREAANIMATION
        return bool(value.value)
    except Exception:
        return True


def render_backdrop(width: int, height: int) -> Image.Image:
    """Static layer of the launcher background: dark CRT gradient, faint expedition grid, an industrial
    skyline on the horizon and scanlines. Everything is composited at low opacity over the base colour."""
    w, h = max(1, width), max(1, height)
    base = Image.new("RGB", (w, h), _hex(C_BG))
    glow = Image.new("L", (w, h), 0)
    gd = ImageDraw.Draw(glow)
    cx, cy, r = int(w * 0.68), int(h * 0.42), int(max(w, h) * 0.62)
    for i in range(24, 0, -1):  # soft radial glow behind the globe
        rr = r * i / 24
        gd.ellipse((cx - rr, cy - rr * 0.8, cx + rr, cy + rr * 0.8), fill=int(70 * (1 - i / 24) ** 1.6))
    base.paste(Image.new("RGB", (w, h), (20, 46, 48)), (0, 0), glow)

    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    step = 48
    for x in range(0, w, step):
        d.line((x, 0, x, h), fill=(82, 188, 175, 16))
    for y in range(0, h, step):
        d.line((0, y, w, y), fill=(82, 188, 175, 16))

    # industrial skyline on the horizon: stacks, a crane, tanks, a water wheel
    horizon = int(h * 0.80)
    far = (24, 44, 47, 245)
    pts = [(0, horizon + 30)]
    x = 0
    rnd = random.Random(7)
    while x < w:
        kind = rnd.random()
        if kind < 0.18:      # chimney
            cw = rnd.randint(10, 18)
            ch = rnd.randint(60, 130)
            pts += [(x, horizon), (x, horizon - ch), (x + cw, horizon - ch), (x + cw, horizon)]
            x += cw + rnd.randint(6, 30)
        elif kind < 0.36:    # tank
            tw = rnd.randint(40, 80)
            th = rnd.randint(30, 55)
            pts += [(x, horizon), (x, horizon - th), (x + tw // 2, horizon - th - 10), (x + tw, horizon - th), (x + tw, horizon)]
            x += tw + rnd.randint(8, 30)
        else:                # low halls with saw-tooth roofs
            hw = rnd.randint(70, 150)
            hh = rnd.randint(18, 40)
            pts.append((x, horizon - hh))
            for k in range(0, hw, 22):
                pts += [(x + k + 16, horizon - hh - 12), (x + k + 22, horizon - hh)]
            x += hw
            pts.append((x, horizon - hh))
    pts += [(w, horizon + 30), (w, h), (0, h)]
    d.polygon(pts, fill=far)
    # crane
    kx = int(w * 0.22)
    d.line((kx, horizon, kx, horizon - 170), fill=far, width=5)
    d.line((kx - 40, horizon - 165, kx + 150, horizon - 165), fill=far, width=4)
    d.line((kx + 120, horizon - 165, kx + 120, horizon - 120), fill=far, width=2)
    # water wheel (Create)
    wx, wy, wr = int(w * 0.47), horizon - 10, 46
    d.ellipse((wx - wr, wy - wr, wx + wr, wy + wr), outline=far, width=4)
    for a in range(0, 360, 30):
        rad = math.radians(a)
        d.line((wx, wy, wx + wr * math.cos(rad), wy + wr * math.sin(rad)), fill=far, width=3)
    # teal haze along the horizon
    for i in range(18):
        d.rectangle((0, horizon - 4 - i * 3, w, horizon - 1 - i * 3), fill=(82, 188, 175, max(0, 22 - i)))
    # near ground and fog
    d.polygon([(0, h), (0, h - 40)] + [(i, h - 40 - 14 * math.sin(i / 90.0)) for i in range(0, w + 40, 40)] + [(w, h)],
              fill=(6, 11, 12, 245))
    for i in range(30):
        d.rectangle((0, horizon - 60 + i * 4, w, horizon - 56 + i * 4), fill=(16, 34, 36, 4))

    out = Image.alpha_composite(base.convert("RGBA"), layer)
    # CRT scanlines and vignette
    scan = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scan)
    for y in range(0, h, 3):
        sd.line((0, y, w, y), fill=(0, 0, 0, 24))
    out = Image.alpha_composite(out, scan)
    vig = Image.new("L", (w, h), 0)
    vd = ImageDraw.Draw(vig)
    for i in range(18):
        inset = i * min(w, h) / 40
        vd.rectangle((inset, inset, w - inset, h - inset), outline=int(110 * (1 - i / 18) ** 2), width=int(min(w, h) / 40) + 1)
    out.paste(Image.new("RGBA", (w, h), (0, 0, 0, 255)), (0, 0), vig)
    return out.convert("RGB")


class MeridianBackdrop:
    """Animated, semi-transparent background drawn on the main window canvas behind the panels:
    a slowly turning wireframe globe (meridians), a Create-style gear, blinking lights on the skyline,
    rising embers and a CRT scan line. Faint colours are pre-blended with the background."""

    def __init__(self, canvas: tk.Canvas, animate: bool) -> None:
        self.cv = canvas
        self.animate = animate
        self.size = (0, 0)
        self.photo: Any = None
        self.phase = 0.0
        self.pending: str | None = None
        self.base: Image.Image | None = None
        self.panels: list[tuple[float, float, float, float]] = []
        self.image_item: int | None = None
        self.items: dict[str, Any] = {}
        self.particles: list[list[float]] = []
        self.rnd = random.Random(11)
        canvas.bind("<Configure>", self._on_configure, add="+")

    def _on_configure(self, event: tk.Event) -> None:
        if (event.width, event.height) == self.size:
            return
        if self.pending:
            self.cv.after_cancel(self.pending)
        self.pending = self.cv.after(120, lambda: self.rebuild(event.width, event.height))

    def rebuild(self, w: int, h: int) -> None:
        self.pending = None
        if w < 50 or h < 50:
            return
        self.size = (w, h)
        self.base = render_backdrop(w, h)
        self.cv.delete("backdrop")
        self.image_item = self.cv.create_image(0, 0, anchor="nw", tags=("backdrop",))
        self._compose()
        line = blend_hex(C_BG, C_TELEMETRY, 0.30)
        copper = blend_hex(C_BG, C_COPPER, 0.50)
        self.globe = (w * 0.36, h * 0.86, min(w, h) * 0.30)
        gx, gy, gr = self.globe
        self.items = {
            "rim": self.cv.create_oval(gx - gr, gy - gr, gx + gr, gy + gr, outline=line, width=1, tags=("backdrop",)),
            "meridians": [self.cv.create_oval(0, 0, 0, 0, outline=line, width=1, tags=("backdrop",)) for _ in range(6)],
            "prime": self.cv.create_oval(0, 0, 0, 0, outline=copper, width=2, tags=("backdrop",)),
            "parallels": [self.cv.create_oval(gx - gr * math.cos(lat), gy + gr * math.sin(lat) - gr * math.cos(lat) * 0.16,
                                              gx + gr * math.cos(lat), gy + gr * math.sin(lat) + gr * math.cos(lat) * 0.16,
                                              outline=blend_hex(C_BG, C_TELEMETRY, 0.20), width=1, tags=("backdrop",))
                          for lat in (-1.0, -0.55, 0.0, 0.55, 1.0)],
            "gear": self.cv.create_polygon(0, 0, 0, 0, 0, 0, outline=blend_hex(C_BG, C_COPPER, 0.30), fill="", width=2,
                                           tags=("backdrop",)),
            "scan": self.cv.create_line(0, 0, w, 0, fill=blend_hex(C_BG, C_TELEMETRY, 0.18), width=2, tags=("backdrop",)),
            "beacons": [self.cv.create_oval(0, 0, 0, 0, fill=C_COPPER, outline="", tags=("backdrop",)) for _ in range(5)],
        }
        horizon = h * 0.80
        self.beacon_pos = [(w * f, horizon - self.rnd.randint(40, 120)) for f in (0.08, 0.27, 0.41, 0.63, 0.86)]
        self.particles = [[self.rnd.uniform(0, w), self.rnd.uniform(h * 0.3, h), self.rnd.uniform(0.3, 1.1),
                           self.rnd.uniform(0, 6.28)] for _ in range(26)]
        self.items["sparks"] = [self.cv.create_oval(0, 0, 0, 0, fill=blend_hex(C_BG, C_COPPER, 0.60), outline="",
                                                    tags=("backdrop",)) for _ in self.particles]
        self.cv.tag_lower("backdrop")
        self.frame()

    def frame(self) -> None:
        """Draws one animation step (also used once when animations are off)."""
        if not self.items:
            return
        w, h = self.size
        gx, gy, gr = self.globe
        t = self.phase
        for i, item in enumerate(self.items["meridians"]):
            rx = gr * abs(math.cos(t + i * math.pi / 6))
            self.cv.coords(item, gx - rx, gy - gr, gx + rx, gy + gr)
        rx = gr * abs(math.sin(t * 1.0))
        self.cv.coords(self.items["prime"], gx - rx, gy - gr, gx + rx, gy + gr)
        # gear in the lower left corner, partly outside the window
        cx, cy, R = w * 0.04, h * 0.92, min(w, h) * 0.30
        pts: list[float] = []
        teeth = 14
        for k in range(teeth * 4):
            a = -t * 0.35 + k * math.pi * 2 / (teeth * 4)
            rr = R if (k % 4) in (1, 2) else R * 0.86
            pts += [cx + rr * math.cos(a), cy + rr * math.sin(a)]
        self.cv.coords(self.items["gear"], *pts)
        sy = (t * 60) % (h + 80) - 40
        self.cv.coords(self.items["scan"], 0, sy, w, sy)
        for k, (bx, by) in enumerate(self.beacon_pos):
            on = math.sin(t * 2.2 + k * 1.7) > 0.35
            s = 2.5 if on else 1.2
            self.cv.coords(self.items["beacons"][k], bx - s, by - s, bx + s, by + s)
        for p, item in zip(self.particles, self.items["sparks"]):
            p[1] -= p[2]
            p[3] += 0.05
            if p[1] < h * 0.25:
                p[0], p[1] = self.rnd.uniform(0, w), h + 5
            x = p[0] + math.sin(p[3]) * 6
            self.cv.coords(item, x - 1.2, p[1] - 1.2, x + 1.2, p[1] + 1.2)

    def set_panels(self, panels: list[tuple[float, float, float, float]]) -> None:
        """Translucent 'glass' panels are part of the background image, so the scene shows through them."""
        rounded = [tuple(round(v) for v in r) for r in panels]
        if rounded != self.panels:
            self.panels = rounded  # type: ignore[assignment]
            self._compose()

    def _compose(self) -> None:
        if self.base is None or self.image_item is None:
            return
        img = self.base.convert("RGBA")
        glass = Image.new("RGBA", img.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glass)
        for x0, y0, x1, y1 in self.panels:
            gd.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(6, 12, 14, 150))
            gd.rectangle((x0, y0, x1 - 1, y1 - 1), outline=(55, 78, 80, 230))
            gd.line((x0 + 1, y0 + 1, x1 - 2, y0 + 1), fill=(82, 188, 175, 40))
        self.photo = ImageTk.PhotoImage(Image.alpha_composite(img, glass).convert("RGB"), master=self.cv)
        self.cv.itemconfigure(self.image_item, image=self.photo)

    def tick(self) -> None:
        if self.animate:
            self.phase += 0.012
            self.frame()


KEYGEN_SCROLL = ("PROJECT MERIDIAN  ///  EXPEDITION NETWORK ONLINE  ///  BRASS * GEARS * COPPER * STEAM  ///  "
                 "MINECRAFT 1.21.1 + NEOFORGE  ///  GREETINGS TO EVERY EXPLORER OF THE MERIDIAN  ///  "
                 "KEEP THE GEARS TURNING  ///  ESC - BACK TO BASE    M - SOUND ON/OFF  ///          ")
C_BRASS, C_BRASS_HI, C_BRASS_LO = "#b5832f", "#e2ac57", "#5a3f16"


def keygen_sound(path: Path | None, on: bool) -> bool:
    """Loops the intro music (Windows only); returns whether it is playing."""
    try:
        import winsound
    except ImportError:
        return False
    try:
        if on and path is not None:
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP
                               | winsound.SND_NODEFAULT)
            return True
        winsound.PlaySound(None, 0)
    except RuntimeError:
        pass
    return False


class KeygenShow:
    """Easter egg behind the Meridian emblem: a keygen/demoscene-style intro with music, drawn on the launcher's
    own canvas after the menu slid away. All graphics are drawn here (no bundled images); canvas items are created
    once (tag "keygen") and only moved each frame."""

    FPS_MS = 33
    TAG = "keygen"

    def __init__(self, canvas: tk.Canvas, width: int, height: int, on_exit: Callable[[], None],
                 sound: bool = True) -> None:
        self.cv = canvas
        self.on_exit = on_exit
        self.W, self.H = width, height
        before = set(canvas.find_all())
        self.bg = canvas.create_rectangle(0, 0, width + px(2000), height + px(2000), fill=C_BG, outline="")
        self.music = resource_file("meridian-keygen.wav")
        self.sound_on = keygen_sound(self.music, True) if sound else False
        self.start = time.perf_counter()
        self.closed = False
        rnd = random.Random(1985)
        W, H = self.W, self.H
        cv = self.cv
        # starfield
        self.stars = [[rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0.05, 1)] for _ in range(80)]
        self.star_items = [cv.create_rectangle(0, 0, 0, 0, fill="#9fb3b4", outline="") for _ in self.stars]
        # perspective grid floor
        self.horizon = H * 0.66
        self.grid_h = [cv.create_line(0, 0, 0, 0, fill="#123c3a") for _ in range(12)]
        self.grid_v = [cv.create_line(W / 2 + j * W / 70, self.horizon, W / 2 + j * W / 7, H, fill="#123c3a")
                       for j in range(-10, 11)]
        # copper raster bars
        self.bar_cols = []
        for i in range(4):
            base = (208, 121, 64) if i % 2 == 0 else (82, 188, 175)
            self.bar_cols.append([blend_hex("#020405", "#%02x%02x%02x" % base, 1 - abs(s - 4) / 4.6) for s in range(9)])
        self.bar_items = [[cv.create_rectangle(0, 0, W, 0, fill=c, outline="") for c in cols] for cols in self.bar_cols]
        # gears (left big, left small meshing, right big)
        self.gears = [
            {"x": W * 0.13, "y": H * 0.47, "r": px(54), "teeth": 14, "speed": 0.9},
            {"x": W * 0.13 + px(54) + px(29), "y": H * 0.47 - px(40), "r": px(30), "teeth": 8, "speed": -0.9 * 14 / 8},
            {"x": W * 0.87, "y": H * 0.47, "r": px(54), "teeth": 14, "speed": -0.9},
        ]
        for g in self.gears:
            g["poly"] = cv.create_polygon(0, 0, 0, 0, fill=C_BRASS, outline=C_BRASS_HI, width=2)
            g["hub"] = cv.create_oval(g["x"] - g["r"] * 0.32, g["y"] - g["r"] * 0.32, g["x"] + g["r"] * 0.32,
                                      g["y"] + g["r"] * 0.32, fill=C_BRASS_LO, outline=C_BRASS_HI)
            g["axle"] = [cv.create_line(0, 0, 0, 0, fill="#8f9a9b", width=max(2, px(4))) for _ in range(2)]
        # voxel blocks orbiting the emblem: 6 faces each, drawn back to front
        self.cubes = [{"phase": k * math.pi, "faces": [cv.create_polygon(0, 0, 0, 0, outline="") for _ in range(6)]}
                      for k in range(2)]
        # 3D Meridian emblem (two diamonds + cross, extruded)
        self.emblem_lines = []
        for _ in range(28):
            self.emblem_lines.append(cv.create_line(0, 0, 0, 0, width=max(2, px(3)), capstyle="round"))
        # title letters and the sine scroller
        self.title_font = tkfont.Font(family="Segoe UI Black", size=max(14, round(26 * min(W / 780, H / 470))))
        self.title = "PROJECT MERIDIAN"
        self.title_items = [cv.create_text(0, 0, text=ch, font=self.title_font, fill=C_INK) for ch in self.title]
        widths = [self.title_font.measure(ch) for ch in self.title]
        x = W / 2 - sum(widths) / 2
        self.title_x = []
        for w in widths:
            self.title_x.append(x + w / 2)
            x += w
        self.scroll_font = tkfont.Font(family="Consolas", size=max(12, round(22 * min(W / 780, H / 470))),
                                       weight="bold")
        self.char_w = self.scroll_font.measure("M")
        self.scroll_items = [cv.create_text(0, 0, text="", font=self.scroll_font) for _ in range(W // self.char_w + 2)]
        self.hint = cv.create_text(W - px(8), H - px(6), anchor="se", font=("Consolas", 8), fill="#4d6466",
                                   text=self._hint_text())
        self.back = cv.create_text(px(14), px(12), anchor="nw", text="\u25c4 МЕНЮ", font=("Consolas", 10, "bold"),
                                   fill=C_TELEMETRY, activefill=C_COPPER)
        cv.tag_bind(self.back, "<Button-1>", lambda _e: self.on_exit())
        cv.tag_bind(self.back, "<Enter>", lambda _e: cv.configure(cursor="hand2"))
        cv.tag_bind(self.back, "<Leave>", lambda _e: cv.configure(cursor=""))
        self.flash = cv.create_rectangle(0, 0, W, H, fill="#ffffff", outline="")
        for item in set(cv.find_all()) - before:
            cv.addtag_withtag(self.TAG, item)
        self.tick()

    def _hint_text(self) -> str:
        return f"ESC — меню    M — звук {'вкл' if self.sound_on else 'выкл'}"

    def toggle_sound(self) -> None:
        self.sound_on = keygen_sound(self.music, not self.sound_on)
        self.cv.itemconfigure(self.hint, text=self._hint_text())

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        keygen_sound(None, False)
        try:
            self.cv.delete(self.TAG)
            self.cv.configure(cursor="")
        except tk.TclError:
            pass

    @staticmethod
    def _rot(p: tuple[float, float, float], ay: float, ax: float) -> tuple[float, float, float]:
        x, y, z = p
        x, z = x * math.cos(ay) + z * math.sin(ay), -x * math.sin(ay) + z * math.cos(ay)
        y, z = y * math.cos(ax) - z * math.sin(ax), y * math.sin(ax) + z * math.cos(ax)
        return x, y, z

    def _proj(self, p: tuple[float, float, float], cx: float, cy: float, s: float) -> tuple[float, float]:
        k = 3.2 / (3.2 + p[2])
        return cx + p[0] * s * k, cy + p[1] * s * k

    def tick(self) -> None:
        if self.closed:
            return
        try:
            self._frame(time.perf_counter() - self.start)
        except tk.TclError:
            self.close()
            return
        self.cv.after(self.FPS_MS, self.tick)

    def _frame(self, t: float) -> None:
        cv, W, H = self.cv, self.W, self.H
        beat = 60 / 140                                     # the music's tempo
        kick = math.exp(-((t % beat) / beat) * 5)            # 1 on every beat, decays
        # intro flash
        if t < 0.6:
            cv.itemconfigure(self.flash, fill=blend_hex("#020405", "#ffffff", 1 - t / 0.6), state="normal")
        else:
            cv.itemconfigure(self.flash, state="hidden")
        # stars fly towards the viewer
        for s, item in zip(self.stars, self.star_items):
            s[2] -= 0.006 + 0.01 * kick
            if s[2] <= 0.04:
                s[0], s[1], s[2] = random.uniform(-1, 1), random.uniform(-1, 1), 1.0
            sx, sy = W / 2 + s[0] / s[2] * W * 0.25, H * 0.4 + s[1] / s[2] * H * 0.25
            size = max(1, px(2.6 * (1 - s[2])))
            cv.coords(item, sx, sy, sx + size, sy + size)
            cv.itemconfigure(item, fill=blend_hex("#1b2a2b", "#cfe3e0", 1 - s[2]))
        # grid floor scrolls towards the viewer
        off = (t * 1.6) % 1.0
        for i, item in enumerate(self.grid_h):
            d = (i + off) / len(self.grid_h)
            y = self.horizon + (H - self.horizon) * d * d
            cv.coords(item, 0, y, W, y)
            cv.itemconfigure(item, fill=blend_hex("#020405", "#1f7f77", 0.25 + 0.75 * d))
        # raster bars swing behind the logo
        for i, items in enumerate(self.bar_items):
            cy = H * 0.3 + math.sin(t * 1.7 + i * 0.85) * H * 0.17
            strip = max(2, px(3))
            for s, item in enumerate(items):
                y0 = cy + (s - 4.5) * strip
                cv.coords(item, 0, y0, W, y0 + strip)
        # gears
        for g in self.gears:
            a0 = t * g["speed"]
            pts = []
            n = g["teeth"]
            for k in range(n * 4):
                a = a0 + k * math.pi * 2 / (n * 4)
                r = g["r"] * (1.0 if k % 4 in (1, 2) else 0.8)
                pts += [g["x"] + math.cos(a) * r, g["y"] + math.sin(a) * r]
            cv.coords(g["poly"], *pts)
            for j, item in enumerate(g["axle"]):
                a = a0 + j * math.pi / 2
                r = g["r"] * 0.3
                cv.coords(item, g["x"] - math.cos(a) * r, g["y"] - math.sin(a) * r, g["x"] + math.cos(a) * r,
                          g["y"] + math.sin(a) * r)
        # emblem: outer diamond (copper), inner diamond (teal), cross lines; extruded front/back
        cx, cy, sc = W / 2, H * 0.43, px(92) * (1 + 0.06 * kick)
        ay, ax = t * 1.1, math.sin(t * 0.7) * 0.35
        depth = 0.16
        segs: list[tuple[tuple, tuple, str]] = []
        for r, col in ((1.0, C_COPPER), (0.46, C_TELEMETRY)):
            for z in (-depth, depth):
                ring = [(0, -r, z), (r, 0, z), (0, r, z), (-r, 0, z)]
                segs += [(ring[k], ring[(k + 1) % 4], col) for k in range(4)]
            segs += [((0, -r, -depth), (0, -r, depth), col), ((r, 0, -depth), (r, 0, depth), col),
                     ((0, r, -depth), (0, r, depth), col), ((-r, 0, -depth), (-r, 0, depth), col)]
        e = 0.94  # cross lines reach past the outer diamond, as in the 2D mark
        segs += [((-e, -e, z), (e, e, z), C_COPPER) for z in (-0.02, 0.02)]
        segs += [((e, -e, z), (-e, e, z), C_COPPER) for z in (-0.02, 0.02)]
        for item, (a, b, col) in zip(self.emblem_lines, segs):
            pa, pb = self._rot(a, ay, ax), self._rot(b, ay, ax)
            shade = 0.55 + 0.45 * (1 - (pa[2] + pb[2] + 2) / 4)
            cv.coords(item, *self._proj(pa, cx, cy, sc), *self._proj(pb, cx, cy, sc))
            cv.itemconfigure(item, fill=blend_hex("#020405", col, shade))
        # voxel blocks orbit the emblem (copper ore / teal crystal), with simple shading and back-face culling
        for k, cube in enumerate(self.cubes):
            ph = t * 0.9 + cube["phase"]
            ox, oz = math.cos(ph) * 2.0, math.sin(ph) * 0.8
            oy = math.sin(t * 2 + k) * 0.25 + 0.15
            spin = t * (1.4 + 0.3 * k)
            hs = 0.24
            corners = [(sx * hs, sy * hs, sz * hs) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
            rc = [self._rot(c, spin, 0.5) for c in corners]
            wc = [(x + ox, y + oy, z + oz) for x, y, z in rc]
            faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
            top = "#d07940" if k == 0 else "#52bcaf"
            side = "#7a4626" if k == 0 else "#2b6f68"
            order = sorted(range(6), key=lambda f: -sum(wc[i][2] for i in faces[f]))
            for item_idx, f in enumerate(order):
                quad = faces[f]
                p = [self._proj(wc[i], cx, cy, sc * 0.9) for i in quad]
                ux, uy = p[1][0] - p[0][0], p[1][1] - p[0][1]
                vx, vy = p[2][0] - p[0][0], p[2][1] - p[0][1]
                visible = (ux * vy - uy * vx) < 0
                item = cube["faces"][item_idx]
                if not visible:
                    cv.itemconfigure(item, state="hidden")
                    continue
                ny = sum(rc[i][1] for i in quad) / 4
                col = top if ny < -0.2 else side
                light = 0.6 + 0.4 * (1 - (sum(wc[i][2] for i in quad) / 4 + 2.5) / 5)
                cv.coords(item, *[v for xy in p for v in xy])
                cv.itemconfigure(item, state="normal", fill=blend_hex("#020405", col, light),
                                 outline=blend_hex("#020405", col, min(1, light + 0.3)))
            behind = oz > 0
            for item in cube["faces"]:
                (cv.tag_lower if behind else cv.tag_raise)(item, self.emblem_lines[0] if behind else self.emblem_lines[-1])
        # title: per-letter bounce and colour cycle
        for i, (item, x) in enumerate(zip(self.title_items, self.title_x)):
            y = H * 0.1 + math.sin(t * 4 + i * 0.5) * px(6) - kick * px(4)
            tcol = (math.sin(t * 2 + i * 0.35) + 1) / 2
            cv.coords(item, x, y)
            cv.itemconfigure(item, fill=blend_hex(C_COPPER, C_INK if i < 7 else C_TELEMETRY, tcol))
        # sine scroller
        pos = t * px(150)
        first = int(pos // self.char_w)
        shift = pos % self.char_w
        for j, item in enumerate(self.scroll_items):
            ch = KEYGEN_SCROLL[(first + j) % len(KEYGEN_SCROLL)]
            x = j * self.char_w - shift + self.char_w / 2
            y = H * 0.86 + math.sin(x * 0.018 + t * 4) * px(14)
            hue = (math.sin(x * 0.01 + t * 1.5) + 1) / 2
            cv.coords(item, x, y)
            cv.itemconfigure(item, text=ch, fill=blend_hex(C_TELEMETRY, C_COPPER, hue))
        cv.tag_raise(self.hint)
        cv.tag_raise(self.back)
        cv.tag_raise(self.flash)


class MeridianLauncher(tk.Tk):
    def __init__(self) -> None:
        global UI_SCALE
        enable_dpi_awareness()
        set_app_user_model_id()
        super().__init__()
        self.withdraw()  # shown once sized and placed: no flash of a cut-off window
        self._icon_images: list[Any] = []
        self.icon_source = apply_window_icon(self, self._icon_images)
        ensure_dirs()
        self.state_data = load_state()
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.busy = False

        # Interface scale follows Windows; a fixed value only through --ui-scale=125 (layout tests).
        self.state_data.pop("ui_scale", None)
        cli_scale = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--ui-scale=")), "auto")
        self.ui_scale_choice = normalize_ui_scale_choice(cli_scale)
        self._animations = windows_animations_enabled()
        self._d = DENSITY[0]
        self._root_frame: tk.Frame | None = None

        self.title(f"{APP_NAME} {APP_VERSION}")
        self.configure(bg=C_BG)

        self.username_var = tk.StringVar(value=str(self.state_data.get("username", "")))
        self.auth_var = tk.StringVar(value="microsoft" if self.state_data.get("auth_mode") == "microsoft" else "offline")
        self.ram_var = tk.IntVar(value=int(self.state_data.get("ram_gb", 8)))
        self.skin_source_var = tk.StringVar(value="")
        self.skin_nick_var = tk.StringVar(value="")
        self.skin_slim_var = tk.BooleanVar(value=False)
        self.skin_cmd_var = tk.StringVar(value="")
        self.skin_info_var = tk.StringVar(value="")
        self.skin_dialog: tk.Toplevel | None = None
        self.log_dialog: tk.Toplevel | None = None
        self.log_dialog_text: tk.Text | None = None
        self.log_lines: list[str] = []
        self.launcher_update_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Система готова")
        self.detail_var = tk.StringVar(value=f"Minecraft {MC_VERSION} • NeoForge {NEOFORGE_VERSION}")
        self.progress_var = tk.StringVar(value="MERIDIAN_SYS // IDLE")
        self.account_name_var = tk.StringVar(value="")
        self.account_type_var = tk.StringVar(value="")
        self.account_note_var = tk.StringVar(value="")
        self.auth_dialog: tk.Toplevel | None = None
        self.auth_code_var = tk.StringVar(value="--------")
        self.auth_step_var = tk.StringVar(value="Получаю код у Microsoft…")
        self.auth_uri = "https://microsoft.com/devicelogin"
        self.skin_photo: ImageTk.PhotoImage | None = None
        self._animation_phase = 0.0
        self.pack_value = tk.StringVar(value=str(self.state_data.get("pack_version") or "Stable"))
        self.core_value = tk.StringVar(value=f"{MC_VERSION} // NF {NEOFORGE_VERSION}")
        self.account_value = tk.StringVar(value="OFFLINE")

        self._layout_main()
        self.after(100, self._drain_events)
        self.after(120, self._animate_ui)
        self.after(400, self._initial_check)
        self.after(900, self._refresh_skin_async)

    def _set_scale(self, scale: float) -> None:
        global UI_SCALE
        UI_SCALE = scale
        # Fonts are given in points: Tk turns them into pixels with this factor (96 DPI baseline = 100 %).
        self.tk.call("tk", "scaling", scale * 96.0 / 72.0)

    def _layout_main(self) -> None:
        """Builds the main window in the first layout that fits the work area of the monitor (taskbar, title bar
        and frame excluded) at the chosen interface scale; only when no layout fits is the scale lowered, in 5 %
        steps, and the limit is shown next to the scale setting. The window never needs scrolling."""
        chosen = resolve_ui_scale(self.ui_scale_choice)
        left, top, work_w, work_h = work_area(None)
        extra_w, extra_h = frame_extra(True)
        avail_w, avail_h = work_w - extra_w, work_h - extra_h
        tried: list[dict[str, Any]] = []
        scale = chosen
        picked: dict[str, Any] | None = None
        while picked is None:
            for columns, density in LAYOUTS:
                req_w, req_h = self._build_main(scale, columns, density)
                attempt = {"scale": round(scale, 3), "columns": columns, "density": density, "req": (req_w, req_h)}
                tried.append(attempt)
                if req_w <= avail_w and req_h <= avail_h:
                    picked = attempt
                    break
            if picked is None:
                if scale <= MIN_EFFECTIVE_SCALE + 1e-6:
                    picked = dict(tried[-1], fits=False)
                    break
                scale = max(MIN_EFFECTIVE_SCALE, round(scale - 0.05, 2))
        if picked.get("columns") != tried[-1]["columns"] or picked.get("density") != tried[-1]["density"] or picked["scale"] != tried[-1]["scale"]:
            self._build_main(picked["scale"], picked["columns"], picked["density"])
        req_w, req_h = picked["req"]
        w = min(max(req_w, px(PREFERRED_SIZE[0])), avail_w)
        h = min(max(req_h, px(PREFERRED_SIZE[1])), avail_h)
        x = left + max(0, (work_w - (w + extra_w)) // 2)
        y = top + max(0, (work_h - (h + extra_h)) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(min(req_w, avail_w), min(req_h, avail_h))
        self.layout_info = {"chosen_scale": round(chosen, 3), "effective_scale": picked["scale"], "columns": picked["columns"],
                            "density": picked["density"], "required": (req_w, req_h), "available": (avail_w, avail_h),
                            "work": (left, top, work_w, work_h), "frame": (extra_w, extra_h), "size": (w, h), "pos": (x, y),
                            "fits": picked.get("fits", True), "tried": len(tried)}
        if picked["scale"] < chosen - 1e-6:
            self._log(f"Окно не помещается на экран при масштабе {round(chosen * 100)}%: интерфейс уменьшен до "
                      f"{round(picked['scale'] * 100)}%.")
        self.deiconify()
        dark_title_bar(self)

    def _build_main(self, scale: float, columns: int, density: int) -> tuple[int, int]:
        """(Re)builds the whole main window content and returns the size it needs (client area, pixels)."""
        self._set_scale(scale)
        self._d = DENSITY[density]
        self._columns = columns
        if self._root_frame is not None:
            self._root_frame.destroy()
        self._build_style()
        self._build_ui()
        self._apply_ui_scale(self)
        self._place_header()
        self._sync_auth_fields()
        self.update_idletasks()
        return self._relayout(0, 0)

    @staticmethod
    def _scaled_pad(value: Any, tk_app: tk.Misc) -> Any:
        parts = value if isinstance(value, (tuple, list)) else tk_app.tk.splitlist(str(value))
        nums = [px(int(float(str(part)))) for part in parts]
        return nums[0] if len(nums) == 1 else tuple(nums)

    def _apply_ui_scale(self, top: tk.Misc) -> None:
        """Scales pixel paddings, wrap widths, frame/canvas sizes and canvas drawings built at 100 %."""
        if abs(UI_SCALE - 1.0) < 1e-6:
            return
        pending: list[tk.Misc] = [top]
        while pending:
            widget = pending.pop()
            pending.extend(widget.winfo_children())
            if getattr(widget, "_meridian_scaled", False):
                continue
            widget._meridian_scaled = True  # type: ignore[attr-defined]
            try:
                self._scale_widget(widget)
            except tk.TclError:
                pass

    def _scale_widget(self, widget: tk.Misc) -> None:
        keys = widget.keys() if hasattr(widget, "keys") else []
        if not isinstance(widget, (tk.Tk, tk.Toplevel)):
            for opt in ("padx", "pady", "wraplength"):
                if opt in keys:
                    try:
                        value = int(float(str(widget.cget(opt))))
                    except (ValueError, tk.TclError):
                        continue
                    if value:
                        widget.configure(**{opt: px(value)})
            if isinstance(widget, (tk.Frame, tk.Canvas)) and not isinstance(widget, RamSlider) and not getattr(widget, "_meridian_scroll", False):
                for opt in ("width", "height"):
                    try:
                        value = int(float(str(widget.cget(opt))))
                    except (ValueError, tk.TclError):
                        continue
                    if value > 0:
                        widget.configure(**{opt: px(value)})
            if isinstance(widget, tk.Canvas) and not isinstance(widget, RamSlider) and not getattr(widget, "_meridian_scroll", False):
                widget.scale("all", 0, 0, UI_SCALE, UI_SCALE)
                for item in widget.find_all():
                    try:
                        line_width = float(widget.itemcget(item, "width"))
                    except (ValueError, tk.TclError):
                        continue
                    if line_width > 0:
                        widget.itemconfigure(item, width=px(line_width))
            manager = widget.winfo_manager()
            if manager in ("pack", "grid"):
                info = widget.pack_info() if manager == "pack" else widget.grid_info()
                changes = {}
                for opt in ("padx", "pady", "ipadx", "ipady"):
                    if opt in info:
                        changes[opt] = self._scaled_pad(info[opt], self)
                if changes:
                    if manager == "pack":
                        widget.pack_configure(**changes)
                    else:
                        widget.grid_configure(**changes)
        columns, rows = widget.grid_size()
        for index in range(columns):
            minsize = int(widget.grid_columnconfigure(index, "minsize") or 0)
            if minsize:
                widget.grid_columnconfigure(index, minsize=px(minsize))
        for index in range(rows):
            minsize = int(widget.grid_rowconfigure(index, "minsize") or 0)
            if minsize:
                widget.grid_rowconfigure(index, minsize=px(minsize))

    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=C_BG)
        style.configure("Panel.TFrame", background=C_PANEL)
        style.configure("TLabel", background=C_BG, foreground=C_INK, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=C_PANEL, foreground=C_INK, font=("Segoe UI", 10))
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor=C_FIELD,
            background=C_AMBER,
            bordercolor=C_FIELD,
            lightcolor=C_AMBER,
            darkcolor=C_AMBER,
        )

    def _button(self, parent: tk.Misc, text: str, command: Callable[[], None], *, accent: bool = False) -> tk.Button:
        bg = C_AMBER if accent else C_PANEL_2
        fg = "#161106" if accent else C_INK
        active_bg = C_AMBER_2 if accent else "#211f19"
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground="#161106" if accent else C_INK,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=C_AMBER if accent else C_LINE,
            highlightcolor=C_AMBER_2,
            font=("Consolas", 10, "bold"),
            cursor="hand2",
            padx=14,
            pady=self._d["btn_pady"],
        )
        return btn

    def _entry(self, parent: tk.Misc, variable: tk.StringVar) -> tk.Entry:
        return tk.Entry(
            parent,
            textvariable=variable,
            bg=C_FIELD,
            fg=C_INK,
            insertbackground=C_AMBER,
            disabledbackground=C_FIELD,
            disabledforeground="#65645f",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=C_LINE,
            highlightcolor=C_AMBER,
            font=("Segoe UI", 10),
        )

    def _section(self, parent: tk.Misc, text: str, first: bool = False) -> None:
        d = self._d
        tk.Label(parent, text=text, bg=C_PANEL, fg=C_AMBER, font=("Consolas", 10, "bold")).pack(
            anchor="w", padx=d["pad"], pady=((d["sec"][0] + 2) if first else d["sec"][0], d["sec"][1])
        )

    def _build_ui(self) -> None:
        # The whole window is one canvas: animated background, translucent "glass" panels baked into it,
        # texts drawn on it with a dark outline, and the interactive controls placed on top as solid chips.
        root = tk.Canvas(self, bg=C_BG, bd=0, highlightthickness=0)
        root._meridian_scroll = True  # type: ignore[attr-defined]  # drawn at real pixels, not rescaled
        root.pack(fill="both", expand=True)
        self._root_frame = root
        self._windows: dict[str, int] = {}
        self._relayout_pending = False
        self.backdrop = MeridianBackdrop(root, self._animations)
        root.bind("<Configure>", self._on_canvas_configure, add="+")
        root.bind("<Button-1>", self._on_canvas_click, add="+")
        root.bind("<Motion>", self._on_canvas_motion, add="+")
        self.update_link = tk.Label(root, textvariable=self.launcher_update_var, bg=C_BG, fg=C_TELEMETRY,
                                    font=("Consolas", 9, "bold"), cursor="hand2")
        self.update_link.bind("<Button-1>", lambda _e: self._update_launcher())
        self._build_account(root)
        self._build_settings(root)
        self._build_launch(root)
        for var in (self.status_var, self.detail_var, self.ram_var, self.pack_value, self.core_value, self.account_value):
            var.trace_add("write", lambda *_: self._request_relayout())

    def _build_account(self, root: tk.Canvas) -> None:
        d = self._d
        self.profile_card = profile = tk.Frame(root, bg=C_PANEL_2, highlightthickness=1, highlightbackground=C_LINE)
        self._skin_base = d["skin"]
        skin_box = tk.Frame(profile, bg=C_FIELD, width=d["skin"], height=d["skin"])
        skin_box.pack_propagate(False)
        skin_box.pack(side="left", padx=d["item_gap"], pady=d["item_gap"])
        self.skin_label = tk.Label(skin_box, text="NO\nSKIN", bg=C_FIELD, fg=C_AMBER,
                                   font=("Consolas", d["skin_font"], "bold"), justify="center")
        self.skin_label.pack(fill="both", expand=True)
        profile_text = tk.Frame(profile, bg=C_PANEL_2)
        profile_text.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=d["item_gap"])
        tk.Label(profile_text, textvariable=self.account_name_var, bg=C_PANEL_2, fg=C_INK,
                 font=("Segoe UI Semibold", 13 if d["hints"] else 12), anchor="w").pack(fill="x")
        tk.Label(profile_text, textvariable=self.account_type_var, bg=C_PANEL_2, fg=C_AMBER,
                 font=("Consolas", 9, "bold"), anchor="w").pack(fill="x", pady=(3, 0))
        tk.Label(profile_text, textvariable=self.account_note_var, bg=C_PANEL_2, fg=C_MUTED, font=("Segoe UI", 9),
                 anchor="w", wraplength=165, justify="left").pack(fill="x", pady=(3, 0))

        # segmented switch: licensed / unlicensed
        self.mode_bar = tk.Frame(root, bg=C_LINE)
        seg = dict(variable=self.auth_var, indicatoron=False, command=self._auth_mode_changed, bg=C_PANEL_2, fg=C_MUTED,
                   selectcolor="#3b2618", activebackground="#2a1d14", activeforeground=C_AMBER, relief="flat", bd=0,
                   offrelief="flat", font=("Consolas", 9, "bold"), cursor="hand2", pady=6)
        self.microsoft_radio = tk.Radiobutton(self.mode_bar, text="ЛИЦЕНЗИЯ", value="microsoft", **seg)
        self.microsoft_radio.pack(side="left", fill="x", expand=True, padx=(1, 0), pady=1)
        self.offline_radio = tk.Radiobutton(self.mode_bar, text="БЕЗ ЛИЦЕНЗИИ", value="offline", **seg)
        self.offline_radio.pack(side="left", fill="x", expand=True, padx=1, pady=1)

        self.login_btn = self._button(root, "ВОЙТИ ЧЕРЕЗ MICROSOFT", self._login_microsoft)
        self.logout_btn = self._button(root, "ВЫЙТИ", self._logout_microsoft)
        self.username_entry = self._entry(root, self.username_var)
        self.username_entry.configure(font=("Segoe UI", 10))
        if not d["hints"]:
            Tooltip(self.login_btn, lambda: MS_HINT)
            Tooltip(self.username_entry, lambda: OFFLINE_HINT)
        self.username_var.trace_add("write", lambda *_: self._sync_auth_fields())
        self.skin_btn = self._button(root, "МОЙ СКИН", self._open_skin_dialog)

    def _build_settings(self, root: tk.Canvas) -> None:
        self.ram_scale = RamSlider(root, self.ram_var, from_=4, to=16)
        self.folder_btn = self._button(root, "ПАПКА ИГРЫ", self._open_game_folder)
        self.logs_btn = self._button(root, "ЖУРНАЛ", self._open_log_dialog)
        self.repair_btn = self._button(root, "ПРОВЕРИТЬ / ПОЧИНИТЬ ФАЙЛЫ", self._repair_pack)
        Tooltip(self.repair_btn, lambda: "Сверяет каждый файл сборки с эталоном (SHA-256) и заново скачивает только "
                                         "повреждённые. Миры, скриншоты и настройки не затрагиваются.")

    def _build_launch(self, root: tk.Canvas) -> None:
        d = self._d
        self.progress_shell = tk.Frame(root, bg=C_PANEL_2, highlightthickness=1, highlightbackground=C_LINE)
        self.progress = ttk.Progressbar(self.progress_shell, mode="determinate", maximum=100)
        self.progress.pack(fill="x", padx=1, pady=(1, 5))
        tk.Label(self.progress_shell, textvariable=self.progress_var, bg=C_PANEL_2, fg=C_MUTED, font=("Consolas", 9),
                 anchor="w").pack(fill="x", padx=12, pady=(0, 6))
        initial_play_text = "ИГРАТЬ" if any(INSTANCE_DIR.iterdir()) else "УСТАНОВИТЬ И ИГРАТЬ"
        self.play_btn = self._button(root, initial_play_text, self._play, accent=True)
        self.play_btn.configure(font=("Consolas", d["play_font"], "bold"), pady=d["play_pady"])

        self.console_wrap = console_wrap = tk.Frame(root, bg=C_FIELD, highlightthickness=1, highlightbackground=C_LINE)
        log_head = tk.Frame(console_wrap, bg=C_FIELD)
        log_head.pack(fill="x", padx=12, pady=(6, 0))
        tk.Label(log_head, text="/// ЖУРНАЛ ДИАГНОСТИКИ", bg=C_FIELD, fg=C_AMBER, font=("Consolas", 8, "bold")).pack(side="left")
        more = tk.Label(log_head, text="ОТКРЫТЬ ПОЛНОСТЬЮ ›", bg=C_FIELD, fg=C_TELEMETRY, font=("Consolas", 8, "bold"),
                        cursor="hand2")
        more.pack(side="right")
        more.bind("<Button-1>", lambda _e: self._open_log_dialog())
        log_frame = tk.Frame(console_wrap, bg=C_FIELD)
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_frame, height=d["log_lines"], width=40, bg=C_FIELD, fg="#a4a39c",
                                insertbackground=C_AMBER, relief="flat", wrap="word", font=("Consolas", 9), padx=12, pady=6)
        log_bar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_bar.set)
        log_bar.pack(side="right", fill="y")  # the only scrolling area: the message log
        self.log_text.pack(side="left", fill="both", expand=True)
        self.log_text.configure(state="disabled")
        for line in self.log_lines[-50:]:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", line + "\n")
            self.log_text.configure(state="disabled")
        if not self.log_lines:
            self._log(f"Project Meridian Launcher {APP_VERSION}. Игра установлена отдельно от обычного .minecraft.")

    # ---------- canvas layout ----------
    def _on_canvas_configure(self, event: tk.Event) -> None:
        if getattr(self, "_show_mode", None):
            return  # the menu is off screen; it is laid out again when it slides back
        self._place_header_right(event.width)
        self._request_relayout()

    def _request_relayout(self) -> None:
        if getattr(self, "_relayout_pending", True) or getattr(self, "_show_mode", None):
            return
        self._relayout_pending = True
        self.after_idle(self._relayout_now)

    def _relayout_now(self) -> None:
        self._relayout_pending = False
        cv = self._root_frame
        try:
            self._relayout(cv.winfo_width(), cv.winfo_height())
        except tk.TclError:
            pass

    def _otext(self, x: float, y: float, text: str, font: Any, fill: str, width: float = 0, anchor: str = "nw") -> int:
        """Text drawn straight on the background with a dark outline so it stays readable over the scene."""
        cv = self._root_frame
        o = max(1, px(1))
        for dx, dy in ((-o, 0), (o, 0), (0, -o), (0, o), (-o, -o), (o, o), (-o, o), (o, -o)):
            cv.create_text(x + dx, y + dy, text=text, font=font, fill=C_TEXT_OUTLINE, width=width, anchor=anchor,
                           tags=("ui",))
        return cv.create_text(x, y, text=text, font=font, fill=fill, width=width, anchor=anchor, tags=("ui",))

    def _text_block(self, x: float, y: float, text: str, font: Any, fill: str, width: float) -> float:
        item = self._otext(x, y, text, font, fill, width=width)
        box = self._root_frame.bbox(item)
        return box[3] if box else y

    def _win(self, widget: tk.Misc, x: float, y: float, w: float, h: float) -> None:
        cv = self._root_frame
        key = str(widget)
        if key not in self._windows:
            self._windows[key] = cv.create_window(x, y, window=widget, anchor="nw", width=w, height=h)
        else:
            cv.coords(self._windows[key], x, y)
            cv.itemconfigure(self._windows[key], width=w, height=h, state="normal")

    def _flow(self, spec: list[tuple[str, Any]], x0: float, x1: float, y: float, fill_to: float | None = None) -> float:
        d = self._d
        width = x1 - x0
        for kind, val in spec:
            if kind == "gap":
                y += px(val)
            elif kind == "title":
                y = self._text_block(x0, y + px(d["sec"][0]), val, ("Consolas", 10, "bold"), C_AMBER, width)
                y += px(d["sec"][1])
            elif kind == "hint":
                y = self._text_block(x0, y, val, ("Segoe UI", 9), C_HINT, width)
            elif kind == "label":
                y = self._text_block(x0, y, val, ("Consolas", 8, "bold"), C_HINT, width)
            elif kind == "status":
                y = self._text_block(x0, y, self.status_var.get(), ("Segoe UI Black", d["status_font"]), C_INK, width)
                y = self._text_block(x0, y + px(2), self.detail_var.get(), ("Consolas", 10), C_HINT, width)
            elif kind == "w":
                h = val.winfo_reqheight()
                if val is self.username_entry:
                    h += 2 * px(d["entry_ipady"])
                self._win(val, x0, y, width, h)
                y += h
            elif kind == "row":
                gap = px(8)
                fixed = sum(w.winfo_reqwidth() for w, weight in val if not weight)
                flex = max(1, sum(weight for _w, weight in val))
                free = width - fixed - gap * (len(val) - 1)
                h = max(w.winfo_reqheight() for w, _weight in val)
                x = x0
                for w, weight in val:
                    ww = free * weight / flex if weight else w.winfo_reqwidth()
                    self._win(w, x, y, ww, h)
                    x += ww + gap
                y += h
            elif kind == "ram":
                h = self.ram_scale.winfo_reqheight()
                value_w = px(64)
                self._win(self.ram_scale, x0, y, width - value_w, h)
                mid = y + h / 2
                self._otext(x1 - px(30), mid, str(self.ram_var.get()), ("Consolas", 13, "bold"), C_AMBER, anchor="e")
                self._otext(x1, mid, "ГБ", ("Consolas", 9, "bold"), C_HINT, anchor="e")
                y += h
            elif kind == "info":
                font_c, font_v = ("Consolas", 8, "bold"), ("Consolas", 9, "bold")
                for caption, var in (("СБОРКА", self.pack_value), ("ЯДРО", self.core_value), ("АККАУНТ", self.account_value)):
                    self._otext(x0, y, caption, font_c, C_HINT)
                    bottom = self._text_block(x0 + px(68), y, var.get(), font_v, C_INK, width - px(68))
                    y = bottom + px(4)
            elif kind == "fill":
                h = val.winfo_reqheight() if fill_to is None else max(val.winfo_reqheight(), fill_to - y)
                self._win(val, x0, y, width, h)
                y += h
        return y

    def _layout_specs(self) -> tuple[list, list, list]:
        d = self._d
        gap = d["item_gap"]
        account: list[tuple[str, Any]] = [("title", "01 / ИГРОВОЙ ПРОФИЛЬ"), ("w", self.profile_card), ("gap", gap),
                                          ("w", self.mode_bar)]
        if self.auth_var.get() == "microsoft":
            if d["hints"]:
                account += [("gap", gap), ("hint", MS_HINT)]
            account += [("gap", gap), ("row", [(self.login_btn, 1), (self.logout_btn, 0)])]
        else:
            account += [("gap", gap), ("label", "ИГРОВОЙ НИК"), ("gap", 3), ("w", self.username_entry)]
            if d["hints"]:
                account += [("gap", 4), ("hint", OFFLINE_HINT)]
        account += [("gap", gap + 6), ("w", self.skin_btn)]
        settings: list[tuple[str, Any]] = [("title", "02 / ПАМЯТЬ"), ("ram", None)]
        if d["hints"]:
            settings += [("gap", 3), ("hint", "Рекомендуется 6–8 ГБ. Больше половины памяти ПК не ставьте.")]
        settings += [("title", "03 / ФАЙЛЫ ИГРЫ"), ("row", [(self.folder_btn, 1), (self.logs_btn, 1)]), ("gap", gap),
                     ("w", self.repair_btn)]
        launch: list[tuple[str, Any]] = [("title", "MERIDIAN // LAUNCH CONTROL"), ("status", None), ("gap", gap + 4),
                                         ("w", self.progress_shell), ("gap", gap), ("w", self.play_btn), ("gap", gap + 2),
                                         ("info", None), ("gap", gap), ("fill", self.console_wrap)]
        return account, settings, launch

    def _relayout(self, width: int, height: int) -> tuple[int, int]:
        """Places everything on the canvas for the given size; returns the size the content needs."""
        d = self._d
        cv = self._root_frame
        cv.delete("ui")
        for item in self._windows.values():
            cv.itemconfigure(item, state="hidden")
        ox, oy, gap, pad = px(d["outer"][0]), px(d["outer"][1]), px(d["gap"]), px(d["pad"])
        top = getattr(self, "_content_top", oy)
        col_a, col_b, col_c_min = px(420), px(270), px(420)
        account, settings, launch = self._layout_specs()
        panels: list[tuple[float, float, float, float]] = []
        x = ox
        if self._columns == 3:
            a_end = self._flow(account, x + pad, x + col_a - pad, top) + pad
            panels.append((x, top, x + col_a, a_end))
            x += col_a + gap
            b_end = self._flow(settings, x + pad, x + col_b - pad, top) + pad
            panels.append((x, top, x + col_b, b_end))
            x += col_b + gap
            left_bottom = max(a_end, b_end)
        else:
            a_end = self._flow(account, x + pad, x + col_a - pad, top) + pad
            panels.append((x, top, x + col_a, a_end))
            b_top = a_end + gap
            b_end = self._flow(settings, x + pad, x + col_a - pad, b_top) + pad
            panels.append((x, b_top, x + col_a, b_end))
            x += col_a + gap
            left_bottom = b_end
        col_c = max(col_c_min, width - ox - x)
        lpad = pad + px(4)
        # natural height first, then stretch the log to the bottom of the window
        natural = self._flow(launch, x + lpad, x + col_c - lpad, top) + lpad
        bottom = max(natural, height - oy)
        cv.delete("ui")
        for item in self._windows.values():
            cv.itemconfigure(item, state="hidden")
        self._redraw_left(account, settings, panels, top, pad)
        self._flow(launch, x + lpad, x + col_c - lpad, top, fill_to=bottom - lpad)
        panels.append((x, top, x + col_c, bottom))
        self.backdrop.set_panels(panels)
        cv.tag_raise("header")
        cv.tag_raise("ui")
        req_w = x + col_c_min + ox
        req_h = max(left_bottom, natural) + oy
        return int(req_w), int(req_h)

    def _redraw_left(self, account: list, settings: list, panels: list, top: float, pad: float) -> None:
        ax0, ay0, ax1 = panels[0][:3]
        bx0, by0, bx1 = panels[1][:3]
        self._flow(account, ax0 + pad, ax1 - pad, ay0)
        self._flow(settings, bx0 + pad, bx1 - pad, by0)

    def _place_header(self) -> None:
        """Emblem, title and status drawn on the background canvas (real pixels, after scaling)."""
        d = self._d
        cv = self._root_frame
        cv.delete("header")
        ox, oy = px(d["outer"][0]), px(d["outer"][1])
        icon = px(d["icon"])
        self._draw_brand_icon(cv, ox, oy, icon / 48.0)
        title_font = tkfont.Font(family="Segoe UI Black", size=d["title_font"])
        sub_font = tkfont.Font(family="Consolas", size=9, weight="bold")
        tx = ox + round(icon * 54 / 48) + px(12)
        self.title_item = cv.create_text(tx, oy - px(2), text="PROJECT MERIDIAN", anchor="nw", font=title_font,
                                         fill=C_INK, tags=("header",))
        y = oy + title_font.metrics("linespace") - px(2)
        if d["subtitle"]:
            cv.create_text(tx, y + px(1), text="EXPEDITION NETWORK // LAUNCH TERMINAL", anchor="nw", font=sub_font,
                           fill=C_MUTED, tags=("header",))
            y += sub_font.metrics("linespace") + px(1)
        bottom = max(oy + icon, y)
        self._sep_y = bottom + px(d["sep"][0])
        self._content_top = self._sep_y + 1 + px(d["sep"][1])
        self._title_font, self._sub_font = title_font, sub_font  # Tk forgets fonts without a reference
        self.system_dot_item = cv.create_oval(0, 0, 0, 0, fill=C_AMBER, outline="", tags=("header",))
        self.status_item = cv.create_text(0, 0, text="SYSTEM ONLINE", anchor="ne", font=sub_font, fill=C_MUTED,
                                          tags=("header",))
        self.version_item = cv.create_text(0, 0, text=f"v{APP_VERSION}  //  STABLE", anchor="ne", font=sub_font,
                                           fill=C_AMBER, tags=("header",))
        self.sep_item = cv.create_line(0, 0, 0, 0, fill=C_LINE, tags=("header",))
        self.update_item = cv.create_window(0, 0, window=self.update_link, anchor="ne", tags=("header",),
                                            state="normal" if self.launcher_update_var.get() else "hidden")
        self._place_header_right(max(cv.winfo_width(), cv.winfo_reqwidth()))

    def _place_header_right(self, width: int) -> None:
        cv = self._root_frame
        if cv is None or not hasattr(self, "version_item"):
            return
        d = self._d
        ox, oy = px(d["outer"][0]), px(d["outer"][1])
        right = width - ox
        line_h = self._sub_font.metrics("linespace")
        try:
            cv.coords(self.version_item, right, oy)
            vx = cv.bbox(self.version_item)[0]
            cv.coords(self.status_item, vx - px(16), oy)
            sx = cv.bbox(self.status_item)[0]
            mid = oy + line_h / 2
            cv.coords(self.system_dot_item, sx - px(15), mid - px(4), sx - px(7), mid + px(4))
            cv.coords(self.update_item, right, oy + line_h + px(d["item_gap"]))
            cv.coords(self.sep_item, ox, self._sep_y, width - ox, self._sep_y)
        except (tk.TclError, TypeError):
            pass

    def _draw_brand_icon(self, cv: tk.Canvas, x0: float, y0: float, k: float = 1.0) -> None:
        """Draw the same mark used in the website header (.meridian-mark); k = size relative to 48 px."""
        cx, cy = x0 + 27 * k, y0 + 24 * k
        r, ext, ir = 15 * k, 20 * k, 7 * k
        tags = ("header",)
        self._brand_box = (cx - ext - 4, cy - ext - 4, cx + ext + 4, cy + ext + 4)  # click target of the intro
        # Website: a square rotated 45deg -> diamond, its pseudo-elements become diagonal cross-lines
        cv.create_polygon(cx, cy - r, cx + r, cy, cx, cy + r, cx - r, cy, outline=C_COPPER, fill="", width=2, tags=tags)
        cv.create_line(cx - ext, cy - ext, cx + ext, cy + ext, fill=C_COPPER, width=1, tags=tags)
        cv.create_line(cx + ext, cy - ext, cx - ext, cy + ext, fill=C_COPPER, width=1, tags=tags)
        # inner telemetry square
        cv.create_polygon(cx, cy - ir, cx + ir, cy, cx, cy + ir, cx - ir, cy, outline=C_TELEMETRY, fill="", width=2,
                          tags=tags)

    def _over_brand(self, event: tk.Event) -> bool:
        box = getattr(self, "_brand_box", None)
        return bool(box) and box[0] <= event.x <= box[2] and box[1] <= event.y <= box[3]

    def _on_canvas_motion(self, event: tk.Event) -> None:
        over = self._over_brand(event)
        if over != getattr(self, "_brand_hover", False):
            self._brand_hover = over
            self._root_frame.configure(cursor="hand2" if over else "")

    def _on_canvas_click(self, event: tk.Event) -> None:
        if not getattr(self, "_show_mode", None) and self._over_brand(event):
            self._open_keygen()

    # ---------- keygen intro: the menu slides away, the show plays in the window, Esc slides the menu back ----------
    SLIDE_SECONDS = 0.6
    SHOW_KEYS = ("<KeyPress-m>", "<KeyPress-M>", "<KeyPress-Cyrillic_softsign>", "<KeyPress-Cyrillic_SOFTSIGN>")

    def _slide_menu_to(self, offset: float) -> None:
        """Moves the whole menu (texts, controls, header, glass panels) horizontally to `offset` px."""
        cv = self._root_frame
        delta = offset - getattr(self, "_slide_off", 0.0)
        if delta:
            cv.move("ui", delta, 0)
            cv.move("header", delta, 0)
            for item in self._windows.values():
                cv.move(item, delta, 0)
        self._slide_off = offset
        base = getattr(self, "_slide_panels", None) or []
        self.backdrop.set_panels([(x0 + offset, y0, x1 + offset, y1) for x0, y0, x1, y1 in base])

    def _animate_slide(self, start: float, end: float, done: Callable[[], None]) -> None:
        t0 = time.perf_counter()

        def step() -> None:
            p = min(1.0, (time.perf_counter() - t0) / self.SLIDE_SECONDS)
            ease = p * p * (3 - 2 * p)
            try:
                self._slide_menu_to(start + (end - start) * ease)
            except tk.TclError:
                return
            if p < 1.0:
                self.after(16, step)
            else:
                done()
        step()

    def _open_keygen(self, sound: bool = True, animate: bool = True) -> KeygenShow | None:
        if getattr(self, "_show_mode", None):
            return getattr(self, "_keygen", None)
        cv = self._root_frame
        self._show_mode = "opening"
        self._slide_off = 0.0
        self._slide_panels = list(self.backdrop.panels)
        width, height = max(cv.winfo_width(), 200), max(cv.winfo_height(), 200)
        self._brand_hover = False
        cv.configure(cursor="")

        def start_show() -> None:
            self._show_mode = "show"
            self._keygen = KeygenShow(cv, width, height, self._close_keygen, sound=sound)
            self.bind("<Escape>", lambda _e: self._close_keygen())
            for key in self.SHOW_KEYS:
                self.bind(key, lambda _e: self._keygen.toggle_sound())

        if animate:
            self._animate_slide(0.0, -(width + px(40)), start_show)
        else:
            self._slide_menu_to(-(width + px(40)))
            start_show()
        return getattr(self, "_keygen", None)

    def _close_keygen(self, animate: bool = True) -> None:
        if getattr(self, "_show_mode", None) != "show":
            return
        self._show_mode = "closing"
        for key in ("<Escape>",) + self.SHOW_KEYS:
            self.unbind(key)
        self._keygen.close()
        cv = self._root_frame
        width = max(cv.winfo_width(), 200)
        # lay the menu out for the current window size, then bring it in from the left
        self._slide_off = 0.0
        self._place_header()   # header drawn again at its normal place (it was moved off screen)
        self._relayout(cv.winfo_width(), cv.winfo_height())
        self._slide_panels = list(self.backdrop.panels)
        self._slide_menu_to(-(width + px(40)))

        def finished() -> None:
            self._show_mode = None
            self._slide_panels = None

        if animate:
            self._animate_slide(-(width + px(40)), 0.0, finished)
        else:
            self._slide_menu_to(0.0)
            finished()

    def _animate_ui(self) -> None:
        self._animation_phase += 0.12
        pulse = (math.sin(self._animation_phase) + 1.0) / 2.0

        def blend(a: str, b: str, t: float) -> str:
            av = tuple(int(a[i:i+2], 16) for i in (1, 3, 5))
            bv = tuple(int(b[i:i+2], 16) for i in (1, 3, 5))
            rv = tuple(round(x + (y - x) * t) for x, y in zip(av, bv))
            return "#" + "".join(f"{v:02x}" for v in rv)

        frame = getattr(self, "_boot_frame", 0)
        self._boot_frame = frame + 1
        if frame < len(BOOT_FLICKER):
            # power-on flicker of the title, like an old game menu (a dozen frames, then a calm glow)
            glow = blend(C_BG, C_INK, BOOT_FLICKER[frame])
        else:
            glow = blend(C_INK, C_AMBER_2, pulse * 0.34)
        dot = blend("#614500", C_AMBER_2, 0.25 + pulse * 0.75)
        try:
            cv = self._root_frame
            cv.itemconfigure(self.title_item, fill=glow)
            cv.itemconfigure(self.system_dot_item, fill=dot)
            if getattr(self, "_show_mode", None) != "show":
                self.backdrop.tick()
        except (tk.TclError, AttributeError):
            pass
        self.after(70, self._animate_ui)

    def _sync_auth_fields(self) -> None:
        try:
            is_ms = self.auth_var.get() == "microsoft"
            msa_name = str(self.state_data.get("msa_username") or "").strip()
            self._request_relayout()
            if is_ms:
                self.login_btn.configure(text="СМЕНИТЬ АККАУНТ" if msa_name else "ВОЙТИ ЧЕРЕЗ MICROSOFT")
                self.logout_btn.configure(state="normal" if msa_name and not self.busy else "disabled")
                if msa_name:
                    self.account_name_var.set(msa_name)
                    self.account_type_var.set("ЛИЦЕНЗИЯ // MICROSOFT")
                    self.account_note_var.set("Профиль подтверждён Microsoft. Скин — официальный.")
                    self.account_value.set(msa_name)
                else:
                    self.account_name_var.set("Вход не выполнен")
                    self.account_type_var.set("ЛИЦЕНЗИЯ // НЕТ ВХОДА")
                    self.account_note_var.set("Войдите через официальную страницу Microsoft.")
                    self.account_value.set("НЕТ ВХОДА")
                    self._set_skin_placeholder()
            else:
                nick = self.username_var.get().strip()
                valid = bool(NICK_RE.match(nick))
                self.account_name_var.set(nick or "Ник не указан")
                self.account_type_var.set("БЕЗ ЛИЦЕНЗИИ // ПАРОЛЬ НА СЕРВЕРЕ" if valid else "БЕЗ ЛИЦЕНЗИИ // НЕВЕРНЫЙ НИК")
                self.account_note_var.set("Ник защищается паролем на сервере." if valid
                                          else "3–16 символов: латиница, цифры, «_».")
                self.account_value.set(nick if valid else "—")
                self._set_skin_placeholder()
        except (tk.TclError, AttributeError):
            pass

    def _set_skin_placeholder(self) -> None:
        self.skin_photo = None
        try:
            self.skin_label.configure(image="", text="NO\nSKIN", fg=C_MUTED)
        except tk.TclError:
            pass

    def _set_skin_image(self, path_value: str) -> None:
        try:
            size = px(getattr(self, "_skin_base", 96))
            image = skin_head_rgba(Path(path_value), size)
            self.skin_photo = ImageTk.PhotoImage(image)
            self.skin_label.configure(image=self.skin_photo, text="")
        except Exception:
            self._set_skin_placeholder()

    def _refresh_skin_async(self) -> None:
        if self.auth_var.get() != "microsoft":
            return
        uuid_value = str(self.state_data.get("msa_uuid") or "").strip()
        if not uuid_value:
            return

        def worker() -> None:
            path = minecraft_skin_path(uuid_value)
            if path:
                self._emit("skin_ready", str(path))

        threading.Thread(target=worker, daemon=True).start()

    def _log(self, text: str) -> None:
        text = mask_secrets(str(text))
        stamp = time.strftime("%H:%M:%S")
        line = f"[{stamp}] {text}"
        self.log_lines.append(line)
        del self.log_lines[:-1000]
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            with (LOG_DIR / "launcher.log").open("a", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d ") + line + "\n")
        except OSError:
            pass
        try:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", line + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        except (tk.TclError, AttributeError):
            pass
        if self.log_dialog_text is not None:
            try:
                self.log_dialog_text.configure(state="normal")
                self.log_dialog_text.insert("end", line + "\n")
                self.log_dialog_text.see("end")
                self.log_dialog_text.configure(state="disabled")
            except tk.TclError:
                self.log_dialog_text = None

    def _emit(self, kind: str, value: Any = None) -> None:
        self.events.put((kind, value))

    def _drain_events(self) -> None:
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self._log(str(value))
            elif kind == "status":
                self.status_var.set(str(value))
            elif kind == "detail":
                self.detail_var.set(str(value))
            elif kind == "progress":
                self.progress.stop()
                self.progress.configure(mode="determinate")
                self.progress["value"] = float(value)
            elif kind == "progress_text":
                self.progress_var.set(str(value))
            elif kind == "progress_indeterminate":
                if bool(value):
                    self.progress.configure(mode="indeterminate")
                    self.progress.start(12)
                else:
                    self.progress.stop()
                    self.progress.configure(mode="determinate")
            elif kind == "clipboard":
                try:
                    self.clipboard_clear()
                    self.clipboard_append(str(value))
                    self.update_idletasks()
                except tk.TclError:
                    pass
            elif kind == "auth_code":
                self._show_auth_code(dict(value))
            elif kind == "auth_success":
                self._show_auth_success(dict(value))
            elif kind == "skin_ready":
                self._set_skin_image(str(value))
            elif kind == "pack_value":
                self.pack_value.set(str(value))
            elif kind == "skin_preview":
                self._show_skin_preview(dict(value))
            elif kind == "skin_signed":
                self._skin_signed(dict(value))
            elif kind == "auth_changed":
                self._sync_auth_fields()
                self._set_skin_placeholder()
            elif kind == "launcher_update":
                self.launcher_update_var.set(f"ОБНОВИТЬ ЛАУНЧЕР ДО v{value} ›")
                try:
                    self._root_frame.itemconfigure(self.update_item, state="normal")
                except (tk.TclError, AttributeError):
                    pass
                self._log(f"Доступна новая версия лаунчера {value}: {LAUNCHER_DOWNLOAD_PAGE}")
            elif kind == "restart_launcher":
                self.destroy()
                return
            elif kind == "busy":
                self._set_busy(bool(value))
            elif kind == "play_text":
                self.play_btn.configure(text=str(value))
            elif kind == "error":
                messagebox.showerror(APP_NAME, str(value))
            elif kind == "info":
                messagebox.showinfo(APP_NAME, str(value))
        self.after(100, self._drain_events)

    def _handle_pmc_event(self, parts: list[str]) -> None:
        if not parts:
            return

        code = parts[0].strip()
        if not code:
            return

        if code == "download":
            try:
                count, total_count = (int(x) for x in parts[1].split("/", 1))
                size, total_size = (int(x) for x in parts[2].split("/", 1))
                speed = float(parts[4]) if len(parts) > 4 else 0.0
                pct = (size / total_size * 100.0) if total_size else 0.0
                self._emit("progress_indeterminate", False)
                self._emit("progress", pct)
                self._emit("status", "Скачиваю компоненты…")
                self._emit(
                    "progress_text",
                    f"{pct:.1f}% • {format_bytes(size)} / {format_bytes(total_size)}"
                    f" • {format_bytes(speed)}/с • {count}/{total_count} файлов",
                )
            except (ValueError, IndexError, ZeroDivisionError):
                pass
            return

        if code == "download_resources":
            self._emit("status", "Скачиваю компоненты…")
            self._emit("progress_indeterminate", True)
            self._emit("progress_text", "Подготавливаю список файлов для загрузки…")
        elif code == "resources_downloaded":
            self._emit("progress_indeterminate", False)
            self._emit("progress", 100)
            self._emit("progress_text", "Компоненты скачаны ✓")
        elif code == "neoforge_fetch_installer":
            version = parts[1] if len(parts) > 1 else NEOFORGE_VERSION
            self._emit("status", "Скачиваю NeoForge…")
            self._emit("progress_indeterminate", True)
            self._emit("progress_text", f"Установщик NeoForge {version}")
        elif code == "neoforge_fetched_installer":
            self._emit("progress_text", "Установщик NeoForge скачан ✓")
        elif code == "neoforge_game_installing":
            self._emit("status", "Устанавливаю Minecraft…")
            self._emit("progress_indeterminate", True)
            self._emit("progress_text", f"Minecraft {MC_VERSION} для NeoForge")
        elif code == "neoforge_installer_libraries_fetching":
            self._emit("status", "Скачиваю библиотеки NeoForge…")
            self._emit("progress_indeterminate", True)
            self._emit("progress_text", "Библиотеки установщика NeoForge")
        elif code == "neoforge_installer_processor":
            task = parts[1] if len(parts) > 1 else "Обработка файлов"
            self._emit("status", "Устанавливаю NeoForge…")
            self._emit("progress_indeterminate", True)
            self._emit("progress_text", task)
        elif code == "neoforge_installed":
            self._emit("progress_indeterminate", False)
            self._emit("progress", 100)
            self._emit("progress_text", f"NeoForge {NEOFORGE_VERSION} установлен ✓")
        elif code == "fetch_version":
            version = parts[1] if len(parts) > 1 else MC_VERSION
            self._emit("status", "Скачиваю Minecraft…")
            self._emit("progress_indeterminate", True)
            self._emit("progress_text", f"Версия Minecraft: {version}")
        elif code == "load_jvm":
            major = parts[1] if len(parts) > 1 else "21"
            self._emit("status", "Проверяю Java…")
            self._emit("progress_indeterminate", True)
            self._emit("progress_text", f"Нужна Java {major}")
        elif code == "loaded_jvm":
            self._emit("progress_text", "Java готова ✓")
        elif code == "launching":
            self._emit("progress_indeterminate", True)
            self._emit("status", "Запускаю Minecraft…")
            self._emit("progress_text", "Все файлы готовы • запускаю игру")
        elif code == "launched":
            pid = parts[1] if len(parts) > 1 else ""
            self._emit("progress_indeterminate", False)
            self._emit("progress", 100)
            self._emit("status", "Minecraft запущен")
            self._emit("progress_text", f"Игра запущена{f' • PID {pid}' if pid else ''}")
        elif code == "terminated":
            self._emit("progress_indeterminate", False)
            self._emit("progress", 100)
            self._emit("progress_text", "Minecraft закрыт")
        elif code.startswith("error_"):
            self._emit("progress_indeterminate", False)
            self._emit("status", "Ошибка запуска")
            self._emit("progress_text", code)
            self._emit("log", "PortableMC: " + " | ".join(parts))

    def _open_auth_dialog(self) -> None:
        if self.auth_dialog is not None and self.auth_dialog.winfo_exists():
            self.auth_dialog.lift()
            return

        dialog = tk.Toplevel(self)
        self.auth_dialog = dialog
        dialog.withdraw()
        dialog.title("Project Meridian // Microsoft")
        apply_window_icon(dialog, self._icon_images)
        dialog.configure(bg=C_BG)
        dialog.transient(self)

        left, top, work_w, work_h = work_area(self)
        extra_w, extra_h = frame_extra(False)
        avail_w, avail_h = work_w - extra_w, work_h - extra_h
        main_density = DENSITY.index(self._d) if self._d in DENSITY else 0
        shell = None
        for density in range(main_density, len(DENSITY)):
            if shell is not None:
                shell.destroy()
            shell = self._build_auth_content(dialog, DENSITY[density])
            self._apply_ui_scale(dialog)
            dialog.update_idletasks()
            req_w, req_h = dialog.winfo_reqwidth(), dialog.winfo_reqheight()
            if req_w <= avail_w and req_h <= avail_h:
                break
        w, h = min(req_w, avail_w), min(req_h, avail_h)
        x = left + max(0, (work_w - (w + extra_w)) // 2)
        y = top + max(0, (work_h - (h + extra_h)) // 2)
        dialog.geometry(f"{w}x{h}+{x}+{y}")
        dialog.resizable(False, False)
        self.auth_layout_info = {"density": density, "required": (req_w, req_h), "available": (avail_w, avail_h),
                                 "size": (w, h), "fits": req_w <= avail_w and req_h <= avail_h}
        dialog.deiconify()
        dark_title_bar(dialog)
        dialog.protocol("WM_DELETE_WINDOW", self._close_auth_dialog)

    def _build_auth_content(self, dialog: tk.Toplevel, d: dict[str, Any]) -> tk.Frame:
        """Content of the Microsoft sign-in dialog at one density (no scrolling)."""
        pad = d["pad"] + 4
        saved = self._d
        self._d = d  # buttons take their padding from the density
        try:
            shell = tk.Frame(dialog, bg=C_PANEL, highlightthickness=1, highlightbackground=C_LINE)
            shell.pack(fill="both", expand=True, padx=d["outer"][1], pady=d["outer"][1])

            top = tk.Frame(shell, bg=C_PANEL)
            top.pack(fill="x", padx=pad, pady=(d["sec"][0] + 4, 0))
            icon = tk.Canvas(top, width=58, height=38, bg=C_PANEL, bd=0, highlightthickness=0)
            icon.pack(side="left", padx=(0, 12))
            icon.create_oval(12, 7, 42, 37, outline=C_AMBER, width=2)
            icon.create_line(27, 0, 27, 38, fill=C_AMBER, width=1)
            icon.create_line(5, 22, 49, 22, fill=C_AMBER, width=1)
            tk.Label(
                top,
                text="ВХОД ЧЕРЕЗ MICROSOFT",
                bg=C_PANEL,
                fg=C_INK,
                font=("Segoe UI Black", max(14, d["title_font"] - 5)),
            ).pack(side="left")

            tk.Label(
                shell,
                text="Это вход по коду устройства. Код из Microsoft Authenticator здесь НЕ нужен.",
                bg=C_PANEL,
                fg=C_MUTED,
                font=("Segoe UI", 10),
                wraplength=470,
                justify="left",
            ).pack(anchor="w", padx=pad, pady=(d["sec"][0], d["sec"][0]))

            steps = tk.Frame(shell, bg=C_PANEL_2, highlightthickness=1, highlightbackground=C_LINE)
            steps.pack(fill="x", padx=pad)
            for n, text_value in (
                ("01", "Лаунчер получит одноразовый код Microsoft."),
                ("02", "Откроется официальная страница Microsoft."),
                ("03", "Вставь код ниже и подтверди нужный аккаунт."),
                ("04", "Вернись сюда — лаунчер закончит вход автоматически."),
            ):
                row = tk.Frame(steps, bg=C_PANEL_2)
                row.pack(fill="x", padx=12, pady=max(1, d["item_gap"] // 2))
                tk.Label(row, text=n, bg=C_PANEL_2, fg=C_AMBER, font=("Consolas", 9, "bold"), width=3).pack(side="left")
                tk.Label(row, text=text_value, bg=C_PANEL_2, fg=C_INK, font=("Segoe UI", 9), anchor="w").pack(side="left")

            tk.Label(shell, text="КОД ИЗ ЛАУНЧЕРА", bg=C_PANEL, fg=C_AMBER, font=("Consolas", 9, "bold")).pack(
                anchor="w", padx=pad, pady=(d["sec"][0], 4)
            )
            tk.Label(
                shell,
                textvariable=self.auth_code_var,
                bg=C_FIELD,
                fg=C_AMBER_2,
                font=("Consolas", max(16, d["status_font"]), "bold"),
                padx=14,
                pady=max(4, d["btn_pady"]),
                highlightthickness=1,
                highlightbackground=C_LINE,
            ).pack(fill="x", padx=pad)

            tk.Label(
                shell,
                textvariable=self.auth_step_var,
                bg=C_PANEL,
                fg=C_MUTED,
                font=("Segoe UI", 9),
                anchor="w",
                justify="left",
                wraplength=470,
            ).pack(fill="x", padx=pad, pady=(d["item_gap"], 0))

            actions = tk.Frame(shell, bg=C_PANEL)
            actions.pack(fill="x", padx=pad, pady=(d["sec"][0], d["sec"][0] + 4))
            self.auth_copy_btn = self._button(actions, "СКОПИРОВАТЬ КОД", self._copy_auth_code)
            self.auth_copy_btn.pack(side="left", fill="x", expand=True)
            self.auth_open_btn = self._button(actions, "ОТКРЫТЬ MICROSOFT", self._open_auth_uri, accent=True)
            self.auth_open_btn.pack(side="left", fill="x", expand=True, padx=(10, 0))
        finally:
            self._d = saved
        return shell

    LAYOUT_KEY_WIDGETS = ("skin_label", "offline_radio", "microsoft_radio", "username_entry", "login_btn", "logout_btn",
                          "skin_btn", "ram_scale", "folder_btn", "logs_btn", "repair_btn",
                          "progress", "play_btn", "log_text", "auth_copy_btn", "auth_open_btn")

    def write_layout_report(self, path: str) -> None:
        """Writes the chosen layout and, for every key control, whether it is shown whole inside its window."""
        rows = {}
        # controls of the other sign-in mode are hidden on purpose
        hidden = {"login_btn", "logout_btn"} if self.auth_var.get() == "offline" else {"username_entry"}
        for name in self.LAYOUT_KEY_WIDGETS:
            if name in hidden:
                continue
            w = getattr(self, name, None)
            try:
                if w is None or not w.winfo_exists():
                    continue
                top = w.winfo_toplevel()
                x, y = w.winfo_rootx() - top.winfo_rootx(), w.winfo_rooty() - top.winfo_rooty()
                ww, wh = w.winfo_width(), w.winfo_height()
                inside = x >= 0 and y >= 0 and x + ww <= top.winfo_width() + 1 and y + wh <= top.winfo_height() + 1
                squeezed = name != "log_text" and (ww + 1 < w.winfo_reqwidth() or wh + 1 < w.winfo_reqheight())
                rows[name] = {"window": top.title(), "mapped": bool(w.winfo_ismapped()), "inside": inside, "squeezed": squeezed,
                              "rect": [x, y, ww, wh], "needed": [w.winfo_reqwidth(), w.winfo_reqheight()]}
            except tk.TclError:
                rows[name] = {"error": True}
        report = {"version": APP_VERSION, "layout": getattr(self, "layout_info", None), "auth_layout": getattr(self, "auth_layout_info", None),
                  "icon": getattr(self, "icon_source", None), "main_size": [self.winfo_width(), self.winfo_height()],
                  "min_size": list(self.minsize()), "widgets": rows,
                  "ok": all(r.get("mapped") and r.get("inside") and not r.get("squeezed") for r in rows.values())}
        Path(path).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    def _close_auth_dialog(self) -> None:
        if self.auth_dialog is not None:
            try:
                self.auth_dialog.destroy()
            except tk.TclError:
                pass
        self.auth_dialog = None

    def _copy_auth_code(self) -> None:
        code = self.auth_code_var.get().strip()
        if not code or code == "--------":
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(code)
            self.update_idletasks()
            self.auth_step_var.set("Код скопирован. Вставь его на странице Microsoft.")
        except tk.TclError:
            pass

    def _open_auth_uri(self) -> None:
        webbrowser.open(self.auth_uri)

    def _show_auth_code(self, data: dict[str, str]) -> None:
        self.auth_uri = data.get("uri") or "https://microsoft.com/devicelogin"
        code = data.get("code") or "--------"
        self.auth_code_var.set(code)
        self.auth_step_var.set("Код уже скопирован. Вставь его на странице Microsoft.")
        self._copy_auth_code()
        self._open_auth_uri()

    def _show_auth_success(self, data: dict[str, str]) -> None:
        username = data.get("username") or "Minecraft"
        self.auth_code_var.set("ГОТОВО ✓")
        self.auth_step_var.set(f"Аккаунт {username} подключён. Это окно можно закрыть.")
        self._sync_auth_fields()
        self._refresh_skin_async()
        if self.auth_dialog is not None and self.auth_dialog.winfo_exists():
            self.after(1800, self._close_auth_dialog)

    def _handle_auth_event(self, parts: list[str]) -> None:
        if not parts:
            return
        code = parts[0].strip()
        if code == "auth_request_device_code":
            self._emit("status", "Получаю код Microsoft…")
            self._emit("progress_indeterminate", True)
            self._emit("progress_text", "Связываюсь с Microsoft…")
        elif code == "auth_device_code":
            verification_uri = parts[1] if len(parts) > 1 else "https://microsoft.com/devicelogin"
            user_code = parts[2] if len(parts) > 2 else ""
            self._emit("auth_code", {"uri": verification_uri, "code": user_code})
            self._emit("status", "Подтверди вход Microsoft")
            self._emit("detail", f"Код: {user_code}" if user_code else "Открыта страница Microsoft")
            self._emit("progress_text", "Не используй код из Authenticator — вставь код из лаунчера")
            self._emit("log", "Получен одноразовый код Microsoft (показан в окне входа).")
        elif code == "auth_wait":
            self._emit("status", "Жду подтверждения Microsoft…")
            self._emit("progress_indeterminate", True)
            self._emit("progress_text", "Подтверди аккаунт в браузере • лаунчер продолжит сам")
        elif code == "auth_account_authenticated":
            uuid = parts[1] if len(parts) > 1 else ""
            username = parts[2] if len(parts) > 2 else ""
            if uuid:
                self.state_data["msa_uuid"] = uuid
            if username:
                self.state_data["msa_username"] = username
            atomic_write_json(STATE_FILE, self.state_data)
            self._emit("progress_indeterminate", False)
            self._emit("progress", 100)
            self._emit("status", "Microsoft подключён")
            self._emit("detail", f"Minecraft: {username}" if username else "Аккаунт Microsoft сохранён")
            self._emit("progress_text", "Авторизация завершена ✓")
            self._emit("auth_success", {"username": username, "uuid": uuid})
            if username:
                self._emit("log", f"Microsoft/Minecraft аккаунт подключён: {username}")
        elif code.startswith("error_"):
            self._emit("progress_indeterminate", False)
            self._emit("status", "Ошибка Microsoft-входа")
            self._emit("progress_text", code)
            self._emit("log", "PortableMC auth: " + " | ".join(parts))

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        for name in ("play_btn", "repair_btn", "login_btn"):
            widget = getattr(self, name, None)
            if widget is not None:
                try:
                    widget.configure(state=state)
                except tk.TclError:
                    pass
        self._sync_auth_fields()

    def _save_preferences(self) -> None:
        self.state_data["username"] = self.username_var.get().strip()
        self.state_data["auth_mode"] = self.auth_var.get()
        self.state_data["ram_gb"] = max(4, min(16, int(self.ram_var.get())))
        atomic_write_json(STATE_FILE, self.state_data)

    def _start_thread(self, target: Callable[[], None]) -> None:
        if self.busy:
            return
        self._save_preferences()
        self._set_busy(True)

        def runner() -> None:
            try:
                target()
            except urllib.error.HTTPError as e:
                self._emit("error", f"Ошибка сети GitHub: HTTP {e.code}")
                self._emit("log", f"HTTPError: {e}")
            except urllib.error.URLError as e:
                self._emit("error", f"Не удалось подключиться к сети: {e.reason}")
                self._emit("log", f"URLError: {e}")
            except Exception as e:
                self._emit("error", str(e))
                self._emit("log", f"Ошибка: {type(e).__name__}: {e}")
            finally:
                self._emit("progress_indeterminate", False)
                self._emit("busy", False)

        threading.Thread(target=runner, daemon=True).start()

    def _initial_check(self) -> None:
        self._sync_auth_fields()
        if INSTALL_JOURNAL.exists():
            self._log("Предыдущая установка была прервана — при запуске сборка будет восстановлена.")
        self._start_thread(lambda: self._check_update_only())

    def _check_update_only(self) -> None:
        self._emit("status", "Проверяю обновления…")
        try:
            asset = get_release_asset()
        except Exception as e:
            if self._pack_installed() and not INSTALL_JOURNAL.exists():
                self._emit("status", "Сборка установлена")
                self._emit("detail", "Нет связи с сервером обновлений • можно играть")
            else:
                self._emit("status", "Нужна установка сборки")
                self._emit("detail", "Нет связи с сервером обновлений • проверьте интернет")
            self._emit("log", f"Не удалось проверить обновления: {type(e).__name__}: {e}")
            return
        try:
            self._check_launcher_version(asset)
        except RuntimeError as e:
            self._emit("status", "Нужен новый лаунчер")
            self._emit("detail", str(e))
            return
        current = self.state_data.get("pack_identity") == asset["identity"] and self._pack_installed()
        if INSTALL_JOURNAL.exists():
            self._emit("status", "Установка не завершена")
            self._emit("detail", "Нажмите «ИГРАТЬ» — лаунчер восстановит сборку")
            self._emit("play_text", "ВОССТАНОВИТЬ И ИГРАТЬ")
        elif current and not legacy_dev_state_present(self.state_data):
            self._emit("status", "Сборка установлена")
            self._emit("detail", f"{asset['release_name']} • Minecraft {MC_VERSION} • NeoForge")
            self._emit("pack_value", asset["release_name"])
            self._emit("log", "Сборка актуальна.")
        elif self._pack_installed():
            self._emit("status", "Доступно обновление")
            self._emit("detail", f"{asset['release_name']} • " + ("только изменённые файлы" if asset.get("file_index") else format_bytes(asset["size"])) + " • установится при запуске")
            self._emit("play_text", "ОБНОВИТЬ И ИГРАТЬ")
            self._emit("log", f"Доступна сборка {asset['release_name']}. Нажмите «ОБНОВИТЬ И ИГРАТЬ».")
        else:
            self._emit("status", "Готов к установке")
            self._emit("detail", f"{asset['release_name']} • {format_bytes(asset['size'])} • Minecraft {MC_VERSION}")
            self._emit("play_text", "УСТАНОВИТЬ И ИГРАТЬ")

    def _ensure_pack(self, force: bool = False) -> None:
        incremental.recover(INSTANCE_DIR, CACHE_DIR / "incremental")
        asset = get_release_asset()
        self._check_launcher_version(asset)
        up_to_date = (self.state_data.get("pack_identity") == asset["identity"] and self._pack_installed()
                      and not INSTALL_JOURNAL.exists() and not legacy_dev_state_present(self.state_data))
        if up_to_date and not force:
            self._emit("log", "Сборка актуальна.")
            return
        if asset.get("file_index") and self._pack_installed() and not legacy_dev_state_present(self.state_data):
            self._install_incremental(asset)
        else:
            self._install_zip(self._obtain_verified_zip(asset), asset)
        self._emit("status", "Сборка готова")
        self._emit("detail", f"{asset['release_name']} • Minecraft {MC_VERSION} • NeoForge {NEOFORGE_VERSION}")
        self._emit("play_text", "ИГРАТЬ")

    def _repair_pack(self) -> None:
        def job() -> None:
            self._emit("status", "Проверяю файлы сборки…")
            self._emit("progress", 0)
            index = load_file_index()
            asset: dict[str, Any] | None = None
            try:
                asset = get_release_asset()
                self._check_launcher_version(asset)
            except RuntimeError as e:
                if "устарела" in str(e):
                    raise
                self._emit("log", f"Манифест недоступен ({e}); проверяю по сохранённому эталону.")
            except Exception as e:
                self._emit("log", f"Манифест недоступен ({type(e).__name__}); проверяю по сохранённому эталону.")
            if asset and asset.get("file_index") and not legacy_dev_state_present(self.state_data):
                self._install_incremental(asset)
                self._emit("status", "Сборка проверена и восстановлена")
                return
            if not index or INSTALL_JOURNAL.exists() or legacy_dev_state_present(self.state_data):
                if asset is None:
                    raise RuntimeError("Для восстановления нужен интернет: эталон файлов ещё не сохранён.")
                self._emit("log", "Эталона файлов нет (установка старым лаунчером) — переустанавливаю сборку целиком.")
                self._install_zip(self._obtain_verified_zip(asset), asset)
                self._emit("status", "Сборка восстановлена")
                self._emit("detail", f"{asset['release_name']} • все файлы проверены")
                return
            broken = verify_installed_files(index)
            unknown = unknown_mod_files(index)
            if unknown:
                self._emit("log", "Посторонние файлы в mods (лаунчер их не удаляет; при ошибках игры уберите вручную): "
                                  + ", ".join(unknown[:20]) + (" …" if len(unknown) > 20 else ""))
            if asset is not None and self.state_data.get("pack_identity") != asset["identity"]:
                self._emit("log", "Есть более новая сборка — она установится при запуске игры.")
            if not broken:
                self._emit("progress", 100)
                self._emit("status", "Файлы в порядке")
                self._emit("detail", f"Проверено файлов: {len(index)} • повреждений нет")
                self._emit("log", f"Проверка: {len(index)} файлов совпадают с эталоном.")
                return
            self._emit("log", f"Повреждены или отсутствуют: {len(broken)} — " + ", ".join(broken[:10])
                              + (" …" if len(broken) > 10 else ""))
            digest = str(self.state_data.get("pack_digest") or "")
            source = cached_pack_path({"digest": digest, "identity": "-"})
            if not (source.is_file() and digest.startswith("sha256:") and sha256_file(source) == digest.split(":", 1)[1]):
                if asset is None or asset["digest"] != digest:
                    raise RuntimeError("Нет проверенного архива этой версии и нет связи с сервером. Подключитесь к "
                                       "интернету и повторите — или нажмите «ИГРАТЬ» для установки новой версии.")
                source = self._obtain_verified_zip(asset)
            self._emit("status", "Восстанавливаю файлы…")
            fixed = restore_files_from_zip(source, broken)
            index.update(fixed)
            atomic_write_json(FILE_INDEX, {"identity": self.state_data.get("pack_identity"), "files": index})
            still = verify_installed_files({rel: index[rel] for rel in broken if rel in index})
            self._emit("progress", 100)
            if still:
                raise RuntimeError(f"Не удалось восстановить {len(still)} файлов (возможно, заняты игрой или антивирусом): "
                                   + ", ".join(still[:5]))
            self._emit("status", "Файлы восстановлены")
            self._emit("detail", f"Исправлено файлов: {len(fixed)} • остальные в порядке")
            self._emit("log", f"Восстановлено файлов: {len(fixed)}.")

        self._start_thread(job)

    def _login_microsoft(self) -> None:
        self._open_auth_dialog()

        def job() -> None:
            self._emit("status", "Вход через Microsoft…")
            self._emit("detail", "Сейчас откроется страница Microsoft")
            self._emit("progress", 0)
            self._emit("progress_indeterminate", True)
            self._emit("progress_text", "Получаю код авторизации…")
            self._emit("log", "Запускаю авторизацию PortableMC через Microsoft…")
            args = [
                "--main-dir", str(INSTANCE_DIR),
                "--output", "machine",
                "auth", "login", "--no-browser",
            ]
            code = run_pmc(args, LAUNCH_LOG, on_event=self._handle_auth_event)
            if code != 0:
                raise RuntimeError(f"Авторизация завершилась с кодом {code}. Открой «Логи» для подробностей.")
            self._emit("progress_indeterminate", False)

        self._start_thread(job)

    def _play(self) -> None:
        if self.auth_var.get() == "offline":
            username = self.username_var.get().strip()
            if not NICK_RE.match(username):
                messagebox.showwarning(APP_NAME, "Ник: от 3 до 16 символов — латинские буквы, цифры и «_».")
                return
        elif not str(self.state_data.get("msa_uuid") or "").strip():
            messagebox.showwarning(APP_NAME, "Сначала войдите через Microsoft или выберите режим «БЕЗ ЛИЦЕНЗИИ».")
            return

        def job() -> None:
            try:
                self._ensure_pack(force=False)
            except Exception as e:
                if self._pack_installed() and not INSTALL_JOURNAL.exists() and "устарела" not in str(e):
                    self._emit("log", f"Обновление недоступно, запускаю установленную сборку: {type(e).__name__}: {e}")
                else:
                    raise
            ram = max(4, min(16, int(self.ram_var.get())))
            self._emit("status", "Готовлю Minecraft…")
            self._emit("detail", f"{self.pack_value.get()} • {MC_VERSION} • NeoForge {NEOFORGE_VERSION} • RAM {ram} ГБ")
            self._emit("log", "Проверяю Minecraft, библиотеки, NeoForge и Java.")
            jvm_args = f"-Xms2G,-Xmx{ram}G,-XX:+UseG1GC,-XX:MaxGCPauseMillis=100"
            args = ["--main-dir", str(INSTANCE_DIR), "--output", "machine", "start", f"--jvm-arg={jvm_args}"]
            if SERVER_HOST:
                args += ["--join-server", SERVER_HOST, "--join-server-port", str(SERVER_PORT)]
            if self.auth_var.get() == "microsoft":
                args += ["--auth", "--uuid", str(self.state_data.get("msa_uuid")).strip()]
            else:
                nick = self.username_var.get().strip()
                args += ["--username", nick, "--uuid", offline_uuid(nick)]
            args += [LAUNCH_SPEC]
            self._emit("progress", 0)
            self._emit("progress_indeterminate", True)
            self._emit("progress_text", "Проверяю Minecraft, NeoForge, Java и библиотеки…")
            code = run_pmc(args, LAUNCH_LOG, on_event=self._handle_pmc_event)
            if code != 0:
                raise RuntimeError(f"Minecraft завершился с ошибкой (код {code}). Нажмите «ЖУРНАЛ» — там причина. "
                                   "Если ошибка повторяется, нажмите «ПРОВЕРИТЬ / ПОЧИНИТЬ ФАЙЛЫ».")
            self._emit("status", "Minecraft закрыт")
            self._emit("detail", "Можно запускать снова")
            self._emit("log", "Игровой процесс завершён.")

        self._start_thread(job)

    def _auth_mode_changed(self) -> None:
        self._sync_auth_fields()
        self.state_data["auth_mode"] = self.auth_var.get()
        atomic_write_json(STATE_FILE, self.state_data)
        if self.auth_var.get() == "microsoft":
            self._refresh_skin_async()

    def _open_log_dialog(self) -> None:
        if self.log_dialog is not None and self.log_dialog.winfo_exists():
            self.log_dialog.lift()
            return
        dialog = tk.Toplevel(self)
        self.log_dialog = dialog
        dialog.title("Project Meridian // Журнал диагностики")
        apply_window_icon(dialog, self._icon_images)
        dialog.configure(bg=C_BG)
        dialog.transient(self)
        shell = tk.Frame(dialog, bg=C_PANEL, highlightthickness=1, highlightbackground=C_LINE)
        shell.pack(fill="both", expand=True, padx=10, pady=10)
        tk.Label(shell, text="/// ЖУРНАЛ ДИАГНОСТИКИ", bg=C_PANEL, fg=C_AMBER, font=("Consolas", 10, "bold")).pack(
            anchor="w", padx=14, pady=(12, 2))
        tk.Label(shell, text="События лаунчера и последние строки запуска игры. Токены входа в журнал не попадают.",
                 bg=C_PANEL, fg=C_MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=14)
        frame = tk.Frame(shell, bg=C_FIELD, highlightthickness=1, highlightbackground=C_LINE)
        frame.pack(fill="both", expand=True, padx=14, pady=10)
        text = tk.Text(frame, width=100, height=26, bg=C_FIELD, fg="#a4a39c", relief="flat", wrap="word",
                       font=("Consolas", 9), padx=10, pady=8)
        bar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)
        text.insert("end", "\n".join(self.log_lines) + "\n")
        tail = self._launch_log_tail(200)
        if tail:
            text.insert("end", "\n----- minecraft-launch.log (последние строки) -----\n" + tail + "\n")
        text.see("end")
        text.configure(state="disabled")
        self.log_dialog_text = text
        actions = tk.Frame(shell, bg=C_PANEL)
        actions.pack(fill="x", padx=14, pady=(0, 12))
        self._button(actions, "СКОПИРОВАТЬ ЖУРНАЛ", lambda: self._copy_text(text.get("1.0", "end"))).pack(side="left")
        self._button(actions, "ОТКРЫТЬ ПАПКУ ЛОГОВ", self._open_logs).pack(side="left", padx=(8, 0))
        self._button(actions, "ЗАКРЫТЬ", dialog.destroy).pack(side="right")
        self._apply_ui_scale(dialog)
        dialog.after(50, lambda: dark_title_bar(dialog))

    @staticmethod
    def _launch_log_tail(lines: int) -> str:
        try:
            with LAUNCH_LOG.open("r", encoding="utf-8", errors="replace") as f:
                f.seek(max(0, LAUNCH_LOG.stat().st_size - 256 * 1024))
                return mask_secrets("\n".join(f.read().splitlines()[-lines:]))
        except OSError:
            return ""

    def _copy_text(self, value: str) -> None:
        try:
            self.clipboard_clear()
            self.clipboard_append(value)
            self.update_idletasks()
        except tk.TclError:
            pass

    def _open_skin_dialog(self) -> None:
        if self.skin_dialog is not None and self.skin_dialog.winfo_exists():
            self.skin_dialog.lift()
            return
        is_ms = self.auth_var.get() == "microsoft" and bool(self.state_data.get("msa_uuid"))
        default_source = "official" if is_ms else "default"
        source = str(self.state_data.get("skin_source") or default_source)
        if source == "official" and not is_ms:
            source = "default"
        self.skin_source_var.set(source)
        self.skin_nick_var.set(str(self.state_data.get("skin_nick") or ""))
        self.skin_slim_var.set(bool(self.state_data.get("skin_slim")))
        self.skin_cmd_var.set("")
        self.skin_info_var.set("Выберите источник и нажмите «ПОКАЗАТЬ».")
        self._skin_pending: dict[str, Any] = {}

        dialog = tk.Toplevel(self)
        self.skin_dialog = dialog
        dialog.title("Project Meridian // Мой скин")
        apply_window_icon(dialog, self._icon_images)
        dialog.configure(bg=C_BG)
        dialog.transient(self)
        shell = tk.Frame(dialog, bg=C_PANEL, highlightthickness=1, highlightbackground=C_LINE)
        shell.pack(fill="both", expand=True, padx=10, pady=10)
        tk.Label(shell, text="МОЙ СКИН", bg=C_PANEL, fg=C_INK, font=("Segoe UI Black", 18)).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 2))
        tk.Label(shell, text="Скин на сервере устанавливается командой — его увидят все игроки. Источник скина "
                             "не меняет ваш аккаунт, права и прогресс.", bg=C_PANEL, fg=C_MUTED, font=("Segoe UI", 9),
                 wraplength=560, justify="left").grid(row=1, column=0, columnspan=2, sticky="w", padx=16)

        left = tk.Frame(shell, bg=C_PANEL)
        left.grid(row=2, column=0, sticky="nw", padx=16, pady=10)
        for value, label in SKIN_SOURCES:
            rb = tk.Radiobutton(left, text=label, variable=self.skin_source_var, value=value, command=self._skin_source_changed,
                                bg=C_PANEL, fg=C_INK, activebackground=C_PANEL, activeforeground=C_AMBER,
                                selectcolor=C_FIELD, font=("Segoe UI", 10), anchor="w")
            rb.pack(fill="x")
            if value == "official" and not is_ms:
                rb.configure(state="disabled")
        tk.Label(left, text="НИК В ИСТОЧНИКЕ", bg=C_PANEL, fg=C_MUTED, font=("Consolas", 8, "bold")).pack(anchor="w", pady=(10, 3))
        self.skin_nick_entry = self._entry(left, self.skin_nick_var)
        self.skin_nick_entry.pack(fill="x", ipady=4)
        self.skin_file_btn = self._button(left, "ВЫБРАТЬ PNG…", self._skin_pick_file)
        self.skin_file_btn.pack(fill="x", pady=(8, 0))
        model = tk.Frame(left, bg=C_PANEL)
        model.pack(fill="x", pady=(8, 0))
        for value, label in ((False, "Steve (обычные руки)"), (True, "Alex (тонкие руки)")):
            tk.Radiobutton(model, text=label, variable=self.skin_slim_var, value=value, bg=C_PANEL, fg=C_INK,
                           activebackground=C_PANEL, selectcolor=C_FIELD, font=("Segoe UI", 9),
                           command=self._skin_refresh_command).pack(anchor="w")
        self._button(left, "ПОКАЗАТЬ", self._skin_preview, accent=True).pack(fill="x", pady=(10, 0))

        right = tk.Frame(shell, bg=C_PANEL)
        right.grid(row=2, column=1, sticky="nsew", padx=(0, 16), pady=10)
        preview_box = tk.Frame(right, bg=C_FIELD, width=180, height=330, highlightthickness=1, highlightbackground=C_LINE)
        preview_box.pack_propagate(False)
        preview_box.pack()
        self.skin_canvas = tk.Label(preview_box, bg=C_FIELD, text="ПРЕДПРОСМОТР", fg=C_MUTED, font=("Consolas", 9, "bold"))
        self.skin_canvas.pack(fill="both", expand=True)
        tk.Label(shell, textvariable=self.skin_info_var, bg=C_PANEL, fg=C_TELEMETRY, font=("Segoe UI", 9),
                 wraplength=560, justify="left").grid(row=3, column=0, columnspan=2, sticky="w", padx=16)
        tk.Label(shell, text="КОМАНДА ДЛЯ ЧАТА ИГРЫ", bg=C_PANEL, fg=C_AMBER, font=("Consolas", 9, "bold")).grid(
            row=4, column=0, columnspan=2, sticky="w", padx=16, pady=(10, 3))
        cmd = tk.Entry(shell, textvariable=self.skin_cmd_var, state="readonly", readonlybackground=C_FIELD, fg=C_INK,
                       relief="flat", font=("Consolas", 9), highlightthickness=1, highlightbackground=C_LINE)
        cmd.grid(row=5, column=0, columnspan=2, sticky="ew", padx=16, ipady=5)
        actions = tk.Frame(shell, bg=C_PANEL)
        actions.grid(row=6, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 14))
        self.skin_sign_btn = self._button(actions, "ПОДГОТОВИТЬ ДЛЯ СЕРВЕРА", self._skin_sign_file)
        self.skin_sign_btn.pack(side="left")
        self._button(actions, "СКОПИРОВАТЬ КОМАНДУ", self._skin_copy_command, accent=True).pack(side="left", padx=(8, 0))
        self._button(actions, "СБРОСИТЬ", self._skin_reset).pack(side="right")
        tk.Label(shell, text="В игре нажмите T, вставьте команду (Ctrl+V) и Enter. Чтобы увидеть новый скин, "
                             "другим игрокам ничего делать не нужно.", bg=C_PANEL, fg=C_MUTED, font=("Segoe UI", 8),
                 wraplength=560, justify="left").grid(row=7, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 12))
        self._skin_source_changed()
        self._apply_ui_scale(dialog)
        dialog.after(50, lambda: dark_title_bar(dialog))

    def _skin_source_changed(self) -> None:
        source = self.skin_source_var.get()
        try:
            self.skin_nick_entry.configure(state="normal" if source in ("elyby", "tlauncher") else "disabled")
            self.skin_file_btn.configure(state="normal" if source == "file" else "disabled")
            self.skin_sign_btn.configure(state="normal" if source in ("elyby", "tlauncher", "file") else "disabled")
        except (tk.TclError, AttributeError):
            pass
        self._skin_pending = {}
        self.skin_cmd_var.set("")
        notes = {
            "official": "Официальный скин аккаунта Microsoft. Команда вернёт его, если вы ставили другой.",
            "elyby": "Публичный скин Ely.by по нику: вход и пароль не нужны. Для сервера скин подписывается MineSkin.",
            "tlauncher": "Публичный скин TLauncher по нику: вход и пароль не нужны. Для сервера скин подписывается MineSkin.",
            "file": "Свой PNG 64×64. Для показа другим игрокам файл подписывается сервисом MineSkin (с вашего согласия).",
            "default": "Стандартный скин Minecraft (Steve/Alex).",
        }
        self.skin_info_var.set(notes.get(source, ""))
        if source in ("official", "default"):
            self.skin_cmd_var.set(skin_command(source))

    def _skin_pick_file(self) -> None:
        selected = filedialog.askopenfilename(parent=self.skin_dialog, title="Выберите PNG-скин",
                                              filetypes=[("PNG", "*.png")])
        if selected:
            self._skin_file_path = selected
            self._skin_preview()

    def _skin_preview(self) -> None:
        source = self.skin_source_var.get()
        nick = self.skin_nick_var.get().strip()
        self.skin_info_var.set("Загружаю скин…")

        def worker() -> None:
            try:
                url = ""
                if source in ("elyby", "tlauncher"):
                    data, url = resolve_external_skin(source, nick)
                elif source == "file":
                    path = Path(getattr(self, "_skin_file_path", "") or "")
                    if not path.is_file():
                        raise ValueError("Сначала выберите PNG-файл.")
                    if path.stat().st_size > SKIN_MAX_BYTES:
                        raise ValueError(f"Файл больше {SKIN_MAX_BYTES // 1024} КБ.")
                    data = path.read_bytes()
                elif source == "official":
                    skin_path = minecraft_skin_path(str(self.state_data.get("msa_uuid") or ""))
                    if skin_path is None:
                        raise RuntimeError("Не удалось получить официальный скин (нет сети или скин не задан).")
                    data = skin_path.read_bytes()
                else:
                    self._emit("skin_preview", {"source": source, "info": "Стандартный скин Minecraft."})
                    return
                facts = validate_skin_png(data)
                self._emit("skin_preview", {"source": source, "facts": facts, "url": url, "data": data})
            except Exception as e:
                self._emit("skin_preview", {"source": source, "error": str(e)})

        threading.Thread(target=worker, daemon=True).start()

    def _show_skin_preview(self, result: dict[str, Any]) -> None:
        if self.skin_dialog is None or not self.skin_dialog.winfo_exists() or result.get("source") != self.skin_source_var.get():
            return
        if result.get("error"):
            self.skin_info_var.set("Не получилось: " + str(result["error"]))
            self._skin_pending = {}
            self.skin_cmd_var.set("")
            return
        facts = result.get("facts")
        if not facts:
            self.skin_info_var.set(str(result.get("info") or ""))
            return
        image = skin_preview_image(facts["image"], max(4, px(5)))
        self._skin_preview_photo = ImageTk.PhotoImage(image)
        self.skin_canvas.configure(image=self._skin_preview_photo, text="")
        if facts["slim"] != self.skin_slim_var.get() and result["source"] != "official":
            self.skin_slim_var.set(facts["slim"])
        self._skin_pending = {"source": result["source"], "data": result.get("data")}
        parts = [f"PNG {facts['width']}×{facts['height']}", "есть прозрачность" if facts["has_transparency"] else "без прозрачности",
                 "модель Alex" if facts["slim"] else "модель Steve"]
        self.skin_info_var.set("Скин проверен: " + ", ".join(parts) + ".")
        self.state_data["skin_source"] = result["source"]
        self.state_data["skin_nick"] = self.skin_nick_var.get().strip()
        self.state_data["skin_slim"] = bool(self.skin_slim_var.get())
        atomic_write_json(STATE_FILE, self.state_data)
        self._skin_refresh_command()

    def _skin_refresh_command(self) -> None:
        pending = getattr(self, "_skin_pending", {}) or {}
        source = self.skin_source_var.get()
        if source in ("official", "default"):
            self.skin_cmd_var.set(skin_command(source))
        elif pending.get("url") and pending.get("source") == source:
            self.skin_cmd_var.set(skin_command(source, pending["url"], bool(self.skin_slim_var.get())))
        else:
            self.skin_cmd_var.set("")

    def _skin_sign_file(self) -> None:
        pending = getattr(self, "_skin_pending", {}) or {}
        source = self.skin_source_var.get()
        if pending.get("source") != source or not pending.get("data"):
            self.skin_info_var.set("Сначала нажмите «ПОКАЗАТЬ» — скин нужно проверить.")
            return
        if not messagebox.askyesno(
                "Скин для сервера",
                "Чтобы все игроки видели этот скин, лаунчер загрузит картинку в сервис MineSkin.org (без вашего ника "
                "и аккаунта, с пометкой «не в общем каталоге»). MineSkin получит подпись Mojang и вернёт ссылку на "
                "textures.minecraft.net.\n\nПродолжить?", parent=self.skin_dialog):
            return
        data, variant = pending["data"], "slim" if self.skin_slim_var.get() else "classic"
        self.skin_info_var.set("Отправляю скин в MineSkin… это может занять до минуты.")

        def worker() -> None:
            try:
                self._emit("skin_signed", {"source": source, "url": mineskin_sign_png(data, variant)})
            except Exception as e:
                self._emit("skin_preview", {"source": source, "error": str(e)})

        threading.Thread(target=worker, daemon=True).start()

    def _skin_signed(self, result: dict[str, str]) -> None:
        if self.skin_dialog is None or not self.skin_dialog.winfo_exists():
            return
        if result.get("source") != self.skin_source_var.get():
            return
        self._skin_pending = {"source": result["source"], "url": result["url"]}
        self._skin_refresh_command()
        self.skin_info_var.set("Готово: скин подписан Mojang. Скопируйте команду и выполните её в игре.")
        self._log("Скин подготовлен для сервера через MineSkin.")

    def _skin_copy_command(self) -> None:
        command = self.skin_cmd_var.get().strip()
        if not command:
            self.skin_info_var.set("Команды пока нет: нажмите «ПОКАЗАТЬ»" +
                                   (", затем «ПОДГОТОВИТЬ ДЛЯ СЕРВЕРА»." if self.skin_source_var.get() in ("elyby", "tlauncher", "file") else "."))
            return
        self._copy_text(command)
        self.skin_info_var.set("Команда скопирована. В игре: T → Ctrl+V → Enter.")

    def _skin_reset(self) -> None:
        source = "official" if self.auth_var.get() == "microsoft" and self.state_data.get("msa_uuid") else "default"
        self.skin_source_var.set(source)
        for key in ("skin_source", "skin_nick", "skin_slim"):
            self.state_data.pop(key, None)
        atomic_write_json(STATE_FILE, self.state_data)
        self.skin_nick_var.set("")
        self._skin_source_changed()
        self.skin_canvas.configure(image="", text="ПРЕДПРОСМОТР")

    def _logout_microsoft(self) -> None:
        uuid_value = str(self.state_data.get("msa_uuid") or "").strip()
        name = str(self.state_data.get("msa_username") or "").strip()
        if not uuid_value or not messagebox.askyesno(APP_NAME, f"Выйти из аккаунта {name}? Сохранённый вход будет удалён "
                                                                "с этого компьютера."):
            return

        def job() -> None:
            code = run_pmc(["--main-dir", str(INSTANCE_DIR), "--output", "machine", "auth", "forget", uuid_value], LAUNCH_LOG)
            if code != 0:
                raise RuntimeError("Не удалось удалить сохранённый вход. Подробности — в «ЖУРНАЛ».")
            for key in ("msa_uuid", "msa_username"):
                self.state_data[key] = ""
            atomic_write_json(STATE_FILE, self.state_data)
            (CACHE_DIR / f"skin-{uuid_value.replace('-', '')}.png").unlink(missing_ok=True)
            self._emit("auth_changed", None)
            self._emit("status", "Вы вышли из аккаунта")
            self._emit("detail", "Сохранённый вход Microsoft удалён с этого компьютера")
            self._emit("log", f"Выход из аккаунта {name} выполнен.")

        self._start_thread(job)

    def _update_launcher(self) -> None:
        def job() -> None:
            asset = get_release_asset()
            info = asset.get("launcher_asset") or {}
            if version_tuple(str(info.get("version", ""))) <= version_tuple(APP_VERSION):
                self._emit("status", "Лаунчер уже обновлён")
                return
            url, digest = str(info.get("url", "")), str(info.get("sha256", ""))
            if not url.startswith("https://") or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise RuntimeError("Некорректные данные обновления лаунчера.")
            self._emit("status", "Скачиваю новую версию лаунчера…")
            staged = CACHE_DIR / ("launcher-" + digest + ".exe")
            download_file(url, staged, int(info["size"]),
                          lambda n,t: self._emit("progress", n/max(t,1)*100))
            self_update.prepare(staged, digest)
            self._emit("restart_launcher", None)
        self._start_thread(job)

    def _install_incremental(self, asset: dict[str, Any]) -> None:
        ref = asset["file_index"]
        digest = str(ref.get("sha256", ""))
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or not str(ref.get("url", "")).startswith("https://"):
            raise RuntimeError("Некорректный индекс обновления.")
        path = CACHE_DIR / ("index-" + digest + ".json")
        download_file(ref["url"], path, int(ref["size"]), lambda n,t: None)
        if sha256_file(path) != digest:
            raise RuntimeError("Индекс обновления повреждён.")
        index = incremental.validate_index(json.loads(path.read_text("utf-8")))
        if index["packageSha256"] != expected_sha256(asset) or index["url"] != asset["url"] or index["packageSize"] != asset["size"]:
            raise RuntimeError("Индекс относится к другой версии сборки.")
        previous = list(self.state_data.get("managed_files", []))
        self._emit("status", "Сравниваю файлы сборки…")
        def progress(done: int, total: int) -> None:
            self._emit("progress", done / max(total, 1) * 100)
            self._emit("progress_text", f"Изменённые файлы: {format_bytes(done)} / {format_bytes(total)}")
        atomic_write_json(INSTALL_JOURNAL, {"target": asset["identity"], "incremental": True})
        managed, hashes = incremental.sync_pack(index, INSTANCE_DIR, previous, CACHE_DIR / "incremental", is_preserved,
                                                progress=progress)
        self.state_data.update(pack_digest=asset["digest"], pack_identity=asset["identity"],
                               pack_version=asset["release_name"], managed_files=managed)
        atomic_write_json(FILE_INDEX, {"identity": asset["identity"], "files": hashes})
        atomic_write_json(STATE_FILE, self.state_data)
        INSTALL_JOURNAL.unlink(missing_ok=True)
        self._emit("pack_value", asset["release_name"])
        self._emit("progress", 100)
        self._emit("log", "Обновление завершено. Неизменённые файлы повторно не скачивались.")

    def _check_launcher_version(self, asset: dict[str, Any]) -> None:
        latest, minimum = asset.get("launcher_version") or "", asset.get("launcher_min") or ""
        if latest and version_tuple(latest) > version_tuple(APP_VERSION):
            self._emit("launcher_update", latest)
        if minimum and version_tuple(APP_VERSION) < version_tuple(minimum):
            raise RuntimeError(f"Эта версия лаунчера ({APP_VERSION}) устарела для текущей сборки. Скачайте лаунчер "
                               f"{latest or minimum} на сайте Project Meridian: {LAUNCHER_DOWNLOAD_PAGE}")

    def _pack_installed(self) -> bool:
        return INSTANCE_DIR.is_dir() and any(INSTANCE_DIR.iterdir()) and bool(self.state_data.get("pack_identity"))

    def _obtain_verified_zip(self, asset: dict[str, Any]) -> Path:
        cache_zip = cached_pack_path(asset)
        expected = expected_sha256(asset)
        if cache_zip.is_file():
            self._emit("status", "Проверяю скачанный архив…")
            if sha256_file(cache_zip) == expected:
                self._emit("log", "Использую уже скачанный проверенный архив.")
                return cache_zip
            cache_zip.unlink(missing_ok=True)
        partial = cache_zip.with_suffix(cache_zip.suffix + ".part")
        already = partial.stat().st_size if partial.exists() else 0
        ensure_free_space(CACHE_DIR, max(0, int(asset["size"]) - already), "скачивания сборки")
        self._emit("status", "Скачиваю сборку Project Meridian…")
        self._emit("log", f"Скачивание {asset['release_name']} ({format_bytes(asset['size'])})"
                          + (f", докачка с {format_bytes(already)}" if already else "") + "…")

        def progress(done: int, total: int) -> None:
            pct = (done / total * 100) if total else 0
            self._emit("progress", pct)
            if total:
                self._emit("progress_text", f"{pct:.1f}% • {format_bytes(done)} / {format_bytes(total)}")

        download_file(asset["url"], cache_zip, asset["size"], progress)
        self._emit("status", "Проверяю архив…")
        if sha256_file(cache_zip) != expected:
            cache_zip.unlink(missing_ok=True)
            raise RuntimeError("Скачанный архив повреждён (SHA-256 не совпал) и удалён. Нажмите «ИГРАТЬ» ещё раз.")
        self._emit("log", "SHA-256 архива совпадает с манифестом.")
        return cache_zip

    def _install_zip(self, zip_path: Path, asset: dict[str, Any]) -> None:
        previous = {k: self.state_data.get(k) for k in ("pack_identity", "pack_digest")}
        previous_managed = list(self.state_data.get("managed_files", []))
        atomic_write_json(INSTALL_JOURNAL, {"target": asset["identity"], "previous": previous,
                                            "started": time.strftime("%Y-%m-%d %H:%M:%S")})
        if legacy_dev_state_present(self.state_data):
            removed = cleanup_legacy_dev_files()
            self._emit("log", f"Переход с тестовой версии: удалено устаревших файлов — {len(removed)}.")
        self._emit("status", "Устанавливаю сборку…")
        self._emit("progress", 0)

        def progress(done: int, total: int) -> None:
            self._emit("progress", done / total * 100)
            self._emit("progress_text", f"Файлы сборки: {done} / {total}")

        try:
            managed, index = install_from_zip(zip_path, previous_managed, progress)
        except Exception as e:
            self._emit("log", f"Установка прервана: {type(e).__name__}: {e}")
            restored = self._rollback(previous, zip_path)
            raise RuntimeError(
                f"Не удалось установить сборку: {e}\n\n"
                + ("Прежняя версия восстановлена — можно играть." if restored else
                   "Лаунчер завершит установку при следующем запуске; миры и настройки не затронуты.")
            ) from e

        self.state_data["pack_digest"] = asset["digest"]
        self.state_data["pack_identity"] = asset["identity"]
        self.state_data["pack_version"] = asset["release_name"]
        self.state_data["managed_files"] = managed
        self.state_data.pop("channel", None)
        atomic_write_json(FILE_INDEX, {"identity": asset["identity"], "files": index})
        atomic_write_json(STATE_FILE, self.state_data)
        finish_legacy_dev_cleanup()
        INSTALL_JOURNAL.unlink(missing_ok=True)
        self._prune_pack_cache(keep={zip_path.name, cached_pack_path({"digest": previous.get("pack_digest") or "",
                                                                     "identity": "-"}).name})
        self._emit("progress", 100)
        self._emit("pack_value", asset["release_name"])
        self._emit("log", f"Сборка {asset['release_name']} установлена: {len(managed)} файлов.")

    def _rollback(self, previous: dict[str, Any], failed_zip: Path) -> bool:
        """Restores the previous working version from its verified cached archive, if there is one."""
        digest = str(previous.get("pack_digest") or "")
        if not digest.startswith("sha256:"):
            return False
        old_zip = cached_pack_path({"digest": digest, "identity": "-"})
        try:
            if not old_zip.is_file() or sha256_file(old_zip) != digest.split(":", 1)[1]:
                return False
            self._emit("status", "Восстанавливаю прежнюю версию…")
            with zipfile.ZipFile(failed_zip) as zf:
                new_files = [rel for rel in pack_members(zf) if not is_preserved(rel)]
            with zipfile.ZipFile(old_zip) as zf:
                old_files = set(pack_members(zf))
            managed, index = install_from_zip(old_zip, [rel for rel in new_files if rel not in old_files])
        except Exception as e:
            self._emit("log", f"Откат не удался: {type(e).__name__}: {e}")
            return False
        self.state_data["managed_files"] = managed
        atomic_write_json(FILE_INDEX, {"identity": previous.get("pack_identity"), "files": index})
        atomic_write_json(STATE_FILE, self.state_data)
        INSTALL_JOURNAL.unlink(missing_ok=True)
        self._emit("log", "Прежняя версия сборки восстановлена из проверенного архива.")
        return True

    @staticmethod
    def _prune_pack_cache(keep: set[str]) -> None:
        for path in CACHE_DIR.glob("minecraft-*.zip"):
            if path.name not in keep:
                path.unlink(missing_ok=True)

    def _open_game_folder(self) -> None:
        ensure_dirs()
        self._open_path(INSTANCE_DIR)

    def _open_logs(self) -> None:
        ensure_dirs()
        self._open_path(LOG_DIR)

    @staticmethod
    def _open_path(path: Path) -> None:
        if os.name == "nt":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--apply-self-update":
        self_update.apply_job(sys.argv[2])
        return
    hide_console_if_needed()
    ensure_dirs()
    app = MeridianLauncher()
    if "--ui-preview=skin" in sys.argv:
        app.after(300, app._open_skin_dialog)
    if "--ui-preview=log" in sys.argv:
        app.after(300, app._open_log_dialog)
    if "--ui-preview=keygen" in sys.argv:
        app.after(300, lambda: app._open_keygen(sound="--mute" not in sys.argv))
    if "--ui-preview=auth" in sys.argv:
        # screenshots of the sign-in dialog: no Microsoft request, placeholder code
        app.auth_code_var.set("XXXX-XXXX")
        app.auth_step_var.set("Предпросмотр окна входа: код скрыт, запрос к Microsoft не отправлялся.")
        app.after(300, app._open_auth_dialog)
    for arg in sys.argv:
        if arg.startswith("--layout-report="):
            target = arg.split("=", 1)[1]
            app.after(2500, lambda t=target: app.write_layout_report(t))
            # a second report after the test resized the window (used to check the minimum size)
            app.after(6500, lambda t=target: app.write_layout_report(t[:-5] + "-2.json" if t.endswith(".json") else t + "-2"))
    if "--smoke-ui" in sys.argv:
        app.update_idletasks()
        show = app._open_keygen(sound=False, animate=False)   # the intro draws a few frames without errors
        for _ in range(5):
            show._frame(time.perf_counter() - show.start + 1.0)
            app.update_idletasks()
        app._close_keygen(animate=False)
        assert app._show_mode is None and not app._root_frame.find_withtag("keygen")
        app.destroy()
        return
    app.mainloop()


if __name__ == "__main__":
    main()
