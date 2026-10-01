"""c27b_cleanup.py - housekeeping. Default = REPORT ONLY (nothing is changed).

--apply          execute safe actions A (caches), B (move root *_out.txt),
                 C (zip+delete root *.log; needs --backup-dir)
--empty-dirs     with --apply, also D (remove file-less dirs under raw/climate/isimip3b)
Git-tracked files are never touched. Dead-code / unmentioned-script lists are
report-only. Report written to <data_root>/outputs/audit/c27b/report.md
"""
import argparse
import ast
import datetime as dt
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parents[1]
LINES: list[str] = []


def out(s=""):
    print(s)
    LINES.append(s)


def tracked_set():
    r = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, capture_output=True, check=True)
    return {REPO / n for n in r.stdout.decode("utf-8").split("\0") if n}


def any_tracked(path, tracked):
    return any(t == path or path in t.parents for t in tracked)


def dsize(p):
    try:
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else p.stat().st_size
    except OSError:
        return 0


def fmt(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.1f} {u}"
        n /= 1024


def has_file(p):
    return any(f.is_file() for f in p.rglob("*"))


def topmost_empty(root):
    res = []
    def rec(d):
        for c in sorted(x for x in d.iterdir() if x.is_dir()):
            if not has_file(c):
                res.append(c)
            else:
                rec(c)
    if root.exists():
        rec(root)
    return res


def dead_code():
    src = list((REPO / "src" / "craei").rglob("*.py"))
    scr = list((REPO / "scripts").glob("*.py"))          # non-recursive: skips scripts/archive
    tst = list((REPO / "tests").rglob("*.py"))
    txt = {p: p.read_text(encoding="utf-8", errors="replace") for p in src + scr + tst}
    rows = []
    for p in src:
        if p.name == "__init__.py":
            continue
        try:
            tree = ast.parse(txt[p])
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                continue
            pat = re.compile(rf"\b{re.escape(node.name)}\b")
            own = len(pat.findall(txt[p])) - 1
            prod = [q for q in src + scr if q != p and q.name != "__init__.py" and pat.search(txt[q])]
            tests = [q for q in tst if pat.search(txt[q])]
            init = [q for q in src if q.name == "__init__.py" and pat.search(txt[q])]
            if prod:
                continue
            st = "TEST-ONLY" if tests else ("INTERNAL-ONLY" if own > 0 else "UNREFERENCED")
            rows.append((st, str(p.relative_to(REPO)), node.name, "re-exported" if init else ""))
    return sorted(rows)


