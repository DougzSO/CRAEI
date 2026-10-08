"""Sequential country pipeline (Phase 7, docs/PIPELINE.md): phase table, input hashing, skip logic.

A phase is complete when all its declared outputs exist AND the state file holds the same hash as the current
one. The hash covers: the declared inputs, the phase's scripts and watched files, and the configuration files
(country YAML, params.yaml, pipeline.yaml). A different hash re-runs the phase. Downstream phases see an
upstream re-run through the hash of its outputs (`phase:<name>` inputs), so they re-run only if the outputs
changed.

Input tokens (`kind:value`):
    processed:F, tables:F, geo:F, article:F   file under that root
    path:KEY                                  file or directory named by `KEY` in config/paths.local.yaml
    raw:GLOB                                  files under raw_dir, hashed directly
    rawcov:GLOB                               files under raw_dir that MUST be listed in the raw manifest; the
                                              manifest sha256 is the hash (no re-reading of the raw data);
                                              a file outside the manifest raises PipelineError
    phase:NAME                                all declared outputs of an earlier phase
`{iso}` in a value is replaced by the country code.
"""

import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml


class PipelineError(Exception):
    """A phase cannot run or a check failed; the run stops here."""


@dataclass
class Phase:
    name: str
    scripts: list
    inputs: list = field(default_factory=list)
    outputs: list = field(default_factory=list)
    watch: list = field(default_factory=list)  # extra files hashed with the scripts (globs relative to scripts/)
    long: bool = False  # runs only when named (--only / --force)
    always: bool = False  # never skipped (check_headlines)
    description: str = ""

    @property
    def deps(self) -> list:
        return [t.split(":", 1)[1] for t in self.inputs if t.startswith("phase:")]


def load_phases(path: Path) -> list[Phase]:
    """Phases of config/pipeline.yaml, validated (unique names, `phase:` inputs refer to earlier phases)."""
    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    phases, seen = [], set()
    for d in raw["phases"]:
        p = Phase(**d)
        if p.name in seen:
            raise PipelineError(f"duplicate phase {p.name}")
        for dep in p.deps:
            if dep not in seen:
                raise PipelineError(f"phase {p.name}: input phase:{dep} is not an earlier phase")
        seen.add(p.name)
        phases.append(p)
    return phases


@dataclass
class Context:
    repo: Path  # scripts live in repo/scripts
    roots: dict  # processed, tables, geo, article, raw -> Path
    path_keys: dict  # name -> str (config/paths.local.yaml)
    state_path: Path
    config_files: list
    iso: str


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm(p) -> str:
    return os.path.normcase(os.path.normpath(str(p)))


