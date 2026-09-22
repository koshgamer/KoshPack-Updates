#!/usr/bin/env python3
from __future__ import annotations

import base64
import colorsys
import hashlib
import io
import json
import re
import struct
import zipfile
from pathlib import Path

from PIL import Image

VERSION = "alpha52-hunter-v2-registryfix"
NOTE = (
    "alpha52 Hunter v2: fixes Hunter DeferredRegister bootstrap in KoshPackArmorMod; "
    "field tracker earth/leather palette with four I-IV armor tiers"
)

ROOT = Path(__file__).resolve().parents[2]
B64_PATH = ROOT / "launcher/dev/current.jar.b64"
OUT_DIR = ROOT / "dist"
OUT_JAR = OUT_DIR / "KoshPack_Armor_DEV.jar"
MANIFEST = ROOT / "launcher/dev-manifest.json"
PUBLISHER = ROOT / ".github/workflows/publish-dev-armor.yml"

REPL_BYTES = (
    (b"koshpackresearcherarmor", b"koshpackhunterarmor"),
    (b"Researcher", b"Hunter"),
    (b"researcher", b"hunter"),
)

CLASS_MAP = {
    "ru/koshpack/forgebridge/researcherarmor/ResearcherArmorAddon.class":
        "ru/koshpack/forgebridge/hunterarmor/HunterArmorAddon.class",
    "ru/koshpack/forgebridge/researcherarmor/ResearcherArmorItem.class":
        "ru/koshpack/forgebridge/hunterarmor/HunterArmorItem.class",
    "ru/koshpack/forgebridge/armor/client/ResearcherArmorClient$1.class":
        "ru/koshpack/forgebridge/armor/client/HunterArmorClient$1.class",
    "ru/koshpack/forgebridge/armor/client/ResearcherArmorClient.class":
        "ru/koshpack/forgebridge/armor/client/HunterArmorClient.class",
    "ru/koshpack/forgebridge/armor/client/ResearcherArmorModel.class":
        "ru/koshpack/forgebridge/armor/client/HunterArmorModel.class",
    "ru/koshpack/forgebridge/armor/client/ResearcherModelGeometry.class":
        "ru/koshpack/forgebridge/armor/client/HunterModelGeometry.class",
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
        if tag == 1:  # CONSTANT_Utf8
            length = struct.unpack(">H", data[pos:pos+2])[0]
            raw = data[pos+2:pos+2+length]
            patched = patch_utf8(raw)
            out += struct.pack(">H", len(patched))
            out += patched
            pos += 2 + length
        elif tag in (3, 4):
            out += data[pos:pos+4]
            pos += 4
        elif tag in (5, 6):
            out += data[pos:pos+8]
            pos += 8
            index += 1
        elif tag in (7, 8, 16, 19, 20):
            out += data[pos:pos+2]
            pos += 2
        elif tag in (9, 10, 11, 12, 17, 18):
            out += data[pos:pos+4]
            pos += 4
        elif tag == 15:
            out += data[pos:pos+3]
            pos += 3
        else:
            raise ValueError(f"Unsupported constant-pool tag {tag} at index {index}")
        index += 1
    out += data[pos:]
    return bytes(out)



def _parse_constant_pool(data: bytes):
    cp_count = struct.unpack(">H", data[8:10])[0]
    entries = [None] * cp_count
    pos = 10
    idx = 1
    while idx < cp_count:
        start = pos
        tag = data[pos]
        pos += 1
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
            value = struct.unpack(">H", data[pos:pos+2])[0]
            pos += 2
        elif tag in (9, 10, 11, 12, 17, 18):
            value = struct.unpack(">HH", data[pos:pos+4])
            pos += 4
        elif tag == 15:
            value = (data[pos], struct.unpack(">H", data[pos+1:pos+3])[0])
            pos += 3
        else:
            raise ValueError(f"Unsupported constant-pool tag {tag} at index {idx}")
        entries[idx] = (tag, value, data[start:pos])
        idx += 1
    return cp_count, entries, pos


def _u2(buf: bytes, pos: int) -> int:
    return struct.unpack(">H", buf[pos:pos+2])[0]


def _u4(buf: bytes, pos: int) -> int:
    return struct.unpack(">I", buf[pos:pos+4])[0]


def patch_koshpack_bootstrap(data: bytes) -> bytes:
    """Append new HunterArmorAddon(eventBus) to KoshPackArmorMod constructor."""
    cp_count, cp, cp_end = _parse_constant_pool(data)

    utf8 = {entry[1]: i for i, entry in enumerate(cp) if entry and entry[0] == 1}
    init_utf = utf8["<init>"]
    bus_desc = "(Lnet/neoforged/bus/api/IEventBus;)V"
    desc_utf = utf8[bus_desc]
    code_utf = utf8["Code"]

    nt_index = None
    for i, entry in enumerate(cp):
        if entry and entry[0] == 12 and entry[1] == (init_utf, desc_utf):
            nt_index = i
            break
    if nt_index is None:
        raise ValueError("Could not find constructor NameAndType for IEventBus")

    hunter_internal = "ru/koshpack/forgebridge/hunterarmor/HunterArmorAddon"
    hunter_raw = hunter_internal.encode("utf-8")
    hunter_utf_idx = cp_count
    hunter_class_idx = cp_count + 1
    hunter_ctor_idx = cp_count + 2

    extra_cp = (
        bytes([1]) + struct.pack(">H", len(hunter_raw)) + hunter_raw
        + bytes([7]) + struct.pack(">H", hunter_utf_idx)
        + bytes([10]) + struct.pack(">HH", hunter_class_idx, nt_index)
    )

    rest = bytearray(data[cp_end:])

    # class header in "rest": access, this, super, interfaces_count...
    p = 0
    p += 6
    interfaces_count = _u2(rest, p)
    p += 2 + interfaces_count * 2

    fields_count = _u2(rest, p)
    p += 2
    for _ in range(fields_count):
        p += 6
        attr_count = _u2(rest, p)
        p += 2
        for _ in range(attr_count):
            attr_len = _u4(rest, p + 2)
            p += 6 + attr_len

    methods_count_pos = p
    methods_count = _u2(rest, p)
    p += 2

    method_chunks = []
    patched = False
    for _ in range(methods_count):
        m_start = p
        access = _u2(rest, p)
        name_idx = _u2(rest, p + 2)
        desc_idx = _u2(rest, p + 4)
        attr_count = _u2(rest, p + 6)
        p += 8

        attrs = []
        is_target = (
            cp[name_idx][1] == "<init>"
            and cp[desc_idx][1] == bus_desc
        )
        for _ in range(attr_count):
            a_name_idx = _u2(rest, p)
            a_len = _u4(rest, p + 2)
            info = bytes(rest[p+6:p+6+a_len])
            p += 6 + a_len

            if is_target and a_name_idx == code_utf:
                max_stack = _u2(info, 0)
                max_locals = _u2(info, 2)
                code_len = _u4(info, 4)
                code = info[8:8+code_len]
                tail = info[8+code_len:]
                if not code or code[-1] != 0xB1:
                    raise ValueError("KoshPackArmorMod constructor does not end with return")

                inject = (
                    b"\\xbb" + struct.pack(">H", hunter_class_idx)
                    + b"\\x59\\x2b\\xb7" + struct.pack(">H", hunter_ctor_idx)
                    + b"\\x57"
                )
                new_code = code[:-1] + inject + code[-1:]
                info = (
                    struct.pack(">HHI", max(max_stack, 3), max_locals, len(new_code))
                    + new_code + tail
                )
                a_len = len(info)
                patched = True

            attrs.append(struct.pack(">HI", a_name_idx, a_len) + info)

        method_chunks.append(
            struct.pack(">HHHH", access, name_idx, desc_idx, attr_count)
            + b"".join(attrs)
        )

    class_tail = bytes(rest[p:])
    methods_prefix = bytes(rest[:methods_count_pos]) + struct.pack(">H", methods_count)
    new_rest = methods_prefix + b"".join(method_chunks) + class_tail

    if not patched:
        raise ValueError("KoshPackArmorMod(IEventBus) constructor was not patched")

    return (
        data[:8]
        + struct.pack(">H", cp_count + 3)
        + data[10:cp_end]
        + extra_cp
        + new_rest
    )


def tier_from_name(name: str) -> int:
    low = name.lower()
    for tier, token in ((4, "_iv"), (3, "_iii"), (2, "_ii"), (1, "_i")):
        if token in low:
            return tier
    return 1


PALETTES = {
    1: ((43, 37, 25), (116, 101, 58), (152, 128, 78)),
    2: ((35, 39, 24), (91, 105, 55), (145, 116, 67)),
    3: ((27, 35, 23), (68, 91, 50), (131, 103, 62)),
    4: ((22, 29, 20), (53, 75, 45), (121, 91, 53)),
}


def lerp(a: int, b: int, t: float) -> int:
    return max(0, min(255, round(a + (b - a) * t)))


def recolor_png(data: bytes, name: str) -> bytes:
    img = Image.open(io.BytesIO(data)).convert("RGBA")
    tier = tier_from_name(name)
    shadow, cloth, leather = PALETTES[tier]
    px = img.load()

    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
            t = max(0.0, min(1.0, lum / 255.0))

            # Keep low-saturation metal/details readable, but warm them slightly.
            if s < 0.16:
                metal_dark = (48, 47, 42)
                metal_light = (154, 148, 126)
                nr = lerp(metal_dark[0], metal_light[0], t)
                ng = lerp(metal_dark[1], metal_light[1], t)
                nb = lerp(metal_dark[2], metal_light[2], t)
            else:
                # Saturated expedition colors become forest cloth + leather.
                target = cloth if (h < 0.18 or h > 0.55) else leather
                if t < 0.42:
                    local = t / 0.42
                    nr = lerp(shadow[0], target[0], local)
                    ng = lerp(shadow[1], target[1], local)
                    nb = lerp(shadow[2], target[2], local)
                else:
                    local = (t - 0.42) / 0.58
                    hi = tuple(min(220, c + 48) for c in target)
                    nr = lerp(target[0], hi[0], local)
                    ng = lerp(target[1], hi[1], local)
                    nb = lerp(target[2], hi[2], local)

            # Preserve original shading/detail instead of flattening the texture.
            nr = round(nr * 0.78 + r * 0.22)
            ng = round(ng * 0.78 + g * 0.22)
            nb = round(nb * 0.78 + b * 0.22)
            px[x, y] = (nr, ng, nb, a)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def patch_text(data: bytes) -> bytes:
    text = data.decode("utf-8")
    text = text.replace("koshpackresearcherarmor", "koshpackhunterarmor")
    text = text.replace("Researcher", "Hunter").replace("researcher", "hunter")
    text = text.replace("Исследователь", "Охотник")
    text = text.replace("исследователь", "охотник")
    return text.encode("utf-8")


def duplicate_toml_sections(text: str) -> str:
    if "koshpackhunterarmor" in text or "koshpackresearcherarmor" not in text:
        return text
    parts = re.split(r"(?=^\[\[)", text, flags=re.MULTILINE)
    out: list[str] = []
    for part in parts:
        out.append(part)
        if "koshpackresearcherarmor" in part:
            clone = (
                part.replace("koshpackresearcherarmor", "koshpackhunterarmor")
                    .replace("Researcher", "Hunter")
                    .replace("researcher", "hunter")
                    .replace("Исследователь", "Охотник")
            )
            out.append(clone)
    return "".join(out)


def main() -> None:
    raw_b64 = "".join(B64_PATH.read_text(encoding="utf-8").split())
    base_jar = base64.b64decode(raw_b64)

    with zipfile.ZipFile(io.BytesIO(base_jar), "r") as zin:
        files = {name: zin.read(name) for name in zin.namelist()}

    required = list(CLASS_MAP) + [
        "data/koshpackarmor/function/spawn_researcher_test.mcfunction",
        "assets/koshpackresearcherarmor/lang/ru_ru.json",
    ]

    missing = [name for name in required if name not in files]
    if missing:
        raise SystemExit("Missing Researcher base files: " + ", ".join(missing))

    # Remove an earlier Hunter build if this script is rerun.
    for name in list(files):
        if (
            "koshpackhunterarmor" in name
            or "/hunterarmor/" in name
            or "/Hunter" in name
            or name.endswith("/spawn_hunter_test.mcfunction")
        ):
            del files[name]

    for src, dst in CLASS_MAP.items():
        files[dst] = patch_class(files[src])

    main_mod = "ru/koshpack/forgebridge/armor/KoshPackArmorMod.class"
    if main_mod not in files:
        raise SystemExit("Missing KoshPackArmorMod.class")
    files[main_mod] = patch_koshpack_bootstrap(files[main_mod])

    researcher_prefix = "assets/koshpackresearcherarmor/"
    for src in [n for n in list(files) if n.startswith(researcher_prefix)]:
        dst = src.replace("koshpackresearcherarmor", "koshpackhunterarmor").replace("researcher", "hunter")
        data = files[src]
        if src.lower().endswith(".png"):
            files[dst] = recolor_png(data, dst)
        elif src.lower().endswith((".json", ".mcmeta", ".txt")):
            files[dst] = patch_text(data)
        else:
            files[dst] = data

    src_fn = "data/koshpackarmor/function/spawn_researcher_test.mcfunction"
    hunter_fn = "data/koshpackarmor/function/spawn_hunter_test.mcfunction"
    files[hunter_fn] = patch_text(files[src_fn])

    # Existing signatures would no longer be valid after patching.
    for name in list(files):
        upper = name.upper()
        if upper.startswith("META-INF/") and upper.endswith((".SF", ".RSA", ".DSA", ".EC")):
            del files[name]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
        for name in sorted(files):
            zout.writestr(name, files[name])
    jar_bytes = buf.getvalue()

    OUT_JAR.write_bytes(jar_bytes)
    B64_PATH.write_text(base64.b64encode(jar_bytes).decode("ascii") + "\n", encoding="utf-8")

    sha = hashlib.sha256(jar_bytes).hexdigest()
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
            "size": len(jar_bytes),
            "sha256": sha,
            "note": NOTE,
        },
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if PUBLISHER.exists():
        text = PUBLISHER.read_text(encoding="utf-8")
        text = re.sub(r'DEV_VERSION: "[^"]*"', f'DEV_VERSION: "{VERSION}"', text)
        text = re.sub(r'DEV_NOTE: "[^"]*"', f'DEV_NOTE: "{NOTE}"', text)
        PUBLISHER.write_text(text, encoding="utf-8")

    print(f"Built {VERSION}")
    print(f"size={len(jar_bytes)}")
    print(f"sha256={sha}")
    print("hunter_function=yes" if hunter_fn in files else "hunter_function=no")
    print("researcher_preserved=yes" if src_fn in files else "researcher_preserved=no")


if __name__ == "__main__":
    main()
