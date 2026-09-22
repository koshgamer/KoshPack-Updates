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

VERSION = "alpha51-hunter-v1-tracker"
NOTE = (
    "alpha51 Hunter v1: field tracker based on Researcher expedition silhouette, "
    "earth/leather palette, preserved Archer separation, four I-IV armor tiers"
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

    mods_toml = "META-INF/neoforge.mods.toml"
    if mods_toml in files:
        text = files[mods_toml].decode("utf-8")
        files[mods_toml] = duplicate_toml_sections(text).encode("utf-8")

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
