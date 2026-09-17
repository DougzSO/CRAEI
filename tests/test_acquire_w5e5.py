from craei.acquire import w5e5
from craei.config import load_datasets
from craei.manifest import Manifest


class FakeW5e5Client:
    def __init__(self, downloaded_path):
        self._downloaded_path = downloaded_path

    def datasets(self, **kwargs):
        name = "tasmax_W5E5v2.0_19790101-20191231.nc"
        return [{"files": [{"name": name, "path": f"ISIMIP3a/.../{name}"}]}]

    def cutout_bbox(self, paths, west, east, south, north, poll=None):
        return {"status": "started", "job_url": "https://files.isimip.org/api/v2/job456"}

    def get_job(self, job_url, poll=None):
        return {"status": "finished", "job_url": job_url, "file_url": "https://files.isimip.org/w5e5_cutout.nc"}

    def download(self, file_url, path=None, validate=False, extract=False):
        return str(self._downloaded_path)


def test_build_jobs_has_3_variables():
    datasets_cfg = load_datasets()
    jobs = w5e5.build_jobs(datasets_cfg)
    assert len(jobs) == 3


def test_run_job_registers_and_skips_on_rerun(tmp_path, monkeypatch):
    from craei.acquire import isimip

    monkeypatch.setattr(isimip, "POLL_INTERVAL_S", 0)
    datasets_cfg = load_datasets()
    job = w5e5.build_jobs(datasets_cfg)[0]

    downloaded = tmp_path / "w5e5_cutout.nc"
    downloaded.write_bytes(b"fake netcdf bytes")
    client = FakeW5e5Client(downloaded)
    manifest = Manifest(tmp_path / "manifest.json")
    raw_dir = tmp_path / "raw"

    entry = w5e5.run_job(client, manifest, job, "BRA", datasets_cfg, raw_dir)
    assert entry is not None
    assert manifest.is_intact(f"{job.key_prefix}/BRA")

    result = w5e5.run_job(client, manifest, job, "BRA", datasets_cfg, raw_dir)
    assert result is None
