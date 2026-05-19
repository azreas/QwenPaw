# -*- coding: utf-8 -*-
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qwenpaw.enterprise.authz.middleware import AuthzMiddleware
from qwenpaw.enterprise.authz.service import AuthzService
from qwenpaw.enterprise.context import RequestContext, RequestActor
from qwenpaw.enterprise.interfaces import AuthzDecision
from qwenpaw.enterprise.runtime import create_enterprise_runtime


class CaptureBus:
    def __init__(self):
        self.events = []

    async def emit(self, event):
        self.events.append(event)


def _make_app_with_real_authz() -> FastAPI:
    """构造使用真实 AuthzService 的测试 app。"""
    app = FastAPI()
    runtime = create_enterprise_runtime()
    runtime.authz = AuthzService()
    app.state.enterprise_runtime = runtime
    app.add_middleware(AuthzMiddleware)
    return app


def _force_console_auth_enabled(monkeypatch):
    from qwenpaw.app import auth as app_auth

    monkeypatch.setattr(app_auth, "is_auth_enabled", lambda: True)
    monkeypatch.setattr(app_auth, "has_registered_users", lambda: True)


def test_authz_middleware_skips_when_console_auth_disabled(monkeypatch):
    from qwenpaw.app import auth as app_auth

    monkeypatch.setattr(app_auth, "is_auth_enabled", lambda: False)
    monkeypatch.setattr(app_auth, "has_registered_users", lambda: True)

    app = _make_app_with_real_authz()

    @app.get("/api/models")
    async def models():
        return {"ok": True}

    response = TestClient(app).get("/api/models")
    assert response.status_code == 200


def test_authz_middleware_keeps_webchat_token_protection_when_console_auth_disabled(
    monkeypatch,
):
    from qwenpaw.app import auth as app_auth

    monkeypatch.setattr(app_auth, "is_auth_enabled", lambda: False)
    monkeypatch.setattr(app_auth, "has_registered_users", lambda: True)

    app = _make_app_with_real_authz()

    @app.get("/api/webchat/sessions")
    async def webchat_sessions():
        return {"ok": True}

    response = TestClient(app).get("/api/webchat/sessions")
    assert response.status_code == 403


def test_authz_middleware_denies_missing_role_on_protected_route(monkeypatch):
    _force_console_auth_enabled(monkeypatch)
    app = _make_app_with_real_authz()

    @app.get("/api/audit/events")
    async def audit_events():
        return {"ok": True}

    response = TestClient(app).get("/api/audit/events")
    assert response.status_code == 403


def test_authz_middleware_denied_emits_platform_invocation_trace(monkeypatch):
    _force_console_auth_enabled(monkeypatch)
    app = _make_app_with_real_authz()
    bus = CaptureBus()
    app.state.enterprise_runtime.audit = bus

    @app.get("/api/audit/events")
    async def audit_events():
        return {"ok": True}

    response = TestClient(app).get("/api/audit/events")

    assert response.status_code == 403
    platform_events = [
        event
        for event in bus.events
        if event.event_type == "platform.invocation"
    ]
    assert len(platform_events) == 1
    assert platform_events[0].payload["call_type"] == "authz"
    assert platform_events[0].payload["status"] == "denied"
    assert platform_events[0].payload["error_code"] == "authz.denied"


def test_authz_middleware_tenant_boundary_denied_emits_trace(monkeypatch):
    _force_console_auth_enabled(monkeypatch)
    app = _make_app_with_real_authz()
    bus = CaptureBus()
    app.state.enterprise_runtime.audit = bus

    class TenantBoundaryAuthz:
        async def check_permission(self, ctx, resource, action):
            return AuthzDecision(allowed=False, reason="tenant_boundary")

    app.state.enterprise_runtime.authz = TenantBoundaryAuthz()

    @app.get("/api/audit/events")
    async def audit_events():
        return {"ok": True}

    response = TestClient(app).get("/api/audit/events")

    assert response.status_code == 403
    platform_events = [
        event
        for event in bus.events
        if event.event_type == "platform.invocation"
    ]
    assert len(platform_events) == 1
    assert platform_events[0].payload["call_type"] == "tenant_boundary"
    assert platform_events[0].payload["status"] == "denied"
    assert platform_events[0].payload["error_code"] == "tenant_boundary.denied"


