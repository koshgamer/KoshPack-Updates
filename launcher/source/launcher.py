from __future__ import annotations

import base64
import ctypes
import hashlib
import io
import math
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import webbrowser
import zipfile
from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageTk

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME = "Project Meridian Launcher"
APP_VERSION = "0.2.5"
REPO = "koshgamer/KoshPack-Updates"
RELEASE_TAG = "current"
UPDATE_MANIFEST_URL = "https://raw.githubusercontent.com/koshgamer/KoshPack-Updates/main/launcher/manifest.json"
DEV_MANIFEST_URL = "https://raw.githubusercontent.com/koshgamer/KoshPack-Updates/main/launcher/dev-manifest.json"
DEV_MANIFEST_API_URL = "https://api.github.com/repos/koshgamer/KoshPack-Updates/contents/launcher/dev-manifest.json?ref=main"
DEV_ARMOR_TARGET = "koshpack-armor-specialties-DEV.jar"
PACK_ASSET_NAME = "minecraft.zip"
EXPECTED_BUNDLED_PACK_SHA256 = "a815398de0b6863bafb15d6cecbaabfca69a8886bb22313847593ec7958bc227"
MC_VERSION = "1.21.1"
NEOFORGE_VERSION = "21.1.248"
LAUNCH_SPEC = f"neoforge::{NEOFORGE_VERSION}"
PMC_VERSION = "5.0.5"
PMC_ARCHIVE_URL = "https://github.com/theorzr/portablemc/releases/download/v5.0.5/portablemc-5.0.5-windows-x86_64-msvc.zip"
PMC_ARCHIVE_SHA256 = "c1ad577e9441040e65a55b521c6ab0fc4c32ec0c6f114d169ae6eee7d3d9fda6"
PROJECT_SITE_URL = ""
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

# Backward-compatible aliases used by the existing UI code.
C_AMBER = C_COPPER
C_AMBER_2 = C_TELEMETRY

USER_AGENT = f"ProjectMeridianLauncher/{APP_VERSION} (+https://github.com/{REPO})"
PRESERVE_PREFIXES = (
    "saves/",
    "screenshots/",
    "crash-reports/",
    "logs/",
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
        "channel": "stable",
        "dev_armor_digest": "",
        "dev_armor_name": "",
        "dev_armor_source": "",
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


def request_json(url: str, timeout: int = 30) -> dict[str, Any]:
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
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def get_release_asset() -> dict[str, Any]:
    manifest = request_json(UPDATE_MANIFEST_URL)
    package = manifest.get("package") or {}
    url = str(package.get("url") or "")
    sha256 = str(package.get("sha256") or "").lower()
    size = int(package.get("size") or 0)
    if not url:
        raise RuntimeError("В публичном манифесте Project Meridian не указан URL сборки.")
    if not sha256:
        raise RuntimeError("В публичном манифесте Project Meridian не указан SHA-256 сборки.")
    identity = f"{manifest.get('packVersion','unknown')}:{sha256}"
    return {
        "url": url,
        "size": size,
        "digest": f"sha256:{sha256}",
        "identity": identity,
        "updated_at": str(manifest.get("packVersion") or ""),
        "release_name": str(manifest.get("packVersion") or RELEASE_TAG),
    }


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


def _reconstruct_chunked_pack(base_dir: Path) -> Path | None:
    wrappers = [
        (base_dir / "KoshPack-part01.zip", "minecraft.zip.part01"),
        (base_dir / "KoshPack-part02.zip", "minecraft.zip.part02"),
    ]
    if not all(wrapper.is_file() for wrapper, _member in wrappers):
        return None

    target = CACHE_DIR / "minecraft-from-chunks.zip"
    if target.is_file():
        try:
            if sha256_file(target) == EXPECTED_BUNDLED_PACK_SHA256:
                return target
        except OSError:
            pass
        target.unlink(missing_ok=True)

    tmp = target.with_suffix(".zip.part")
    tmp.unlink(missing_ok=True)
    with tmp.open("wb") as out:
        for wrapper, member in wrappers:
            with zipfile.ZipFile(wrapper) as zf:
                names = zf.namelist()
                chosen = member if member in names else next((n for n in names if n.endswith(member)), None)
                if not chosen:
                    raise RuntimeError(f"В {wrapper.name} не найден {member}")
                with zf.open(chosen) as src:
                    shutil.copyfileobj(src, out, length=4 * 1024 * 1024)

    actual = sha256_file(tmp)
    if actual != EXPECTED_BUNDLED_PACK_SHA256:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            "Части KoshPack скачались неправильно: SHA-256 восстановленного minecraft.zip не совпал."
        )
    tmp.replace(target)
    return target


def bundled_pack_path() -> Path | None:
    candidates: list[Path] = []
    base_dir: Path
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
        candidates.append(base_dir / PACK_ASSET_NAME)
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / PACK_ASSET_NAME)
    else:
        base_dir = Path(__file__).resolve().parent
        candidates.append(base_dir / PACK_ASSET_NAME)

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return _reconstruct_chunked_pack(base_dir)


def download_file(url: str, dest: Path, expected_size: int, on_progress: Callable[[int, int], None]) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    max_attempts = 5
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
            with urllib.request.urlopen(req, timeout=90) as response:
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


def _armor_jar_name(name: str) -> bool:
    low = name.lower()
    return low.endswith(".jar") and (
        low.startswith("koshpack_armor_")
        or low.startswith("koshpack-armor-specialties")
    )


def find_local_dev_armor() -> Path | None:
    candidates: list[Path] = []
    shallow_roots = [
        Path.home() / "Downloads",
        Path.home() / "Загрузки",
    ]
    if getattr(sys, "frozen", False):
        shallow_roots.append(Path(sys.executable).resolve().parent)
    else:
        shallow_roots.append(Path(__file__).resolve().parent)

    for root in shallow_roots:
        if not root.is_dir():
            continue
        try:
            for item in root.iterdir():
                if item.is_file() and _armor_jar_name(item.name) and item.name != DEV_ARMOR_TARGET:
                    candidates.append(item)
        except OSError:
            pass

    # Also reuse armor builds that were already tested through PrismLauncher.
    appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    prism_instances = appdata / "PrismLauncher" / "instances"
    if prism_instances.is_dir():
        try:
            for mods_dir in prism_instances.glob("*/minecraft/mods"):
                if not mods_dir.is_dir():
                    continue
                for item in mods_dir.iterdir():
                    if item.is_file() and _armor_jar_name(item.name) and item.name != DEV_ARMOR_TARGET:
                        candidates.append(item)
            for mods_dir in prism_instances.glob("*/.minecraft/mods"):
                if not mods_dir.is_dir():
                    continue
                for item in mods_dir.iterdir():
                    if item.is_file() and _armor_jar_name(item.name) and item.name != DEV_ARMOR_TARGET:
                        candidates.append(item)
        except OSError:
            pass

    if not candidates:
        return None

    def score(path: Path) -> tuple[int, float]:
        name = path.name.lower()
        alpha = 0
        marker = "alpha"
        pos = name.rfind(marker)
        if pos >= 0:
            digits = []
            for ch in name[pos + len(marker):]:
                if ch.isdigit():
                    digits.append(ch)
                elif digits:
                    break
            if digits:
                try:
                    alpha = int("".join(digits))
                except ValueError:
                    alpha = 0
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0.0
        return alpha, mtime

    return max(candidates, key=score)


