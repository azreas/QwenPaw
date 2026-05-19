from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class MetricType(StrEnum):
    COUNTER = "counter"
    GAUGE = "gauge"


@dataclass(frozen=True, slots=True)
class MetricSample:
    name: str
    value: float
    metric_type: MetricType
    labels: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TraceEvent:
    """追踪事件，用于关联跨模块的分布式追踪上下文。

    注意：这是轻量事件聚合，不替代完整的 OpenTelemetry。
    高基数字段（user_id, session_id）只存在于事件 payload，
    不作为指标 label 使用。
    """

    event_id: str
    event_type: str
    timestamp: datetime
    request_id: str = ""
    trace_id: str = ""
    tenant_id: str = ""
    agent_id: str = ""
    duration_ms: float | None = None
    status: str = ""
    error_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
