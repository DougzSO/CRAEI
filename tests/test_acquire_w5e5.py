import zipfile

import h5py

from craei.acquire import w5e5
from craei.config import load_datasets
from craei.manifest import Manifest


def _write_fake_netcdf_zip(path, n_steps=3):
    nc_path = path.parent / "_tmp_member.nc"
    with h5py.File(nc_path, "w") as f:
        f.create_dataset("time", data=list(range(n_steps)))
    with zipfile.ZipFile(path, "w") as zf:
        zf.write(nc_path, arcname="tasmax_W5E5v2.0_19790101-20191231.nc")
    nc_path.unlink()


class FakeW5e5Client:
    """`.download` mimics the real `DownloadMixin.download`: writes the file into
    `path` under the URL's basename and returns None (matching the real API,
    which does not return the local path either -- see `w5e5.run_job`).
    """

    def datasets(self, **kwargs):
        name = "tasmax_W5E5v2.0_19790101-20191231.nc"
        return [{"files": [{"name": name, "path": f"ISIMIP3a/.../{name}"}]}]

    def cutout_bbox(self, paths, west, east, south, north, poll=None):
        return {"status": "started", "job_url": "https://files.isimip.org/api/v2/job456"}

    def get_job(self, job_url, poll=None):
        return {
            "status": "finished",
            "job_url": job_url,
            "file_url": "https://files.isimip.org/w5e5_cutout.zip",
        }

    def download(self, file_url, path=None, validate=False, extract=False):
        out_dir = __import__("pathlib").Path(path)
        out_dir.mkdir(parents=True, exist_ok=True)
        zip_path = out_dir / "w5e5_cutout.zip"
        _write_fake_netcdf_zip(zip_path)
        if extract:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(out_dir)


def test_build_jobs_has_3_variables():
    datasets_cfg = load_datasets()
    jobs = w5e5.build_jobs(datasets_cfg)
    assert len(jobs) == 3


def test_run_job_registers_and_skips_on_rerun(tmp_path, monkeypatch):
    from craei.acquire import isimip

    monkeypatch.setattr(isimip, "POLL_INTERVAL_S", 0)
    datasets_cfg = load_datasets()
    job = w5e5.build_jobs(datasets_cfg)[0]

    client = FakeW5e5Client()
    manifest = Manifest(tmp_path / "manifest.json")
    raw_dir = tmp_path / "raw"

    entry = w5e5.run_job(client, manifest, job, "BRA", datasets_cfg, raw_dir)
    assert entry is not None
    assert manifest.is_intact(f"{job.key_prefix}/BRA")

    result = w5e5.run_job(client, manifest, job, "BRA", datasets_cfg, raw_dir)
    assert result is None
