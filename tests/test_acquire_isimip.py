import time
from pathlib import Path

import h5py
import pytest

from craei.acquire import isimip
from craei.config import load_datasets
from craei.manifest import Manifest


def _write_fake_netcdf(path, n_steps=3):
    with h5py.File(path, "w") as f:
        f.create_dataset("time", data=list(range(n_steps)))
    return path.read_bytes()


class _FakeStreamResponse:
    """Minimal stand-in for `requests.get(..., stream=True)`'s context-manager result."""

    def __init__(self, body: bytes, chunks: list[bytes] | None = None):
        self._chunks = chunks if chunks is not None else [body]
        self.headers = {"Content-Length": str(len(body))}

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        yield from self._chunks

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


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


def test_validate_raw_netcdf_accepts_valid_file(tmp_path):
    path = tmp_path / "valid.nc"
    _write_fake_netcdf(path)
    isimip._validate_raw_netcdf(path)  # must not raise


def test_validate_raw_netcdf_rejects_truncated_file(tmp_path):
    path = tmp_path / "truncated.nc"
    body = _write_fake_netcdf(path)
    path.write_bytes(body[: len(body) // 2])  # corrupt after writing a valid copy

    with pytest.raises(OSError):
        isimip._validate_raw_netcdf(path)


def test_download_global_file_stages_on_ssd_then_moves_to_cache(tmp_path, monkeypatch):
    """COMANDO 12 rework, item 2: the live write goes to staging_dir; cache_dir only
    ever receives the finished, validated file via one move — never a partial."""
    src = tmp_path / "src.nc"
    body = _write_fake_netcdf(src)

    staging_dir = tmp_path / "staging"
    cache_dir = tmp_path / "cache"
    repo_path = "ISIMIP3b/some/global/file.nc"

    def fake_head(url, timeout=30, allow_redirects=True):
        class R:
            headers = {"Content-Length": str(len(body)), "Accept-Ranges": "bytes"}

            def raise_for_status(self):
                pass

        return R()

    seen_during_download = {}

    def fake_get(url, headers=None, stream=True, timeout=120):
        # While the "network" response is being iterated, the partial file
        # must live under staging_dir, never under cache_dir.
        seen_during_download["staging_part_exists_mid_download"] = True
        return _FakeStreamResponse(body, chunks=[body[:5], body[5:]])

    monkeypatch.setattr(isimip.requests, "head", fake_head)
    monkeypatch.setattr(isimip.requests, "get", fake_get)

    result = isimip.download_global_file(cache_dir, repo_path, staging_dir=staging_dir)

    assert result == cache_dir / repo_path
    assert (cache_dir / repo_path).exists()
    assert (cache_dir / repo_path).read_bytes() == body
    assert not (staging_dir / (Path(repo_path).name + ".part")).exists()
    assert not list(staging_dir.rglob("*.part"))  # no leftover partials on the SSD


def test_download_global_file_deletes_file_that_fails_h5py_validation(tmp_path, monkeypatch):
    bad_body = b"not an hdf5 file at all"
    cache_dir = tmp_path / "cache"
    repo_path = "ISIMIP3b/bad/file.nc"

    def fake_head(url, timeout=30, allow_redirects=True):
        class R:
            headers = {"Content-Length": str(len(bad_body))}

            def raise_for_status(self):
                pass

        return R()

    def fake_get(url, headers=None, stream=True, timeout=120):
        return _FakeStreamResponse(bad_body)

    monkeypatch.setattr(isimip.requests, "head", fake_head)
    monkeypatch.setattr(isimip.requests, "get", fake_get)

    with pytest.raises(OSError, match="h5py validation"):
        isimip.download_global_file(cache_dir, repo_path)

    assert not (cache_dir / repo_path).exists()
    assert not list(cache_dir.rglob("*.part"))


def test_stall_watchdog_triggers_after_no_growth(tmp_path, monkeypatch):
    """COMANDO 12 rework, item 3: a download whose partial file never grows past
    the first chunk is aborted (not left hanging) after WATCHDOG_STALL_S."""
    monkeypatch.setattr(isimip, "WATCHDOG_POLL_S", 0.02)
    monkeypatch.setattr(isimip, "WATCHDOG_STALL_S", 0.08)
    monkeypatch.setattr(isimip, "WATCHDOG_MAX_RESTARTS", 1)

    body = b"x" * 64
    cache_dir = tmp_path / "cache"
    repo_path = "ISIMIP3b/stalled/file.nc"

    def fake_head(url, timeout=30, allow_redirects=True):
        class R:
            headers = {"Content-Length": str(len(body))}

            def raise_for_status(self):
                pass

        return R()

    def stalled_chunks():
        yield body[:8]
        time.sleep(1.0)  # never reached before the watchdog fires
        yield body[8:]

    def fake_get(url, headers=None, stream=True, timeout=120):
        return _FakeStreamResponse(body, chunks=stalled_chunks())

    monkeypatch.setattr(isimip.requests, "head", fake_head)
    monkeypatch.setattr(isimip.requests, "get", fake_get)

    with pytest.raises((TimeoutError, OSError)):
        isimip.download_global_file(cache_dir, repo_path)