class Pipeline:
    def __init__(self, phases, ctx: Context, runner=None, log=print):
        self.phases = phases
        self.by_name = {p.name: p for p in phases}
        self.ctx = ctx
        self.runner = runner or self._subprocess_runner
        self.log = log
        self.state = self._load_state()
        self._manifest = None

    # ---- state -------------------------------------------------------------------------------------
    def _load_state(self) -> dict:
        if self.ctx.state_path.exists():
            return json.loads(self.ctx.state_path.read_text(encoding="utf-8"))
        return {"phases": {}, "filecache": {}}

    def _save_state(self):
        self.ctx.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.ctx.state_path.write_text(json.dumps(self.state, indent=1, sort_keys=True), encoding="utf-8")

    # ---- hashing -----------------------------------------------------------------------------------
    def file_hash(self, path: Path) -> str:
        """sha256 of a file; cached by (size, mtime) in the state file."""
        st = path.stat()
        key = _norm(path)
        hit = self.state["filecache"].get(key)
        if hit and hit[0] == st.st_size and hit[1] == st.st_mtime_ns:
            return hit[2]
        sha = sha256_file(path)
        self.state["filecache"][key] = [st.st_size, st.st_mtime_ns, sha]
        return sha

    def manifest_hashes(self) -> dict:
        """normalized path -> sha256 for every file registered in the raw manifest."""
        if self._manifest is None:
            m = json.loads((self.ctx.roots["raw"] / "manifest.json").read_text(encoding="utf-8"))
            self._manifest = {_norm(v["path"]): v["sha256"] for v in m.values()
                              if isinstance(v, dict) and "path" in v and "sha256" in v}
        return self._manifest

    def _files_under(self, p: Path) -> list[Path]:
        return sorted(f for f in p.rglob("*") if f.is_file()) if p.is_dir() else [p]

    def resolve(self, token: str) -> list[tuple]:
        """[(label, sha or None)] for an input/output token; sha None = missing."""
        kind, _, value = token.partition(":")
        value = value.replace("{iso}", self.ctx.iso)
        if kind in ("processed", "tables", "geo", "article"):
            p = self.ctx.roots[kind] / value
            return [(token, self.file_hash(p) if p.exists() else None)]
        if kind == "path":
            p = Path(self.ctx.path_keys[value])
            if not p.exists():
                return [(token, None)]
            return [(f"{token}/{f.name}", self.file_hash(f)) for f in self._files_under(p)]
        if kind in ("raw", "rawcov"):
            files = sorted(self.ctx.roots["raw"].glob(value))
            if not files:
                return [(token, None)]
            if kind == "raw":
                return [(f"raw:{f.name}", self.file_hash(f)) for f in files]
            cov = self.manifest_hashes()
            out = []
            for f in files:
                if _norm(f) not in cov:
                    raise PipelineError(f"file read outside the manifest: {f} (token {token})")
                out.append((f"rawcov:{f.name}", cov[_norm(f)]))
            return out
        if kind == "phase":
            items = []
            for o in self.by_name[value].outputs:
                items += self.resolve(o)
            return items
        raise PipelineError(f"unknown input token {token!r}")

    def script_files(self, ph: Phase) -> list[Path]:
        scripts = self.ctx.repo / "scripts"
        files = [scripts / shlex.split(s)[0] for s in ph.scripts]
        for pat in ph.watch:
            files += sorted(scripts.glob(pat))
        return files

    def phase_hash(self, ph: Phase) -> tuple[str, list]:
        """(hash, missing input labels)."""
        items, missing = [], []
        for t in ph.inputs:
            for label, sha in self.resolve(t):
                (missing if sha is None else items).append(label if sha is None else (label, sha))
        for f in self.script_files(ph):
            if not f.exists():
                raise PipelineError(f"phase {ph.name}: script missing: {f}")
            items.append((f"script:{f.name}", self.file_hash(f)))
        for f in self.ctx.config_files:
            items.append((f"config:{Path(f).name}", self.file_hash(Path(f))))
        h = hashlib.sha256(json.dumps(sorted(items), sort_keys=True).encode()).hexdigest()
        return h, missing

    def outputs_present(self, ph: Phase) -> bool:
        return all(sha is not None for t in ph.outputs for _, sha in self.resolve(t))

    # ---- execution ---------------------------------------------------------------------------------
    def _subprocess_runner(self, ph: Phase):
        env = dict(os.environ, CRAEI_COUNTRY=self.ctx.iso)
        for s in ph.scripts:
            parts = shlex.split(s)
            cmd = [sys.executable, str(self.ctx.repo / "scripts" / parts[0]), *parts[1:]]
            self.log(f"[RUN ] {ph.name}: {' '.join(parts)}")
            r = subprocess.run(cmd, cwd=self.ctx.repo, env=env)
            if r.returncode != 0:
                raise PipelineError(f"phase {ph.name}: {parts[0]} failed (exit {r.returncode})")

    def _record(self, ph: Phase, h: str):
        outs = {label: sha for t in ph.outputs for label, sha in self.resolve(t)}
        self.state["phases"][ph.name] = {"hash": h, "outputs": outs, "recorded": time.strftime("%Y-%m-%d %H:%M:%S")}
        self._save_state()

    def run(self, only=None, force=(), dry_run=False, adopt=False) -> list[tuple]:
        """Walk the phases in order; returns [(phase, action)], action in RUN / SKIP / LONG / OFF / ADOPT / BLOCKED.

        Default run = every phase that is not `long`. `only` limits the run to the named phases (long phases
        included); `always` phases (the headline check) run in every case. `force` re-runs the named phases.
        `adopt` records the current hashes of phases (long ones included) whose outputs already exist, without
        running anything (first use on an existing data tree).
        """
        names = set(self.by_name)
        for n in list(only or []) + list(force):
            if n not in names:
                raise PipelineError(f"unknown phase {n!r}; phases: {', '.join(self.by_name)}")
        force = set(force)
        dirty, result = set(), []
        for ph in self.phases:
            selected = adopt or ph.always or ph.name in force or (ph.name in only if only else not ph.long)
            if not selected:
                what = "LONG" if ph.long and not only else "OFF"
                if what == "LONG":
                    h, missing = self.phase_hash(ph)
                    entry = self.state["phases"].get(ph.name)
                    ok = self.outputs_present(ph) and entry is not None and entry["hash"] == h and not missing
                    self.log(f"[LONG] {ph.name}: long phase not run; "
                             + ("saídas presentes, hash igual" if ok else "STALE or never recorded")
                             + " (name it with --only or --force to run)")
                else:
                    self.log(f"[OFF ] {ph.name}: not selected")
                result.append((ph.name, what))
                continue
            h, missing = self.phase_hash(ph)
            entry = self.state["phases"].get(ph.name)
            present = self.outputs_present(ph)
            upstream = dry_run and any(d in dirty for d in ph.deps)  # real runs see upstream changes through the hashes
            if adopt:
                if present and not missing:
                    self.log(f"[ADOPT] {ph.name}: saídas presentes, hash registrado")
                    if not dry_run:
                        self._record(ph, h)
                    result.append((ph.name, "ADOPT"))
                else:
                    self.log(f"[WARN] {ph.name}: not adopted (outputs or inputs missing: {missing[:2]})")
                    result.append((ph.name, "BLOCKED"))
                continue
            if ph.always:
                reason = "always runs"
            elif ph.name in force:
                reason = "--force"
            elif upstream:
                reason = "upstream phase will run"
            elif not present:
                reason = "outputs missing"
            elif entry is None:
                reason = "no recorded hash"
            elif entry["hash"] != h:
                reason = "hash changed"
            else:
                self.log(f"[SKIP] {ph.name}: saídas presentes, hash igual")
                result.append((ph.name, "SKIP"))
                continue
            if missing and not (upstream or dry_run):
                raise PipelineError(f"phase {ph.name}: inputs missing: {missing[:4]}")
            if missing and not upstream:
                self.log(f"[BLOCKED] {ph.name}: inputs missing: {missing[:4]}")
                result.append((ph.name, "BLOCKED"))
                continue
            if dry_run:
                self.log(f"[DRY ] {ph.name}: would run ({reason})")
                dirty.add(ph.name)
                result.append((ph.name, "RUN"))
                continue
            self.runner(ph)
            if not self.outputs_present(ph):
                raise PipelineError(f"phase {ph.name}: declared outputs missing after the run")
            h2, _ = self.phase_hash(ph)
            self._record(ph, h2)
            dirty.add(ph.name)
            result.append((ph.name, "RUN"))
        if not dry_run:
            self._save_state()
        return result
