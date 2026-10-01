"""C24 Action 0: read-only recovery search + fuel-field inspection."""
import pathlib
import re

import pandas as pd
import yaml

ROOT = pathlib.Path(".").resolve()
PAT = re.compile(
    r"null model|\bnulo\b|internal variab|excess over|leave-one-out|"
    r"leave one out|\bLOO\b|SPI vs|SPI/SPEI|53\s?%", re.I)
EXT = {".py", ".md", ".txt", ".csv", ".json", ".yaml", ".yml"}
SKIP = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}

print("== A. text hits (file:line) ==")
found = False
for base in (ROOT, ROOT.parent / "data" / "outputs"):
    if not base.exists():
        continue
    for p in base.rglob("*"):
        if (not p.is_file() or p.suffix.lower() not in EXT
                or p.name == "c24_action0.py"
                or any(s in SKIP or s.endswith(".egg-info") for s in p.parts)
                or p.stat().st_size > 5_000_000):
            continue
        try:
            lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        n = 0
        for i, ln in enumerate(lines, 1):
            if PAT.search(ln):
                print(f"{p.relative_to(base.parent)}:{i}: {ln.strip()[:140]}")
                found = True
                n += 1
                if n >= 3:
                    break
if not found:
    print("not found")

cfg = yaml.safe_load(open("config/paths.local.yaml", encoding="utf-8"))

print("\n== B. plants.parquet ==")
pl = pd.read_parquet(pathlib.Path(cfg["processed_dir"]) / "plants.parquet")
print("columns:", list(pl.columns))
print("countries:", pl["country"].unique().tolist())
bra = pl[pl["country"].isin(["BRA", "Brazil"])]
print((bra.groupby(["fleet", "tech_class"])["capacity_mw"]
       .agg(["count", lambda s: round(s.sum() / 1000, 2)])
       .rename(columns={"<lambda_0>": "GW"})))

print("\n== C. GEM raw (Brazil) ==")
gem = pathlib.Path(cfg["gem_file"])
if not gem.exists():
    cand = list(gem.parent.glob("gem_global*.xlsx"))
    gem = cand[0] if cand else gem
print("file:", gem)
xl = pd.ExcelFile(gem)
print("sheets:", xl.sheet_names)
for sh in xl.sheet_names:
    cols = list(xl.parse(sh, nrows=0).columns)
    if not any("apacity" in str(c) for c in cols):
        continue
    print(f"\n-- sheet '{sh}' columns --\n{cols}")
    df = xl.parse(sh)
    ccol = next(c for c in df.columns if re.search("country", str(c), re.I))
    capc = next(c for c in df.columns if re.search(r"capacity.*mw", str(c), re.I))
    stc = next((c for c in df.columns if str(c).strip().lower() == "status"), None)
    b = df[df[ccol].astype(str).str.contains("Brazil", case=False)].copy()
    b[capc] = pd.to_numeric(b[capc], errors="coerce")
    print("Brazil rows:", len(b))
    cands = [c for c in b.columns
             if re.search(r"fuel|^type|technology|bio", str(c), re.I)
             and b[c].nunique() < 80]
    for c in cands:
        keys = [stc, c] if stc else [c]
        print(f"\n[{c}] GW by {keys}")
        print((b.groupby(keys)[capc].sum() / 1000).round(2).to_string())