def test_authz_middleware_allows_public_route():
    app = _make_app_with_real_authz()

    @app.get("/api/auth/login")
    async def auth_login():
        return {"ok": True}

    response = TestClient(app).get("/api/auth/login")
    assert response.status_code == 200


def test_authz_middleware_allows_non_api_route():
    app = _make_app_with_real_authz()

    @app.get("/")
    async def root():
        return {"ok": True}

    response = TestClient(app).get("/")
    assert response.status_code == 200


def test_authz_middleware_allows_with_preset_request_context(monkeypatch):
    """request.state.request_context 已有角色时放行。"""
    _force_console_auth_enabled(monkeypatch)
    app = _make_app_with_real_authz()

    @app.get("/api/audit/events")
    async def audit_events():
        return {"ok": True}

    # 通过 middleware 预设 request_context
    from starlette.middleware.base import BaseHTTPMiddleware

    class _InjectContextMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.state.request_context = RequestContext(
                request_id="r",
                trace_id="t",
                roles=("platform_admin",),
                actor=RequestActor(actor_id="admin", actor_type="console_user"),
            )
            return await call_next(request)

    app.add_middleware(_InjectContextMiddleware)

    response = TestClient(app).get("/api/audit/events")
    assert response.status_code == 200


def test_authz_middleware_builds_console_context_from_state_user(monkeypatch):
    """AuthMiddleware 设置 request.state.user 后，AuthzMiddleware 主动构建 context。"""
    _force_console_auth_enabled(monkeypatch)
    app = _make_app_with_real_authz()

    @app.get("/api/agents")
    async def agents_list():
        return {"ok": True}

    # 模拟 AuthMiddleware 预设 request.state.user
    from starlette.middleware.base import BaseHTTPMiddleware

    class _InjectUserMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.state.user = "admin"
            return await call_next(request)

    app.add_middleware(_InjectUserMiddleware)

    response = TestClient(app).get("/api/agents")
    assert response.status_code == 200


def test_authz_middleware_no_x_roles_header_injection(monkeypatch):
    """确认 x-roles header 不再作为角色来源。"""
    _force_console_auth_enabled(monkeypatch)
    app = _make_app_with_real_authz()

    @app.get("/api/audit/events")
    async def audit_events():
        return {"ok": True}

    # 尝试通过 x-roles 注入 platform_admin 角色应被拒绝
    response = TestClient(app).get(
        "/api/audit/events",
        headers={"x-roles": "platform_admin"},
    )
    assert response.status_code == 403


def test_authz_after_auth_middleware_order(monkeypatch):
    """验证 Auth 先于 Authz 执行：Auth 写 state.user，Authz 读取放行。

    注册顺序（LIFO）：Auth 先加 → Authz 后加
    实际执行：Authz → Auth → route
    这意味着 Auth 先执行写 state.user，Authz 后执行读 state.user。
    """
    _force_console_auth_enabled(monkeypatch)
    from qwenpaw.enterprise.middleware import RequestIdentityMiddleware

    app = FastAPI()
    runtime = create_enterprise_runtime()
    runtime.authz = AuthzService()
    app.state.enterprise_runtime = runtime

    # 模拟 _app.py 的注册顺序：AgentContext → Authz → Auth → RequestIdentity
    # LIFO 实际执行：RequestIdentity → Auth → Authz → AgentContext
    from starlette.middleware.base import BaseHTTPMiddleware

    class _FakeAgentContextMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            return await call_next(request)

    class _FakeAuthMiddleware(BaseHTTPMiddleware):
        """模拟真实 AuthMiddleware：写 request.state.user。"""
        async def dispatch(self, request, call_next):
            request.state.user = "admin"
            return await call_next(request)

    app.add_middleware(_FakeAgentContextMiddleware)
    app.add_middleware(AuthzMiddleware)
    app.add_middleware(_FakeAuthMiddleware)
    app.add_middleware(RequestIdentityMiddleware)

    @app.get("/api/agents")
    async def agents_list():
        return {"ok": True}

    # Auth 先执行写 state.user → Authz 构建平台管理员上下文 → 放行
    response = TestClient(app).get("/api/agents")
    assert response.status_code == 200


