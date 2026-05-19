import asyncio

import pytest

from qwenpaw.enterprise.audit.models import AuditEventType
from qwenpaw.enterprise.context import (
    RequestContext,
    clear_current_request_context,
    set_current_request_context,
)
from qwenpaw.enterprise.interfaces import ToolPolicyPatch
from qwenpaw.enterprise.runtime_registry import (
    clear_enterprise_runtime,
    set_enterprise_runtime,
)
from qwenpaw.security.tool_guard.engine import ToolGuardEngine


class CaptureBus:
    def __init__(self):
        self.events = []

    async def emit(self, event):
        self.events.append(event)


@pytest.mark.asyncio
async def test_tool_guard_audit_uses_runtime_registry():
    bus = CaptureBus()
    runtime = type("Runtime", (), {"audit": bus})()
    set_enterprise_runtime(runtime)
    token = set_current_request_context(
        RequestContext(
            request_id="req-1",
            trace_id="trace-1",
            tenant_id="wx_acme",
            agent_id="wx_acme",
            session_id="s1",
        )
    )
    try:
        engine = ToolGuardEngine(guardians=[], enabled=True)
        result = engine.guard("read_file", {"path": "README.md"})
        assert result is not None
        await asyncio.sleep(0)
    finally:
        clear_current_request_context(token)
        clear_enterprise_runtime(runtime)

    assert len(bus.events) == 1
    assert bus.events[0].event_type == AuditEventType.TOOL_GUARD_EVALUATED
    assert bus.events[0].tenant_id == "wx_acme"


@pytest.mark.asyncio
async def test_tool_guard_deny_emits_platform_invocation_payload():
    bus = CaptureBus()
    runtime = type("Runtime", (), {"audit": bus})()
    set_enterprise_runtime(runtime)
    token = set_current_request_context(
        RequestContext(
            request_id="req-2",
            trace_id="trace-2",
            tenant_id="wx_acme",
            agent_id="wx_acme",
            session_id="s2",
        )
    )
    from qwenpaw.enterprise.context import set_current_tool_policy_patch

    set_current_tool_policy_patch(
        ToolPolicyPatch(deny_tools=frozenset({"execute_shell_command"}))
    )
    try:
        engine = ToolGuardEngine(guardians=[], enabled=True)
        result = engine.guard("execute_shell_command", {"command": "ls"})
        assert result is not None
        assert not result.is_safe
        await asyncio.sleep(0)
    finally:
        set_current_tool_policy_patch(None)
        clear_current_request_context(token)
        clear_enterprise_runtime(runtime)

    platform_events = [
        event
        for event in bus.events
        if event.event_type == AuditEventType.PLATFORM_INVOCATION
    ]
    assert len(platform_events) == 1
    assert platform_events[0].payload["call_type"] == "tool_guard"
    assert platform_events[0].payload["status"] == "denied"
    assert platform_events[0].payload["error_code"] == "tool_guard.denied"
