#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARMOR_B64 = ROOT / "launcher/dev/current.jar.b64"
FORGE_UI_B64 = ROOT / "launcher/dev/forge-ui.jar.b64"
MANIFEST = ROOT / "launcher/dev-manifest.json"
OUT_DIR = ROOT / "dist"
OUT_JAR = OUT_DIR / "KoshPack_Armor_DEV.jar"

VERSION = "alpha55-all17-pilot-forge-ui-alpha7-integrated"
FORGE_UI_VERSION = "0.1.0-alpha7"
NOTE = (
    "Native Forge Bench UI alpha7 integrated into KoshPack_Armor_DEV.jar: installed treatment icons are rendered after slot labels "
    "with a safe fallback, guaranteeing the treatment icon remains visible; launcher 0.2.13 remains sufficient."
)

BEGIN = "# BEGIN KOSHPACK_FORGE_UI\n"
END = "# END KOSHPACK_FORGE_UI\n"


def decode_b64(path: Path) -> bytes:
    return base64.b64decode("".join(path.read_text(encoding="utf-8").split()))


def files_from_jar(data: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(data), "r") as zin:
        return {n: zin.read(n) for n in zin.namelist() if not n.endswith("/")}


def strip_old_descriptor(text: str) -> str:
    if BEGIN in text and END in text:
        before, rest = text.split(BEGIN, 1)
        _old, after = rest.split(END, 1)
        return (before.rstrip() + "\n" + after.lstrip()).rstrip() + "\n"
    return text.rstrip() + "\n"


def forge_descriptor_block(forge_toml: str) -> str:
    pos = forge_toml.find("[[mods]]")
    if pos < 0:
        raise SystemExit("Forge UI neoforge.mods.toml has no [[mods]] section")
    return BEGIN + forge_toml[pos:].strip() + "\n" + END


def main() -> None:
    armor = files_from_jar(decode_b64(ARMOR_B64))
    forge = files_from_jar(decode_b64(FORGE_UI_B64))

    required_armor = [
        "META-INF/neoforge.mods.toml",
        "ru/koshpack/forgebridge/armor/KoshPackArmorMod.class",
    ]
    required_forge = [
        "META-INF/neoforge.mods.toml",
        "ru/koshpack/forgeui/KoshPackForgeUI.class",
        "ru/koshpack/forgeui/client/ForgeBenchScreen.class",
        "ru/koshpack/forgeui/forge/ForgeService.class",
        "data/koshpack_forge_ui/forge_modifiers.json",
    ]
    missing = [n for n in required_armor if n not in armor]
    missing += [n for n in required_forge if n not in forge]
    if missing:
        raise SystemExit("Missing required integration files: " + ", ".join(missing))

    forge_toml_text = forge["META-INF/neoforge.mods.toml"].decode("utf-8")
    if f'version="{FORGE_UI_VERSION}"' not in forge_toml_text:
        raise SystemExit(
            "Stale Forge UI payload: expected "
            + FORGE_UI_VERSION
            + " in META-INF/neoforge.mods.toml"
        )

    # Remove a previously integrated Forge UI payload to make this operation idempotent.
    prefixes = (
        "ru/koshpack/forgeui/",
        "assets/koshpack_forge_ui/",
        "data/koshpack_forge_ui/",
    )
    for name in list(armor):
        if name.startswith(prefixes):
            del armor[name]

    # Overlay only the Forge UI's classes and own resources. Keep the armor JAR's
    # manifest/pack metadata as the canonical outer JAR metadata.
    for name, payload in forge.items():
        if name.startswith(prefixes):
            armor[name] = payload

    armor_toml = armor["META-INF/neoforge.mods.toml"].decode("utf-8")
    forge_toml = forge["META-INF/neoforge.mods.toml"].decode("utf-8")
    armor_toml = strip_old_descriptor(armor_toml)
    armor["META-INF/neoforge.mods.toml"] = (
        armor_toml.rstrip() + "\n\n" + forge_descriptor_block(forge_toml)
    ).encode("utf-8")

    # Modified JAR signatures are no longer valid.
    for name in list(armor):
        upper = name.upper()
        if upper.startswith("META-INF/") and upper.endswith((".SF", ".RSA", ".DSA", ".EC")):
            del armor[name]

    armor["META-INF/koshpack/forge-ui-integrated.txt"] = (
        "KoshPack Forge UI 0.1.0-alpha7\n"
        "Integrated into KoshPack_Armor_DEV.jar for Project Meridian Launcher 0.2.13 compatibility.\n"
    ).encode("utf-8")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
        for name in sorted(armor):
            zout.writestr(name, armor[name])
    jar = buf.getvalue()

    # Sanity-check the merged descriptor and payload before updating public files.
    with zipfile.ZipFile(io.BytesIO(jar), "r") as z:
        names = set(z.namelist())
        assert "ru/koshpack/forgeui/client/ForgeBenchScreen.class" in names
        assert "ru/koshpack/forgebridge/armor/KoshPackArmorMod.class" in names
        merged_toml = z.read("META-INF/neoforge.mods.toml").decode("utf-8")
        assert 'modId="koshpack_forge_ui"' in merged_toml
        assert "koshpack_forge_ui" in merged_toml

    OUT_JAR.write_bytes(jar)
    ARMOR_B64.write_text(base64.b64encode(jar).decode("ascii") + "\n", encoding="utf-8")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["launcherMinVersion"] = "0.2.13"
    manifest["hotfixRevision"] = max(int(manifest.get("hotfixRevision", 0)) + 1, 8)
    manifest["armor"]["version"] = VERSION
    manifest["armor"]["note"] = NOTE
    manifest["armor"]["size"] = len(jar)
    manifest["armor"]["sha256"] = hashlib.sha256(jar).hexdigest()

    # 0.2.13 supports KubeJS extras, so keep those. The Java UI now rides inside
    # the armor JAR and must not be installed as mods/KoshPack_Forge_UI_DEV.jar.
    manifest["extras"] = [
        x for x in manifest.get("extras", [])
        if x.get("path") != "mods/KoshPack_Forge_UI_DEV.jar"
    ]

    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Integrated Forge UI into armor JAR")
    print("version=", VERSION)
    print("size=", len(jar))
    print("sha256=", hashlib.sha256(jar).hexdigest())
    print("launcherMinVersion=", manifest["launcherMinVersion"])
    print("extras=", len(manifest["extras"]))


if __name__ == "__main__":
    main()
