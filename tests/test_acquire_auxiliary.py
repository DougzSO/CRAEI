import json

from craei.acquire import auxiliary
from craei.manifest import Manifest


def test_build_jobs_has_4_sources():
    jobs = auxiliary.build_jobs()
    assert len(jobs) == 4
    assert {j.name for j in jobs} == {"hydrobasins", "natural_earth", "ons_ena", "ren_productivity"}


def test_run_hydrobasins_downloads_and_registers(tmp_path, monkeypatch):
    calls = []

    def fake_download(url, dest):
        calls.append(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"fake zip bytes")
        return dest

    monkeypatch.setattr(auxiliary, "_download", fake_download)
    manifest = Manifest(tmp_path / "manifest.json")

    registered = auxiliary.run_hydrobasins(manifest, tmp_path / "raw")

    assert len(registered) == 3
    assert len(calls) == 3
    assert manifest.is_intact("hydrobasins/BRA")
    assert manifest.is_intact("hydrobasins/IND")
    assert manifest.is_intact("hydrobasins/PRT")


def test_run_hydrobasins_skips_already_intact(tmp_path, monkeypatch):
    call_count = {"n": 0}

    def fake_download(url, dest):
        call_count["n"] += 1
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"fake zip bytes")
        return dest

    monkeypatch.setattr(auxiliary, "_download", fake_download)
    manifest = Manifest(tmp_path / "manifest.json")

    auxiliary.run_hydrobasins(manifest, tmp_path / "raw")
    assert call_count["n"] == 3

    auxiliary.run_hydrobasins(manifest, tmp_path / "raw")
    assert call_count["n"] == 3  # no new downloads on rerun


def test_run_natural_earth_imports_local_file(tmp_path):
    source = tmp_path / "source" / "ne_10m_coastline.shp"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"fake shapefile bytes")
    manifest = Manifest(tmp_path / "manifest.json")

    registered = auxiliary.run_natural_earth(
        manifest, {"natural_earth_coastline": str(source)}, tmp_path / "raw"
    )

    assert len(registered) == 1
    assert manifest.is_intact("natural_earth/coastline")
    assert (tmp_path / "raw" / "boundaries" / "ne_10m_coastline.shp").exists()


def test_run_ons_ena_downloads_csv_resources(tmp_path, monkeypatch):
    fake_package = {
        "result": {
            "resources": [
                {"name": "ENA_Diario_por_Subsistema-2020", "format": "CSV", "url": "https://example.com/2020.csv"},
                {"name": "ENA_Diario_por_Subsistema-2020", "format": "XLSX", "url": "https://example.com/2020.xlsx"},
                {"name": "Dicionario de Dados", "format": "PDF", "url": "https://example.com/dict.pdf"},
            ]
        }
    }

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return fake_package

    def fake_get(url, timeout=None):
        return FakeResponse()

    def fake_download(url, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"fake csv bytes")
        return dest

    monkeypatch.setattr(auxiliary.requests, "get", fake_get)
    monkeypatch.setattr(auxiliary, "_download", fake_download)
    manifest = Manifest(tmp_path / "manifest.json")

    registered = auxiliary.run_ons_ena(manifest, tmp_path / "raw")

    assert len(registered) == 1  # only the CSV resource, not XLSX/PDF
    assert manifest.is_intact("ons_ena/ENA_Diario_por_Subsistema-2020")


def test_run_ren_productivity_skipped_without_local_file(tmp_path):
    manifest = Manifest(tmp_path / "manifest.json")
    result = auxiliary.run_ren_productivity(manifest, {}, tmp_path / "raw")
    assert result is None


def test_import_existing_local_data_copies_gem_and_gadm(tmp_path):
    gem_file = tmp_path / "source" / "gem.xlsx"
    gem_file.parent.mkdir(parents=True)
    gem_file.write_bytes(b"fake xlsx bytes")

    gadm_dir = tmp_path / "source" / "gadm"
    gadm_dir.mkdir()
    (gadm_dir / "gadm41_BRA.gpkg").write_bytes(b"fake gpkg bytes")

    manifest = Manifest(tmp_path / "manifest.json")
    local_paths = {"gem_file": str(gem_file), "gadm_dir": str(gadm_dir)}

    registered = auxiliary.import_existing_local_data(local_paths, manifest, tmp_path / "raw")

    assert len(registered) == 2
    assert manifest.is_intact("local/gem_file/gem.xlsx")
    assert manifest.is_intact("local/gadm_dir/gadm41_BRA.gpkg")


def test_manifest_json_is_valid_after_multiple_registrations(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest = Manifest(manifest_path)
    for i in range(3):
        f = tmp_path / f"f{i}.nc"
        f.write_bytes(f"bytes{i}".encode())
        manifest.register(f"key{i}", f, origin="test")

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(data) == 3
