"""Functional tests of the public launcher's update, repair, migration and skin code.

Runs against a sandbox: LOCALAPPDATA points to a temporary folder before the launcher module is imported, so the
installed launcher of the user is never touched. A local HTTP server provides packs (with HTTP Range support,
optional connection drops) and redirect endpoints.

    python launcher/tests/test_public_launcher.py [--real-pack PATH_TO_CLIENT_ZIP]
"""
from __future__ import annotations

import hashlib
import http.server
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from pathlib import Path

SANDBOX = Path(tempfile.mkdtemp(prefix="meridian-launcher-test-"))
os.environ["LOCALAPPDATA"] = str(SANDBOX / "localappdata")
SOURCE = Path(__file__).resolve().parents[1] / "source" / "launcher.py"
spec = importlib.util.spec_from_file_location("launcher", SOURCE)
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)  # type: ignore[union-attr]
assert str(L.APP_ROOT).startswith(str(SANDBOX)), L.APP_ROOT

RESULTS: list[tuple[str, str, str]] = []
SERVE = SANDBOX / "www"
SERVE.mkdir()
DROP_AFTER: dict[str, int] = {}


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):  # quiet
        pass

    def do_GET(self):
        if self.path.startswith("/redirect?to="):
            self.send_response(302)
            self.send_header("Location", self.path.split("=", 1)[1])
            self.end_headers()
            return
        path = SERVE / self.path.lstrip("/")
        if not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        start = 0
        rng = self.headers.get("Range")
        if rng and rng.startswith("bytes="):
            start = int(rng[6:].split("-")[0])
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{len(data) - 1}/{len(data)}")
        else:
            self.send_response(200)
        body = data[start:]
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        drop = DROP_AFTER.pop(self.path, None)
        if drop is not None:
            self.wfile.write(body[:drop])
            self.wfile.flush()
            self.connection.shutdown(2)
            return
        self.wfile.write(body)


server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{server.server_port}"


def check(name: str, cond: bool, detail: str = "") -> None:
    RESULTS.append((name, "PASS" if cond else "FAIL", detail))
    print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail else ""))


def make_pack(name: str, files: dict[str, bytes]) -> tuple[Path, dict]:
    path = SERVE / name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel, data in files.items():
            zf.writestr(rel, data)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    asset = {"url": f"{BASE}/{name}", "size": path.stat().st_size, "digest": f"sha256:{sha}",
             "identity": f"{name}:{sha}", "updated_at": name, "release_name": name,
             "launcher_version": "", "launcher_min": ""}
    return path, asset


class FakeApp:
    """Runs the launcher's pack methods without a window."""
    def __init__(self):
        self.state_data = L.load_state()
        self.events: list[tuple[str, object]] = []
        self.asset = None

    def _emit(self, kind, value=None):
        self.events.append((kind, value))

    def _start_thread(self, target):
        target()

    def logs(self):
        return [str(v) for k, v in self.events if k == "log"]


for name in ("_check_update_only", "_install_zip", "_rollback", "_prune_pack_cache", "_obtain_verified_zip", "_check_launcher_version",
             "_pack_installed", "_ensure_pack", "_repair_pack"):
    setattr(FakeApp, name, L.MeridianLauncher.__dict__[name])


