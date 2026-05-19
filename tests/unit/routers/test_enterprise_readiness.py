from fastapi.testclient import TestClient

from qwenpaw.app._app import app


def test_enterprise_readiness_is_publicly_accessible_without_auth():
    """readiness 接口应公开可访问，无需 Console token"""
    response = TestClient(app).get("/api/enterprise/readiness")
    # 已加入 _PUBLIC_PATHS，AuthMiddleware 应该放行返回 200
    assert response.status_code == 200


def test_enterprise_readiness_public_returns_only_status(monkeypatch):
    """公开访问只返回粗粒度 status，不泄露详细检查信息"""
    monkeypatch.setenv("QWENPAW_WEBCHAT_SESSION_SECRET", "x" * 32)
    monkeypatch.setenv("QWENPAW_STORAGE_BACKEND", "json")
    monkeypatch.setenv("QWENPAW_QUOTA_ENABLED", "false")

    response = TestClient(app).get("/api/enterprise/readiness")

    assert response.status_code == 200
    data = response.json()
    # 公开访问只返回 status 字段
    assert set(data.keys()) == {"status"}
    assert data["status"] == "degraded"
    # 不能泄露详细检查信息
    assert "checks" not in data
    assert "blockers" not in data


def test_enterprise_readiness_admin_returns_full_details(monkeypatch):
    """platform_admin 访问返回完整 checks 和 blockers 详情"""
    monkeypatch.setenv("QWENPAW_WEBCHAT_SESSION_SECRET", "x" * 32)
    monkeypatch.setenv("QWENPAW_STORAGE_BACKEND", "json")
    monkeypatch.setenv("QWENPAW_QUOTA_ENABLED", "false")

    from qwenpaw.enterprise.context import RequestContext, RequestActor

    # 构造 mock request
    class MockRequest:
        def __init__(self, roles):
            self.state = type(
                "State",
                (),
                {
                    "request_context": RequestContext(
                        request_id="test",
                        trace_id="test",
                        roles=roles,
                        actor=RequestActor(actor_id="test-admin", actor_type="user"),
                    )
                },
            )()

    # 导入路由函数
    from qwenpaw.app.routers.enterprise_readiness import get_enterprise_readiness

    # 管理员访问
    import asyncio

    result = asyncio.run(get_enterprise_readiness(MockRequest(roles=("platform_admin",))))
    data = result.model_dump()
    assert data["status"] == "degraded"
    assert "checks" in data
    assert "blockers" in data
    assert any(item["name"] == "webchat_session_secret" for item in data["checks"])

    # 非管理员访问只返回 status
    result = asyncio.run(get_enterprise_readiness(MockRequest(roles=("tenant_member",))))
    data = result.model_dump()
    assert set(data.keys()) == {"status"}
    assert "checks" not in data
    assert "blockers" not in data


def test_enterprise_readiness_returns_ready_when_all_configured(monkeypatch):
    """所有检查都配置完成时返回 ready"""
    monkeypatch.setenv("QWENPAW_WEBCHAT_SESSION_SECRET", "x" * 32)
    monkeypatch.setenv("QWENPAW_STORAGE_BACKEND", "json")
    monkeypatch.setenv("QWENPAW_QUOTA_ENABLED", "false")
    monkeypatch.setenv("QWENPAW_WEBCHAT_SSO_LOGIN_URL", "https://sso.example.com")
    monkeypatch.setenv("QWENPAW_WEBCHAT_QRCODE_LOGIN_URL", "https://wecom.example.com")
    monkeypatch.setenv("QWENPAW_CORS_ORIGINS", "https://ai.example.com")

    response = TestClient(app).get("/api/enterprise/readiness")

    assert response.status_code == 200
    data = response.json()
    # 公开访问只返回 status
    assert data["status"] == "ready"
    assert "checks" not in data
