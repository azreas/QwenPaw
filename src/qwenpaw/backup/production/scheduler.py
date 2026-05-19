from __future__ import annotations

import logging
import time
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# 默认配置
_DEFAULT_SCHEDULE = "0 3 * * *"
_DEFAULT_RETENTION_DAYS = 90


class RetentionConfig(BaseModel):
    retention_days: int = _DEFAULT_RETENTION_DAYS


class BackupScheduler:
    """备份定时调度配置和保留策略。"""

    def __init__(
        self,
        schedule: str = _DEFAULT_SCHEDULE,
        retention_days: int = _DEFAULT_RETENTION_DAYS,
    ) -> None:
        self.schedule = schedule
        self.retention_days = retention_days
        self.retention = RetentionConfig(retention_days=retention_days)


def cleanup_expired_backups(
    backup_dir: Path,
    retention_days: int = _DEFAULT_RETENTION_DAYS,
) -> int:
    """清理超过保留天数的备份文件。

    只删除 .zip 文件，跳过其他文件。
    返回删除的文件数量。
    """
    if not backup_dir.is_dir():
        return 0
    cutoff = time.time() - retention_days * 86400
    removed = 0
    for f in backup_dir.iterdir():
        if not f.is_file() or f.suffix != ".zip":
            continue
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink(missing_ok=True)
                removed += 1
                logger.info("Expired backup removed: %s", f.name)
        except OSError:
            logger.warning("Failed to check/remove expired backup: %s", f.name)
    return removed