def restore_stable_armor() -> int:
    mods = INSTANCE_DIR / "mods"
    if not mods.is_dir():
        return 0

    changed = 0
    dev_target = mods / DEV_ARMOR_TARGET
    if dev_target.exists():
        try:
            dev_target.unlink()
            changed += 1
        except OSError:
            pass

    for backup in list(mods.glob("*.meridian-stable-bak")):
        original = Path(str(backup)[: -len(".meridian-stable-bak")])
        try:
            if original.exists():
                backup.unlink()
            else:
                backup.replace(original)
            changed += 1
        except OSError:
            pass
    return changed


def apply_dev_armor(source: Path) -> tuple[str, str]:
    if not source.is_file():
        raise RuntimeError(f"DEV JAR не найден: {source}")

    mods = INSTANCE_DIR / "mods"
    mods.mkdir(parents=True, exist_ok=True)
    restore_stable_armor()

    # Hide the stable copy of this mod while DEV is active.
    for jar in list(mods.glob("*.jar")):
        if jar.name == DEV_ARMOR_TARGET:
            continue
        if _armor_jar_name(jar.name):
            backup = Path(str(jar) + ".meridian-stable-bak")
            try:
                if backup.exists():
                    backup.unlink()
                jar.replace(backup)
            except OSError as e:
                raise RuntimeError(f"Не удалось временно отключить {jar.name}: {e}") from e

    target = mods / DEV_ARMOR_TARGET
    shutil.copy2(source, target)
    digest = sha256_file(target)
    return target.name, digest


def get_dev_manifest() -> dict[str, Any]:
    """Read DEV manifest through the GitHub API to avoid stale raw CDN responses."""
    payload = request_json(DEV_MANIFEST_API_URL)
    encoded = str(payload.get("content") or "").replace("\\n", "")
    if not encoded:
        # Last-resort compatibility path.
        return request_json(DEV_MANIFEST_URL + f"?nocache={int(time.time())}")
    try:
        decoded = base64.b64decode(encoded).decode("utf-8")
        manifest = json.loads(decoded)
    except Exception as e:
        raise RuntimeError(f"Не удалось прочитать DEV-манифест: {e}") from e
    if not isinstance(manifest, dict):
        raise RuntimeError("DEV-манифест имеет неверный формат.")
    return manifest


def download_dev_armor_from_manifest(on_progress: Callable[[int, int], None]) -> tuple[Path, str]:
    manifest = get_dev_manifest()
    armor = manifest.get("armor") or {}
    version = str(armor.get("version") or "dev-current")
    url = str(armor.get("url") or "")
    sha256 = str(armor.get("sha256") or "").lower()
    size = int(armor.get("size") or 0)
    if not url or not sha256:
        raise RuntimeError("DEV-канал доступен, но в нём пока не опубликован JAR.")

    safe_version = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in version)
    target = CACHE_DIR / f"KoshPack_Armor_{safe_version}.jar"
    if target.is_file() and sha256_file(target) == sha256:
        return target, version
    target.unlink(missing_ok=True)

    download_file(url, target, size, on_progress)
    actual = sha256_file(target)
    if actual != sha256:
        target.unlink(missing_ok=True)
        raise RuntimeError("SHA-256 DEV-брони не совпал. Файл удалён.")
    return target, version


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


def choose_payload_root(staging: Path) -> Path:
    for name in (".minecraft", "minecraft"):
        p = staging / name
        if p.is_dir():
            return p
    entries = [p for p in staging.iterdir() if p.name != "__MACOSX"]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return staging


def is_preserved(rel: str) -> bool:
    normalized = rel.replace("\\", "/")
    return normalized in PRESERVE_FILES or any(normalized.startswith(prefix) for prefix in PRESERVE_PREFIXES)


def remove_old_managed_files(managed_files: list[str]) -> None:
    for rel in managed_files:
        if is_preserved(rel):
            continue
        target = INSTANCE_DIR / rel
        try:
            if target.is_file() or target.is_symlink():
                target.unlink()
        except OSError:
            pass
    for root, dirs, _files in os.walk(INSTANCE_DIR, topdown=False):
        for d in dirs:
            p = Path(root) / d
            try:
                p.rmdir()
            except OSError:
                pass


def install_payload(payload_root: Path, previous_managed: list[str]) -> list[str]:
    remove_old_managed_files(previous_managed)
    managed: list[str] = []
    for src in payload_root.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(payload_root).as_posix()
        dst = INSTANCE_DIR / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if is_preserved(rel) and dst.exists():
            continue
        shutil.copy2(src, dst)
        if not is_preserved(rel):
            managed.append(rel)
    return sorted(managed)


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
        log.write("PortableMC args: " + " ".join(pmc_args) + "\n")
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
            log.write(line + "\n")
            log.flush()
            if on_event is not None:
                try:
                    on_event(line.split("\t"))
                except Exception as callback_error:
                    log.write(f"[launcher progress parser] {callback_error}\n")
                    log.flush()
        return proc.wait()


