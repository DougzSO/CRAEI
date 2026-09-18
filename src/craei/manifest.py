"""Download manifest: tracks path, SHA-256, size, origin and date per file.

Used by the acquisition scripts to make downloads resumable: a file already
registered with a matching hash and size is skipped.
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

_CHUNK_SIZE = 1 << 20


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Manifest:
    """JSON-backed registry of acquired files, keyed by a logical dataset key."""

    def __init__(self, manifest_path: Path):
        self.manifest_path = Path(manifest_path)
        self.entries: dict[str, dict] = self._load()

    def _load(self) -> dict[str, dict]:
        if self.manifest_path.exists():
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return {}

    def save(self) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(
            json.dumps(self.entries, indent=2, sort_keys=True), encoding="utf-8"
        )

    def is_intact(self, key: str) -> bool:
        """True if `key` is registered, its file exists, and size/hash match."""
        entry = self.entries.get(key)
        if entry is None:
            return False
        path = Path(entry["path"])
        if not path.exists() or path.stat().st_size != entry["size"]:
            return False
        return sha256_file(path) == entry["sha256"]

    def register(
        self,
        key: str,
        path: Path,
        origin: str,
        content_length: int | None = None,
        route: str | None = None,
    ) -> dict:
        """Register `path` under `key`.

        `content_length` (server-reported size) and `route` (how the file
        was acquired) are optional context recorded alongside the local
        SHA-256. `server_checksum` starts "pending": the ISIMIP files API
        that would provide an authoritative checksum was unreachable at
        acquisition time (see COMANDO 11 in docs/DECISIONS.md), so it is
        filled in later by `verify_pending_checksums` when reachable.
        """
        path = Path(path)
        entry = {
            "path": str(path),
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
            "content_length": content_length,
            "route": route,
            "server_checksum": "pending",
            "origin": origin,
            "registered_at": datetime.now(UTC).isoformat(),
        }
        self.entries[key] = entry
        self.save()
        return entry
