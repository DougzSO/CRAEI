"""Skip logic of the sequential pipeline (src/craei/pipeline.py) and the country interface (Phase 7)."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from craei.countries import CountryNotImplemented, load_country
from craei.pipeline import Context, Phase, Pipeline, PipelineError, load_phases

REPO = Path(__file__).resolve().parents[1]

COPY_SCRIPT = (
    "import sys, pathlib\n"
    "src, dst, tag = sys.argv[1], sys.argv[2], sys.argv[3]\n"
    "text = pathlib.Path(src).read_text() if src != '-' else ''\n"
    "if tag == 'const':\n    text = 'constant'\n"
    "pathlib.Path(dst).parent.mkdir(parents=True, exist_ok=True)\n"
    "pathlib.Path(dst).write_text(text)\n"
    "with open('runs.log', 'a') as fh:\n    fh.write(pathlib.Path(sys.argv[0]).name + ' ' + dst + '\\n')\n"
)


def make_repo(tmp_path, const_a=False):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "copy.py").write_text(COPY_SCRIPT)
    (tmp_path / "processed").mkdir()
    (tmp_path / "tables").mkdir()
    (tmp_path / "processed" / "in.txt").write_text("v1")
    (tmp_path / "cfg.yaml").write_text("a: 1\n")
    a_tag = "const" if const_a else "copy"
    phases = [
        Phase("A", [f"copy.py processed/in.txt processed/a.txt {a_tag}"], ["processed:in.txt"], ["processed:a.txt"]),
        Phase("B", ["copy.py processed/a.txt tables/b.txt copy"], ["phase:A"], ["tables:b.txt"]),
        Phase("L", ["copy.py - tables/l.txt copy"], [], ["tables:l.txt"], long=True),
        Phase("H", ["copy.py - tables/h.txt copy"], ["phase:B"], [], always=True),
    ]
    ctx = Context(repo=tmp_path, roots={"processed": tmp_path / "processed", "tables": tmp_path / "tables",
                                        "geo": tmp_path / "geo", "article": tmp_path / "article",
                                        "raw": tmp_path / "raw"},
                  path_keys={}, state_path=tmp_path / "state.json", config_files=[tmp_path / "cfg.yaml"], iso="BRA")
    return phases, ctx


class Runner:
    """Runs the phase scripts like main.py does, but with cwd = the temporary repo, and counts the runs."""

    def __init__(self, p):
        self.p = p

    def __call__(self, ph):
        import subprocess

        for s in ph.scripts:
            parts = s.split()
            r = subprocess.run([sys.executable, str(self.p.ctx.repo / "scripts" / parts[0]), *parts[1:]],
                               cwd=self.p.ctx.repo)
            assert r.returncode == 0


def build(tmp_path, **kw):
    phases, ctx = make_repo(tmp_path, **kw)
    p = Pipeline(phases, ctx, log=lambda *_: None)
    p.runner = Runner(p)
    return p


def runs(tmp_path):
    f = tmp_path / "runs.log"
    return f.read_text().splitlines() if f.exists() else []


def actions(res):
    return dict(res)


def test_first_run_runs_then_skips_and_headline_always_runs(tmp_path):
    p = build(tmp_path)
    r1 = actions(p.run())
    assert r1 == {"A": "RUN", "B": "RUN", "L": "LONG", "H": "RUN"}
    n1 = len(runs(tmp_path))
    r2 = actions(Pipeline(p.phases, p.ctx, runner=p.runner, log=lambda *_: None).run())
    assert r2["A"] == "SKIP" and r2["B"] == "SKIP" and r2["H"] == "RUN"  # always runs, never skipped
    assert len(runs(tmp_path)) == n1 + 1


def test_skip_message_text(tmp_path):
    p = build(tmp_path)
    p.run()
    msgs = []
    p2 = Pipeline(p.phases, p.ctx, runner=p.runner, log=msgs.append)
    p2.run()
    assert "[SKIP] A: saídas presentes, hash igual" in msgs


def test_changed_input_reruns_phase_and_downstream(tmp_path):
    p = build(tmp_path)
    p.run()
    (tmp_path / "processed" / "in.txt").write_text("v2")
    res = actions(Pipeline(p.phases, p.ctx, runner=p.runner, log=lambda *_: None).run())
    assert res["A"] == "RUN" and res["B"] == "RUN"
    assert (tmp_path / "tables" / "b.txt").read_text() == "v2"


def test_downstream_skips_when_upstream_outputs_are_identical(tmp_path):
    p = build(tmp_path, const_a=True)
    p.run()
    (tmp_path / "processed" / "in.txt").write_text("v2")  # A re-runs but writes the same constant
    res = actions(Pipeline(p.phases, p.ctx, runner=p.runner, log=lambda *_: None).run())
    assert res["A"] == "RUN" and res["B"] == "SKIP"


def test_changed_script_and_config_rerun(tmp_path):
    p = build(tmp_path)
    p.run()
    (tmp_path / "scripts" / "copy.py").write_text(COPY_SCRIPT + "\n# changed\n")
    assert actions(Pipeline(p.phases, p.ctx, runner=p.runner, log=lambda *_: None).run())["A"] == "RUN"
    (tmp_path / "cfg.yaml").write_text("a: 2\n")
    assert actions(Pipeline(p.phases, p.ctx, runner=p.runner, log=lambda *_: None).run())["A"] == "RUN"


def test_missing_output_reruns(tmp_path):
    p = build(tmp_path)
    p.run()
    (tmp_path / "processed" / "a.txt").unlink()
    res = actions(Pipeline(p.phases, p.ctx, runner=p.runner, log=lambda *_: None).run())
    assert res["A"] == "RUN"


def test_force_reruns_one_phase(tmp_path):
    p = build(tmp_path)
    p.run()
    n = len(runs(tmp_path))
    res = actions(Pipeline(p.phases, p.ctx, runner=p.runner, log=lambda *_: None).run(force=["A"]))
    assert res["A"] == "RUN" and res["B"] == "SKIP"  # same outputs -> downstream unchanged
    assert len(runs(tmp_path)) == n + 2  # A and the headline phase


def test_dry_run_runs_nothing_and_writes_no_state(tmp_path):
    p = build(tmp_path)
    res = actions(p.run(dry_run=True))
    assert res == {"A": "RUN", "B": "RUN", "L": "LONG", "H": "RUN"}
    assert runs(tmp_path) == [] and not (tmp_path / "state.json").exists()


def test_long_phase_only_when_named(tmp_path):
    p = build(tmp_path)
    assert actions(p.run())["L"] == "LONG" and not (tmp_path / "tables" / "l.txt").exists()
    res = actions(Pipeline(p.phases, p.ctx, runner=p.runner, log=lambda *_: None).run(only=["L"]))
    assert res["L"] == "RUN" and res["A"] == "OFF" and res["H"] == "RUN"
    assert (tmp_path / "tables" / "l.txt").exists()


def test_adopt_records_existing_outputs_without_running(tmp_path):
    p = build(tmp_path)
    p.run()
    (tmp_path / "state.json").unlink()
    (tmp_path / "runs.log").unlink()
    p2 = Pipeline(p.phases, p.ctx, runner=p.runner, log=lambda *_: None)
    res = actions(p2.run(adopt=True))
    assert res["A"] == "ADOPT" and runs(tmp_path) == []
    res = actions(Pipeline(p.phases, p.ctx, runner=p.runner, log=lambda *_: None).run())
    assert res["A"] == "SKIP" and res["B"] == "SKIP"


def test_missing_input_stops_the_run(tmp_path):
    p = build(tmp_path)
    (tmp_path / "processed" / "in.txt").unlink()
    with pytest.raises(PipelineError, match="inputs missing"):
        p.run()


def test_unknown_phase_name_is_an_error(tmp_path):
    p = build(tmp_path)
    with pytest.raises(PipelineError, match="unknown phase"):
        p.run(only=["nope"])


def test_failed_script_stops_and_records_nothing(tmp_path):
    p = build(tmp_path)
    p.phases[0].scripts = ["missing_script.py"]
    with pytest.raises(PipelineError):
        p.run()
    assert not (tmp_path / "state.json").exists() or "A" not in json.loads((tmp_path / "state.json").read_text())["phases"]


def test_rawcov_requires_the_file_in_the_manifest(tmp_path):
    p = build(tmp_path)
    raw = tmp_path / "raw"
    (raw / "climate").mkdir(parents=True)
    f = raw / "climate" / "x_BRA.nc"
    f.write_text("data")
    (raw / "manifest.json").write_text(json.dumps({"k": {"path": str(f), "sha256": "abc"}}))
    items = p.resolve("rawcov:climate/*_{iso}.nc")
    assert items == [("rawcov:x_BRA.nc", "abc")]  # the manifest sha256 is the hash, the file is not read
    g = raw / "climate" / "y_BRA.nc"
    g.write_text("other")
    with pytest.raises(PipelineError, match="outside the manifest"):
        Pipeline(p.phases, p.ctx, log=lambda *_: None).resolve("rawcov:climate/*_{iso}.nc")


def test_phase_input_must_refer_to_an_earlier_phase(tmp_path):
    f = tmp_path / "p.yaml"
    f.write_text("phases:\n  - {name: B, scripts: [b.py], inputs: ['phase:A']}\n  - {name: A, scripts: [a.py]}\n")
    with pytest.raises(PipelineError, match="not an earlier phase"):
        load_phases(f)


def test_repo_pipeline_yaml_is_consistent():
    phases = load_phases(REPO / "config" / "pipeline.yaml")
    names = [p.name for p in phases]
    assert names[-1] == "headlines" and phases[-1].always
    assert {p.name for p in phases if p.long} == {"acquire", "indices", "hydro"}
    for p in phases:
        for s in p.scripts:
            assert (REPO / "scripts" / s.split()[0]).exists(), s


def test_countries_resolve_aliases_and_refuse_unimplemented():
    assert load_country("Brazil")["iso"] == "BRA" and load_country("bra")["iso"] == "BRA"
    for iso in ("PRT", "IND", "Portugal"):
        with pytest.raises(CountryNotImplemented, match="país não implementado"):
            load_country(iso)
    with pytest.raises(ValueError):
        load_country("XXX")


def test_main_refuses_unimplemented_country_before_any_phase(capsys):
    spec = importlib.util.spec_from_file_location("craei_main", REPO / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main(["PRT"]) == 2
    assert "país não implementado: PRT" in capsys.readouterr().err
