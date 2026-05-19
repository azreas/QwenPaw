from fastapi import FastAPI
from fastapi.testclient import TestClient

from qwenpaw.enterprise.context import RequestContext
from qwenpaw.enterprise.policy.deps import require_policy
from qwenpaw.enterprise.policy.models import PolicyAction, PolicyEffect, PolicyRule
from qwenpaw.enterprise.policy.service import PolicyService
from qwenpaw.enterprise.runtime import EnterpriseRuntime


class CaptureBus:
    def __init__(self):
        self.events = []

    async def emit(self, event):
        self.events.append(event)


def test_require_policy_allows_when_decision_allows():
    app = FastAPI()
    app.state.enterprise_runtime = EnterpriseRuntime(policy=PolicyService())

    @app.get("/export", dependencies=[require_policy(PolicyAction.DATA_EXPORT, "csv")])
    def export():
        return {"ok": True}

    @app.middleware("http")
    async def inject_context(request, call_next):
        request.state.request_context = RequestContext("r", "t")
        return await call_next(request)

    assert TestClient(app).get("/export").status_code == 200


def test_require_policy_denies_when_policy_denies():
    bus = CaptureBus()
    app = FastAPI()
    app.state.enterprise_runtime = EnterpriseRuntime(
        audit=bus,
        policy=PolicyService(
            rules=[
                PolicyRule(
                    rule_id="deny-export",
                    effect=PolicyEffect.DENY,
                    action=PolicyAction.DATA_EXPORT,
                    resource="csv",
                    reason="export blocked",
                )
            ]
        )
    )

    @app.get("/export", dependencies=[require_policy(PolicyAction.DATA_EXPORT, "csv")])
    def export():
        return {"ok": True}

    @app.middleware("http")
    async def inject_context(request, call_next):
        request.state.request_context = RequestContext("r", "t")
        return await call_next(request)

    response = TestClient(app).get("/export")
    assert response.status_code == 403
    body = response.json()["detail"]
    assert body["detail"] == "export blocked"
    assert body["error_code"] == "policy.denied"
    platform_events = [
        event
        for event in bus.events
        if event.event_type == "platform.invocation"
    ]
    assert len(platform_events) == 1
    assert platform_events[0].payload["call_type"] == "policy"
    assert platform_events[0].payload["status"] == "denied"
    assert platform_events[0].payload["error_code"] == "policy.denied"
