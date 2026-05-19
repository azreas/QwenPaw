from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request

from qwenpaw.enterprise.context import RequestContext
from qwenpaw.enterprise.quota.middleware import QuotaMiddleware
from qwenpaw.enterprise.quota.models import QuotaDimension, QuotaLimit, QuotaWindow
from qwenpaw.enterprise.quota.service import QuotaService
from qwenpaw.enterprise.quota.store import InMemoryQuotaStore
from qwenpaw.enterprise.runtime import EnterpriseRuntime


class CaptureBus:
    def __init__(self):
        self.events = []

    async def emit(self, event):
        self.events.append(event)


def test_quota_middleware_returns_429_after_limit():
    bus = CaptureBus()
    app = FastAPI()
    app.state.enterprise_runtime = EnterpriseRuntime(
        audit=bus,
        quota=QuotaService(
            store=InMemoryQuotaStore(),
            limits=[
                QuotaLimit(
                    dimension=QuotaDimension.HTTP_REQUEST,
                    window=QuotaWindow.MINUTE,
                    max_value=1,
                    resource="GET:/api/ping",
                )
            ],
        )
    )
    app.add_middleware(QuotaMiddleware)

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/api/ping").status_code == 200
    response = client.get("/api/ping")
    assert response.status_code == 429
    body = response.json()
    assert body["detail"] == "quota exceeded"
    assert body["error_code"] == "quota.denied"
    assert body["recoverable"] is True
    platform_events = [
        event
        for event in bus.events
        if event.event_type == "platform.invocation"
    ]
    assert len(platform_events) == 1
    assert platform_events[0].payload["call_type"] == "quota"
    assert platform_events[0].payload["status"] == "denied"
    assert platform_events[0].payload["error_code"] == "quota.denied"


class PreWriteEmptyTenantContextMiddleware(BaseHTTPMiddleware):
    """模拟 Authz 先写空 tenant ctx，AgentContext 后写 agent_id 的真实场景"""
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ):
        # Authz-like: 先写入空 tenant 的 context
        request.state.request_context = RequestContext(
            request_id="req_123",
            trace_id="trace_456",
            tenant_id="",
            agent_id="",
        )
        # AgentContext-like: 后写 agent_id state
        request.state.agent_id = "wx_acme"
        return await call_next(request)


def test_quota_middleware_fills_tenant_id_from_agent_id_post_injection():
    """回归测试：已有空 tenant RequestContext + agent_id 后置注入时，应正确补全 tenant_id 触发租户级配额"""
    bus = CaptureBus()
    app = FastAPI()
    app.state.enterprise_runtime = EnterpriseRuntime(
        audit=bus,
        quota=QuotaService(
            store=InMemoryQuotaStore(),
            limits=[
                QuotaLimit(
                    dimension=QuotaDimension.HTTP_REQUEST,
                    window=QuotaWindow.MINUTE,
                    max_value=1,
                    tenant_id="wx_acme",  # 租户级配额
                    resource="GET:/api/ping",
                )
            ],
        )
    )
    # 注册顺序（LIFO）：Quota 后执行
    app.add_middleware(QuotaMiddleware)
    app.add_middleware(PreWriteEmptyTenantContextMiddleware)

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    client = TestClient(app)
    # 第一次请求通过
    assert client.get("/api/ping").status_code == 200
    # 第二次请求应触发租户级配额 429
    response = client.get("/api/ping")
    assert response.status_code == 429, f"预期 429 但得到 {response.status_code}，租户级配额未生效"
    assert response.json()["detail"] == "quota exceeded"
    platform_events = [
        event
        for event in bus.events
        if event.event_type == "platform.invocation"
    ]
    assert len(platform_events) == 1
    assert platform_events[0].payload["call_type"] == "quota"
    assert platform_events[0].payload["status"] == "denied"
    assert platform_events[0].payload["tenant_id"] == "wx_acme"
