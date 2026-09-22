#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import struct
import zipfile
from pathlib import Path

VERSION = "alpha55-all17-pilot"
NOTE = (
    "alpha55: all 17 profession armor families are present in the DEV JAR; "
    "Pilot I-IV added on top of alpha54 without rolling back existing Diver/Hunter/Artillery work"
)

ROOT = Path(__file__).resolve().parents[2]
B64_PATH = ROOT / "launcher/dev/current.jar.b64"
OUT_DIR = ROOT / "dist"
OUT_JAR = OUT_DIR / "KoshPack_Armor_DEV.jar"
MANIFEST = ROOT / "launcher/dev-manifest.json"

REPL_BYTES = (
    (b"koshpackdiverhelmet", b"koshpackpilothelmet"),
    (b"DIVER", b"PILOT"),
    (b"Diver", b"Pilot"),
    (b"diver", b"pilot"),
)

CLASS_MAP = {
    "ru/koshpack/forgebridge/diverhelmet/DiverArmorItem.class":
        "ru/koshpack/forgebridge/pilothelmet/PilotArmorItem.class",
    "ru/koshpack/forgebridge/diverhelmet/DiverHelmetAddon.class":
        "ru/koshpack/forgebridge/pilothelmet/PilotHelmetAddon.class",
    "ru/koshpack/forgebridge/armor/client/DiverArmorModel.class":
        "ru/koshpack/forgebridge/armor/client/PilotArmorModel.class",
    "ru/koshpack/forgebridge/armor/client/DiverHelmetClient$1.class":
        "ru/koshpack/forgebridge/armor/client/PilotHelmetClient$1.class",
    "ru/koshpack/forgebridge/armor/client/DiverHelmetClient.class":
        "ru/koshpack/forgebridge/armor/client/PilotHelmetClient.class",
    "ru/koshpack/forgebridge/armor/client/DiverModelGeometry.class":
        "ru/koshpack/forgebridge/armor/client/PilotModelGeometry.class",
}


def patch_utf8(raw: bytes) -> bytes:
    for old, new in REPL_BYTES:
        raw = raw.replace(old, new)
    return raw


def patch_class(data: bytes) -> bytes:
    if data[:4] != b"\xca\xfe\xba\xbe":
        raise ValueError("Not a Java class file")
    cp_count = struct.unpack(">H", data[8:10])[0]
    out = bytearray(data[:10])
    pos = 10
    index = 1
    while index < cp_count:
        tag = data[pos]
        out.append(tag)
        pos += 1
        if tag == 1:
            length = struct.unpack(">H", data[pos:pos+2])[0]
            raw = data[pos+2:pos+2+length]
            patched = patch_utf8(raw)
            out += struct.pack(">H", len(patched)) + patched
            pos += 2 + length
        elif tag in (3, 4):
            out += data[pos:pos+4]; pos += 4
        elif tag in (5, 6):
            out += data[pos:pos+8]; pos += 8; index += 1
        elif tag in (7, 8, 16, 19, 20):
            out += data[pos:pos+2]; pos += 2
        elif tag in (9, 10, 11, 12, 17, 18):
            out += data[pos:pos+4]; pos += 4
        elif tag == 15:
            out += data[pos:pos+3]; pos += 3
        else:
            raise ValueError(f"Unsupported constant-pool tag {tag} at index {index}")
        index += 1
    out += data[pos:]
    return bytes(out)


def parse_cp(data: bytes):
    count = struct.unpack(">H", data[8:10])[0]
    entries = [None] * count
    pos = 10
    idx = 1
    while idx < count:
        start = pos
        tag = data[pos]; pos += 1
        value = None
        if tag == 1:
            ln = struct.unpack(">H", data[pos:pos+2])[0]
            raw = data[pos+2:pos+2+ln]
            pos += 2 + ln
            try:
                value = raw.decode("utf-8")
            except UnicodeDecodeError:
                value = None
        elif tag in (3, 4):
            pos += 4
        elif tag in (5, 6):
            pos += 8
            entries[idx] = (tag, value, data[start:pos])
            idx += 1
        elif tag in (7, 8, 16, 19, 20):
            value = struct.unpack(">H", data[pos:pos+2])[0]; pos += 2
        elif tag in (9, 10, 11, 12, 17, 18):
            value = struct.unpack(">HH", data[pos:pos+4]); pos += 4
        elif tag == 15:
            value = (data[pos], struct.unpack(">H", data[pos+1:pos+3])[0]); pos += 3
        else:
            raise ValueError(f"Unsupported constant-pool tag {tag}")
        entries[idx] = (tag, value, data[start:pos])
        idx += 1
    return count, entries, pos


