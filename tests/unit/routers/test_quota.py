from fastapi import FastAPI
from fastapi.testclient import TestClient

from qwenpaw.app.routers.quota import router as quota_router


def test_quota_summary_returns_limits_without_redis_url(monkeypatch):
    monkeypatch.setenv("QWENPAW_QUOTA_ENABLED", "true")
    monkeypatch.setenv("QWENPAW_REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("QWENPAW_QUOTA_HTTP_PER_MINUTE", "120")
    monkeypatch.setenv("QWENPAW_QUOTA_AUTH_LOGIN_PER_MINUTE", "12")
    monkeypatch.setenv("QWENPAW_QUOTA_LLM_TOKENS_PER_DAY", "500000")

    app = FastAPI()
    app.include_router(quota_router, prefix="/api")

    response = TestClient(app).get("/api/quota/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert data["redis_url_set"] is True
    assert "redis_url" not in data
    assert "redis://localhost:6379/1" not in response.text
    assert {
        "dimension": "http.request",
        "window": "minute",
        "max_value": 120,
        "resource": "*",
    } in data["default_limits"]
    assert {
        "dimension": "http.request",
        "window": "minute",
        "max_value": 12,
        "resource": "POST:/api/auth/login",
    } in data["default_limits"]
    assert {
        "dimension": "llm.token",
        "window": "day",
        "max_value": 500000,
        "resource": "*",
    } in data["default_limits"]
