from __future__ import annotations

from qwenpaw.enterprise.context import RequestContext
from qwenpaw.enterprise.policy.models import PolicyDecision

from .models import QuotaDimension
from .service import QuotaService


async def consume_tool_call(
    quota: QuotaService | None,
    ctx: RequestContext | None,
    tool_name: str,
) -> PolicyDecision | None:
    if quota is None or ctx is None or not tool_name:
        return None
    return await quota.consume(
        ctx,
        QuotaDimension.TOOL_CALL,
        resource=tool_name,
    )
