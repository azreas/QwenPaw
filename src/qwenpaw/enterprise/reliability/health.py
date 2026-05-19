"""健康检查服务 - 聚合所有运行时组件的健康状态。"""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from typing import Any

from qwenpaw.constant import BACKUP_DIR, WORKING_DIR

from .models import ComponentHealth, HealthStatus, ReadinessReport

logger = logging.getLogger(__name__)


class HealthService:
    """运行时健康检查服务。

    聚合 storage、audit、observability、quota、runtime extensions、
    磁盘空间等状态，提供统一的 readiness 报告。
    """

    def __init__(
        self,
        *,
        storage: Any = None,
        audit: Any = None,
        observability: Any = None,
        quota: Any = None,
        extensions: Any = None,
        working_dir: Path | None = None,
    ) -> None:
        self._storage = storage
        self._audit = audit
        self._observability = observability
        self._quota = quota
        self._extensions = extensions
        self._working_dir = working_dir or WORKING_DIR

    async def readiness(self) -> ReadinessReport:
        """生成完整的就绪状态报告。

        Returns:
            ReadinessReport 包含所有组件的健康状态
        """
        return ReadinessReport(
            components=[
                await self._check_storage(),
                self._check_component("audit", self._audit),
                self._check_component("observability", self._observability),
                await self._check_quota_service(self._quota),
                self._check_component("runtime_extensions", self._extensions),
                self._check_disk_space(),
                self._check_backup_dir(),
            ]
        )

    async def _check_storage(self) -> ComponentHealth:
        """检查存储服务健康状态。"""
        if self._storage is None:
            return ComponentHealth("storage", HealthStatus.DEGRADED, message="not configured")

        started = time.perf_counter()
        try:
            health = await self._storage.healthcheck()
            status_value = health.get("status", "")
            # StorageManager 返回 status: "ok" | "error" | "disabled"
            if status_value == "ok":
                status = HealthStatus.OK
            elif status_value == "disabled":
                status = HealthStatus.DEGRADED
            else:  # error 或其他值
                status = HealthStatus.DOWN
            return ComponentHealth(
                "storage",
                status,
                message=health.get("message", ""),
                details={"backend": health.get("backend", "")},
                latency_ms=(time.perf_counter() - started) * 1000,
            )
        except Exception as exc:
            logger.error("Storage health check failed: %s", exc)
            return ComponentHealth(
                "storage",
                HealthStatus.DOWN,
                message="Storage health check failed",
                latency_ms=(time.perf_counter() - started) * 1000,
            )

    @staticmethod
    async def _check_quota_service(quota: Any) -> ComponentHealth:
        """检查 quota 服务及其 Redis 后端状态。"""
        if quota is None:
            return ComponentHealth("quota", HealthStatus.DEGRADED, message="not configured")

        # 如果有 Redis store，尝试健康检查
        store = getattr(quota, "_store", None)
        if store is not None and hasattr(store, "_client"):
            try:
                # 检查 Redis 连接
                await store._client.ping()
                return ComponentHealth("quota", HealthStatus.OK, details={"backend": "redis"})
            except Exception as exc:
                logger.error("Quota Redis health check failed: %s", exc)
                return ComponentHealth(
                    "quota",
                    HealthStatus.DOWN,
                    message="Redis backend unavailable",
                    details={"backend": "redis"},
                )

        # 内存 store，直接 OK
        return ComponentHealth("quota", HealthStatus.OK, details={"backend": "memory"})

    @staticmethod
    def _check_component(name: str, component: Any) -> ComponentHealth:
        """检查可选组件是否已配置。

        None = not configured = DEGRADED
        已配置 = OK（不进行深度健康检查，避免性能影响）
        """
        if component is None:
            return ComponentHealth(name, HealthStatus.DEGRADED, message="not configured")
        return ComponentHealth(name, HealthStatus.OK)

    def _check_disk_space(self) -> ComponentHealth:
        """检查工作目录所在磁盘的可用空间。

        剩余空间 < 5% 时标记为 DEGRADED。
        """
        try:
            usage = shutil.disk_usage(self._working_dir)
            free_ratio = usage.free / usage.total if usage.total else 0
            status = HealthStatus.OK if free_ratio >= 0.05 else HealthStatus.DEGRADED
            return ComponentHealth(
                "disk",
                status,
                details={"free_ratio": round(free_ratio, 4)},
            )
        except Exception as exc:
            logger.error("Disk space check failed: %s", exc)
            return ComponentHealth(
                "disk",
                HealthStatus.DEGRADED,
                message="Disk space check unavailable",
            )

    @staticmethod
    def _check_backup_dir() -> ComponentHealth:
        """检查备份目录是否可写。"""
        try:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            probe = BACKUP_DIR / ".healthcheck"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return ComponentHealth("backup_dir", HealthStatus.OK)
        except Exception as exc:
            logger.error("Backup dir health check failed: %s", exc)
            return ComponentHealth(
                "backup_dir",
                HealthStatus.DEGRADED,
                message="Backup dir health check unavailable",
            )
