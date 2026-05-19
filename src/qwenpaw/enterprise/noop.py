from __future__ import annotations

from typing import Any

from .context import RequestContext
from .interfaces import AuthzDecision, RuntimeExtensionBundle


class NoopStorageManager:
    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def healthcheck(self) -> dict[str, Any]:
        return {"status": "disabled"}


class NoopAuthzService:
    async def check_permission(
        self,
        ctx: RequestContext,
        resource: str,
        action: str,
    ) -> AuthzDecision:
        return AuthzDecision(allowed=True, reason="noop")

    async def check_tenant_access(
        self,
        ctx: RequestContext,
        target_tenant_id: str,
    ) -> AuthzDecision:
        return AuthzDecision(allowed=True, reason="noop")


class NoopAuditEventBus:
    def __init__(self) -> None:
        self.events_seen: int = 0

    async def emit(self, event: dict[str, Any]) -> None:
        self.events_seen += 1


class NoopRuntimeExtensionResolver:
    async def resolve(self, ctx: RequestContext) -> RuntimeExtensionBundle:
        return RuntimeExtensionBundle()