def u2(buf: bytes, p: int) -> int:
    return struct.unpack(">H", buf[p:p+2])[0]


def u4(buf: bytes, p: int) -> int:
    return struct.unpack(">I", buf[p:p+4])[0]


def patch_bootstrap(data: bytes, internal_name: str) -> bytes:
    count, cp, cp_end = parse_cp(data)
    utf8 = {e[1]: i for i, e in enumerate(cp) if e and e[0] == 1}

    # Idempotence guard.
    if internal_name in utf8:
        return data

    init_utf = utf8["<init>"]
    bus_desc = "(Lnet/neoforged/bus/api/IEventBus;)V"
    desc_utf = utf8[bus_desc]
    code_utf = utf8["Code"]

    nt_idx = next(
        (i for i, e in enumerate(cp) if e and e[0] == 12 and e[1] == (init_utf, desc_utf)),
        None,
    )
    if nt_idx is None:
        raise ValueError("IEventBus constructor NameAndType not found")

    raw = internal_name.encode("utf-8")
    utf_idx, cls_idx, ctor_idx = count, count + 1, count + 2
    extra = (
        bytes([1]) + struct.pack(">H", len(raw)) + raw
        + bytes([7]) + struct.pack(">H", utf_idx)
        + bytes([10]) + struct.pack(">HH", cls_idx, nt_idx)
    )

    rest = bytearray(data[cp_end:])
    p = 6
    interfaces = u2(rest, p); p += 2 + interfaces * 2
    fields = u2(rest, p); p += 2
    for _ in range(fields):
        p += 6
        ac = u2(rest, p); p += 2
        for _ in range(ac):
            ln = u4(rest, p + 2); p += 6 + ln

    methods_count_pos = p
    methods = u2(rest, p); p += 2
    method_chunks = []
    patched = False

    for _ in range(methods):
        access, name_idx, desc_idx, ac = struct.unpack(">HHHH", rest[p:p+8])
        p += 8
        attrs = []
        target = cp[name_idx][1] == "<init>" and cp[desc_idx][1] == bus_desc
        for _ in range(ac):
            an = u2(rest, p)
            ln = u4(rest, p + 2)
            info = bytes(rest[p+6:p+6+ln])
            p += 6 + ln

            if target and an == code_utf:
                max_stack = u2(info, 0)
                max_locals = u2(info, 2)
                code_len = u4(info, 4)
                code = info[8:8+code_len]
                tail = info[8+code_len:]
                if not code or code[-1] != 0xB1:
                    raise ValueError("Constructor does not end with return")
                inject = (
                    bytes([0xBB]) + struct.pack(">H", cls_idx)
                    + bytes([0x59, 0x2B, 0xB7]) + struct.pack(">H", ctor_idx)
                    + bytes([0x57])
                )
                code = code[:-1] + inject + code[-1:]
                info = struct.pack(">HHI", max(max_stack, 3), max_locals, len(code)) + code + tail
                ln = len(info)
                patched = True

            attrs.append(struct.pack(">HI", an, ln) + info)

        method_chunks.append(
            struct.pack(">HHHH", access, name_idx, desc_idx, ac) + b"".join(attrs)
        )

    if not patched:
        raise ValueError("KoshPackArmorMod constructor was not patched")

    return (
        data[:8] + struct.pack(">H", count + 3) + data[10:cp_end] + extra
        + bytes(rest[:methods_count_pos]) + struct.pack(">H", methods)
        + b"".join(method_chunks) + bytes(rest[p:])
    )


def patch_text(data: bytes) -> bytes:
    text = data.decode("utf-8")
    text = text.replace("koshpackdiverhelmet", "koshpackpilothelmet")
    text = text.replace("DIVER", "PILOT")
    text = text.replace("Diver", "Pilot").replace("diver", "pilot")
    text = text.replace("Водолаз", "Пилот").replace("водолаз", "пилот")
    text = text.replace('"dark_aqua"', '"blue"')
    return text.encode("utf-8")


def move_function_row(text: str, z: int) -> str:
    pattern = re.compile(r"^(summon minecraft:armor_stand ~[+-]?\d+ ~[+-]?\d+ )~[+-]?\d+", re.MULTILINE)
    return pattern.sub(lambda m: m.group(1) + f"~{z}", text)


