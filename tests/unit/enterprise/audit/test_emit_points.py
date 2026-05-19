"""审计事件 emit 测试。"""

import pytest

from qwenpaw.enterprise.audit.emit import emit_audit_event
from qwenpaw.enterprise.audit.models import AuditEventType, AuditOutcome


class CaptureBus:
    def __init__(self):
        self.events = []

    async def emit(self, event):
        self.events.append(event)


@pytest.mark.asyncio
async def test_emit_audit_event_uses_runtime_bus():
    bus = CaptureBus()
    runtime = type("Runtime", (), {"audit": bus})()
    app = type("App", (), {"state": type("State", (), {"enterprise_runtime": runtime})()})()
    request = type("Request", (), {"app": app, "state": type("State", (), {"request_id": "r1", "trace_id": "t1"})()})()

    await emit_audit_event(
        request,
        event_type=AuditEventType.AUTH_REGISTER,
        action="register",
        outcome=AuditOutcome.SUCCESS,
    )

    assert bus.events[0].event_type == AuditEventType.AUTH_REGISTER


@pytest.mark.asyncio
async def test_emit_audit_event_noop_on_missing_runtime():
    """缺失 runtime 时不应抛出异常。"""
    app = type("App", (), {"state": type("State", (), {})()})()
    request = type("Request", (), {"app": app, "state": type("State", (), {})()})()

    await emit_audit_event(
        request,
        event_type=AuditEventType.AUTH_REGISTER,
        action="register",
        outcome=AuditOutcome.SUCCESS,
    )
    # 不应抛出异常