def snapshot() -> dict[str, str]:
    out = {}
    for p in L.INSTANCE_DIR.rglob("*"):
        if p.is_file():
            out[p.relative_to(L.INSTANCE_DIR).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def use_asset(app: FakeApp, asset: dict) -> None:
    L.get_release_asset = lambda: dict(asset)  # the manifest parser itself is tested separately


V1 = {"mods/a.jar": b"A1" * 5000, "mods/b.jar": b"B1" * 5000, "config/x.toml": b"x=1\n", "kubejs/s.js": b"//1\n",
      "options.txt": b"pack-default-options\n"}
V2 = {"mods/a.jar": b"A2" * 5000, "mods/c.jar": b"C2" * 5000, "config/x.toml": b"x=2\n", "kubejs/s.js": b"//2\n",
      "options.txt": b"pack-default-options-v2\n"}


def test_manifest_parser():
    good = {"packVersion": "stable-r2h", "launcherMinVersion": "1.0.0",
            "package": {"url": "https://example.invalid/p.zip", "sha256": "a" * 64, "size": 5},
            "launcher": {"version": "1.0.1"}}
    spec2 = importlib.util.spec_from_file_location("launcher_parse", SOURCE)
    M = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(M)
    M.request_json = lambda url, **kw: good
    a = M.get_release_asset()
    check("manifest: Stable r2h parsed", a["release_name"] == "Stable r2h" and a["launcher_min"] == "1.0.0", str(a["release_name"]))
    M.request_json = lambda url, **kw: {**good, "package": {**good["package"], "url": "http://example.invalid/p.zip"}}
    try:
        M.get_release_asset(); ok = False
    except RuntimeError:
        ok = True
    check("manifest: non-HTTPS pack URL rejected", ok)
    M.request_json = lambda url, **kw: {**good, "package": {**good["package"], "sha256": "xyz"}}
    try:
        M.get_release_asset(); ok = False
    except RuntimeError:
        ok = True
    check("manifest: invalid SHA-256 rejected", ok)
    check("launcher URL: only the Stable manifest", "dev" not in L.UPDATE_MANIFEST_URL.lower()
          and not any(n.startswith("DEV_") for n in dir(L)))


def test_versions_and_identity():
    check("version: 0.2.21-dev5 < 1.0.0", L.version_tuple("0.2.21-dev5") < L.version_tuple("1.0.0"))
    check("version: 1.0 == 1.0.0", L.version_tuple("1.0") == L.version_tuple("1.0.0"))
    check("version: 1.0.1 > 1.0.0", L.version_tuple("1.0.1") > L.version_tuple("1.0.0"))
    check("offline UUID = Java nameUUIDFromBytes", L.offline_uuid("Notch") == "b50ad385-829d-3141-a216-7e7d7539ba7f",
          L.offline_uuid("Notch"))
    masked = L.mask_secrets("accessToken=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijklmn x --accessToken 123abc")
    check("log masking: tokens removed", "eyJ" not in masked and "123abc" not in masked, masked)
    app = FakeApp()
    try:
        app._check_launcher_version({"launcher_version": "1.0.1", "launcher_min": "1.0.0"})
        update_notice = any(k == "launcher_update" for k, _ in app.events)
        ok = True
    except RuntimeError:
        ok = update_notice = False
    check("launcher update notice when newer version exists", ok and update_notice)
    try:
        app._check_launcher_version({"launcher_version": "2.0.0", "launcher_min": "2.0.0"})
        blocked = False
    except RuntimeError:
        blocked = True
    check("launcher below launcherMinVersion is refused", blocked)


def test_install_update_repair():
    p1, a1 = make_pack("pack-v1.zip", V1)
    p2, a2 = make_pack("pack-v2.zip", V2)
    app = FakeApp()
    use_asset(app, a1)
    app._ensure_pack()
    snap = snapshot()
    check("clean install: all files", all(snap.get(k) == hashlib.sha256(v).hexdigest() for k, v in V1.items()))
    check("clean install: file index written", len(L.load_file_index()) == 4)
    # user data appears after first start
    (L.INSTANCE_DIR / "saves" / "World").mkdir(parents=True)
    (L.INSTANCE_DIR / "saves" / "World" / "level.dat").write_bytes(b"world")
    (L.INSTANCE_DIR / "options.txt").write_bytes(b"user-options\n")
    (L.INSTANCE_DIR / "servers.dat").write_bytes(b"user-servers")
    (L.INSTANCE_DIR / "screenshots").mkdir()
    (L.INSTANCE_DIR / "screenshots" / "s.png").write_bytes(b"png")
    (L.INSTANCE_DIR / "mods" / "user-extra.jar").write_bytes(b"user mod")
    requests_before = len([e for e in app.events if e[0] == "status" and "Скачиваю" in str(e[1])])
    app._ensure_pack()
    requests_after = len([e for e in app.events if e[0] == "status" and "Скачиваю" in str(e[1])])
    check("up to date: no download on next start", requests_before == requests_after)
    # update to v2
    use_asset(app, a2)
    app._ensure_pack()
    snap = snapshot()
    check("update: changed files replaced", snap["mods/a.jar"] == hashlib.sha256(V2["mods/a.jar"]).hexdigest())
    check("update: removed pack file deleted", "mods/b.jar" not in snap)
    check("update: new file added", "mods/c.jar" in snap)
    check("update: saves/options/servers/screenshots kept",
          (L.INSTANCE_DIR / "saves/World/level.dat").read_bytes() == b"world"
          and (L.INSTANCE_DIR / "options.txt").read_bytes() == b"user-options\n"
          and (L.INSTANCE_DIR / "servers.dat").read_bytes() == b"user-servers"
          and (L.INSTANCE_DIR / "screenshots/s.png").exists())
    check("update: unknown user mod not deleted", (L.INSTANCE_DIR / "mods/user-extra.jar").exists())
    cached = sorted(p.name for p in L.CACHE_DIR.glob("minecraft-*.zip"))
    check("cache: current + previous archive kept for rollback", len(cached) == 2, str(cached))
    # repair: corrupt one file, delete another
    (L.INSTANCE_DIR / "mods/a.jar").write_bytes(b"broken")
    (L.INSTANCE_DIR / "kubejs/s.js").unlink()
    before = snapshot()
    app.events.clear()
    app._repair_pack()
    after = snapshot()
    check("repair: corrupted + missing restored", after["mods/a.jar"] == hashlib.sha256(V2["mods/a.jar"]).hexdigest()
          and after.get("kubejs/s.js") == hashlib.sha256(V2["kubejs/s.js"]).hexdigest())
    untouched = {k for k in before if k not in ("mods/a.jar",)}
    check("repair: other files untouched", all(after[k] == before[k] for k in untouched))
    check("repair: unknown mod reported, kept", any("user-extra.jar" in l for l in app.logs())
          and (L.INSTANCE_DIR / "mods/user-extra.jar").exists())
    app.events.clear()
    app._repair_pack()
    check("repair: clean state reports OK", any(k == "status" and v == "Файлы в порядке" for k, v in app.events))
    return app, a1, a2


def test_disk_full_and_rollback(app, a1, a2):
    # back on v1, then a v3 update fails half-way (simulated disk full while writing)
    use_asset(app, a1)
    app._ensure_pack()
    good_v1 = snapshot()
    p3, a3 = make_pack("pack-v3.zip", {**V2, "mods/d.jar": b"D3" * 5000, "mods/e.jar": b"E3" * 5000})
    use_asset(app, a3)
    real = L._write_member
    count = {"n": 0}

    def failing(zf, info, dst):
        count["n"] += 1
        if count["n"] == 3:
            raise OSError(28, "No space left on device")
        return real(zf, info, dst)

    L._write_member = failing
    try:
        app._ensure_pack()
        failed = False
    except RuntimeError as e:
        failed = "Прежняя версия восстановлена" in str(e)
    finally:
        L._write_member = real
    check("disk full mid-update: error reported, previous version restored", failed)
    check("disk full mid-update: instance equals previous version", snapshot() == good_v1)
    check("disk full mid-update: state still previous version", app.state_data["pack_identity"] == a1["identity"])
    check("disk full mid-update: journal cleared after rollback", not L.INSTALL_JOURNAL.exists())
    # not enough space before starting: nothing touched
    real_usage = shutil.disk_usage
    L.shutil.disk_usage = lambda p: type(real_usage(p))(10**9, 10**9 - 1000, 1000)
    try:
        app._ensure_pack()
        refused = False
    except RuntimeError as e:
        refused = "Недостаточно места" in str(e)
    finally:
        L.shutil.disk_usage = real_usage
    check("low disk space: refused before any change", refused and snapshot() == good_v1)


def test_interrupted_download(app):
    p4, a4 = make_pack("pack-v4.zip", {**V1, "mods/big.jar": os.urandom(400_000)})
    use_asset(app, a4)
    DROP_AFTER["/pack-v4.zip"] = 150_000
    real_sleep = time.sleep
    L.time.sleep = lambda s: None  # no back-off pauses between retries
    app.events.clear()
    try:
        app._ensure_pack()
    finally:
        L.time.sleep = real_sleep
    check("interrupted download: resumed via HTTP Range and verified", app.state_data["pack_identity"] == a4["identity"]
          and snapshot()["mods/big.jar"] == hashlib.sha256(zipfile.ZipFile(p4).read("mods/big.jar")).hexdigest())
    # corrupted download: server delivers different bytes than the manifest says
    p5, a5 = make_pack("pack-v5.zip", V2)
    bad = dict(a5, digest="sha256:" + "0" * 64, identity="bad:" + "0" * 64)
    use_asset(app, bad)
    try:
        app._ensure_pack(); ok = False
    except RuntimeError as e:
        ok = "SHA-256" in str(e)
    check("corrupted download: rejected and deleted, instance unchanged", ok
          and not any(p.name.startswith("minecraft-0000") for p in L.CACHE_DIR.iterdir())
          and app.state_data["pack_identity"] == a4["identity"])


def test_power_loss(app):
    """Kills a separate process in the middle of an install; the next start must finish it."""
    p6, a6 = make_pack("pack-v6.zip", {**V2, **{f"kubejs/f{i}.js": os.urandom(20_000) for i in range(400)}})
    script = SANDBOX / "kill_me.py"
    script.write_text(
        "import os, sys, importlib.util, time\n"
        f"os.environ['LOCALAPPDATA']={str(L.APP_ROOT.parent)!r}\n"
        f"spec=importlib.util.spec_from_file_location('launcher', {str(SOURCE)!r})\n"
        "L=importlib.util.module_from_spec(spec); spec.loader.exec_module(L)\n"
        "real=L._write_member\n"
        "def slow(zf,info,dst):\n    time.sleep(0.01); return real(zf,info,dst)\n"
        "L._write_member=slow\n"
        f"import json; asset=json.loads({json.dumps(json.dumps(a6))})\n"
        "L.atomic_write_json(L.INSTALL_JOURNAL, {'target': asset['identity']})\n"
        f"L.install_from_zip(L.Path({str(p6)!r}), [])\n", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, str(script)], stderr=subprocess.PIPE, text=True)
    for _ in range(100):  # kill once it is writing files, as a power cut would
        time.sleep(0.1)
        if proc.poll() is not None or len(list(L.INSTANCE_DIR.rglob("f*.js"))) > 20:
            break
    early_exit = proc.poll()
    proc.kill()
    _, err = proc.communicate()
    print("power-loss probe:", "early exit" if early_exit is not None else "killed", early_exit,
          "files:", len(list(L.INSTANCE_DIR.rglob("f*.js"))), "journal:", L.INSTALL_JOURNAL, L.INSTALL_JOURNAL.exists(),
          "stderr:", err[-600:])
    leftovers = [p for p in L.INSTANCE_DIR.rglob("*.meridian-new")]
    check("power loss: journal left behind", L.INSTALL_JOURNAL.exists())
    use_asset(app, a6)
    app._ensure_pack()
    snap = snapshot()
    with zipfile.ZipFile(p6) as zf:
        expected = {n: hashlib.sha256(zf.read(n)).hexdigest() for n in zf.namelist() if n != "options.txt"}
    check("power loss: next start completes the install", all(snap.get(k) == v for k, v in expected.items())
          and not L.INSTALL_JOURNAL.exists(), f"temp files seen after kill: {len(leftovers)}")
    check("power loss: no temporary files remain", not list(L.INSTANCE_DIR.rglob("*.meridian-new")))


