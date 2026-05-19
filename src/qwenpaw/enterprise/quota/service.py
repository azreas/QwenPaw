from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from qwenpaw.enterprise.context import RequestContext
from qwenpaw.enterprise.policy.models import PolicyDecision, PolicyEffect

from .models import QuotaDimension, QuotaLimit, QuotaUsage, QuotaWindow
from .store import QuotaCounterStoreProtocol, QuotaLease


@dataclass(slots=True)
class QuotaAcquireResult:
    acquired: bool
    decision: PolicyDecision
    release: object


class QuotaService:
    def __init__(
        self,
        *,
        store: QuotaCounterStoreProtocol,
        limits: Sequence[QuotaLimit],
    ) -> None:
        self._store = store
        self._limits = tuple(limits)

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        await self._store.close()

    async def consume(
        self,
        ctx: RequestContext,
        dimension: QuotaDimension,
        *,
        resource: str = "*",
        amount: int = 1,
    ) -> PolicyDecision:
        limit = self._find_limit(ctx, dimension, resource)
        if limit is None:
            return PolicyDecision.allow("quota not configured")
        key = limit.counter_key(self._bucket(limit.window))
        current = await self._store.increment(
            key,
            amount=amount,
            ttl_seconds=limit.window.ttl_seconds,
        )
        usage = QuotaUsage(limit=limit, current_value=current - amount, requested_value=amount)
        metadata = self._metadata(usage, current)
        if current > limit.max_value:
            return PolicyDecision(
                allowed=False,
                effect=PolicyEffect.DENY,
                reason="quota exceeded",
                metadata=metadata,
            )
        return PolicyDecision(
            allowed=True,
            effect=PolicyEffect.ALLOW,
            reason="quota allowed",
            metadata=metadata,
        )

    async def acquire(
        self,
        ctx: RequestContext,
        dimension: QuotaDimension,
        *,
        resource: str,
    ) -> QuotaAcquireResult:
        limit = self._find_limit(ctx, dimension, resource)
        if limit is None:
            async def noop() -> None:
                return None

            return QuotaAcquireResult(True, PolicyDecision.allow("quota not configured"), noop)
        lease: QuotaLease = await self._store.acquire_lease(
            limit.counter_key("active"),
            limit=limit.max_value,
            ttl_seconds=limit.window.ttl_seconds,
        )
        decision = (
            PolicyDecision.allow("quota lease acquired")
            if lease.acquired
            else PolicyDecision(
                allowed=False,
                effect=PolicyEffect.DENY,
                reason="concurrency quota exceeded",
                metadata={
                    "quota": {
                        "dimension": dimension.value,
                        "resource": resource,
                        "limit": limit.max_value,
                    }
                },
            )
        )
        return QuotaAcquireResult(lease.acquired, decision, lease.release)

    def _find_limit(
        self,
        ctx: RequestContext,
        dimension: QuotaDimension,
        resource: str,
    ) -> QuotaLimit | None:
        tenant_id = ctx.tenant_id or "*"
        candidates = [
            limit
            for limit in self._limits
            if limit.dimension is dimension
            and limit.tenant_id in {tenant_id, "*"}
            and limit.resource in {resource, "*"}
        ]
        if not candidates:
            return None
        return sorted(
            candidates,
            key=lambda limit: (limit.tenant_id == tenant_id, limit.resource == resource),
            reverse=True,
        )[0]

    @staticmethod
    def _bucket(window: QuotaWindow) -> str:
        now = datetime.now(timezone.utc)
        if window is QuotaWindow.MINUTE:
            return now.strftime("%Y%m%d%H%M")
        if window is QuotaWindow.HOUR:
            return now.strftime("%Y%m%d%H")
        if window is QuotaWindow.DAY:
            return now.strftime("%Y%m%d")
        return "active"

    @staticmethod
    def _metadata(usage: QuotaUsage, current: int) -> dict:
        return {
            "quota": {
                "dimension": usage.limit.dimension.value,
                "window": usage.limit.window.value,
                "resource": usage.limit.resource,
                "limit": usage.limit.max_value,
                "current_value": current,
                "requested_value": usage.requested_value,
            }
        }
