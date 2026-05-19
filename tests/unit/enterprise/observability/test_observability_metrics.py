from qwenpaw.enterprise.observability.metrics import MetricsRegistry


def test_metrics_registry_counts_with_low_cardinality_labels():
    registry = MetricsRegistry()
    registry.inc("http_requests_total", labels={"method": "GET", "route": "/api/version"})
    registry.inc("http_requests_total", labels={"method": "GET", "route": "/api/version"})

    samples = registry.samples()
    assert samples[0].name == "http_requests_total"
    assert samples[0].value == 2


def test_metrics_registry_rejects_high_cardinality_labels():
    registry = MetricsRegistry()

    try:
        registry.inc("bad_metric", labels={"session_id": "s1"})
    except ValueError as exc:
        assert "session_id" in str(exc)
    else:
        raise AssertionError("session_id label must be rejected")
