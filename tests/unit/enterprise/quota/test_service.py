import pytest

from qwenpaw.enterprise.context import RequestContext
from qwenpaw.enterprise.policy.models import PolicyEffect
from qwenpaw.enterprise.quota.models import QuotaDimension, QuotaLimit, QuotaWindow
from qwenpaw.enterprise.quota.service import QuotaService
from qwenpaw.enterprise.quota.store import InMemoryQuotaStore


@pytest.mark.asyncio
async def test_quota_service_denies_over_limit():
    service = QuotaService(
        store=InMemoryQuotaStore(),
        limits=[
            QuotaLimit(
                dimension=QuotaDimension.HTTP_REQUEST,
                window=QuotaWindow.MINUTE,
                max_value=1,
                tenant_id="wx_acme",
                resource="GET:/api/version",
            )
        ],
    )
    ctx = RequestContext(request_id="r", trace_id="t", tenant_id="wx_acme")

    first = await service.consume(
        ctx,
        QuotaDimension.HTTP_REQUEST,
        resource="GET:/api/version",
    )
    second = await service.consume(
        ctx,
        QuotaDimension.HTTP_REQUEST,
        resource="GET:/api/version",
    )

    assert first.allowed is True
    assert second.allowed is False
    assert second.effect is PolicyEffect.DENY
    assert second.metadata["quota"]["current_value"] == 2


@pytest.mark.asyncio
async def test_quota_service_lease_release_allows_next_request():
    service = QuotaService(
        store=InMemoryQuotaStore(),
        limits=[
            QuotaLimit(
                dimension=QuotaDimension.LLM_CONCURRENCY,
                window=QuotaWindow.CONCURRENT,
                max_value=1,
                tenant_id="wx_acme",
                resource="dashscope:qwen-max",
            )
        ],
    )
    ctx = RequestContext(request_id="r", trace_id="t", tenant_id="wx_acme")

    lease = await service.acquire(
        ctx,
        QuotaDimension.LLM_CONCURRENCY,
        resource="dashscope:qwen-max",
    )
    denied = await service.acquire(
        ctx,
        QuotaDimension.LLM_CONCURRENCY,
        resource="dashscope:qwen-max",
    )
    await lease.release()
    allowed = await service.acquire(
        ctx,
        QuotaDimension.LLM_CONCURRENCY,
        resource="dashscope:qwen-max",
    )

    assert lease.acquired is True
    assert denied.decision.allowed is False
    assert allowed.acquired is True
