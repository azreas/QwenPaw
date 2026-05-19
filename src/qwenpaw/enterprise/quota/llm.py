from __future__ import annotations

from qwenpaw.enterprise.context import RequestContext
from qwenpaw.enterprise.policy.models import PolicyDecision

from .models import QuotaDimension
from .service import QuotaService


async def consume_llm_tokens(
    quota: QuotaService | None,
    ctx: RequestContext | None,
    *,
    provider_id: str,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> PolicyDecision | None:
    if quota is None or ctx is None:
        return None
    return await quota.consume(
        ctx,
        QuotaDimension.LLM_TOKEN,
        resource=f"{provider_id}:{model_name}",
        amount=max(0, prompt_tokens) + max(0, completion_tokens),
    )
