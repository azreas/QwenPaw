"""健康检查路由单元测试。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qwenpaw.enterprise.reliability.router import create_reliability_router


def test_health_endpoint_is_liveness_only() -> None:
    """/health 应仅返回 liveness 状态，不依赖任何外部服务。"""
    app = FastAPI()
    app.include_router(create_reliability_router(), prefix="")

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_endpoint_returns_503_when_no_runtime() -> None:
    """没有 enterprise_runtime 时 /ready 应返回 503。"""
    app = FastAPI()
    app.include_router(create_reliability_router(), prefix="")

    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["ready"] is False
    assert data["status"] == "down"
    assert "components" in data
