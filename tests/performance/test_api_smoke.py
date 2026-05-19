# -*- coding: utf-8 -*-
"""API 延迟冒烟测试——低成本，不做压测。"""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from qwenpaw.app._app import app


def test_health_endpoint_latency_smoke():
    client = TestClient(app)

    start = time.perf_counter()
    for _ in range(20):
        response = client.get("/health")
        assert response.status_code == 200
    elapsed = time.perf_counter() - start

    # 20 次请求应在 2 秒内完成（TestClient 无网络开销）
    assert elapsed < 2.0
