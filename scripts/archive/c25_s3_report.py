"""C25-S3 report (read-only): references to removal candidates and the new test floor."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "outputs" / "audit" / "c25_s3"
CAND_GLOBS = [
    "src/craei/exposure/compound.py",
    "src/craei/audit/*.py",
    "scripts/22_audit*.py",
    "scripts/c23_scope_audit.py",
    "scripts/c22b_regional_assignment.py",
    "scripts/11_compound*.py",
    "scripts/c23b_finish.py",
    "scripts/c23_code_audit.py",
]
SKIP_PARTS = {"__pycache__", "archive", "craei.egg-info"}


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def candidate_files(log: list[str]) -> list[Path]:
    found: list[Path] = []
    for g in CAND_GLOBS:
        hits = sorted(ROOT.glob(g))
        if not hits:
            log.append(f"- NOT FOUND: `{g}`")
        found.extend(hits)
    return found


def scan_files() -> list[Path]:
    files: list[Path] = []
    for top in ("src", "scripts", "tests"):
        for p in (ROOT / top).rglob("*.py"):
            if not SKIP_PARTS & set(p.relative_to(ROOT).parts):
                files.append(p)
    for name in ("CLAUDE.md", "README.md", "pyproject.toml"):
        if (ROOT / name).exists():
            files.append(ROOT / name)
    return sorted(files)


def patterns_for(c: Path) -> list[re.Pattern[str]]:
    if c.relative_to(ROOT).parts[0] == "src":
        parts = list(c.relative_to(ROOT / "src").with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        mod = ".".join(parts)
        pats = [re.escape(mod) + r"\b"]
        if "." in mod:
            parent, last = mod.rsplit(".", 1)
            pats.append(
                r"from " + re.escape(parent) + r" import[^\n]*\b" + re.escape(last) + r"\b"
            )
        return [re.compile(p) for p in pats]
    return [re.compile(r"\b" + re.escape(c.stem) + r"\b")]


def run_pytest(f: Path) -> str:
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(f)]
    r = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=ROOT, check=False,
    )
    out = r.stdout.strip().splitlines()
    return out[-1] if out else "(no output)"


def main() -> None:
    rep: list[str] = ["# C25-S3 report (read-only)", "", "## Candidates found", ""]
    cands = candidate_files(rep)
    rep.extend(f"- `{rel(c)}`" for c in cands)
    cset = set(cands)
    pats = {c: patterns_for(c) for c in cands}
    files = scan_files()
    external: list[str] = []
    ingroup: list[str] = []
    progress: list[str] = []
    test_files: set[Path] = set()
    for f in files:
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines, 1):
            if "PROGRESS.json" in line:
                progress.append(f"- `{rel(f)}:{i}` {line.strip()[:80]}")
        for c in cands:
            if c == f:
                continue
            for i, line in enumerate(lines, 1):
                if any(p.search(line) for p in pats[c]):
                    item = f"- `{rel(c)}` <- `{rel(f)}:{i}` {line.strip()[:80]}"
                    (ingroup if f in cset else external).append(item)
                    if rel(f).startswith("tests/"):
                        test_files.add(f)
    rep += ["", "## External references (block removal until handled)", ""]
    rep += external or ["- none"]
    rep += ["", "## References from inside the removal group", ""]
    rep += ingroup or ["- none"]
    rep += ["", "## PROGRESS.json mentions (non-archive)", ""]
    rep += progress or ["- none"]
    rep += ["", "## Test files that reference a candidate (pytest summary per file)", ""]
    for f in sorted(test_files):
        rep.append(f"- `{rel(f)}`: {run_pytest(f)}")
    if not test_files:
        rep.append("- none")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "report.md"
    path.write_text("\n".join(rep) + "\n", encoding="utf-8")
    print("external refs:", len(external), "| in-group refs:", len(ingroup))
    print("report:", path)


if __name__ == "__main__":
    main()