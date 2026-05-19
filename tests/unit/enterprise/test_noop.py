import pytest

from qwenpaw.enterprise.context import RequestContext
from qwenpaw.enterprise.noop import (
    NoopAuditEventBus,
    NoopAuthzService,
    NoopRuntimeExtensionResolver,
    NoopStorageManager,
)


@pytest.mark.asyncio
async def test_noop_storage_lifecycle():
    storage = NoopStorageManager()
    await storage.start()
    assert await storage.healthcheck() == {"status": "disabled"}
    await storage.stop()


@pytest.mark.asyncio
async def test_noop_authz_allows_existing_behavior():
    service = NoopAuthzService()
    decision = await service.check_permission(
        RequestContext(request_id="r", trace_id="t"),
        "agents",
        "read",
    )
    assert decision.allowed is True
    assert decision.reason == "noop"


@pytest.mark.asyncio
async def test_noop_audit_accepts_event():
    bus = NoopAuditEventBus()
    await bus.emit({"event_type": "test.event"})
    assert bus.events_seen == 1


@pytest.mark.asyncio
async def test_noop_extension_resolver_returns_empty_bundle():
    resolver = NoopRuntimeExtensionResolver()
    bundle = await resolver.resolve(RequestContext(request_id="r", trace_id="t"))
    assert bundle.mcp_clients == []
    assert bundle.tool_policy.disable_tools == frozenset()
