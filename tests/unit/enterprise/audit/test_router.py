"""审计查询 API 授权和租户过滤测试。"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from qwenpaw.app.routers.audit import router
from qwenpaw.enterprise.authz.middleware import AuthzMiddleware
from qwenpaw.enterprise.authz.service import AuthzService
from qwenpaw.enterprise.context import RequestActor, RequestContext


def _row(
    *,
    event_type: str,
    tenant_id: str,
    resource_type: str = "",
    resource_id: str = "",
    outcome: str = "success",
    payload: dict | None = None,
    actor_id: str = "user_acme_001",
    agent_id: str = "",
    session_id: str = "",
):
    return SimpleNamespace(
        id=f"{event_type}:{tenant_id}:{resource_id}:{session_id}",
        event_type=event_type,
        action="call" if event_type.endswith(".called") else "read",
        outcome=outcome,
        tenant_id=tenant_id,
        agent_id=agent_id or tenant_id,
        session_id=session_id,
        actor_id=actor_id,
        actor_type="console_user",
        resource_type=resource_type,
        resource_id=resource_id,
        request_id="req-1",
        trace_id="trace-1",
        ip_address="127.0.0.1",
        user_agent="pytest",
        payload=payload or {},
        created_at=datetime(2026, 5, 12, 9, 0, tzinfo=timezone.utc),
    )


class FakeAuditRepository:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    async def query(self, **kwargs):
        self.calls.append(kwargs)
        result = list(self.rows)
        for key in (
            "tenant_id",
            "actor_id",
            "agent_id",
            "session_id",
            "resource_type",
            "resource_id",
            "event_type",
            "outcome",
        ):
            value = kwargs.get(key)
            if value is not None:
                result = [row for row in result if getattr(row, key) == value]

        event_types = kwargs.get("event_types")
        if event_types:
            result = [row for row in result if row.event_type in event_types]

        return result[: kwargs.get("limit", 100)]


class _InjectContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, ctx: RequestContext):
        super().__init__(app)
        self._ctx = ctx

    async def dispatch(self, request, call_next):
        request.state.request_context = self._ctx
        return await call_next(request)


def _make_app(ctx: RequestContext, rows):
    app = FastAPI()
    repo = FakeAuditRepository(rows)
    runtime = SimpleNamespace(
        authz=AuthzService(),
        audit=SimpleNamespace(_repository=repo),
    )
    app.state.enterprise_runtime = runtime
    app.include_router(router, prefix="/api")
    app.add_middleware(AuthzMiddleware)
    app.add_middleware(_InjectContextMiddleware, ctx=ctx)
    return app, repo


def _ctx(*, roles: tuple[str, ...], tenant_id: str = "", actor_id: str = "admin"):
    return RequestContext(
        request_id="req",
        trace_id="trace",
        tenant_id=tenant_id,
        agent_id=tenant_id,
        roles=roles,
        actor=RequestActor(actor_id=actor_id, actor_type="console_user"),
    )


def test_audit_router_requires_runtime():
    """审计路由缺少 runtime 时返回 503。"""
    app = FastAPI()
    app.include_router(router, prefix="/api")

    response = TestClient(app).get("/api/audit/events")
    assert response.status_code == 503


def test_platform_admin_can_query_all_tenants():
    app, repo = _make_app(
        _ctx(roles=("platform_admin",)),
        [
            _row(event_type="auth.login_success", tenant_id="wx_acme"),
            _row(event_type="auth.login_success", tenant_id="wx_other"),
        ],
    )

    response = TestClient(app).get("/api/audit/events")

    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert repo.calls[0]["tenant_id"] is None


def test_tenant_audit_query_is_forced_to_context_tenant():
    app, repo = _make_app(
        _ctx(roles=("tenant_admin",), tenant_id="wx_acme"),
        [
            _row(event_type="auth.login_success", tenant_id="wx_acme"),
            _row(event_type="auth.login_success", tenant_id="wx_other"),
        ],
    )

    response = TestClient(app).get("/api/audit/events")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["events"][0]["tenant_id"] == "wx_acme"
    assert repo.calls[0]["tenant_id"] == "wx_acme"


def test_tenant_audit_query_rejects_cross_tenant_param():
    app, repo = _make_app(
        _ctx(roles=("tenant_admin",), tenant_id="wx_acme"),
        [_row(event_type="auth.login_success", tenant_id="wx_acme")],
    )

    response = TestClient(app).get("/api/audit/events?tenant_id=wx_other")

    assert response.status_code == 403
    assert repo.calls == []


def test_tenant_readonly_can_read_only_own_tenant():
    app, repo = _make_app(
        _ctx(roles=("tenant_readonly",), tenant_id="wx_acme"),
        [
            _row(event_type="auth.login_success", tenant_id="wx_acme"),
            _row(event_type="auth.login_success", tenant_id="wx_other"),
        ],
    )

    response = TestClient(app).get("/api/audit/events")

    assert response.status_code == 200
    assert response.json()["events"][0]["tenant_id"] == "wx_acme"
    assert repo.calls[0]["tenant_id"] == "wx_acme"


def test_tenant_audit_query_requires_context_tenant():
    app, repo = _make_app(
        _ctx(roles=("tenant_admin",)),
        [_row(event_type="auth.login_success", tenant_id="wx_acme")],
    )

    response = TestClient(app).get("/api/audit/events")

    assert response.status_code == 403
    assert repo.calls == []


def test_business_calls_returns_product_fields_and_filters_payload():
    rows = [
        _row(
            event_type="skill.called",
            tenant_id="wx_acme",
            resource_type="skill",
            resource_id="sales_report",
            session_id="session-1",
            payload={
                "entrypoint": "webchat",
                "ability_type": "skill",
                "ability_name": "sales_report",
                "status": "success",
                "duration_ms": 80.0,
                "error_reason": "",
            },
        ),
        _row(
            event_type="mcp.called",
            tenant_id="wx_acme",
            resource_type="mcp",
            resource_id="doris_query",
            outcome="failure",
            session_id="session-2",
            payload={
                "entrypoint": "webchat",
                "ability_type": "mcp",
                "ability_name": "doris_query",
                "status": "failure",
                "duration_ms": 3000.0,
                "error_reason": "timeout",
            },
        ),
    ]
    app, repo = _make_app(
        _ctx(roles=("tenant_admin",), tenant_id="wx_acme"),
        rows,
    )

    response = TestClient(app).get(
        "/api/audit/business-calls",
        params={
            "ability_type": "mcp",
            "ability_name": "doris_query",
            "status": "failure",
            "entrypoint": "webchat",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    trace = body["traces"][0]
    assert trace["tenant_id"] == "wx_acme"
    assert trace["entrypoint"] == "webchat"
    assert trace["ability_type"] == "mcp"
    assert trace["ability_name"] == "doris_query"
    assert trace["call_type"] == "mcp"
    assert trace["call_name"] == "doris_query"
    assert trace["status"] == "failure"
    assert trace["error_reason"] == "timeout"
    assert repo.calls[0]["event_types"] == ("mcp.called",)


def test_business_call_trace_filters_by_call_type_and_error_code():
    rows = [
        _row(
            event_type="platform.invocation",
            tenant_id="wx_acme",
            resource_type="builtin_tool",
            resource_id="file_search",
            outcome="failure",
            session_id="session-1",
            payload={
                "entrypoint": "webchat",
                "call_type": "builtin_tool",
                "call_name": "file_search",
                "status": "failure",
                "duration_ms": 1200.0,
                "error_code": "tool.timeout",
                "error_reason": "tool timeout",
                "request_id": "req-tool",
                "trace_id": "trace-tool",
            },
        ),
        _row(
            event_type="platform.invocation",
            tenant_id="wx_acme",
            resource_type="quota",
            resource_id="llm_tokens",
            outcome="denied",
            session_id="session-2",
            payload={
                "entrypoint": "webchat",
                "call_type": "quota",
                "call_name": "llm_tokens",
                "status": "denied",
                "error_code": "quota.denied",
                "error_reason": "quota exceeded",
            },
        ),
    ]
    app, repo = _make_app(
        _ctx(roles=("tenant_admin",), tenant_id="wx_acme"),
        rows,
    )

    response = TestClient(app).get(
        "/api/audit/business-calls",
        params={
            "call_type": "builtin_tool",
            "error_code": "tool.timeout",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    trace = body["traces"][0]
    assert trace["tenant_id"] == "wx_acme"
    assert trace["call_type"] == "builtin_tool"
    assert trace["call_name"] == "file_search"
    assert trace["ability_type"] == "builtin_tool"
    assert trace["ability_name"] == "file_search"
    assert trace["status"] == "failure"
    assert trace["error_code"] == "tool.timeout"
    assert trace["request_id"] == "req-1"
    assert trace["trace_id"] == "trace-1"
    assert repo.calls[0]["event_types"] == ("platform.invocation",)


def test_business_calls_rejects_unknown_ability_type():
    app, _ = _make_app(
        _ctx(roles=("platform_admin",)),
        [],
    )

    response = TestClient(app).get(
        "/api/audit/business-calls?ability_type=unknown",
    )

    assert response.status_code == 400
