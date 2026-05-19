from pathlib import Path

import pytest

from qwenpaw.backup.production.remote_store import FilesystemRemoteStore


def test_filesystem_remote_store_put_and_get(tmp_path: Path):
    source = tmp_path / "source.zip"
    source.write_bytes(b"data")
    store = FilesystemRemoteStore(tmp_path / "remote")

    stored = store.put(source, "backup/source.zip")
    restored = tmp_path / "restored.zip"
    store.get("backup/source.zip", restored)

    assert stored == tmp_path / "remote" / "backup" / "source.zip"
    assert restored.read_bytes() == b"data"


def test_filesystem_remote_store_rejects_path_escape(tmp_path: Path):
    store = FilesystemRemoteStore(tmp_path / "remote")

    with pytest.raises(ValueError, match="escapes root"):
        store.put(tmp_path / "x.zip", "../escape.zip")


def test_filesystem_remote_store_rejects_get_path_escape(tmp_path: Path):
    store = FilesystemRemoteStore(tmp_path / "remote")

    with pytest.raises(ValueError, match="escapes root"):
        store.get("../../etc/passwd", tmp_path / "out")
