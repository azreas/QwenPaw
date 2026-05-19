from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class QuotaDimension(StrEnum):
    HTTP_REQUEST = "http.request"
    LLM_REQUEST = "llm.request"
    LLM_CONCURRENCY = "llm.concurrency"
    LLM_TOKEN = "llm.token"
    TOOL_CALL = "tool.call"
    MCP_CALL = "mcp.call"
    FILE_WRITE = "file.write"


class QuotaWindow(StrEnum):
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    CONCURRENT = "concurrent"

    @property
    def ttl_seconds(self) -> int:
        return {
            QuotaWindow.MINUTE: 60,
            QuotaWindow.HOUR: 3600,
            QuotaWindow.DAY: 86400,
            QuotaWindow.CONCURRENT: 300,
        }[self]


@dataclass(frozen=True, slots=True)
class QuotaLimit:
    dimension: QuotaDimension
    window: QuotaWindow
    max_value: int
    tenant_id: str = "*"
    resource: str = "*"
    metadata: dict[str, Any] = field(default_factory=dict)

    def counter_key(self, bucket: str) -> str:
        return (
            "quota:"
            f"{self.tenant_id}:{self.dimension.value}:"
            f"{self.resource}:{self.window.value}:{bucket}"
        )


@dataclass(frozen=True, slots=True)
class QuotaUsage:
    limit: QuotaLimit
    current_value: int
    requested_value: int = 1

    @property
    def projected_value(self) -> int:
        return self.current_value + self.requested_value

    @property
    def exceeded(self) -> bool:
        return self.projected_value > self.limit.max_value
