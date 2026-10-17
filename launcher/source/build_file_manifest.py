"""Create a full per-file release manifest from an unpacked Project Meridian client.

Usage:
  python launcher/source/build_file_manifest.py ./client-files https://example.org/releases/files > files.json

Upload every file from client-files under the same relative paths to the HTTPS
base URL first, and verify URLs are public before publishing manifest.json.
No stable manifest is changed by this script.
"""
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import quote

def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: build_file_manifest.py DIRECTORY HTTPS_BASE_URL")
    root = Path(sys.argv[1]).resolve()
    base = sys.argv[2].rstrip("/")
    if not root.is_dir() or not base.startswith("https://"):
        raise SystemExit("Expected existing directory and HTTPS URL")
    result = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith(("saves/", "screenshots/", "logs/", "crash-reports/", "config/voicechat/")) or rel in ("options.txt", "servers.dat", "servers.dat_old", "usercache.json"):
            continue
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        result[rel] = {"url": base + "/" + "/".join(quote(p, safe="") for p in rel.split("/")),
                       "sha256": h.hexdigest(), "size": path.stat().st_size}
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
