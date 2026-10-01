"""C24 finish: fix header false positive, plan commit hash, remaining checks."""
import pathlib
import re

DOCS = pathlib.Path("docs")


def rd(p):
    raw = pathlib.Path(p).read_bytes()
    return raw.decode("utf-8-sig").replace("\r\n", "\n"), ("\r\n" if b"\r\n" in raw else "\n")


def wr(p, t, eol):
    pathlib.Path(p).write_bytes(t.replace("\n", eol).encode("utf-8"))


# 1. header false positive
t, eol = rd(DOCS / "METHODS_SPEC.md")
old = "Anything not yet defined is written as TO BE DEFINED with its open item."
assert t.count(old) == 1, "header phrase not found"
t = t.replace(old, 'Anything not yet defined is marked "to be defined" with its open item (O-id).')
wr(DOCS / "METHODS_SPEC.md", t, eol)
tbd = [l for l in t.splitlines() if "TO BE DEFINED" in l]
assert all(re.search(r"O\d+", l) for l in tbd)
print(f"1. METHODS_SPEC: {len(tbd)} TO BE DEFINED lines, all with O-id")

# 2. plan row
pl, eolp = rd(DOCS / "CRAEI_work_plan_v2.md")
row = "| C24 | pending commit, tag pre-docs-v2 | docs v2 |"
if row in pl:
    pl = pl.replace(row, "| C24 | bd7184d | docs v2 (SCOPE, work plan, status indexes, METHODS_SPEC v2) |")
    wr(DOCS / "CRAEI_work_plan_v2.md", pl, eolp)
    print("2. work plan: C24 row updated")
else:
    print("2. work plan: C24 row not found (already updated?)")

# 3. mojibake
for f in ("SCOPE.md", "CRAEI_work_plan_v2.md", "DECISIONS.md", "LIMITATIONS.md", "METHODS_SPEC.md"):
    n = rd(DOCS / f)[0].count("\u00c2\u00a7")
    print(f"3. mojibake in {f}: {n}")

# 4. who reads PROGRESS.json (archive and c24 scripts excluded)
hits = []
cands = []
for r in ("scripts", "src", "tests", ".github"):
    if pathlib.Path(r).exists():
        cands += [p for p in pathlib.Path(r).rglob("*") if p.is_file()]
cands += [p for p in map(pathlib.Path, ("pyproject.toml", "Makefile", "README.md", "environment.yml"))
          if p.exists()]
for p in cands:
    if "archive" in p.parts or p.name.startswith("c24_") or p.suffix in (".pyc", ".parquet"):
        continue
    if "PROGRESS.json" in p.read_text(encoding="utf-8", errors="ignore"):
        hits.append(str(p))
print("4. files referencing PROGRESS.json:", hits or "none")

cl = pathlib.Path("CLAUDE.md")
if cl.exists():
    c, ec = rd(cl)
    n = c.count("PROGRESS.json")
    if n and not hits:
        wr(cl, c.replace("PROGRESS.json", "docs/CRAEI_work_plan_v2.md"), ec)
        print(f"   CLAUDE.md: {n} pointer(s) updated")
    else:
        print(f"   CLAUDE.md pointers: {n}; updated: no (hits={bool(hits)})")

# 5. METHODS_SPEC coverage: v1 lines absent in v2, per v1 section
v1, _ = rd(DOCS / "archive" / "METHODS_SPEC_v1_pre_rework.md")
v2set = {l.strip() for l in t.splitlines()}
sec, drop, tot = "(top)", {}, {}
for l in v1.splitlines():
    if re.match(r"^#{2,3} ", l):
        sec = l[:70]
    if not l.strip():
        continue
    tot[sec] = tot.get(sec, 0) + 1
    if l.strip() not in v2set:
        drop[sec] = drop.get(sec, 0) + 1
print("5. v1 lines absent from v2, per v1 section:")
for s in tot:
    print(f"   {drop.get(s, 0):4d}/{tot[s]:4d}  {s}")

# 6. D56 row (TO CONFIRM)
d, _ = rd(DOCS / "DECISIONS.md")
m = re.search(r"^\| D56 \|.*$", d, re.M)
print("6. D56:", (m.group(0)[:500] if m else "not found"))