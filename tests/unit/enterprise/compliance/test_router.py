from fastapi import FastAPI
from fastapi.testclient import TestClient

from qwenpaw.enterprise.audit.models import AuditEventType, AuditOutcome
from qwenpaw.enterprise.compliance.router import create_compliance_router


def test_retention_policy_endpoint_returns_defaults():
    app = FastAPI()
    app.include_router(create_compliance_router(), prefix="/api")

    response = TestClient(app).get("/api/compliance/retention/policy")

    assert response.status_code == 200
    assert response.json()["audit_retention_days"] == 365


def test_export_audit_emits_compliance_event(monkeypatch):
    emitted = []

    async def fake_emit_audit_event(request, event_type, action, outcome, **kwargs):
        emitted.append(
            {
                "event_type": event_type,
                "action": action,
                "outcome": outcome,
                "payload": kwargs["payload"],
            }
        )

    class FakeStorage:
        session_factory = object()

    class FakeRuntime:
        storage = FakeStorage()

    class FakeService:
        def __init__(self, repository):
            self.repository = repository

        async def export_audit(self, request):
            return "[]", "application/json", "audit-export-20260510.json"

    monkeypatch.setattr(
        "qwenpaw.enterprise.compliance.router.emit_audit_event",
        fake_emit_audit_event,
    )
    monkeypatch.setattr(
        "qwenpaw.enterprise.compliance.router.ComplianceService",
        FakeService,
    )

    app = FastAPI()
    app.state.enterprise_runtime = FakeRuntime()
    app.include_router(create_compliance_router(), prefix="/api")

    response = TestClient(app).post(
        "/api/compliance/audit/export",
        json={"format": "json", "limit": 10, "tenant_id": "tenant-a"},
    )

    assert response.status_code == 200
    assert emitted == [
        {
            "event_type": AuditEventType.COMPLIANCE_EXPORTED,
            "action": "audit_export",
            "outcome": AuditOutcome.SUCCESS,
            "payload": {
                "format": "json",
                "limit": 10,
                "tenant_id": "tenant-a",
                "filename": "audit-export-20260510.json",
                "event_type": "",
                "start_time": "",
                "end_time": "",
            },
        }
    ]


def test_export_audit_returns_file(monkeypatch):
    class FakeStorage:
        session_factory = object()

    class FakeRuntime:
        storage = FakeStorage()

    class FakeService:
        def __init__(self, repository):
            pass

        async def export_audit(self, request):
            return '[{"id":"1"}]', "application/json", "audit-export.json"

    async def fake_emit_noop(*a, **kw):
        pass

    monkeypatch.setattr(
        "qwenpaw.enterprise.compliance.router.emit_audit_event",
        fake_emit_noop,
    )
    monkeypatch.setattr(
        "qwenpaw.enterprise.compliance.router.ComplianceService",
        FakeService,
    )

    app = FastAPI()
    app.state.enterprise_runtime = FakeRuntime()
    app.include_router(create_compliance_router(), prefix="/api")

    response = TestClient(app).post(
        "/api/compliance/audit/export",
        json={"format": "json", "limit": 10},
    )

    assert response.status_code == 200
    assert "audit-export.json" in response.headers["content-disposition"]


def test_export_audit_503_when_no_storage():
    app = FastAPI()
    # 不设 enterprise_runtime → storage 为 None
    app.include_router(create_compliance_router(), prefix="/api")

    response = TestClient(app).post(
        "/api/compliance/audit/export",
        json={"format": "json", "limit": 10},
    )

    assert response.status_code == 503


def test_export_audit_503_when_json_backend():
    """默认 JSON 后端下 session_factory 为 None,应返回 503 而非空文件。"""

    class FakeStorage:
        session_factory = None

    class FakeRuntime:
        storage = FakeStorage()

    app = FastAPI()
    app.state.enterprise_runtime = FakeRuntime()
    app.include_router(create_compliance_router(), prefix="/api")

    response = TestClient(app).post(
        "/api/compliance/audit/export",
        json={"format": "json", "limit": 10},
    )

    assert response.status_code == 503
    assert "SQL backend required" in response.json()["detail"]


def test_export_audit_event_payload_includes_filters(monkeypatch):
    """合规导出审计事件的 payload 应包含筛选字段。"""
    emitted = []

    async def fake_emit_audit_event(request, event_type, action, outcome, **kwargs):
        emitted.append(kwargs["payload"])

    class FakeStorage:
        session_factory = object()

    class FakeRuntime:
        storage = FakeStorage()

    class FakeService:
        def __init__(self, repository):
            pass

        async def export_audit(self, request):
            return "[]", "text/csv", "audit-export.csv"

    monkeypatch.setattr(
        "qwenpaw.enterprise.compliance.router.emit_audit_event",
        fake_emit_audit_event,
    )
    monkeypatch.setattr(
        "qwenpaw.enterprise.compliance.router.ComplianceService",
        FakeService,
    )

    app = FastAPI()
    app.state.enterprise_runtime = FakeRuntime()
    app.include_router(create_compliance_router(), prefix="/api")

    response = TestClient(app).post(
        "/api/compliance/audit/export",
        json={
            "format": "csv",
            "limit": 10,
            "tenant_id": "wx_acme",
            "event_type": "compliance.exported",
            "start_time": "2026-05-18T00:00:00+00:00",
            "end_time": "2026-05-18T23:59:59+00:00",
        },
    )

    assert response.status_code == 200
    assert emitted[0]["format"] == "csv"
    assert emitted[0]["tenant_id"] == "wx_acme"
    assert emitted[0]["event_type"] == "compliance.exported"
    assert emitted[0]["start_time"] == "2026-05-18T00:00:00+00:00"
    assert emitted[0]["end_time"] == "2026-05-18T23:59:59+00:00"
