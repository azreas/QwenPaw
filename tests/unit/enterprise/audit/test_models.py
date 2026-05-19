"""审计模型测试。"""

from qwenpaw.enterprise.audit.models import AuditEvent, AuditEventType, AuditOutcome
from qwenpaw.enterprise.context import RequestActor, RequestContext
from qwenpaw.enterprise.storage.models import AuditLogRow


def test_audit_event_from_context():
    ctx = RequestContext(
        request_id="req-1",
        trace_id="trace-1",
        tenant_id="wx_acme",
        agent_id="wx_acme",
        session_id="s1",
        actor=RequestActor(actor_id="u1", actor_type="webchat_user"),
    )
    event = AuditEvent.from_context(
        ctx,
        event_type=AuditEventType.AUTHZ_DENIED,
        action="audit:read",
        outcome=AuditOutcome.FAILURE,
        resource_type="audit",
        resource_id="events",
    )

    assert event.tenant_id == "wx_acme"
    assert event.actor_id == "u1"
    assert event.request_id == "req-1"


def test_audit_log_row_has_append_only_fields():
    columns = AuditLogRow.__table__.columns
    assert "id" in columns
    assert "event_type" in columns
    assert "tenant_id" in columns
    assert "request_id" in columns
    assert "payload" in columns
    assert "created_at" in columns
