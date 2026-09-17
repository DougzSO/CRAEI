from craei.acquire import isimip
from craei.config import load_datasets
from craei.manifest import Manifest


class FakeIsimipClient:
    """Simulates the ISIMIP data API responses used by acquire/isimip.py."""

    def __init__(self, downloaded_path):
        self._downloaded_path = downloaded_path
        self.datasets_calls = []
        self.cutout_calls = []

    def datasets(self, **kwargs):
        self.datasets_calls.append(kwargs)
        return [
            {
                "files": [
                    {"name": "gfdl-esm4_r1i1p1f1_w5e5_historical_tasmax_global_daily_2010_2014.nc",
                     "path": "ISIMIP3b/.../..._2010_2014.nc"},
                ],
            }
        ]

    def cutout_bbox(self, paths, west, east, south, north, poll=None):
        self.cutout_calls.append((paths, west, east, south, north))
        job_url = f"https://files.isimip.org/api/v2/job{len(self.cutout_calls)}"
        return {"status": "queued", "job_url": job_url}

    def get_job(self, job_url, poll=None):
        return {"status": "finished", "job_url": job_url, "file_url": "https://files.isimip.org/cutout.nc"}

    def download(self, file_url, path=None, validate=False, extract=False):
        return str(self._downloaded_path)


def test_build_jobs_has_60_combinations():
    datasets_cfg = load_datasets()
    jobs = isimip.build_jobs(datasets_cfg)
    assert len(jobs) == 60


def test_run_job_registers_manifest_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(isimip, "POLL_INTERVAL_S", 0)
    datasets_cfg = load_datasets()
    job = isimip.build_jobs(datasets_cfg)[0]

    downloaded = tmp_path / "cutout.nc"
    downloaded.write_bytes(b"fake netcdf bytes")
    client = FakeIsimipClient(downloaded)
    manifest = Manifest(tmp_path / "manifest.json")
    raw_dir = tmp_path / "raw"

    entry = isimip.run_job(client, manifest, job, "PRT", datasets_cfg, raw_dir)

    assert entry is not None
    assert manifest.is_intact(f"{job.key_prefix}/PRT")
    assert client.cutout_calls  # bbox was requested


def test_run_job_skips_when_already_intact(tmp_path, monkeypatch):
    monkeypatch.setattr(isimip, "POLL_INTERVAL_S", 0)
    datasets_cfg = load_datasets()
    job = isimip.build_jobs(datasets_cfg)[0]

    downloaded = tmp_path / "cutout.nc"
    downloaded.write_bytes(b"fake netcdf bytes")
    client = FakeIsimipClient(downloaded)
    manifest = Manifest(tmp_path / "manifest.json")
    raw_dir = tmp_path / "raw"

    isimip.run_job(client, manifest, job, "PRT", datasets_cfg, raw_dir)
    client.datasets_calls.clear()

    result = isimip.run_job(client, manifest, job, "PRT", datasets_cfg, raw_dir)

    assert result is None
    assert not client.datasets_calls  # no API call made on skip


def test_submit_then_poll_all_then_finalize(tmp_path, monkeypatch):
    """Simulates the submit-all/poll-all pattern used by scripts/03_pilot_download.py."""
    datasets_cfg = load_datasets()
    jobs = isimip.build_jobs(datasets_cfg)[:2]

    downloaded = tmp_path / "cutout.nc"
    downloaded.write_bytes(b"fake netcdf bytes")
    client = FakeIsimipClient(downloaded)
    manifest = Manifest(tmp_path / "manifest.json")
    raw_dir = tmp_path / "raw"

    pending = [isimip.submit_job(client, manifest, job, "PRT", datasets_cfg) for job in jobs]
    assert all(p["submitted"]["status"] == "queued" for p in pending)

    isimip.poll_all(client, pending, timeout_s=10, interval_s=0)
    assert all(p["submitted"]["status"] == "finished" for p in pending)

    for p in pending:
        entry = isimip.finalize_job(client, manifest, p, raw_dir)
        assert entry is not None
        assert manifest.is_intact(p["key"])