def main() -> None:
    base = base64.b64decode("".join(B64_PATH.read_text(encoding="utf-8").split()))
    with zipfile.ZipFile(io.BytesIO(base), "r") as zin:
        files = {n: zin.read(n) for n in zin.namelist()}

    required = list(CLASS_MAP) + [
        "assets/koshpackdiverhelmet/lang/ru_ru.json",
        "data/koshpackarmor/function/spawn_diver_test.mcfunction",
        "data/koshpackarmor/function/spawn_armor_test.mcfunction",
        "ru/koshpack/forgebridge/armor/KoshPackArmorMod.class",
    ]
    missing = [n for n in required if n not in files]
    if missing:
        raise SystemExit("Missing alpha54 base files: " + ", ".join(missing))

    # Clean an earlier pilot payload if the builder is rerun.
    for n in list(files):
        if (
            "koshpackpilothelmet" in n
            or "/pilothelmet/" in n
            or "/Pilot" in n
            or n.endswith("/spawn_pilot_test.mcfunction")
            or n == "META-INF/koshpack/pilot-alpha55.txt"
        ):
            del files[n]

    for src, dst in CLASS_MAP.items():
        files[dst] = patch_class(files[src])

    main_mod = "ru/koshpack/forgebridge/armor/KoshPackArmorMod.class"
    files[main_mod] = patch_bootstrap(
        files[main_mod],
        "ru/koshpack/forgebridge/pilothelmet/PilotHelmetAddon",
    )

    prefix = "assets/koshpackdiverhelmet/"
    for src in [n for n in list(files) if n.startswith(prefix)]:
        dst = src.replace("koshpackdiverhelmet", "koshpackpilothelmet").replace("diver", "pilot")
        data = files[src]
        if src.lower().endswith((".json", ".mcmeta", ".txt")):
            files[dst] = patch_text(data)
        else:
            files[dst] = data

    diver_fn = "data/koshpackarmor/function/spawn_diver_test.mcfunction"
    pilot_fn = "data/koshpackarmor/function/spawn_pilot_test.mcfunction"
    pilot_text = patch_text(files[diver_fn]).decode("utf-8")
    pilot_text = move_function_row(pilot_text, 3)
    files[pilot_fn] = pilot_text.encode("utf-8")

    all_fn = "data/koshpackarmor/function/spawn_armor_test.mcfunction"
    all_text = files[all_fn].decode("utf-8")
    all_text = "\n".join(
        line for line in all_text.splitlines()
        if "koshpackpilothelmet:" not in line and '"Пилот ' not in line
    ).rstrip() + "\n"

    z_values = [
        int(m.group(1))
        for m in re.finditer(
            r"^summon minecraft:armor_stand ~[+-]?\d+ ~[+-]?\d+ ~([+-]?\d+)",
            all_text,
            flags=re.MULTILINE,
        )
    ]
    new_z = (max(z_values) + 4) if z_values else 67
    all_text += move_function_row(pilot_text, new_z).rstrip() + "\n"
    files[all_fn] = all_text.encode("utf-8")

    files["META-INF/koshpack/pilot-alpha55.txt"] = (
        "KoshPack DEV alpha55\n"
        "Pilot I-IV added as the 17th profession family on top of alpha54.\n"
        "Existing alpha54 classes/assets are preserved; Pilot currently uses the Diver model family as its in-mod base.\n"
    ).encode("utf-8")

    # Patched JAR signatures would no longer be valid.
    for n in list(files):
        upper = n.upper()
        if upper.startswith("META-INF/") and upper.endswith((".SF", ".RSA", ".DSA", ".EC")):
            del files[n]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
        for n in sorted(files):
            zout.writestr(n, files[n])
    jar = buf.getvalue()

    OUT_JAR.write_bytes(jar)
    B64_PATH.write_text(base64.b64encode(jar).decode("ascii") + "\n", encoding="utf-8")

    sha = hashlib.sha256(jar).hexdigest()
    manifest = {
        "schema": 1,
        "channel": "dev-armor",
        "label": "DEV / БРОНЯ",
        "launcherMinVersion": "0.2.3",
        "minecraft": "1.21.1",
        "neoforge": "21.1.248",
        "armor": {
            "version": VERSION,
            "file": "KoshPack_Armor_DEV.jar",
            "url": "https://github.com/koshgamer/KoshPack-Updates/releases/download/armor-dev-current/KoshPack_Armor_DEV.jar",
            "size": len(jar),
            "sha256": sha,
            "note": NOTE,
        },
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Built {VERSION}")
    print(f"size={len(jar)}")
    print(f"sha256={sha}")
    print(f"pilot_row_z={new_z}")


if __name__ == "__main__":
    main()