def unmentioned_scripts():
    docs = []
    for pat in ("docs/*.md", "CLAUDE.md", "README.md", ".github/workflows/*.yml"):
        docs += list(REPO.glob(pat))
    dtxt = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in docs)
    scr = list((REPO / "scripts").glob("*.py"))
    others = {p: p.read_text(encoding="utf-8", errors="replace")
              for p in scr + list((REPO / "tests").rglob("*.py"))}
    res = []
    for s in scr:
        if s.stem in dtxt:
            continue
        if any(s.stem in t for q, t in others.items() if q != s):
            continue
        res.append(s.name)
    return sorted(res)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--empty-dirs", action="store_true")
    ap.add_argument("--backup-dir", type=Path, default=None)
    ap.add_argument("--data-root", type=Path, default=REPO.parent / "data")
    a = ap.parse_args()
    data = a.data_root
    tracked = tracked_set()
    out(f"c27b cleanup | mode={'APPLY' if a.apply else 'DRY-RUN'} | data_root={data}")

    # A caches
    caches = [p for p in REPO.rglob("__pycache__") if ".git" not in p.parts]
    caches += [REPO / ".pytest_cache", REPO / ".ruff_cache"]
    caches = [p for p in caches if p.exists()]
    out("\n== A. regenerable caches ==")
    for p in caches:
        tr = any_tracked(p, tracked)
        out(f"  {'TRACKED-skip' if tr else 'delete'}  {p.relative_to(REPO)}  {fmt(dsize(p))}")
        if a.apply and not tr:
            shutil.rmtree(p, ignore_errors=True)
    out("  (kept on purpose: src/craei.egg-info - may be needed by the editable install)")

    # B root stdout copies
    outs = sorted(REPO.glob("*_out.txt"))
    dest = data / "outputs" / "audit" / "stdout_root"
    out(f"\n== B. root *_out.txt -> {dest} ==")
    for f in outs:
        tr = f in tracked
        out(f"  {'TRACKED-skip' if tr else 'move'}  {f.name}  {fmt(f.stat().st_size)}")
        if a.apply and not tr:
            dest.mkdir(parents=True, exist_ok=True)
            t = dest / f.name
            if t.exists():
                t = dest / f"{f.stem}_{dt.datetime.now():%H%M%S}{f.suffix}"
            shutil.move(str(f), str(t))

    # C logs
    logs = sorted(REPO.glob("*.log"))
    out("\n== C. root *.log -> zip in --backup-dir, then delete ==")
    tot = sum(f.stat().st_size for f in logs)
    out(f"  {len(logs)} files, {fmt(tot)}, tracked: {sum(f in tracked for f in logs)}")
    if a.apply and logs:
        if a.backup_dir is None:
            out("  SKIPPED: --backup-dir not given")
        elif any(f in tracked for f in logs):
            out("  SKIPPED: some logs are git-tracked (decide git rm manually)")
        else:
            a.backup_dir.mkdir(parents=True, exist_ok=True)
            zp = a.backup_dir / f"repo_root_logs_{dt.datetime.now():%Y%m%d}.zip"
            with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
                for f in logs:
                    z.write(f, f.name)
            with zipfile.ZipFile(zp) as z:
                ok = z.testzip() is None and {i.filename: i.file_size for i in z.infolist()} == \
                    {f.name: f.stat().st_size for f in logs}
            if ok:
                for f in logs:
                    f.unlink()
                out(f"  zipped+verified -> {zp}; originals deleted")
            else:
                out("  ZIP VERIFY FAILED - originals kept")

    # D empty dirs
    iso = data / "raw" / "climate" / "isimip3b"
    ed = topmost_empty(iso)
    out(f"\n== D. file-less dirs under {iso} ==")
    out(f"  {len(ed)} top-level file-less dirs (flag --empty-dirs to remove)")
    for p in ed:
        out(f"  {p.relative_to(iso)}")
        if a.apply and a.empty_dirs:
            shutil.rmtree(p, ignore_errors=True)

    # report-only sizes
    out("\n== sizes (report only) ==")
    cands = [data / "interim", data / "outputs" / "archive", data / "processed" / "archive",
             data / "outputs" / "audit", data / "outputs" / "diagnostics",
             data / "outputs" / "figures", data / "outputs" / "tables",
             REPO / "reports", REPO / "scripts" / "archive", REPO / "docs" / "archive",
             REPO / "data" / "validation"]
    for p in cands:
        if p.exists():
            n = sum(1 for f in p.rglob("*") if f.is_file())
            out(f"  {fmt(dsize(p)):>10}  {n:>5} files  {p}  {'(tracked)' if any_tracked(p, tracked) else ''}")
        else:
            out(f"  {'-':>10}  missing  {p}")

    out("\n== dead-code candidates in src/craei (AST, top-level defs; non-transitive) ==")
    for st, mod, name, ex in dead_code():
        out(f"  {st:<14} {mod}::{name} {ex}")
    out("\n== scripts/*.py not mentioned in docs, tests or other scripts ==")
    for s in unmentioned_scripts():
        out(f"  {s}")

    rp = data / "outputs" / "audit" / "c27b"
    rp.mkdir(parents=True, exist_ok=True)
    (rp / "report.md").write_text("\n".join(LINES), encoding="utf-8")
    out(f"\nreport: {rp / 'report.md'}")


if __name__ == "__main__":
    main()