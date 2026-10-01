"""COMANDO 23-B Bloc 1.3: verify sha256 of every file copied from raw_dir
into RAW_ROOT/raw. Read-only against the source; writes only its own CSV
report under outputs_audit_dir.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from craei.config import load_paths

SRC = Path(r"C:\Users\User\Desktop\DOUGLAS\DOUTORADO\PHD RELATED WORKS\CLIMATE RISK FRAMEWORK\data\raw")
DST = Path(r"D:\Douglas\OUTROS\CRAEI_raw_data\raw")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    paths = load_paths()
    manifest = json.loads((SRC / "manifest.json").read_text(encoding="utf-8"))
    manifest_by_relpath = {}
    for _key, v in manifest.items():
        if not isinstance(v, dict) or "path" not in v:
            continue
        p = Path(v["path"])
        try:
            rel = p.relative_to(SRC)
        except ValueError:
            continue
        manifest_by_relpath[str(rel)] = v.get("sha256")

    rows = []
    divergences = 0
    src_files = sorted(p for p in SRC.rglob("*") if p.is_file() and p.name != "manifest.json")
    for sf in src_files:
        rel = sf.relative_to(SRC)
        df = DST / rel
        if not df.exists():
            rows.append((str(rel), "MISSING_IN_DEST", "", "", ""))
            divergences += 1
            continue
        src_hash = sha256_of(sf)
        dst_hash = sha256_of(df)
        match = src_hash == dst_hash
        manifest_hash = manifest_by_relpath.get(str(rel), "")
        manifest_match = (manifest_hash == "") or (manifest_hash == src_hash)
        if not match or not manifest_match:
            divergences += 1
        rows.append((str(rel), "OK" if match else "MISMATCH", src_hash, dst_hash, manifest_hash))

    outp = Path(paths["outputs_audit_dir"]) / "c23" / "c23e" / "c23b_copy_verification.csv"
    outp.parent.mkdir(parents=True, exist_ok=True)
    import csv

    with open(outp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["relpath", "status", "src_sha256", "dst_sha256", "manifest_sha256"])
        w.writerows(rows)

    print(f"Checked {len(rows)} files. Divergences: {divergences}")
    print(f"Report: {outp}")


if __name__ == "__main__":
    main()
