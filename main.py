"""Run the CRAEI pipeline for one country, phase by phase (Phase 7, docs/PIPELINE.md).

    python main.py BRA                     # every phase except the long ones; completed phases are skipped
    python main.py Brazil --dry-run        # print the plan, run nothing
    python main.py BRA --only w3,w4        # only these phases (long phases included) plus the headline check
    python main.py BRA --force coexposure  # re-run a phase even if its hash is unchanged
    python main.py BRA --adopt             # record the hashes of outputs that already exist (first use)
    python main.py BRA --list              # phases and their state

Completed phase = declared outputs present and the recorded hash (inputs, scripts, configuration) unchanged:
"[SKIP] <phase>: saídas presentes, hash igual". `check_headlines` is always the last phase and never skipped.
Countries that are not implemented (PRT, IND) stop with an explicit error before any phase runs.
"""

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "src"))

from craei.config import CONFIG_DIR, load_paths  # noqa: E402
from craei.countries import CountryNotImplemented, load_country  # noqa: E402
from craei.pipeline import Context, Pipeline, PipelineError, load_phases  # noqa: E402


def build_context(iso: str) -> Context:
    paths = load_paths()
    data_root = Path(paths["data_root"])
    return Context(
        repo=REPO,
        roots={"processed": Path(paths["processed_dir"]), "tables": Path(paths["outputs_tables_dir"]),
               "geo": data_root / "external" / "geo", "article": Path(paths["outputs_dir"]) / "article",
               "raw": Path(paths["raw_dir"])},
        path_keys={k: v for k, v in paths.items() if isinstance(v, str)},
        state_path=Path(paths["interim_dir"]) / f"pipeline_state_{iso}.json",
        config_files=[CONFIG_DIR / "countries" / f"{iso}.yaml", CONFIG_DIR / "params.yaml",
                      CONFIG_DIR / "pipeline.yaml"],
        iso=iso)


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("country", help="ISO code or name (BRA, Brazil)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, run nothing")
    ap.add_argument("--force", action="append", default=[], metavar="PHASE", help="re-run this phase (repeatable)")
    ap.add_argument("--only", help="comma-separated phases to run (long phases included)")
    ap.add_argument("--adopt", action="store_true", help="record the hashes of existing outputs, run nothing")
    ap.add_argument("--list", action="store_true", help="list the phases")
    args = ap.parse_args(argv)
    try:
        country = load_country(args.country)
    except CountryNotImplemented as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2
    phases = load_phases(CONFIG_DIR / "pipeline.yaml")
    pipe = Pipeline(phases, build_context(country["iso"]))
    if args.list:
        for p in phases:
            print(f"{p.name:12s} {'long ' if p.long else '     '}{'always ' if p.always else ''}{p.description}")
        return 0
    only = [n for n in args.only.split(",") if n] if args.only else None
    try:
        pipe.run(only=only, force=args.force, dry_run=args.dry_run, adopt=args.adopt)
    except PipelineError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