def test_offline(app):
    """No internet: an installed pack stays playable; a first start explains what is missing."""
    import urllib.error

    def no_network():
        raise urllib.error.URLError("no network")

    L.get_release_asset = no_network
    app.events.clear()
    app._check_update_only()
    status = [v for k, v in app.events if k == "status"]
    detail = [v for k, v in app.events if k == "detail"]
    check("no internet, pack installed: stays playable", status[-1:] == ["Сборка установлена"]
          and "можно играть" in str(detail[-1:]), f"{status[-1:]} {detail[-1:]}")
    fresh = FakeApp()
    fresh.state_data["pack_identity"] = ""
    fresh._check_update_only()
    status = [v for k, v in fresh.events if k == "status"]
    check("no internet, first start: clear message, no crash", status[-1:] == ["Нужна установка сборки"], str(status[-1:]))


def test_legacy_dev_migration():
    app = FakeApp()
    mods = L.INSTANCE_DIR / "mods"
    (mods / L.LEGACY_DEV_ARMOR_JAR).write_bytes(b"dev armor")
    (mods / "koshpack_armor_stable.jar.meridian-stable-bak").write_bytes(b"bak")
    (L.INSTANCE_DIR / "kubejs" / "server_scripts").mkdir(parents=True, exist_ok=True)
    (L.INSTANCE_DIR / "kubejs/server_scripts/dev_recipes.js").write_bytes(b"dev")
    L.atomic_write_json(L.LEGACY_DEV_TRACK_FILE, {"paths": ["kubejs/server_scripts/dev_recipes.js", "../../evil.txt"]})
    L.LEGACY_DEV_BACKUP_DIR.mkdir(exist_ok=True)
    (SANDBOX / "evil.txt").write_text("must survive")
    app.state_data["channel"] = "dev"
    check("migration: DEV state detected", L.legacy_dev_state_present(app.state_data))
    p7, a7 = make_pack("pack-v7.zip", V1)
    use_asset(app, a7)
    app._ensure_pack()
    check("migration: DEV armor + backups + tracked DEV scripts removed",
          not (mods / L.LEGACY_DEV_ARMOR_JAR).exists() and not list(mods.glob("*.meridian-stable-bak"))
          and not (L.INSTANCE_DIR / "kubejs/server_scripts/dev_recipes.js").exists())
    check("migration: path traversal in old tracking file ignored", (SANDBOX / "evil.txt").exists())
    check("migration: DEV bookkeeping cleared, channel dropped", not L.LEGACY_DEV_TRACK_FILE.exists()
          and not L.LEGACY_DEV_BACKUP_DIR.exists() and "channel" not in app.state_data)


