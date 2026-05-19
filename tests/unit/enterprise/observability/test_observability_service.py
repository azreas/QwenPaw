from qwenpaw.enterprise.observability.service import ObservabilityService


def test_observability_service_records_runtime_metric():
    service = ObservabilityService()
    service.record_event("runtime_started_total", labels={"component": "enterprise"})

    assert "runtime_started_total" in service.metrics.to_prometheus_text()


def test_runtime_exposes_observability_service():
    from qwenpaw.enterprise.runtime import create_enterprise_runtime

    runtime = create_enterprise_runtime()
    assert isinstance(runtime.observability, ObservabilityService)
