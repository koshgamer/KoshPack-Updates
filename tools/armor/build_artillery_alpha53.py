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

VERSION = "alpha53-artillery-v1-crew"
NOTE = (
    "alpha53 Artillery v1: heavy artillery-crew armor I-IV, olive/graphite/metal palette; "
    "registered in KoshPackArmorMod DEV bootstrap"
)

ROOT = Path(__file__).resolve().parents[2]
B64_PATH = ROOT / "launcher/dev/current.jar.b64"
OUT_DIR = ROOT / "dist"
OUT_JAR = OUT_DIR / "KoshPack_Armor_DEV.jar"
MANIFEST = ROOT / "launcher/dev-manifest.json"
PUBLISHER = ROOT / ".github/workflows/publish-dev-armor.yml"

REPL_BYTES = (
    (b"koshpackfighterarmor", b"koshpackartilleryarmor"),
    (b"Fighter", b"Artillery"),
    (b"fighter", b"artillery"),
)

CLASS_MAP = {
    "ru/koshpack/forgebridge/fighterarmor/FighterArmorAddon.class":
        "ru/koshpack/forgebridge/artilleryarmor/ArtilleryArmorAddon.class",
    "ru/koshpack/forgebridge/fighterarmor/FighterArmorItem.class":
        "ru/koshpack/forgebridge/artilleryarmor/ArtilleryArmorItem.class",
    "ru/koshpack/forgebridge/armor/client/FighterArmorClient$1.class":
        "ru/koshpack/forgebridge/armor/client/ArtilleryArmorClient$1.class",
    "ru/koshpack/forgebridge/armor/client/FighterArmorClient.class":
        "ru/koshpack/forgebridge/armor/client/ArtilleryArmorClient.class",
    "ru/koshpack/forgebridge/armor/client/FighterArmorModel.class":
        "ru/koshpack/forgebridge/armor/client/ArtilleryArmorModel.class",
    "ru/koshpack/forgebridge/armor/client/FighterModelGeometry.class":
        "ru/koshpack/forgebridge/armor/client/ArtilleryModelGeometry.class",
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
            try: value = raw.decode("utf-8")
            except UnicodeDecodeError: value = None
        elif tag in (3,4): pos += 4
        elif tag in (5,6):
            pos += 8
            entries[idx] = (tag, value, data[start:pos])
            idx += 1
        elif tag in (7,8,16,19,20):
            value = struct.unpack(">H", data[pos:pos+2])[0]; pos += 2
        elif tag in (9,10,11,12,17,18):
            value = struct.unpack(">HH", data[pos:pos+4]); pos += 4
        elif tag == 15:
            value = (data[pos], struct.unpack(">H", data[pos+1:pos+3])[0]); pos += 3
        else:
            raise ValueError(f"Unsupported cp tag {tag}")
        entries[idx] = (tag, value, data[start:pos])
        idx += 1
    return count, entries, pos

def u2(buf: bytes, p: int) -> int:
    return struct.unpack(">H", buf[p:p+2])[0]

def u4(buf: bytes, p: int) -> int:
    return struct.unpack(">I", buf[p:p+4])[0]

def patch_bootstrap(data: bytes, internal_name: str) -> bytes:
    count, cp, cp_end = parse_cp(data)
    utf8 = {e[1]: i for i,e in enumerate(cp) if e and e[0] == 1}
    init_utf = utf8["<init>"]
    bus_desc = "(Lnet/neoforged/bus/api/IEventBus;)V"
    desc_utf = utf8[bus_desc]
    code_utf = utf8["Code"]

    nt_idx = next(
        (i for i,e in enumerate(cp) if e and e[0] == 12 and e[1] == (init_utf, desc_utf)),
        None
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
            ln = u4(rest, p+2); p += 6 + ln

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
            ln = u4(rest, p+2)
            info = bytes(rest[p+6:p+6+ln])
            p += 6 + ln
            if target and an == code_utf:
                max_stack = u2(info,0)
                max_locals = u2(info,2)
                code_len = u4(info,4)
                code = info[8:8+code_len]
                tail = info[8+code_len:]
                if not code or code[-1] != 0xB1:
                    raise ValueError("Constructor does not end with return")
                inject = (
                    bytes([0xBB]) + struct.pack(">H", cls_idx)
                    + bytes([0x59,0x2B,0xB7]) + struct.pack(">H", ctor_idx)
                    + bytes([0x57])
                )
                code = code[:-1] + inject + code[-1:]
                info = struct.pack(">HHI", max(max_stack,3), max_locals, len(code)) + code + tail
                ln = len(info)
                patched = True
            attrs.append(struct.pack(">HI", an, ln) + info)
        method_chunks.append(struct.pack(">HHHH", access, name_idx, desc_idx, ac) + b"".join(attrs))

    if not patched:
        raise ValueError("KoshPackArmorMod constructor was not patched")

    return (
        data[:8] + struct.pack(">H", count + 3) + data[10:cp_end] + extra
        + bytes(rest[:methods_count_pos]) + struct.pack(">H", methods)
        + b"".join(method_chunks) + bytes(rest[p:])
    )

def tier_from_name(name: str) -> int:
    low = name.lower()
    for tier, token in ((4,"_iv"),(3,"_iii"),(2,"_ii"),(1,"_i")):
        if token in low: return tier
    return 1

PALETTES = {
    1: ((42, 43, 38), (91, 91, 70), (120, 108, 78)),
    2: ((36, 39, 34), (79, 83, 61), (132, 112, 69)),
    3: ((31, 34, 31), (67, 72, 55), (143, 116, 64)),
    4: ((25, 28, 27), (57, 63, 51), (154, 119, 56)),
}

def lerp(a:int,b:int,t:float)->int:
    return max(0,min(255,round(a+(b-a)*t)))

def recolor_png(data: bytes, name: str) -> bytes:
    img = Image.open(io.BytesIO(data)).convert("RGBA")
    tier = tier_from_name(name)
    shadow, cloth, metal = PALETTES[tier]
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r,g,b,a = px[x,y]
            if a == 0: continue
            h,s,v = colorsys.rgb_to_hsv(r/255,g/255,b/255)
            lum = (0.2126*r + 0.7152*g + 0.0722*b)/255.0
            if s < 0.18:
                lo=(45,47,46); hi=(173,168,150)
                nr,ng,nb=(lerp(lo[0],hi[0],lum),lerp(lo[1],hi[1],lum),lerp(lo[2],hi[2],lum))
            else:
                target = metal if (h < 0.16 or h > 0.88) else cloth
                if lum < 0.46:
                    q=lum/0.46
                    nr,ng,nb=(lerp(shadow[0],target[0],q),lerp(shadow[1],target[1],q),lerp(shadow[2],target[2],q))
                else:
                    q=(lum-0.46)/0.54
                    hi=tuple(min(215,c+42) for c in target)
                    nr,ng,nb=(lerp(target[0],hi[0],q),lerp(target[1],hi[1],q),lerp(target[2],hi[2],q))
            nr=round(nr*0.80+r*0.20); ng=round(ng*0.80+g*0.20); nb=round(nb*0.80+b*0.20)
            px[x,y]=(nr,ng,nb,a)
    out=io.BytesIO(); img.save(out,format="PNG",optimize=True)
    return out.getvalue()

def patch_text(data: bytes) -> bytes:
    text=data.decode("utf-8")
    text=text.replace("koshpackfighterarmor","koshpackartilleryarmor")
    text=text.replace("Fighter","Artillery").replace("fighter","artillery")
    text=text.replace("Боец","Артиллерист").replace("боец","артиллерист")
    return text.encode("utf-8")

def main():
    base=base64.b64decode("".join(B64_PATH.read_text(encoding="utf-8").split()))
    with zipfile.ZipFile(io.BytesIO(base),"r") as zin:
        files={n:zin.read(n) for n in zin.namelist()}

    required=list(CLASS_MAP)+[
        "data/koshpackarmor/function/spawn_fighter_test.mcfunction",
        "assets/koshpackfighterarmor/lang/ru_ru.json",
    ]
    missing=[n for n in required if n not in files]
    if missing:
        raise SystemExit("Missing Fighter base files: "+", ".join(missing))

    for n in list(files):
        if "koshpackartilleryarmor" in n or "/artilleryarmor/" in n or "/Artillery" in n or n.endswith("/spawn_artillery_test.mcfunction"):
            del files[n]

    for src,dst in CLASS_MAP.items():
        files[dst]=patch_class(files[src])

    main_mod="ru/koshpack/forgebridge/armor/KoshPackArmorMod.class"
    files[main_mod]=patch_bootstrap(files[main_mod],"ru/koshpack/forgebridge/artilleryarmor/ArtilleryArmorAddon")

    prefix="assets/koshpackfighterarmor/"
    for src in [n for n in list(files) if n.startswith(prefix)]:
        dst=src.replace("koshpackfighterarmor","koshpackartilleryarmor").replace("fighter","artillery")
        data=files[src]
        if src.lower().endswith(".png"):
            files[dst]=recolor_png(data,dst)
        elif src.lower().endswith((".json",".mcmeta",".txt")):
            files[dst]=patch_text(data)
        else:
            files[dst]=data

    src_fn="data/koshpackarmor/function/spawn_fighter_test.mcfunction"
    art_fn="data/koshpackarmor/function/spawn_artillery_test.mcfunction"
    files[art_fn]=patch_text(files[src_fn])

    for n in list(files):
        u=n.upper()
        if u.startswith("META-INF/") and u.endswith((".SF",".RSA",".DSA",".EC")):
            del files[n]

    OUT_DIR.mkdir(parents=True,exist_ok=True)
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as zout:
        for n in sorted(files):
            zout.writestr(n,files[n])
    jar=buf.getvalue()
    OUT_JAR.write_bytes(jar)
    B64_PATH.write_text(base64.b64encode(jar).decode("ascii")+"\n",encoding="utf-8")

    sha=hashlib.sha256(jar).hexdigest()
    manifest={
        "schema":1,"channel":"dev-armor","label":"DEV / БРОНЯ","launcherMinVersion":"0.2.3",
        "minecraft":"1.21.1","neoforge":"21.1.248",
        "armor":{
            "version":VERSION,"file":"KoshPack_Armor_DEV.jar",
            "url":"https://github.com/koshgamer/KoshPack-Updates/releases/download/armor-dev-current/KoshPack_Armor_DEV.jar",
            "size":len(jar),"sha256":sha,"note":NOTE
        }
    }
    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Built {VERSION}")
    print(f"size={len(jar)}")
    print(f"sha256={sha}")
    print("artillery_function=yes" if art_fn in files else "artillery_function=no")
    print("hunter_preserved=yes" if "data/koshpackarmor/function/spawn_hunter_test.mcfunction" in files else "hunter_preserved=no")

if __name__=="__main__":
    main()
