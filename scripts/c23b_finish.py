"""C23-B finish: archive old outputs (Bloco 5) and copy v1 docs (Bloco 6).

Dry-run by default. Use --apply to execute. Nothing is ever deleted: files are
moved/copied and verified by sha256.
"""

import argparse
import datetime
import hashlib
import shutil
from pathlib import Path

from craei.config import load_paths

REPO = Path(__file__).resolve().parents[1]
KEEP_DIAGNOSTICS = {"c22b_plant_region.parquet"}
TABLES_TO_ARCHIVE = set()  # compound tables stay until C25 (read by c23_scope_audit.py and src/craei/audit)
# exposure_si.csv is rewritten by the active 10_exposure.py, so it stays in tables/.
DOCS = ["DECISIONS.md", "LIMITATIONS.md", "METHODS_SPEC.md"]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def files_of(path: Path) -> list[Path]:
    return [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    out = Path(load_paths()["outputs_dir"])
    archive = out / "archive"
    plan: list[tuple[Path, Path]] = []

    diag = out / "diagnostics"
    if diag.exists():
        for c in sorted(diag.iterdir()):
            if c.name not in KEEP_DIAGNOSTICS:
                plan.append((c, archive / "diagnostics" / c.name))
    audit = out / "audit"
    if audit.exists():
        for c in sorted(audit.iterdir()):
            if not c.name.startswith("c23"):
                plan.append((c, archive / "audit" / c.name))
    tables = out / "tables"
    for name in sorted(TABLES_TO_ARCHIVE):
        if (tables / name).exists():
            plan.append((tables / name, archive / "tables" / name))

    print(f"MODE: {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"\n[Bloco 5] outputs to archive ({len(plan)} items):")
    for src, dst in plan:
        n = len(files_of(src))
        print(f"  {src.relative_to(out)}  ->  archive/{dst.relative_to(archive)}  ({n} file(s))")
    print("\nStays in tables/:", sorted(p.name for p in tables.iterdir() if p.name not in TABLES_TO_ARCHIVE))
    print("Stays in diagnostics/:", sorted(KEEP_DIAGNOSTICS))

    docs_plan = [
        (REPO / "docs" / d, REPO / "docs" / "archive" / d.replace(".md", "_v1_pre_rework.md"))
        for d in DOCS
    ]
    print("\n[Bloco 6] docs to COPY (originals stay):")
    for src, dst in docs_plan:
        print(f"  {src.name}  ->  docs/archive/{dst.name}  (exists={src.exists()})")

    if not args.apply:
        print("\nDry-run only. Re-run with --apply to execute.")
        return

    log = [f"\n## C23-B finish ({datetime.datetime.now():%Y-%m-%d %H:%M})\n",
           "### Outputs moved to data/outputs/archive/ (sha256 verified)\n"]
    for src, dst in plan:
        before = {p.relative_to(src) if src.is_dir() else Path(p.name): sha(p) for p in files_of(src)}
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        after = {p.relative_to(dst) if dst.is_dir() else Path(p.name): sha(p) for p in files_of(dst)}
        status = "OK" if before == after else "MISMATCH"
        print(f"  moved {src.name}: {status}")
        log.append(f"- `{src.relative_to(out)}` -> `archive/{dst.relative_to(archive)}` "
                   f"({len(before)} file(s), sha256 {status})\n")

    log.append("\n### Docs copied to docs/archive/ (originals kept until C24)\n")
    (REPO / "docs" / "archive").mkdir(exist_ok=True)
    for src, dst in docs_plan:
        shutil.copy2(src, dst)
        status = "OK" if sha(src) == sha(dst) else "MISMATCH"
        print(f"  copied {src.name}: {status}")
        log.append(f"- `docs/{src.name}` -> `docs/archive/{dst.name}` (sha256 {status})\n")

    log.append("\n### Pending\n- C24: rewrite docs (SCOPE, METHODS_SPEC, DECISIONS, LIMITATIONS, work plan v2).\n"
               "- C25: src/ cleanup (dead code, country/scope branches, lint).\n"
               "- Kept in doubt (review in C25): 22_audit.py, audit_tx_tn_and_pet_truncation.py, "
               "c21_2_fix_emdat.py, c22b_regional_assignment.py.\n"
               "- PROGRESS.json not edited here; superseded by CRAEI_work_plan_v2.\n")
    with (REPO / "docs" / "REORG.md").open("a", encoding="utf-8") as f:
        f.writelines(log)
    print("\nAppended to docs/REORG.md")


if __name__ == "__main__":
    main()
