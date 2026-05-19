from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .context import RequestContext


@dataclass(frozen=True, slots=True)
class AuthzDecision:
    allowed: bool
    reason: str = ""
    matched_roles: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ToolPolicyPatch:
    disable_tools: frozenset[str] = frozenset()
    allow_tools: frozenset[str] = frozenset()
    deny_tools: frozenset[str] = frozenset()

    def merge(self, other: ToolPolicyPatch) -> ToolPolicyPatch:
        """合并两个 patch，各字段取并集。"""
        return ToolPolicyPatch(
            disable_tools=self.disable_tools | other.disable_tools,
            allow_tools=self.allow_tools | other.allow_tools,
            deny_tools=self.deny_tools | other.deny_tools,
        )

    def effective_allowed(self, all_tools: set[str]) -> set[str]:
        """从 all_tools 中计算实际允许的工具集。

        规则：
        1. 若 allow_tools 非空，候选集为 allow_tools；否则为 all_tools。
        2. 从候选集中移除 disable_tools 中的工具。
        3. 再移除 deny_tools 中的工具（deny 优先级最高）。
        """
        candidates = (
            set(self.allow_tools) if self.allow_tools else set(all_tools)
        )
        candidates -= set(self.disable_tools)
        candidates -= set(self.deny_tools)
        return candidates


@dataclass(frozen=True, slots=True)
class RuntimeExtensionBundle:
    mcp_clients: list[Any] = field(default_factory=list)
    tool_policy: ToolPolicyPatch = field(default_factory=ToolPolicyPatch)
    metadata: dict[str, Any] = field(default_factory=dict)


class StorageManagerProtocol(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def healthcheck(self) -> dict[str, Any]: ...


class AuthzServiceProtocol(Protocol):
    async def check_permission(
        self,
        ctx: RequestContext,
        resource: str,
        action: str,
    ) -> AuthzDecision: ...

    async def check_tenant_access(
        self,
        ctx: RequestContext,
        target_tenant_id: str,
    ) -> AuthzDecision: ...


class AuditEventBusProtocol(Protocol):
    async def emit(self, event: dict[str, Any]) -> None: ...


class RuntimeExtensionResolverProtocol(Protocol):
    async def resolve(self, ctx: RequestContext) -> RuntimeExtensionBundle: ...


class ObservabilityServiceProtocol(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...


class PolicyServiceProtocol(Protocol):
    async def evaluate(
        self,
        ctx: RequestContext,
        action: Any,
        resource: str,
    ) -> Any: ...


class QuotaServiceProtocol(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...


class HealthServiceProtocol(Protocol):
    async def readiness(self) -> Any: ...
