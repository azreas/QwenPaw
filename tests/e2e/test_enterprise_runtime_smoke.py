# -*- coding: utf-8 -*-
"""企业运行时 E2E 冒烟测试。"""
from __future__ import annotations

from fastapi.testclient import TestClient

from qwenpaw.app._app import app


def test_health_ready_metrics_smoke():
    client = TestClient(app)

    health = client.get("/health")
    ready = client.get("/ready")
    metrics = client.get("/api/metrics")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    # 无 enterprise_runtime 时返回 503，有则 200
    assert ready.status_code in {200, 503}
    assert "ready" in ready.json()
    # 有 enterprise_runtime 时 200 + text/plain，无则 403
    assert metrics.status_code in {200, 403}
    if metrics.status_code == 200:
        assert "text/plain" in metrics.headers["content-type"]


def test_console_auth_status_smoke():
    client = TestClient(app)

    response = client.get("/api/auth/status")

    assert response.status_code == 200
    body = response.json()
    assert "enabled" in body
    assert "has_users" in body
