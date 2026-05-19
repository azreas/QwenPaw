from pathlib import Path

from qwenpaw.backup.production.manifest import build_manifest, verify_manifest


def test_build_and_verify_manifest(tmp_path: Path):
    backup = tmp_path / "backup.zip"
    backup.write_bytes(b"backup-data")

    manifest = build_manifest(backup)

    assert manifest.filename == "backup.zip"
    assert manifest.size_bytes == len(b"backup-data")
    assert verify_manifest(backup, manifest)


def test_verify_manifest_rejects_tampered_file(tmp_path: Path):
    backup = tmp_path / "backup.zip"
    backup.write_bytes(b"backup-data")
    manifest = build_manifest(backup)
    backup.write_bytes(b"changed")

    assert not verify_manifest(backup, manifest)
