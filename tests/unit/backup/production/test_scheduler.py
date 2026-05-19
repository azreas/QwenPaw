from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from qwenpaw.backup.production.scheduler import (
    BackupScheduler,
    RetentionConfig,
    cleanup_expired_backups,
)


@pytest.fixture
def scheduler():
    return BackupScheduler()


def test_scheduler_default_config(scheduler: BackupScheduler):
    assert scheduler.schedule == "0 3 * * *"
    assert scheduler.retention_days == 90


def test_retention_config_defaults():
    cfg = RetentionConfig()
    assert cfg.retention_days == 90


def test_retention_config_custom():
    cfg = RetentionConfig(retention_days=30)
    assert cfg.retention_days == 30


def test_cleanup_expired_backups_removes_old(tmp_path: Path):
    import time

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    old = backup_dir / "old-backup.zip"
    old.write_bytes(b"old")
    # 修改 mtime 为 100 天前
    old_age = time.time() - 100 * 86400
    import os

    os.utime(old, (old_age, old_age))

    recent = backup_dir / "recent-backup.zip"
    recent.write_bytes(b"recent")

    removed = cleanup_expired_backups(backup_dir, retention_days=90)
    assert removed == 1
    assert not old.exists()
    assert recent.exists()


def test_cleanup_expired_backups_skips_non_zip(tmp_path: Path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    txt = backup_dir / "notes.txt"
    txt.write_text("keep")

    removed = cleanup_expired_backups(backup_dir, retention_days=90)
    assert removed == 0
    assert txt.exists()


def test_cleanup_expired_backups_no_dir(tmp_path: Path):
    removed = cleanup_expired_backups(tmp_path / "nonexistent", retention_days=90)
    assert removed == 0
