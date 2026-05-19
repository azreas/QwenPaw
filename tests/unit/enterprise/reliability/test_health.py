"""HealthService 单元测试。"""

import pytest

from qwenpaw.enterprise.reliability.health import HealthService
from qwenpaw.enterprise.reliability.models import HealthStatus


class GoodStorage:
    async def healthcheck(self):
        return {"status": "ok", "backend": "sqlite"}


class BadStorage:
    async def healthcheck(self):
        raise RuntimeError("db down")


@pytest.mark.asyncio
async def test_health_service_reports_ready_when_components_ok() -> None:
    """所有组件正常时应报告为就绪。"""
    service = HealthService(
        storage=GoodStorage(),
        audit=object(),
        observability=object(),
        quota=object(),
        extensions=object(),
    )

    report = await service.readiness()

    assert report.ready is True
    assert report.status is HealthStatus.OK
    assert any(c.name == "storage" for c in report.components)
    assert any(c.name == "disk" for c in report.components)


@pytest.mark.asyncio
async def test_ready_is_true_when_only_degraded_components() -> None:
    """只有 DEGRADED 组件时仍应可服务（ready=True）。"""
    # 未配置 audit、observability、quota 都是 DEGRADED
    service = HealthService(storage=GoodStorage(), audit=None, observability=None)

    report = await service.readiness()

    assert report.ready is True  # DEGRADED 不影响可服务性
    assert report.status is HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_health_service_reports_down_when_storage_fails() -> None:
    """存储失败时整体状态应为 DOWN，且不泄露异常详情。"""
    service = HealthService(storage=BadStorage(), audit=object(), observability=object())

    report = await service.readiness()

    assert report.ready is False
    storage_component = next(c for c in report.components if c.name == "storage")
    assert storage_component.status is HealthStatus.DOWN
    # 不应泄露内部异常详情
    assert "db down" not in storage_component.message
    assert "Storage health check failed" in storage_component.message


@pytest.mark.asyncio
async def test_unconfigured_components_are_degraded() -> None:
    """未配置的组件应为 DEGRADED 状态。"""
    service = HealthService(storage=GoodStorage(), audit=None, observability=None)

    report = await service.readiness()

    audit_component = next(c for c in report.components if c.name == "audit")
    assert audit_component.status is HealthStatus.DEGRADED
    assert "not configured" in audit_component.message