class RamSlider(tk.Canvas):
    """Small custom slider so the handle is always visible on Windows."""

    def __init__(self, parent: tk.Misc, variable: tk.IntVar, from_: int = 4, to: int = 16) -> None:
        super().__init__(
            parent,
            height=30,
            bg=C_PANEL,
            bd=0,
            highlightthickness=0,
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
        left, right = 9, max(10, width - 9)
        ratio = max(0.0, min(1.0, (event.x - left) / max(1, right - left)))
        value = round(self.minimum + ratio * (self.maximum - self.minimum))
        self.variable.set(max(self.minimum, min(self.maximum, value)))

    def _draw(self) -> None:
        self.delete("all")
        width = max(1, self.winfo_width())
        left, right, y = 9, max(10, width - 9), 15
        value = max(self.minimum, min(self.maximum, int(self.variable.get())))
        ratio = (value - self.minimum) / max(1, self.maximum - self.minimum)
        x = left + (right - left) * ratio

        self.create_line(left, y, right, y, fill=C_LINE, width=2)
        self.create_line(left, y, x, y, fill=C_COPPER, width=3)

        for step in range(self.minimum, self.maximum + 1, 2):
            r = (step - self.minimum) / max(1, self.maximum - self.minimum)
            tick_x = left + (right - left) * r
            self.create_line(tick_x, y - 4, tick_x, y + 4, fill="#314346", width=1)

        # Permanent high-contrast handle; no hover required.
        self.create_rectangle(
            x - 9, y - 9, x + 9, y + 9,
            fill=C_COPPER,
            outline=C_TELEMETRY,
            width=2,
        )
        self.create_rectangle(
            x - 3, y - 3, x + 3, y + 3,
            fill=C_TELEMETRY,
            outline="",
        )


class MeridianLauncher(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        ensure_dirs()
        self.state_data = load_state()
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.busy = False

        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1180x760")
        self.minsize(1040, 700)
        self.configure(bg=C_BG)

        self.username_var = tk.StringVar(value=str(self.state_data.get("username", "Player")))
        self.email_var = tk.StringVar(value=str(self.state_data.get("email", "")))
        self.auth_var = tk.StringVar(value=str(self.state_data.get("auth_mode", "offline")))
        self.ram_var = tk.IntVar(value=int(self.state_data.get("ram_gb", 8)))
        self.channel_var = tk.StringVar(value=str(self.state_data.get("channel", "stable")))
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

        self._build_style()
        self._build_ui()
        self._sync_auth_fields()
        self.after(100, self._drain_events)
        self.after(120, self._animate_ui)
        self.after(400, self._initial_check)
        self.after(900, self._refresh_skin_async)

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
            pady=11,
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

    def _build_ui(self) -> None:
        # Header
        root = tk.Frame(self, bg=C_BG)
        root.pack(fill="both", expand=True, padx=28, pady=22)

        header = tk.Frame(root, bg=C_BG, height=84)
        header.pack(fill="x")

        self.brand_icon = tk.Canvas(header, width=54, height=48, bg=C_BG, bd=0, highlightthickness=0)
        self.brand_icon.pack(side="left", padx=(0, 14))
        self._draw_brand_icon()

        brand_box = tk.Frame(header, bg=C_BG)
        brand_box.pack(side="left", fill="y")
        self.brand_title = tk.Label(
            brand_box,
            text="PROJECT MERIDIAN",
            bg=C_BG,
            fg=C_INK,
            font=("Segoe UI Black", 26),
            anchor="w",
        )
        self.brand_title.pack(anchor="w")
        tk.Label(
            brand_box,
            text="MERIDIAN_SYS // KOSHPACK LAUNCH CONTROL",
            bg=C_BG,
            fg=C_MUTED,
            font=("Consolas", 9, "bold"),
        ).pack(anchor="w", pady=(2, 0))

        head_right = tk.Frame(header, bg=C_BG)
        head_right.pack(side="right", anchor="n")
        status_row = tk.Frame(head_right, bg=C_BG)
        status_row.pack(anchor="e")
        self.system_dot = tk.Canvas(status_row, width=12, height=12, bg=C_BG, bd=0, highlightthickness=0)
        self.system_dot.pack(side="left", padx=(0, 7))
        self.system_dot_id = self.system_dot.create_oval(2, 2, 10, 10, fill=C_AMBER, outline="")
        tk.Label(
            status_row,
            text="SYSTEM ONLINE",
            bg=C_BG,
            fg=C_MUTED,
            font=("Consolas", 9, "bold"),
        ).pack(side="left")
        tk.Label(
            head_right,
            text=f"v{APP_VERSION}  //  CURRENT",
            bg=C_BG,
            fg=C_AMBER,
            font=("Consolas", 9, "bold"),
        ).pack(anchor="e", pady=(7, 0))

        tk.Frame(root, bg=C_LINE, height=1).pack(fill="x", pady=(10, 18))

        body = tk.Frame(root, bg=C_BG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, minsize=330)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # Account / controls
        left = tk.Frame(body, bg=C_PANEL, highlightthickness=1, highlightbackground=C_LINE)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

        tk.Label(left, text="01 / АККАУНТ", bg=C_PANEL, fg=C_AMBER, font=("Consolas", 10, "bold")).pack(
            anchor="w", padx=22, pady=(20, 14)
        )

        profile = tk.Frame(left, bg=C_PANEL_2, highlightthickness=1, highlightbackground=C_LINE)
        profile.pack(fill="x", padx=22)

        self.skin_label = tk.Label(
            profile,
            text="NO\nSKIN",
            bg=C_FIELD,
            fg=C_AMBER,
            font=("Consolas", 18, "bold"),
            width=7,
            height=5,
            justify="center",
        )
        self.skin_label.pack(side="left", padx=12, pady=12)

        profile_text = tk.Frame(profile, bg=C_PANEL_2)
        profile_text.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=14)
        tk.Label(
            profile_text,
            textvariable=self.account_name_var,
            bg=C_PANEL_2,
            fg=C_INK,
            font=("Segoe UI Semibold", 14),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            profile_text,
            textvariable=self.account_type_var,
            bg=C_PANEL_2,
            fg=C_AMBER,
            font=("Consolas", 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(4, 0))
        tk.Label(
            profile_text,
            textvariable=self.account_note_var,
            bg=C_PANEL_2,
            fg=C_MUTED,
            font=("Segoe UI", 9),
            anchor="w",
            wraplength=150,
            justify="left",
        ).pack(fill="x", pady=(5, 0))

        mode = tk.Frame(left, bg=C_PANEL)
        mode.pack(fill="x", padx=22, pady=(16, 0))
        self.offline_radio = tk.Radiobutton(
            mode,
            text="OFFLINE",
            variable=self.auth_var,
            value="offline",
            command=self._sync_auth_fields,
            bg=C_PANEL,
            fg=C_INK,
            activebackground=C_PANEL,
            activeforeground=C_AMBER,
            selectcolor=C_FIELD,
            font=("Consolas", 9, "bold"),
        )
        self.offline_radio.pack(side="left")
        self.microsoft_radio = tk.Radiobutton(
            mode,
            text="MICROSOFT",
            variable=self.auth_var,
            value="microsoft",
            command=self._sync_auth_fields,
            bg=C_PANEL,
            fg=C_INK,
            activebackground=C_PANEL,
            activeforeground=C_AMBER,
            selectcolor=C_FIELD,
            font=("Consolas", 9, "bold"),
        )
        self.microsoft_radio.pack(side="left", padx=(18, 0))

        self.nick_label = tk.Label(left, text="ИГРОВОЙ НИК", bg=C_PANEL, fg=C_MUTED, font=("Consolas", 8, "bold"))
        self.nick_label.pack(anchor="w", padx=22, pady=(16, 5))
        self.username_entry = self._entry(left, self.username_var)
        self.username_entry.pack(fill="x", padx=22, ipady=8)

        self.microsoft_hint = tk.Label(
            left,
            text="Microsoft-вход откроется на официальной странице.\nПочту и пароль лаунчер не запрашивает.",
            bg=C_PANEL,
            fg=C_MUTED,
            font=("Segoe UI", 9),
            justify="left",
            wraplength=275,
        )
        self.microsoft_hint.pack(anchor="w", padx=22, pady=(12, 0))

        self.login_btn = self._button(left, "ПОДКЛЮЧИТЬ MICROSOFT", self._login_microsoft, accent=False)
        self.login_btn.pack(fill="x", padx=22, pady=(10, 0))

        tk.Label(left, text="02 / КАНАЛ СБОРКИ", bg=C_PANEL, fg=C_AMBER, font=("Consolas", 10, "bold")).pack(
            anchor="w", padx=22, pady=(18, 7)
        )
        channel_row = tk.Frame(left, bg=C_PANEL)
        channel_row.pack(fill="x", padx=22)
        self.stable_radio = tk.Radiobutton(
            channel_row,
            text="STABLE",
            variable=self.channel_var,
            value="stable",
            command=self._channel_changed,
            bg=C_PANEL,
            fg=C_INK,
            activebackground=C_PANEL,
            activeforeground=C_COPPER,
            selectcolor=C_FIELD,
            font=("Consolas", 9, "bold"),
        )
        self.stable_radio.pack(side="left")
        self.dev_radio = tk.Radiobutton(
            channel_row,
            text="DEV / БРОНЯ",
            variable=self.channel_var,
            value="dev",
            command=self._channel_changed,
            bg=C_PANEL,
            fg=C_TELEMETRY,
            activebackground=C_PANEL,
            activeforeground=C_TELEMETRY,
            selectcolor=C_FIELD,
            font=("Consolas", 9, "bold"),
        )
        self.dev_radio.pack(side="left", padx=(18, 0))
        self.channel_hint = tk.Label(
            left,
            text="DEV ищет свежую броню в сети, «Загрузках» и PrismLauncher.",
            bg=C_PANEL,
            fg=C_MUTED,
            font=("Segoe UI", 8),
            justify="left",
            wraplength=275,
        )
        self.channel_hint.pack(anchor="w", padx=22, pady=(3, 0))

        self.channel_update_btn = self._button(
            left,
            "↻  ОБНОВИТЬ DEV-БРОНЮ",
            self._update_pack,
        )
        self.channel_update_btn.pack(fill="x", padx=22, pady=(8, 0))

        tk.Label(left, text="03 / ПАМЯТЬ", bg=C_PANEL, fg=C_AMBER, font=("Consolas", 10, "bold")).pack(
            anchor="w", padx=22, pady=(12, 4)
        )
        ram_line = tk.Frame(left, bg=C_PANEL)
        ram_line.pack(fill="x", padx=22)
        self.ram_scale = RamSlider(ram_line, self.ram_var, from_=4, to=16)
        self.ram_scale.pack(side="left", fill="x", expand=True)
        self.ram_label = tk.Label(
            ram_line,
            textvariable=self.ram_var,
            bg=C_PANEL,
            fg=C_AMBER,
            font=("Consolas", 13, "bold"),
            width=3,
        )
        self.ram_label.pack(side="left")
        tk.Label(ram_line, text="ГБ", bg=C_PANEL, fg=C_MUTED, font=("Consolas", 9, "bold")).pack(side="left")

        tools = tk.Frame(left, bg=C_PANEL)
        tools.pack(fill="x", padx=22, pady=(10, 12))
        row = tk.Frame(tools, bg=C_PANEL)
        row.pack(fill="x")
        self._button(row, "ПАПКА", self._open_game_folder).pack(side="left", fill="x", expand=True)
        self._button(row, "ЛОГИ", self._open_logs).pack(side="left", fill="x", expand=True, padx=(8, 0))
        self._button(tools, "ПРОВЕРИТЬ / ПОЧИНИТЬ", self._repair_pack).pack(fill="x", pady=(7, 0))

        # Dashboard
        right = tk.Frame(body, bg=C_PANEL, highlightthickness=1, highlightbackground=C_LINE)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(6, weight=1)
        right.grid_columnconfigure(0, weight=1)

        tk.Label(
            right,
            text="MERIDIAN // LAUNCH CONTROL",
            bg=C_PANEL,
            fg=C_AMBER,
            font=("Consolas", 10, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=26, pady=(23, 0))

        self.status_label = tk.Label(
            right,
            textvariable=self.status_var,
            bg=C_PANEL,
            fg=C_INK,
            font=("Segoe UI Black", 25),
            anchor="w",
            justify="left",
        )
        self.status_label.grid(row=1, column=0, sticky="ew", padx=26, pady=(12, 2))

        tk.Label(
            right,
            textvariable=self.detail_var,
            bg=C_PANEL,
            fg=C_MUTED,
            font=("Consolas", 10),
            anchor="w",
            justify="left",
        ).grid(row=2, column=0, sticky="ew", padx=26)

        progress_shell = tk.Frame(right, bg=C_PANEL_2, highlightthickness=1, highlightbackground=C_LINE)
        progress_shell.grid(row=3, column=0, sticky="ew", padx=26, pady=(22, 14))
        self.progress = ttk.Progressbar(progress_shell, mode="determinate", maximum=100)
        self.progress.pack(fill="x", padx=1, pady=(1, 7))
        tk.Label(
            progress_shell,
            textvariable=self.progress_var,
            bg=C_PANEL_2,
            fg=C_MUTED,
            font=("Consolas", 9),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 9))

        initial_play_text = "ИГРАТЬ" if any(INSTANCE_DIR.iterdir()) else "УСТАНОВИТЬ И ИГРАТЬ"
        self.play_btn = self._button(right, initial_play_text, self._play, accent=True)
        self.play_btn.configure(font=("Consolas", 14, "bold"), pady=15)
        self.play_btn.grid(row=4, column=0, sticky="ew", padx=26)

        info = tk.Frame(right, bg=C_PANEL)
        info.grid(row=5, column=0, sticky="ew", padx=26, pady=(16, 12))
        for idx in range(3):
            info.grid_columnconfigure(idx, weight=1)

        self.pack_value = tk.StringVar(value="KoshPack // current")
        self.core_value = tk.StringVar(value=f"{MC_VERSION} // NF {NEOFORGE_VERSION}")
        self.account_value = tk.StringVar(value="OFFLINE")
        for idx, (caption, var) in enumerate((
            ("СБОРКА", self.pack_value),
            ("ЯДРО", self.core_value),
            ("АККАУНТ", self.account_value),
        )):
            card = tk.Frame(info, bg=C_PANEL_2, highlightthickness=1, highlightbackground=C_LINE)
            card.grid(row=0, column=idx, sticky="ew", padx=(0 if idx == 0 else 5, 0 if idx == 2 else 5))
            tk.Label(card, text=caption, bg=C_PANEL_2, fg="#65645f", font=("Consolas", 8, "bold")).pack(
                anchor="w", padx=11, pady=(9, 3)
            )
            tk.Label(card, textvariable=var, bg=C_PANEL_2, fg=C_INK, font=("Consolas", 9, "bold")).pack(
                anchor="w", padx=11, pady=(0, 10)
            )

        console_wrap = tk.Frame(right, bg=C_FIELD, highlightthickness=1, highlightbackground=C_LINE)
        console_wrap.grid(row=6, column=0, sticky="nsew", padx=26, pady=(0, 24))
        tk.Label(
            console_wrap,
            text="/// SYSTEM LOG",
            bg=C_FIELD,
            fg=C_AMBER,
            font=("Consolas", 8, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 0))
        self.log_text = tk.Text(
            console_wrap,
            height=8,
            bg=C_FIELD,
            fg="#a4a39c",
            insertbackground=C_AMBER,
            relief="flat",
            wrap="word",
            font=("Consolas", 9),
            padx=12,
            pady=9,
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")
        self._log("MERIDIAN_SYS ready. Сборка изолирована от обычного .minecraft.")

    def _draw_brand_icon(self) -> None:
        """Draw the same mark used in the website header (.meridian-mark)."""
        cv = self.brand_icon
        cv.delete("all")
        cx, cy = 27, 24
        r = 15
        ext = 20

        # Website: a square rotated 45deg -> diamond.
        cv.create_polygon(
            cx, cy - r,
            cx + r, cy,
            cx, cy + r,
            cx - r, cy,
            outline=C_COPPER,
            fill="",
            width=2,
        )

        # Website pseudo-elements rotate with the square, producing diagonal cross-lines.
        cv.create_line(cx - ext, cy - ext, cx + ext, cy + ext, fill=C_COPPER, width=1)
        cv.create_line(cx + ext, cy - ext, cx - ext, cy + ext, fill=C_COPPER, width=1)

        # Inner telemetry square, also rotated with the outer mark.
        ir = 7
        cv.create_polygon(
            cx, cy - ir,
            cx + ir, cy,
            cx, cy + ir,
            cx - ir, cy,
            outline=C_TELEMETRY,
            fill="",
            width=2,
        )

    def _animate_ui(self) -> None:
        self._animation_phase += 0.12
        pulse = (math.sin(self._animation_phase) + 1.0) / 2.0
        def blend(a: str, b: str, t: float) -> str:
            av = tuple(int(a[i:i+2], 16) for i in (1, 3, 5))
            bv = tuple(int(b[i:i+2], 16) for i in (1, 3, 5))
            rv = tuple(round(x + (y - x) * t) for x, y in zip(av, bv))
            return "#" + "".join(f"{v:02x}" for v in rv)
        glow = blend(C_INK, C_AMBER_2, pulse * 0.34)
        dot = blend("#614500", C_AMBER_2, 0.25 + pulse * 0.75)
        try:
            self.brand_title.configure(fg=glow)
            self.system_dot.itemconfigure(self.system_dot_id, fill=dot)
        except tk.TclError:
            return
        self.after(70, self._animate_ui)

    def _sync_auth_fields(self) -> None:
        is_ms = self.auth_var.get() == "microsoft"
        msa_name = str(self.state_data.get("msa_username") or "").strip()

        if is_ms:
            self.username_entry.configure(state="disabled")
            self.login_btn.configure(
                text="СМЕНИТЬ MICROSOFT" if msa_name else "ПОДКЛЮЧИТЬ MICROSOFT",
                state="normal",
            )
            if msa_name:
                self.account_name_var.set(msa_name)
                self.account_type_var.set("MICROSOFT // CONNECTED")
                self.account_note_var.set("Minecraft-профиль подтверждён Microsoft.")
                self.account_value.set(msa_name)
            else:
                self.account_name_var.set("Microsoft не подключён")
                self.account_type_var.set("MICROSOFT // WAITING")
                self.account_note_var.set("Подключи аккаунт через безопасную страницу Microsoft.")
                self.account_value.set("НЕ ПОДКЛЮЧЁН")
        else:
            self.username_entry.configure(state="normal")
            self.login_btn.configure(state="disabled")
            nick = self.username_var.get().strip() or "Player"
            self.account_name_var.set(nick)
            self.account_type_var.set("OFFLINE // LOCAL PROFILE")
            self.account_note_var.set("Локальный профиль без Microsoft.")
            self.account_value.set(nick)
            self._set_skin_placeholder()

    def _set_skin_placeholder(self) -> None:
        self.skin_photo = None
        try:
            self.skin_label.configure(image="", text="NO\nSKIN", fg=C_MUTED)
        except tk.TclError:
            pass

    def _set_skin_image(self, path_value: str) -> None:
        try:
            image = skin_head_rgba(Path(path_value), 104)
            self.skin_photo = ImageTk.PhotoImage(image)
            self.skin_label.configure(image=self.skin_photo, text="", width=104, height=104)
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
        stamp = time.strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{stamp}] {text}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

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
            elif kind == "channel_ui":
                self._update_channel_ui()
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
        dialog.title("Project Meridian // Microsoft")
        dialog.geometry("560x470")
        dialog.resizable(False, False)
        dialog.configure(bg=C_BG)
        dialog.transient(self)

        shell = tk.Frame(dialog, bg=C_PANEL, highlightthickness=1, highlightbackground=C_LINE)
        shell.pack(fill="both", expand=True, padx=18, pady=18)

        top = tk.Frame(shell, bg=C_PANEL)
        top.pack(fill="x", padx=24, pady=(22, 0))
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
            font=("Segoe UI Black", 19),
        ).pack(side="left")

        tk.Label(
            shell,
            text="Это вход по коду устройства. Код из Microsoft Authenticator здесь НЕ нужен.",
            bg=C_PANEL,
            fg=C_MUTED,
            font=("Segoe UI", 10),
            wraplength=470,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(16, 16))

        steps = tk.Frame(shell, bg=C_PANEL_2, highlightthickness=1, highlightbackground=C_LINE)
        steps.pack(fill="x", padx=24)
        for n, text_value in (
            ("01", "Лаунчер получит одноразовый код Microsoft."),
            ("02", "Откроется официальная страница Microsoft."),
            ("03", "Вставь код ниже и подтверди нужный аккаунт."),
            ("04", "Вернись сюда — лаунчер закончит вход автоматически."),
        ):
            row = tk.Frame(steps, bg=C_PANEL_2)
            row.pack(fill="x", padx=12, pady=5)
            tk.Label(row, text=n, bg=C_PANEL_2, fg=C_AMBER, font=("Consolas", 9, "bold"), width=3).pack(side="left")
            tk.Label(row, text=text_value, bg=C_PANEL_2, fg=C_INK, font=("Segoe UI", 9), anchor="w").pack(side="left")

        tk.Label(shell, text="КОД ИЗ ЛАУНЧЕРА", bg=C_PANEL, fg=C_AMBER, font=("Consolas", 9, "bold")).pack(
            anchor="w", padx=24, pady=(18, 5)
        )
        tk.Label(
            shell,
            textvariable=self.auth_code_var,
            bg=C_FIELD,
            fg=C_AMBER_2,
            font=("Consolas", 24, "bold"),
            padx=14,
            pady=10,
            highlightthickness=1,
            highlightbackground=C_LINE,
        ).pack(fill="x", padx=24)

        tk.Label(
            shell,
            textvariable=self.auth_step_var,
            bg=C_PANEL,
            fg=C_MUTED,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="x", padx=24, pady=(8, 0))

        actions = tk.Frame(shell, bg=C_PANEL)
        actions.pack(fill="x", padx=24, pady=(18, 22))
        self.auth_copy_btn = self._button(actions, "СКОПИРОВАТЬ КОД", self._copy_auth_code)
        self.auth_copy_btn.pack(side="left", fill="x", expand=True)
        self.auth_open_btn = self._button(actions, "ОТКРЫТЬ MICROSOFT", self._open_auth_uri, accent=True)
        self.auth_open_btn.pack(side="left", fill="x", expand=True, padx=(10, 0))

        dialog.protocol("WM_DELETE_WINDOW", self._close_auth_dialog)

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
            self._emit("log", f"Код Microsoft: {user_code} (одноразовый код лаунчера)")
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

    def _update_channel_ui(self) -> None:
        channel = self.channel_var.get()
        if channel == "dev":
            name = str(self.state_data.get("dev_armor_name") or "").strip()
            self.pack_value.set(f"DEV // {name}" if name else "DEV // БРОНЯ")
            self.channel_hint.configure(
                text="DEV: кнопка ниже проверит сеть, «Загрузки» и PrismLauncher.",
                fg=C_TELEMETRY,
            )
            self.channel_update_btn.configure(text="↻  ОБНОВИТЬ DEV-БРОНЮ")
        else:
            self.pack_value.set("KoshPack // current")
            self.channel_hint.configure(
                text="STABLE: обычная сборка без тестовых версий брони.",
                fg=C_MUTED,
            )
            self.channel_update_btn.configure(text="↻  ОБНОВИТЬ STABLE")

    def _channel_changed(self) -> None:
        self.state_data["channel"] = self.channel_var.get()
        atomic_write_json(STATE_FILE, self.state_data)
        if self.channel_var.get() == "stable":
            restored = restore_stable_armor()
            if restored:
                self._log("DEV-броня отключена. Стабильная версия восстановлена.")
        self._update_channel_ui()
        self.status_var.set("DEV-канал выбран" if self.channel_var.get() == "dev" else "STABLE-канал выбран")
        self.detail_var.set(
            "Нажми «Обновить сборку», чтобы применить тестовую броню."
            if self.channel_var.get() == "dev"
            else f"Minecraft {MC_VERSION} • NeoForge {NEOFORGE_VERSION}"
        )

    def _ensure_dev_armor(self) -> None:
        if self.channel_var.get() != "dev":
            return

        self._emit("status", "Ищу свежую DEV-броню…")
        self._emit("detail", "Проверяю DEV-канал, «Загрузки» и PrismLauncher.")

        def progress(done: int, total: int) -> None:
            pct = (done / total * 100.0) if total else 0.0
            self._emit("progress", pct)
            if total:
                self._emit("progress_text", f"DEV броня • {format_bytes(done)} / {format_bytes(total)}")

        source: Path | None = None
        source_kind = "DEV-канал"
        remote_version = ""
        try:
            source, remote_version = download_dev_armor_from_manifest(progress)
            self._emit("log", f"DEV-канал: найдена версия {remote_version} ({source.name}).")
        except Exception as e:
            self._emit("log", f"DEV-канал недоступен: {type(e).__name__}: {e}")
            self._emit("detail", "DEV-сеть недоступна • ищу резервный локальный JAR")
            source = find_local_dev_armor()
            source_kind = "локальный резерв"

        if source is None:
            raise RuntimeError(
                "Не удалось получить DEV-броню из сети, и локального резервного JAR тоже нет."
            )

        source_digest = sha256_file(source)
        current_digest = str(self.state_data.get("dev_armor_digest") or "")
        target = INSTANCE_DIR / "mods" / DEV_ARMOR_TARGET
        if current_digest == source_digest and target.is_file() and sha256_file(target) == source_digest:
            label = remote_version or source.name
            self._emit("status", "DEV-броня уже актуальна")
            self._emit("detail", f"{label} • {source_kind}")
            self._emit("pack_value", f"DEV // {label}")
            self._emit("log", f"DEV JAR уже установлен: {label}")
            return

        self._emit("status", "Устанавливаю DEV-броню…")
        installed_name, digest = apply_dev_armor(source)
        display_name = remote_version or source.name
        self.state_data["dev_armor_digest"] = digest
        self.state_data["dev_armor_name"] = display_name
        self.state_data["dev_armor_source"] = source_kind
        atomic_write_json(STATE_FILE, self.state_data)
        self._emit("progress", 100)
        self._emit("status", "DEV-броня установлена")
        self._emit("detail", f"{display_name} • источник: {source_kind}")
        self._emit("pack_value", f"DEV // {display_name}")
        self._emit("log", f"DEV JAR установлен как {installed_name}: {display_name}")

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.play_btn.configure(state="disabled" if busy else "normal")

    def _save_preferences(self) -> None:
        self.state_data["username"] = self.username_var.get().strip() or "Player"
        self.state_data["email"] = self.email_var.get().strip()
        self.state_data["auth_mode"] = self.auth_var.get()
        self.state_data["ram_gb"] = max(4, min(16, int(self.ram_var.get())))
        self.state_data["channel"] = self.channel_var.get()
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
                self._emit("busy", False)

        threading.Thread(target=runner, daemon=True).start()

    def _initial_check(self) -> None:
        self._sync_auth_fields()
        self._update_channel_ui()
        self._start_thread(lambda: self._check_update_only())

    def _check_update_only(self) -> None:
        if self.channel_var.get() == "stable":
            restore_stable_armor()
        self._emit("status", "Проверяю локальный пакет…")
        local_pack = bundled_pack_path()
        if local_pack is not None and not any(INSTANCE_DIR.iterdir()):
            self._emit("status", "Готов к установке")
            self._emit("detail", "KoshPack найден • нажми «Установить и играть»")
            self._emit("play_text", "УСТАНОВИТЬ И ИГРАТЬ")
            self._emit("log", f"Найден локальный пакет сборки: {local_pack}")
            return

        self._emit("status", "Проверяю обновления…")
        try:
            asset = get_release_asset()
        except Exception as e:
            if any(INSTANCE_DIR.iterdir()):
                self._emit("status", "Сборка установлена")
                self._emit("detail", "Автообновление сейчас недоступно • можно играть офлайн")
            else:
                self._emit("status", "Нужна установка сборки")
                self._emit("detail", "GitHub сейчас недоступен • можно установить minecraft.zip вручную")
            self._emit("log", f"Не удалось проверить обновления: {type(e).__name__}: {e}")
            return

        current = self.state_data.get("pack_identity") == asset["identity"] and INSTANCE_DIR.exists()
        if current:
            if self.channel_var.get() == "dev":
                local_dev = find_local_dev_armor()
                self._emit("status", "DEV-канал готов")
                self._emit(
                    "detail",
                    f"Найдено: {local_dev.name}" if local_dev else "Нажми «Обновить сборку» для проверки DEV-брони",
                )
                self._emit("pack_value", f"DEV // {local_dev.name}" if local_dev else "DEV // БРОНЯ")
            else:
                self._emit("status", "Сборка установлена")
                self._emit("detail", f"{asset['release_name']} • {MC_VERSION} • NeoForge")
                self._emit("pack_value", str(asset["release_name"]))
            self._emit("log", "Обновлений базовой сборки не найдено.")
        else:
            self._emit("status", "Доступно обновление")
            self._emit("detail", f"{asset['release_name']} • {asset['updated_at'] or 'новый архив'}")
            self._emit("log", "Есть новая версия minecraft.zip. Нажми «Обновить сборку» или сразу «Играть».")

    def _ensure_pack(self, force: bool = False) -> None:
        local_pack = bundled_pack_path()
        if local_pack is not None:
            local_digest = sha256_file(local_pack)
            local_identity = f"bundled:{local_digest}"
            if not force and self.state_data.get("pack_identity") == local_identity and any(INSTANCE_DIR.iterdir()):
                self._emit("log", "Локальная сборка уже установлена.")
                return
            self._emit("status", "Устанавливаю KoshPack…")
            self._emit("detail", f"{local_pack.name} • локальный пакет")
            self._emit("log", "Использую minecraft.zip рядом с лаунчером.")
            staging = Path(tempfile.mkdtemp(prefix="meridian-bundled-", dir=str(APP_ROOT)))
            try:
                safe_extract(local_pack, staging)
                payload = choose_payload_root(staging)
                managed = install_payload(payload, list(self.state_data.get("managed_files", [])))
            finally:
                shutil.rmtree(staging, ignore_errors=True)
            self.state_data["pack_digest"] = f"sha256:{local_digest}"
            self.state_data["pack_identity"] = local_identity
            self.state_data["managed_files"] = managed
            atomic_write_json(STATE_FILE, self.state_data)
            self._emit("progress", 100)
            self._emit("status", "Сборка установлена")
            self._emit("detail", f"{len(managed)} файлов • дальше Minecraft и NeoForge")
            self._emit("play_text", "ИГРАТЬ")
            self._emit("log", "KoshPack установлен из локального пакета.")
            return

        asset = get_release_asset()
        if not force and self.state_data.get("pack_identity") == asset["identity"] and any(INSTANCE_DIR.iterdir()):
            self._emit("log", "Сборка уже актуальна.")
            return

        cache_zip = cached_pack_path(asset)
        expected = expected_sha256(asset)
        valid_cache = cache_zip.is_file()
        if valid_cache and expected:
            self._emit("log", "Проверяю кэш архива…")
            valid_cache = sha256_file(cache_zip) == expected
            if not valid_cache:
                cache_zip.unlink(missing_ok=True)

        if not valid_cache:
            self._emit("status", "Скачиваю KoshPack…")
            self._emit("detail", f"{asset['size'] / (1024**2):.0f} МБ • публичный канал Project Meridian")
            self._emit("log", f"Скачивание {PACK_ASSET_NAME}…")

            def progress(done: int, total: int) -> None:
                pct = (done / total * 100) if total else 0
                self._emit("progress", pct)
                if total:
                    self._emit("detail", f"{done / (1024**2):.0f} / {total / (1024**2):.0f} МБ")

            download_file(asset["url"], cache_zip, asset["size"], progress)
        else:
            self._emit("log", "Использую уже скачанный проверенный архив.")

        if expected:
            self._emit("status", "Проверяю архив…")
            actual = sha256_file(cache_zip)
            if actual != expected:
                cache_zip.unlink(missing_ok=True)
                raise RuntimeError("SHA-256 архива не совпал. Файл удалён из кэша.")
            self._emit("log", "SHA-256 архива совпадает с GitHub Release.")

        self._emit("status", "Распаковываю сборку…")
        self._emit("progress", 0)
        staging = Path(tempfile.mkdtemp(prefix="meridian-pack-", dir=str(APP_ROOT)))
        try:
            safe_extract(cache_zip, staging)
            payload = choose_payload_root(staging)
            self._emit("log", f"Корень сборки: {payload.name}")
            managed = install_payload(payload, list(self.state_data.get("managed_files", [])))
        finally:
            shutil.rmtree(staging, ignore_errors=True)

        self.state_data["pack_digest"] = asset.get("digest", "")
        self.state_data["pack_identity"] = asset["identity"]
        self.state_data["managed_files"] = managed
        atomic_write_json(STATE_FILE, self.state_data)
        self._emit("progress", 100)
        self._emit("status", "Сборка готова")
        self._emit("detail", f"{asset['release_name']} • {len(managed)} файлов под управлением лаунчера")
        self._emit("play_text", "ИГРАТЬ")
        self._emit("pack_value", str(asset["release_name"]) if self.channel_var.get() == "stable" else "DEV // БРОНЯ")
        self._emit("log", "KoshPack установлен/обновлён.")

    def _install_local_pack(self) -> None:
        selected = filedialog.askopenfilename(
            title="Выбери minecraft.zip",
            filetypes=[("ZIP-архив", "*.zip"), ("Все файлы", "*.*")],
        )
        if not selected:
            return
        zip_path = Path(selected)

        def job() -> None:
            self._emit("status", "Проверяю ZIP…")
            try:
                with zipfile.ZipFile(zip_path) as zf:
                    bad = zf.testzip()
                    if bad:
                        raise RuntimeError(f"Повреждён файл внутри ZIP: {bad}")
            except zipfile.BadZipFile as e:
                raise RuntimeError("Выбранный файл не является исправным ZIP-архивом.") from e

            digest = sha256_file(zip_path)
            self._emit("log", f"Локальный ZIP: {zip_path.name}")
            self._emit("log", f"SHA-256: {digest}")

            self._emit("status", "Устанавливаю локальную сборку…")
            staging = Path(tempfile.mkdtemp(prefix="meridian-local-", dir=str(APP_ROOT)))
            try:
                safe_extract(zip_path, staging)
                payload = choose_payload_root(staging)
                managed = install_payload(payload, list(self.state_data.get("managed_files", [])))
            finally:
                shutil.rmtree(staging, ignore_errors=True)

            self.state_data["pack_digest"] = f"sha256:{digest}"
            self.state_data["pack_identity"] = f"local:{digest}"
            self.state_data["managed_files"] = managed
            atomic_write_json(STATE_FILE, self.state_data)
            self._emit("progress", 100)
            self._emit("status", "Сборка установлена")
            self._emit("detail", f"Локальный ZIP • {len(managed)} файлов • Minecraft {MC_VERSION}")
            self._emit("play_text", "ИГРАТЬ")
            self._emit("log", "Локальная сборка установлена. Теперь можно нажимать «Играть».")

        self._start_thread(job)

    def _update_pack(self) -> None:
        def job() -> None:
            if self.channel_var.get() == "stable":
                restore_stable_armor()
                self._ensure_pack(force=False)
            else:
                self._ensure_pack(force=False)
                self._ensure_dev_armor()
        self._start_thread(job)

    def _repair_pack(self) -> None:
        def job() -> None:
            restore_stable_armor()
            self._ensure_pack(force=True)
            if self.channel_var.get() == "dev":
                self._ensure_dev_armor()
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
            if not username:
                messagebox.showwarning(APP_NAME, "Укажи игровой ник.")
                return
        else:
            pass

        def job() -> None:
            try:
                if self.channel_var.get() == "stable":
                    restore_stable_armor()
                    self._ensure_pack(force=False)
                else:
                    self._ensure_pack(force=False)
                    self._ensure_dev_armor()
            except Exception as e:
                if any(INSTANCE_DIR.iterdir()):
                    self._emit("log", f"Автообновление недоступно, запускаю установленную сборку: {type(e).__name__}: {e}")
                else:
                    raise
            self._emit("status", "Готовлю Minecraft…")
            channel_label = "DEV / БРОНЯ" if self.channel_var.get() == "dev" else "STABLE"
            self._emit("detail", f"{channel_label} • {MC_VERSION} • NeoForge {NEOFORGE_VERSION} • RAM {self.ram_var.get()} ГБ")
            self._emit("log", "PortableMC проверит Minecraft, библиотеки, NeoForge и Java.")

            ram = max(4, min(16, int(self.ram_var.get())))
            jvm_args = f"-Xms2G,-Xmx{ram}G,-XX:+UseG1GC,-XX:MaxGCPauseMillis=100"
            args = [
                "--main-dir", str(INSTANCE_DIR),
                "--output", "machine",
                "start",
                f"--jvm-arg={jvm_args}",
            ]
            if SERVER_HOST:
                args += ["--join-server", SERVER_HOST, "--join-server-port", str(SERVER_PORT)]
            if self.auth_var.get() == "microsoft":
                msa_uuid = str(self.state_data.get("msa_uuid") or "").strip()
                msa_username = str(self.state_data.get("msa_username") or "").strip()
                if msa_uuid:
                    args += ["--auth", "--uuid", msa_uuid]
                elif msa_username:
                    args += ["--auth", "--username", msa_username]
                else:
                    raise RuntimeError("Сначала нажми «Войти через Microsoft» и заверши вход в браузере.")
            else:
                args += ["--username", self.username_var.get().strip()]
            args += [LAUNCH_SPEC]

            self._emit("status", "Готовлю Minecraft…")
            self._emit("progress", 0)
            self._emit("progress_indeterminate", True)
            self._emit("progress_text", "Проверяю Minecraft, NeoForge, Java и библиотеки…")
            code = run_pmc(args, LAUNCH_LOG, on_event=self._handle_pmc_event)
            if code != 0:
                raise RuntimeError(f"Minecraft/PortableMC завершился с кодом {code}. Открой «Логи».")
            self._emit("status", "Minecraft закрыт")
            self._emit("detail", "Можно запускать снова")
            self._emit("log", "Игровой процесс завершён.")

        self._start_thread(job)

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
    hide_console_if_needed()
    ensure_dirs()
    app = MeridianLauncher()
    if "--smoke-ui" in sys.argv:
        app.update_idletasks()
        app.destroy()
        return
    app.mainloop()


if __name__ == "__main__":
    main()
