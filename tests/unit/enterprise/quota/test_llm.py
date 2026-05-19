import pytest

from qwenpaw.enterprise.context import RequestContext
from qwenpaw.enterprise.quota.llm import consume_llm_tokens
from qwenpaw.enterprise.quota.models import QuotaDimension, QuotaLimit, QuotaWindow
from qwenpaw.enterprise.quota.service import QuotaService
from qwenpaw.enterprise.quota.store import InMemoryQuotaStore


@pytest.mark.asyncio
async def test_consume_llm_tokens_uses_quota_service():
    quota = QuotaService(
        store=InMemoryQuotaStore(),
        limits=[
            QuotaLimit(
                dimension=QuotaDimension.LLM_TOKEN,
                window=QuotaWindow.DAY,
                max_value=10,
                tenant_id="wx_acme",
                resource="dashscope:qwen",
            )
        ],
    )
    ctx = RequestContext(request_id="r", trace_id="t", tenant_id="wx_acme")

    decision = await consume_llm_tokens(
        quota,
        ctx,
        provider_id="dashscope",
        model_name="qwen",
        prompt_tokens=6,
        completion_tokens=5,
    )

    assert decision.allowed is False
