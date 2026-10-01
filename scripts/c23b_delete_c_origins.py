"""COMANDO 23-B Parada A, second part: delete the C: raw_dir files that have
a fresh, re-verified sha256-identical copy in RAW_ROOT/raw, excluding the
explicit keep-list authorized by the author. Deletes files individually
(never a whole directory), and only files it just re-hashed and matched.
"""

from __future__ import annotations

import csv
import hashlib
import os
from pathlib import Path

DRY_RUN = os.environ.get("C23B_DRY_RUN") == "1"

SRC = Path(r"C:\Users\User\Desktop\DOUGLAS\DOUTORADO\PHD RELATED WORKS\CLIMATE RISK FRAMEWORK\data\raw")
DST = Path(r"D:\Douglas\OUTROS\CRAEI_raw_data\raw")

# Kept on C: -- explicit author decision, not deletion candidates.
# Each entry is a tuple of path parts; a file matches if its own parts start
# with these parts (directory entries) or equal them exactly (file entries).
KEEP_RELPARTS = [
    # 1. crops whose global source is missing/anomalous in the D: cache
    ("climate", "isimip3b", "gfdl-esm4", "historical", "tasmax", "gfdl-esm4_historical_tasmax_BRA.nc"),
    ("climate", "isimip3b", "gfdl-esm4", "historical", "tasmax", "gfdl-esm4_historical_tasmax_IND.nc"),
    ("climate", "isimip3b", "gfdl-esm4", "historical", "tasmax", "gfdl-esm4_historical_tasmax_PRT.nc"),
    ("climate", "isimip3b", "gfdl-esm4", "historical", "tasmin", "gfdl-esm4_historical_tasmin_BRA.nc"),
    ("climate", "isimip3b", "gfdl-esm4", "historical", "tasmin", "gfdl-esm4_historical_tasmin_IND.nc"),
    ("climate", "isimip3b", "gfdl-esm4", "historical", "tasmin", "gfdl-esm4_historical_tasmin_PRT.nc"),
    # 2. datasets with no copy anywhere else (GEAR_framework), total < 3 GB
    ("boundaries", "hydrobasins"),
    ("climate", "w5e5v2.0"),
    ("validation", "ren_iph"),
    ("validation", "dgeg"),
    ("validation", "ons_ena"),
    ("manifest.json",),
]


def is_kept(relpath: Path) -> bool:
    parts = relpath.parts
    for keep in KEEP_RELPARTS:
        if parts[: len(keep)] == keep:
            return True
    return False


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    all_files = sorted(p for p in SRC.rglob("*") if p.is_file())
    deleted, kept, failed = [], [], []

    for sf in all_files:
        rel = sf.relative_to(SRC)
        if is_kept(rel):
            kept.append((str(rel), sf.stat().st_size, "kept (author exception)"))
            continue
        df = DST / rel
        if not df.exists():
            failed.append((str(rel), "NO_DEST_COPY"))
            continue
        src_hash = sha256_of(sf)
        dst_hash = sha256_of(df)
        if src_hash != dst_hash:
            failed.append((str(rel), f"HASH_MISMATCH src={src_hash} dst={dst_hash}"))
            continue
        size = sf.stat().st_size
        if not DRY_RUN:
            sf.unlink()
        deleted.append((str(rel), size, src_hash))

    report_dir = Path(
        r"C:\Users\User\Desktop\DOUGLAS\DOUTORADO\PHD RELATED WORKS\CLIMATE RISK FRAMEWORK\data\outputs\audit\c23\c23e"
    )
    report_dir.mkdir(parents=True, exist_ok=True)
    with open(report_dir / "c23b_deleted_from_c.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["relpath", "size_bytes", "sha256_at_deletion"])
        w.writerows(deleted)
    with open(report_dir / "c23b_kept_on_c.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["relpath", "size_bytes", "reason"])
        w.writerows(kept)

    print(f"Deleted: {len(deleted)} files, {sum(x[1] for x in deleted)/1e9:.4f} GB")
    print(f"Kept: {len(kept)} files, {sum(x[1] for x in kept)/1e9:.4f} GB")
    print(f"Failed/skipped (not deleted, needs attention): {len(failed)}")
    for f_ in failed:
        print("  ", f_)


if __name__ == "__main__":
    main()
