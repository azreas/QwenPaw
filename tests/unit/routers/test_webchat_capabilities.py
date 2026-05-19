# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from qwenpaw.app.webchat.session import WebchatIdentity, sign_webchat_token
from qwenpaw.tenancy.product_models import TenantPolicy, TenantRecord

TEST_SECRET = "test-secret"
TEST_IDENTITY = WebchatIdentity(
    employee_id="E000001",
    username="测试员工",
    wechat_company_id="test_user",
    tenant_id="test_user",
    agent_id="wx_test_user",
)


class FakeTenantProductStore:
    def __init__(self, policy: TenantPolicy) -> None:
        self.policy = policy
        self.tenant: TenantRecord | None = None

    def get_tenant(self, tenant_id: str) -> TenantRecord | None:
        return self.tenant if self.tenant and self.tenant.tenant_id == tenant_id else None

    def upsert_tenant(self, tenant: TenantRecord) -> TenantRecord:
        self.tenant = tenant
        return tenant

    def get_policy(self, policy_id: str) -> TenantPolicy | None:
        if policy_id in {self.policy.policy_id, "default"}:
            return self.policy
        return None


@pytest.fixture
def policy() -> TenantPolicy:
    return TenantPolicy(
        policy_id="locked-down",
        allow_tasks=False,
        allow_mcp=False,
        allow_skill_upload_zip=False,
        advanced_config_enabled=False,
    )


@pytest.fixture
def app(monkeypatch, policy):
    from qwenpaw.app.routers import webchat_capabilities

    store = FakeTenantProductStore(policy)
    monkeypatch.setattr(
        "qwenpaw.app.webchat.session.get_webchat_session_secret",
        lambda: TEST_SECRET,
    )
    monkeypatch.setattr(
        webchat_capabilities,
        "TenantProductStore",
        lambda: store,
    )
    app = FastAPI()
    app.include_router(webchat_capabilities.router, prefix="/api")
    app.state.fake_store = store
    return app


@pytest.fixture
def client(app):
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def make_token() -> str:
    return sign_webchat_token(TEST_IDENTITY, secret=TEST_SECRET, ttl_seconds=60)


@pytest.mark.asyncio
async def test_capabilities_apply_tenant_policy(client):
    token = make_token()

    async with client:
        resp = await client.get(
            "/api/webchat/capabilities",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == "test_user"
    assert body["agent_id"] == "wx_test_user"
    assert body["policy_id"] == "locked-down"
    capabilities = body["capabilities"]
    assert capabilities["tasks"] is False
    assert capabilities["task_run_now"] is False
    assert capabilities["mcp"] is False
    assert capabilities["skill_upload_zip"] is False
    assert capabilities["advanced_config"] is False
    assert capabilities["platform_ops"] is False
    assert capabilities["chat"] is True
    assert body["limits"]["max_cron_jobs"] == 20


@pytest.mark.asyncio
async def test_capabilities_require_token(client):
    async with client:
        resp = await client.get("/api/webchat/capabilities")

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_platform_ops_is_never_exposed(client, policy):
    policy.allow_tasks = True
    policy.allow_mcp = True
    policy.allow_skill_upload_zip = True
    policy.advanced_config_enabled = True
    token = make_token()

    async with client:
        resp = await client.get(
            "/api/webchat/capabilities",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    assert resp.json()["capabilities"]["platform_ops"] is False