def test_zip_safety():
    evil = SANDBOX / "evil.zip"
    with zipfile.ZipFile(evil, "w") as zf:
        zf.writestr("../outside.txt", b"x")
    for name in ("../outside.txt", "C:/Windows/x.dll", "/abs.txt", "mods/../../x", "mods/con. "):
        try:
            L.safe_rel_path(name); ok = False
        except RuntimeError:
            ok = True
        check(f"zip: unsafe path rejected ({name!r})", ok)
    try:
        L.install_from_zip(evil, []); ok = False
    except RuntimeError:
        ok = True
    check("zip: archive with traversal refused, nothing written outside", ok and not (L.APP_ROOT / "outside.txt").exists())


def test_skins():
    from PIL import Image
    def png(w, h, slim=False, mode="RGBA"):
        img = Image.new(mode, (w, h), (200, 80, 40, 255) if mode == "RGBA" else (200, 80, 40))
        if slim and mode == "RGBA":
            for y in range(20, 32):
                for x in (54, 55):
                    img.putpixel((x, y), (0, 0, 0, 0))
        b = io.BytesIO(); img.save(b, "PNG"); return b.getvalue()
    f = L.validate_skin_png(png(64, 64))
    check("skin: 64x64 accepted, Steve", f["width"] == 64 and not f["slim"])
    check("skin: Alex detected", L.validate_skin_png(png(64, 64, slim=True))["slim"])
    check("skin: legacy 64x32 accepted", L.validate_skin_png(png(64, 32))["height"] == 32)
    for label, data in (("wrong size 128x128", png(128, 128)), ("JPEG", b"\xff\xd8\xff" + b"0" * 100),
                        ("truncated PNG", png(64, 64)[:60]), ("oversize", b"\x89PNG\r\n\x1a\n" + b"0" * 300_000),
                        ("PNG bomb header 30000x30000", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + (30000).to_bytes(4, "big") * 2 + b"\x08\x06\x00\x00\x00" + b"0" * 50)):
        try:
            L.validate_skin_png(data); ok = False
        except ValueError:
            ok = True
        check(f"skin: rejected {label}", ok)
    check("skin: allowlist", L.skin_host_allowed("https://textures.minecraft.net/texture/x")
          and L.skin_host_allowed("http://auth.tlauncher.org/skin/a.png") and L.skin_host_allowed("https://ely.by/storage/a.png")
          and not L.skin_host_allowed("http://127.0.0.1/x.png") and not L.skin_host_allowed("file:///C:/x.png")
          and not L.skin_host_allowed("https://evil.com/ely.by") and not L.skin_host_allowed("https://notely.by/x")
          and not L.skin_host_allowed("https://user:pw@ely.by/x") and not L.skin_host_allowed("https://ely.by:8443/x"))
    try:
        L.fetch_limited(f"{BASE}/redirect?to=http://127.0.0.1/x"); ok = False
    except RuntimeError:
        ok = True
    check("skin: local/non-allowlisted URL refused (no SSRF)", ok)
    check("skin: command format", L.skin_command("elyby", "https://textures.minecraft.net/texture/ab12", True)
          == '/skin set web slim "https://textures.minecraft.net/texture/ab12"' and L.skin_command("official") == "/skin reset"
          and L.skin_command("default") == "/skin clear")
    try:
        L.skin_command("elyby", "https://ely.by/storage/skins/a.png"); ok = False
    except ValueError:
        ok = True
    check("skin: unsigned Ely.by URL not used in server command", ok)
    try:
        L.skin_command("file", "http://127.0.0.1/a.png"); ok = False
    except ValueError:
        ok = True
    check("skin: command refuses non-allowlisted URL", ok)
    for nick in ("bad nick", "a", "x" * 17, "../etc"):
        try:
            L.resolve_external_skin("elyby", nick); ok = False
        except ValueError:
            ok = True
        check(f"skin: invalid nick refused ({nick!r})", ok)


