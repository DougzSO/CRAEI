"""C23-B regression gate: recompute baseline hashes and compare (read-only)."""

import hashlib
import sys
import tempfile
from pathlib import Path

import pandas as pd

from craei.config import load_paths
from craei.exposure import aggregate as agg
from craei.hazards.consolidate import _assign_bucket


def sha_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parquet_variants(df: pd.DataFrame) -> dict[str, str]:
    """Hash variants of the DataFrame content (the exact baseline recipe is
    'content_sha256_of_hash_pandas_object'; try the plausible variants)."""
    out = {}
    for sort_cols in (True, False):
        base = df[sorted(df.columns)] if sort_cols else df
        for sort_rows in (False, True):
            d = base
            if sort_rows:
                d = base.sort_values(list(base.columns)).reset_index(drop=True)
            for use_index in (False, True):
                h = pd.util.hash_pandas_object(d, index=use_index).values
                key = f"cols_sorted={sort_cols},rows_sorted={sort_rows},index={use_index}"
                out[key] = hashlib.sha256(h.tobytes()).hexdigest()
    return out


def main() -> int:
    paths = load_paths()
    outputs_root = Path(paths["outputs_dir"])
    baseline = pd.read_csv(outputs_root / "audit" / "c23b_baseline.csv")
    results = []

    for _, row in baseline.iterrows():
        p = Path(row["path"])
        if not p.exists():
            results.append((row["name"], "FAIL", "file missing"))
            continue
        if row["method"] == "bytes_sha256":
            ok = sha_bytes(p) == row["hash"]
            results.append((row["name"], "PASS" if ok else "FAIL", "bytes on disk"))
        else:
            df = pd.read_parquet(p)
            rows_ok = len(df) == int(row["n_rows_or_bytes"])
            match = [k for k, v in parquet_variants(df).items() if v == row["hash"]]
            if match:
                results.append((row["name"], "PASS", f"content hash ({match[0]})"))
            elif rows_ok:
                results.append((row["name"], "UNRESOLVED", "row count ok, hash recipe not matched"))
            else:
                results.append((row["name"], "FAIL", "row count differs"))

    # Recompute the exposure tables in memory and hash the CSV bytes (no overwrite)
    inputs = agg.load_exposure_inputs()
    plants = inputs["plants"].copy()
    plants["bucket"] = _assign_bucket(plants)
    tables = {
        "exposure_summary": agg.build_exposure_summary(plants, inputs["plant_hazards"]),
        "exposure_aqueduct": agg.build_exposure_aqueduct(plants, inputs["plant_aqueduct"]),
    }
    with tempfile.TemporaryDirectory() as td:
        for name, df in tables.items():
            tmp = Path(td) / f"{name}.csv"
            df.to_csv(tmp, index=False)
            expected = baseline.loc[baseline["name"] == name, "hash"].iloc[0]
            ok = sha_bytes(tmp) == expected
            results.append((f"{name} (recomputed)", "PASS" if ok else "FAIL", "in-memory rebuild"))

    print(f"{'item':32s} {'status':11s} detail")
    for name, status, detail in results:
        print(f"{name:32s} {status:11s} {detail}")
    return 1 if any(s == "FAIL" for _, s, _ in results) else 0


if __name__ == "__main__":
    sys.exit(main())