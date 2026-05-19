from fastapi import FastAPI
from fastapi.testclient import TestClient

from qwenpaw.enterprise.observability.metrics import MetricsRegistry
from qwenpaw.enterprise.observability.router import create_metrics_router


def test_metrics_router_exports_prometheus_text():
    app = FastAPI()
    registry = MetricsRegistry()
    registry.inc("http_requests_total", labels={"method": "GET", "route": "/api/version"})

    # 模拟真实 app 行为：router 在模块级别注册，运行时从 app.state 获取 registry
    app.include_router(create_metrics_router(), prefix="/api")

    # 无 registry 时返回空指标
    response1 = TestClient(app).get("/api/metrics")
    assert response1.status_code == 200
    assert "text/plain" in response1.headers["content-type"]
    assert "not available" in response1.text

    # 设置 registry 后返回真实指标
    class MockRuntime:
        class MockObservability:
            metrics = registry
        observability = MockObservability()

    app.state.enterprise_runtime = MockRuntime()
    response2 = TestClient(app).get("/api/metrics")
    assert response2.status_code == 200
    assert 'http_requests_total{method="GET",route="/api/version"} 1.0' in response2.text
