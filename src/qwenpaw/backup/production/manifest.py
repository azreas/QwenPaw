from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel


class BackupManifest(BaseModel):
    filename: str
    size_bytes: int
    sha256: str
    created_at: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(path: Path) -> BackupManifest:
    stat = path.stat()
    return BackupManifest(
        filename=path.name,
        size_bytes=stat.st_size,
        sha256=_sha256(path),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def verify_manifest(path: Path, manifest: BackupManifest) -> bool:
    if not path.is_file():
        return False
    stat = path.stat()
    return (
        path.name == manifest.filename
        and stat.st_size == manifest.size_bytes
        and _sha256(path) == manifest.sha256
    )
