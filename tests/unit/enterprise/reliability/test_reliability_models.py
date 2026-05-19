"""可靠性模型单元测试。"""

from qwenpaw.enterprise.reliability.models import (
    ComponentHealth,
    HealthStatus,
    ReadinessReport,
)


def test_readiness_report_is_ready_when_all_components_ok() -> None:
    """所有组件正常时应报告为就绪。"""
    report = ReadinessReport(
        components=[
            ComponentHealth(name="storage", status=HealthStatus.OK),
            ComponentHealth(name="audit", status=HealthStatus.OK),
        ]
    )

    assert report.ready is True
    assert report.status is HealthStatus.OK


def test_readiness_report_degrades_on_any_failure() -> None:
    """任何组件失败时应降级状态。"""
    report = ReadinessReport(
        components=[
            ComponentHealth(name="storage", status=HealthStatus.OK),
            ComponentHealth(name="redis", status=HealthStatus.DOWN, message="refused"),
        ]
    )

    assert report.ready is False
    assert report.status is HealthStatus.DOWN


def test_readiness_report_degraded_status() -> None:
    """包含 degraded 组件时整体状态为 degraded，但仍可服务（ready=True）。"""
    report = ReadinessReport(
        components=[
            ComponentHealth(name="storage", status=HealthStatus.OK),
            ComponentHealth(name="disk", status=HealthStatus.DEGRADED, message="low space"),
        ]
    )

    assert report.ready is True  # DEGRADED 不影响可服务性
    assert report.status is HealthStatus.DEGRADED


def test_readiness_report_as_dict() -> None:
    """as_dict() 应正确序列化所有字段。"""
    report = ReadinessReport(
        components=[
            ComponentHealth(
                name="storage",
                status=HealthStatus.OK,
                latency_ms=12.5,
                details={"backend": "sqlite"},
            ),
        ]
    )

    result = report.as_dict()

    assert result["ready"] is True
    assert result["status"] == "ok"
    assert "checked_at" in result
    assert len(result["components"]) == 1
    assert result["components"][0]["name"] == "storage"
    assert result["components"][0]["latency_ms"] == 12.5
    assert result["components"][0]["details"]["backend"] == "sqlite"
