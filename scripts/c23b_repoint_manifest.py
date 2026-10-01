"""COMANDO 23-B Bloc 1.5: repoint the RAW_ROOT copy of manifest.json from the
old C: raw_dir to the new D: RAW_ROOT/raw location. Only the `path` field is
rewritten; `sha256` and every other field are left untouched. The original
manifest.json on C: (inside the old raw_dir) is not touched.
"""

import json
from pathlib import Path

OLD_PREFIX = str(
    Path(
        r"C:\Users\User\Desktop\DOUGLAS\DOUTORADO\PHD RELATED WORKS\CLIMATE RISK FRAMEWORK\data\raw"
    )
)
NEW_PREFIX = str(Path(r"D:\Douglas\OUTROS\CRAEI_raw_data\raw"))
TARGET_MANIFEST = Path(r"D:\Douglas\OUTROS\CRAEI_raw_data\raw\manifest.json")


def main() -> None:
    manifest = json.loads(TARGET_MANIFEST.read_text(encoding="utf-8"))
    n_updated = 0
    for _key, entry in manifest.items():
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        if path and path.startswith(OLD_PREFIX):
            entry["path"] = NEW_PREFIX + path[len(OLD_PREFIX):]
            n_updated += 1
    TARGET_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Updated {n_updated} 'path' entries in {TARGET_MANIFEST}")


if __name__ == "__main__":
    main()
