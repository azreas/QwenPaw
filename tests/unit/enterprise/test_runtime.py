import pytest

from qwenpaw.enterprise.context import RequestContext
from qwenpaw.enterprise.runtime import create_enterprise_runtime


@pytest.mark.asyncio
async def test_runtime_starts_and_stops_noop_services():
    runtime = create_enterprise_runtime()

    await runtime.start()
    health = await runtime.storage.healthcheck()
    assert health["status"] == "disabled"

    await runtime.stop()
    assert runtime.started is False


def test_create_runtime_has_all_services():
    runtime = create_enterprise_runtime()
    assert runtime.storage is not None
    assert runtime.authz is not None
    assert runtime.audit is not None
    assert runtime.extensions is not None


@pytest.mark.asyncio
async def test_runtime_exposes_policy_service():
    from qwenpaw.enterprise.policy import PolicyAction, PolicyService

    runtime = create_enterprise_runtime()
    assert isinstance(runtime.policy, PolicyService)

    decision = await runtime.policy.evaluate(
        RequestContext(request_id="r", trace_id="t"),
        PolicyAction.AGENT_RUN,
        "default",
    )
    assert decision.allowed is True


@pytest.mark.asyncio
async def test_runtime_exposes_quota_service(monkeypatch):
    from qwenpaw.enterprise.quota import QuotaService

    monkeypatch.setenv("QWENPAW_QUOTA_ENABLED", "true")
    monkeypatch.setenv("QWENPAW_REDIS_URL", "redis://localhost:6379/1")

    runtime = create_enterprise_runtime()
    assert isinstance(runtime.quota, QuotaService)


def test_runtime_exposes_reliability_components():
    from qwenpaw.enterprise.reliability import HealthService, InMemoryDeadLetterQueue
    from qwenpaw.enterprise.reliability.circuit_breaker import CircuitBreakerService

    runtime = create_enterprise_runtime()

    assert isinstance(runtime.health, HealthService)
    assert isinstance(runtime.circuit_breaker, CircuitBreakerService)
    assert isinstance(runtime.dead_letter, InMemoryDeadLetterQueue)