def test_authz_denies_protected_route_when_auth_enabled_but_no_users(monkeypatch):
    """auth enabled 但无注册用户时，受保护路由不被放行。"""
    from qwenpaw.app import auth as app_auth

    monkeypatch.setattr(app_auth, "is_auth_enabled", lambda: True)
    monkeypatch.setattr(app_auth, "has_registered_users", lambda: False)

    app = _make_app_with_real_authz()

    @app.get("/api/audit/events")
    async def audit_events():
        return {"ok": True}

    response = TestClient(app).get("/api/audit/events")
    assert response.status_code == 403


def test_authz_allows_public_auth_routes_when_no_users(monkeypatch):
    """auth enabled 但无用户时，公开 auth 路由仍可访问。"""
    from qwenpaw.app import auth as app_auth

    monkeypatch.setattr(app_auth, "is_auth_enabled", lambda: True)
    monkeypatch.setattr(app_auth, "has_registered_users", lambda: False)

    app = _make_app_with_real_authz()

    @app.get("/api/auth/login")
    async def auth_login():
        return {"ok": True}

    @app.get("/api/auth/status")
    async def auth_status():
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/api/auth/login").status_code == 200
    assert client.get("/api/auth/status").status_code == 200


def test_authz_fallback_from_bearer_token(monkeypatch, tmp_path):
    """AuthMiddleware state 传播失败时，Authz 从 Bearer token 回退构建 context。"""
    _force_console_auth_enabled(monkeypatch)
    # 隔离认证文件，避免读写本机 ~/.qwenpaw.secret/auth.json
    from qwenpaw.app import auth as app_auth

    monkeypatch.setattr(app_auth, "AUTH_FILE", tmp_path / "auth.json")

    # 注册用户以初始化 jwt_secret（否则 create_token 和 verify 使用不同 secret）
    app_auth.register_user("admin", "test-password", roles=("platform_admin",))

    app = _make_app_with_real_authz()

    @app.get("/api/agents")
    async def agents_list():
        return {"ok": True}

    # 不注入任何 state，直接带 Bearer token
    from qwenpaw.app.auth import create_token

    token = create_token("admin")
    response = TestClient(app).get(
        "/api/agents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_authz_denies_tenant_admin_on_platform_quota_summary(monkeypatch):
    """配额管理是平台级管理面，tenant_admin 不应访问 /api/quota。"""
    _force_console_auth_enabled(monkeypatch)
    app = _make_app_with_real_authz()

    @app.get("/api/quota/summary")
    async def quota_summary():
        return {"ok": True, "secret_quota": {"monthly_limit": 999999}}

    from starlette.middleware.base import BaseHTTPMiddleware

    class _InjectTenantAdminMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.state.request_context = RequestContext(
                request_id="r",
                trace_id="t",
                tenant_id="acme",
                roles=("tenant_admin",),
                actor=RequestActor(actor_id="tenant-admin", actor_type="console_user"),
            )
            return await call_next(request)

    app.add_middleware(_InjectTenantAdminMiddleware)

    response = TestClient(app).get("/api/quota/summary")

    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied: platform:read"
    assert "secret_quota" not in response.text


def test_authz_denies_tenant_admin_on_platform_policy_write(monkeypatch):
    """安全中心策略写契约必须保持平台级权限。"""
    _force_console_auth_enabled(monkeypatch)
    app = _make_app_with_real_authz()

    @app.put("/api/platform/tenancy/policies/default")
    async def update_policy():
        return {"ok": True, "secret_policy": {"allow_mcp": True}}

    from starlette.middleware.base import BaseHTTPMiddleware

    class _InjectTenantAdminMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.state.request_context = RequestContext(
                request_id="r",
                trace_id="t",
                tenant_id="acme",
                roles=("tenant_admin",),
                actor=RequestActor(actor_id="tenant-admin", actor_type="console_user"),
            )
            return await call_next(request)

    app.add_middleware(_InjectTenantAdminMiddleware)

    response = TestClient(app).put("/api/platform/tenancy/policies/default")

    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied: platform:write"
    assert "secret_policy" not in response.text
