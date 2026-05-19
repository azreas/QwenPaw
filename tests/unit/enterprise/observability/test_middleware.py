from fastapi import FastAPI
from fastapi.testclient import TestClient

from qwenpaw.enterprise.observability.middleware import ObservabilityMiddleware
from qwenpaw.enterprise.observability.service import ObservabilityService
from qwenpaw.enterprise.runtime import EnterpriseRuntime


def test_observability_middleware_records_http_metrics():
    app = FastAPI()
    service = ObservabilityService()
    app.state.enterprise_runtime = EnterpriseRuntime(observability=service)
    app.add_middleware(ObservabilityMiddleware)

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    response = TestClient(app).get("/api/ping")

    assert response.status_code == 200
    text = service.metrics.to_prometheus_text()
    assert 'http_requests_total{method="GET",route="/api/ping",status="200"}' in text