def test_skins_online():
    """Public, read-only requests to Ely.by and TLauncher (no sign-in)."""
    for source, nick in (("elyby", "ErickSkrauch"), ("tlauncher", "Notch")):
        try:
            data, url = L.resolve_external_skin(source, nick)
            facts = L.validate_skin_png(data)
            check(f"skin online: {source} '{nick}' downloaded and valid", L.skin_host_allowed(url),
                  f"{url} {facts['width']}x{facts['height']}")
        except Exception as e:
            RESULTS.append((f"skin online: {source} '{nick}'", "NOT RUN", f"{type(e).__name__}: {e}"))
            print("NOT RUN", source, e)


def test_real_pack(path: Path):
    shutil.rmtree(L.INSTANCE_DIR, ignore_errors=True)
    L.INSTANCE_DIR.mkdir(parents=True)
    t = time.time()
    managed, index = L.install_from_zip(path, [])
    took = time.time() - t
    with zipfile.ZipFile(path) as zf:
        n = len([i for i in zf.infolist() if not i.is_dir()])
        jars = len([i for i in zf.infolist() if i.filename.startswith("mods/") and i.filename.endswith(".jar")])
    installed = len(list((L.INSTANCE_DIR / "mods").glob("*.jar")))
    check(f"pack ZIP {path.name}: installs completely", len(managed) == n and installed == jars,
          f"{len(managed)} files, {installed} mods, {took:.0f} s")
    t = time.time()
    broken = L.verify_installed_files(index)
    check(f"pack ZIP {path.name}: verification clean", not broken, f"{time.time() - t:.0f} s for {len(index)} files")


def main():
    real = None
    if "--real-pack" in sys.argv:
        real = Path(sys.argv[sys.argv.index("--real-pack") + 1])
    L.ensure_dirs()
    test_manifest_parser()
    test_versions_and_identity()
    app, a1, a2 = test_install_update_repair()
    test_disk_full_and_rollback(app, a1, a2)
    test_interrupted_download(app)
    test_power_loss(app)
    test_offline(app)
    test_legacy_dev_migration()
    test_zip_safety()
    test_skins()
    test_skins_online()
    if real:
        test_real_pack(real)
    out = Path(os.environ.get("MERIDIAN_TEST_REPORT", SANDBOX / "results.json"))
    out.write_text(json.dumps([{"test": a, "result": b, "detail": c} for a, b, c in RESULTS], ensure_ascii=False, indent=1),
                   encoding="utf-8")
    fails = [r for r in RESULTS if r[1] == "FAIL"]
    print(f"\n{len(RESULTS)} checks, {len(fails)} failed. Report: {out}")
    server.shutdown()
    shutil.rmtree(SANDBOX, ignore_errors=True)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
