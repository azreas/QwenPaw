"""可靠性数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class HealthStatus(StrEnum):
    """健康状态。"""

    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass(frozen=True, slots=True)
class ComponentHealth:
    """单个组件的健康状态。"""

    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    """就绪状态报告，聚合所有组件状态。"""

    components: list[ComponentHealth]
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def ready(self) -> bool:
        """是否可服务。

        DOWN = 不可服务（核心依赖故障）
        DEGRADED = 可服务（可选组件未启用或降级运行）
        OK = 所有组件正常
        """
        return not any(component.status is HealthStatus.DOWN for component in self.components)

    @property
    def status(self) -> HealthStatus:
        """整体健康状态。"""
        if any(component.status is HealthStatus.DOWN for component in self.components):
            return HealthStatus.DOWN
        if any(component.status is HealthStatus.DEGRADED for component in self.components):
            return HealthStatus.DEGRADED
        return HealthStatus.OK

    def as_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "ready": self.ready,
            "status": self.status.value,
            "checked_at": self.checked_at.isoformat(),
            "components": [
                {
                    "name": component.name,
                    "status": component.status.value,
                    "message": component.message,
                    "latency_ms": component.latency_ms,
                    "details": component.details,
                }
                for component in self.components
            ],
        }


@dataclass(frozen=True, slots=True)
class DeadLetterMessage:
    """死信消息 - 记录失败任务以便重试。"""

    id: str
    source: str
    payload: dict[str, Any]
    error: str
    attempts: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
