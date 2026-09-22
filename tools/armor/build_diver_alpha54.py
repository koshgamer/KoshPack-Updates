#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import io
import json
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

VERSION = "alpha54-diver-v2-donor-rebuild"
NOTE = (
    "alpha54 Diver v2 donor rebuild: Public Domain Scuba Diving Suit geometry adapted into "
    "four strongly separated KoshPack tiers: improvised I, equipped II, professional SCUBA III, "
    "elite deep-sea IV"
)

ROOT = Path(__file__).resolve().parents[2]
B64_PATH = ROOT / "launcher/dev/current.jar.b64"
MANIFEST_PATH = ROOT / "launcher/dev-manifest.json"
OUT_DIR = ROOT / "dist"
OUT_JAR = OUT_DIR / "KoshPack_Armor_DEV.jar"

CLASS_PATH = (
    ROOT
    / "tools/armor/diver_v2/build/classes/java/main"
    / "ru/koshpack/forgebridge/armor/client/DiverModelGeometry.class"
)
JAR_CLASS = "ru/koshpack/forgebridge/armor/client/DiverModelGeometry.class"

PALETTES = {
    1: {
        "base": (48, 61, 59),
        "mid": (69, 75, 64),
        "metal": (91, 80, 61),
        "accent": (125, 76, 43),
        "line": (33, 42, 41),
        "glass": (76, 148, 150, 170),
    },
    2: {
        "base": (24, 55, 65),
        "mid": (38, 79, 89),
        "metal": (92, 105, 104),
        "accent": (154, 118, 54),
        "line": (17, 38, 45),
        "glass": (66, 169, 185, 176),
    },
    3: {
        "base": (18, 46, 60),
        "mid": (31, 73, 89),
        "metal": (110, 123, 122),
        "accent": (176, 132, 51),
        "line": (13, 31, 40),
        "glass": (55, 187, 207, 182),
    },
    4: {
        "base": (18, 27, 34),
        "mid": (34, 51, 61),
        "metal": (122, 136, 137),
        "accent": (184, 112, 44),
        "line": (10, 16, 21),
        "glass": (51, 205, 224, 190),
    },
}


def make_texture(tier: int, piece: str) -> bytes:
    p = PALETTES[tier]
    img = Image.new("RGBA", (64, 64), p["base"] + (255,))
    px = img.load()

    # Pixel-art weave / worn metal variation without flattening the texture.
    for y in range(64):
        for x in range(64):
            if (x + y) % 7 == 0:
                c = p["mid"]
            elif (x * 3 + y * 5) % 19 == 0:
                c = p["line"]
            else:
                c = p["base"]
            px[x, y] = (*c, 255)

    d = ImageDraw.Draw(img)

    # Large UV regions for plates, straps, metal, warning accents.
    d.rectangle((0, 16, 63, 31), fill=p["mid"] + (255,))
    for x in range(0, 64, 8):
        d.line((x, 16, x + 6, 31), fill=p["line"] + (255,), width=1)

    d.rectangle((0, 32, 63, 47), fill=p["metal"] + (255,))
    for y in (35, 43):
        d.line((0, y, 63, y), fill=p["line"] + (255,), width=1)

    d.rectangle((0, 48, 63, 63), fill=p["base"] + (255,))
    d.line((0, 51, 63, 51), fill=p["accent"] + (255,), width=2)
    d.line((0, 60, 63, 60), fill=p["line"] + (255,), width=2)

    # Profession accent: brass/orange equipment bands.
    if tier >= 2:
        d.rectangle((28, 8, 35, 11), fill=p["accent"] + (255,))
        d.rectangle((4, 38, 15, 40), fill=p["accent"] + (255,))
    if tier >= 3:
        d.rectangle((38, 34, 47, 37), fill=p["accent"] + (255,))
        d.rectangle((18, 52, 26, 55), fill=p["accent"] + (255,))
    if tier == 4:
        # Elite set: visible technical markings.
        d.rectangle((1, 1, 14, 3), fill=p["metal"] + (255,))
        d.rectangle((17, 1, 29, 3), fill=p["accent"] + (255,))
        d.rectangle((2, 27, 11, 29), fill=p["accent"] + (255,))

    # Helmet viewport UV block. DiverArmorModel renders translucent textures.
    if piece == "helmet":
        glass = p["glass"]
        d.rectangle((48, 0, 63, 15), fill=glass)
        d.rectangle((49, 1, 62, 2), fill=(150, 235, 240, min(225, glass[3] + 25)))
        d.rectangle((49, 14, 62, 15), fill=(20, 55, 62, glass[3]))

    # Tier I must look visibly poor / patched.
    if tier == 1:
        rust = (116, 69, 39, 255)
        patch = (84, 81, 62, 255)
        d.rectangle((6, 6, 12, 10), fill=patch)
        d.line((6, 6, 12, 10), fill=rust, width=1)
        d.line((12, 6, 6, 10), fill=rust, width=1)
        d.rectangle((37, 21, 42, 25), outline=rust)
        d.rectangle((17, 53, 22, 57), fill=patch)

    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def main() -> None:
    if not CLASS_PATH.exists():
        raise SystemExit(f"Compiled DiverModelGeometry missing: {CLASS_PATH}")

    raw_b64 = "".join(B64_PATH.read_text(encoding="utf-8").split())
    base_jar = base64.b64decode(raw_b64)

    with zipfile.ZipFile(io.BytesIO(base_jar), "r") as zin:
        files = {name: zin.read(name) for name in zin.namelist()}

    required = [
        "data/koshpackarmor/function/spawn_diver_test.mcfunction",
        "data/koshpackarmor/function/spawn_hunter_test.mcfunction",
        "data/koshpackarmor/function/spawn_artillery_test.mcfunction",
        "ru/koshpack/forgebridge/armor/client/DiverArmorModel.class",
        JAR_CLASS,
    ]
    missing = [name for name in required if name not in files]
    if missing:
        raise SystemExit("Current DEV JAR missing required entries: " + ", ".join(missing))

    files[JAR_CLASS] = CLASS_PATH.read_bytes()

    for tier, roman in ((1, "i"), (2, "ii"), (3, "iii"), (4, "iv")):
        for piece in ("helmet", "chestplate", "leggings", "boots"):
            name = (
                f"assets/koshpackdiverhelmet/textures/models/armor/"
                f"diver_{piece}_{roman}.png"
            )
            files[name] = make_texture(tier, piece)

    files["META-INF/koshpack/diver-alpha54-donor.txt"] = (
        "KoshPack Diver alpha54 donor rebuild\n"
        "Base geometry reference: Scuba Diving Suit 1.0.0 for NeoForge 1.21.1\n"
        "CurseForge project 1483852, file 7744940\n"
        "Upstream license: Public Domain\n"
        "Adaptation: four-tier KoshPack progression with substantial geometry changes.\n"
    ).encode("utf-8")

    # Modified JARs must not retain stale signatures.
    for name in list(files):
        upper = name.upper()
        if upper.startswith("META-INF/") and upper.endswith((".SF", ".RSA", ".DSA", ".EC")):
            del files[name]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
        for name in sorted(files):
            zout.writestr(name, files[name])

    jar = out.getvalue()
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
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Built {VERSION}")
    print(f"size={len(jar)}")
    print(f"sha256={sha}")
    print("replacement_class=yes")
    print("diver_test_preserved=yes")
    print("hunter_preserved=yes")
    print("artillery_preserved=yes")


if __name__ == "__main__":
    main()
