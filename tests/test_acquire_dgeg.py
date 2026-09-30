import pandas as pd

from craei.acquire import dgeg
from craei.manifest import Manifest


def test_run_builds_clean_monthly_table_without_network(tmp_path, monkeypatch):
    monkeypatch.setattr(dgeg, "_download", lambda url, dest: dest.write_bytes(b""))
    monkeypatch.setattr(
        dgeg, "_extract_gross_hydro_row", lambda path: [float(i) for i in range(1, 13)]
    )

    manifest = Manifest(tmp_path / "manifest.json")
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"

    entry = dgeg.run(manifest, raw_dir, processed_dir)
    assert entry is not None
    assert manifest.is_intact("dgeg_hydro_generation")

    df = pd.read_parquet(processed_dir / "dgeg_hydro_generation.parquet")
    assert len(df) == 12 * len(dgeg.DGEG_XLS_URLS)
    assert set(df["year"]) == set(dgeg.DGEG_XLS_URLS)
    assert df["date"].is_monotonic_increasing
    assert df["date"].is_unique

    # Rerun is a no-op once registered.
    result = dgeg.run(manifest, raw_dir, processed_dir)
    assert result is None


def test_run_does_not_redownload_existing_raw_files(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(dgeg, "_download", lambda url, dest: calls.append(dest))
    monkeypatch.setattr(
        dgeg, "_extract_gross_hydro_row", lambda path: [1.0] * 12
    )

    manifest = Manifest(tmp_path / "manifest.json")
    raw_dir = tmp_path / "raw"
    (raw_dir / "validation" / "dgeg").mkdir(parents=True)
    for year in dgeg.DGEG_XLS_URLS:
        (raw_dir / "validation" / "dgeg" / f"dgeg_{year}.xls").write_bytes(b"")

    dgeg.run(manifest, raw_dir, tmp_path / "processed")
    assert calls == []


def test_variable_label_documents_it_as_auxiliary_not_iph():
    # Explicit guard against ever conflating DGEG generation with REN's IPH
    # (author's instruction: DGEG is an auxiliary check only, never IPH).
    assert "auxiliary" in dgeg.VARIABLE.lower()
    assert "not iph" in dgeg.VARIABLE.lower()
