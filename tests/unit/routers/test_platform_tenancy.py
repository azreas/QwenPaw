# -*- coding: utf-8 -*-
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from qwenpaw.enterprise.audit.models import AuditEventType, AuditOutcome
from qwenpaw.tenancy.product_models import TenantPolicy, TenantRecord, TenantTemplate


class FakeTenantProductStore:
    def __init__(self) -> None:
        self.tenants = [
            TenantRecord(
                tenant_id="alice",
                display_name="Alice",
                agent_id="wx_alice",
                source="webchat",
            ),
        ]
        self.policies = [TenantPolicy()]
        self.templates = [TenantTemplate()]

    def list_tenants(self) -> list[TenantRecord]:
        return list(self.tenants)

    def list_policies(self) -> list[TenantPolicy]:
        return list(self.policies)

    def upsert_policy(self, policy: TenantPolicy) -> TenantPolicy:
        for index, existing in enumerate(self.policies):
            if existing.policy_id == policy.policy_id:
                self.policies[index] = policy
                break
        else:
            self.policies.append(policy)
        return policy

    def delete_policy(self, policy_id: str) -> bool:
        for index, existing in enumerate(self.policies):
            if existing.policy_id == policy_id:
                del self.policies[index]
                return True
        return False

    def list_templates(self) -> list[TenantTemplate]:
        return list(self.templates)

    def upsert_template(self, template: TenantTemplate) -> TenantTemplate:
        for index, existing in enumerate(self.templates):
            if existing.template_id == template.template_id:
                self.templates[index] = template
                break
        else:
            self.templates.append(template)
        return template

    def delete_template(self, template_id: str) -> bool:
        for index, existing in enumerate(self.templates):
            if existing.template_id == template_id:
                del self.templates[index]
                return True
        return False


class CaptureBus:
    def __init__(self) -> None:
        self.events = []

    async def emit(self, event) -> None:
        self.events.append(event)


@pytest.fixture
def store() -> FakeTenantProductStore:
    return FakeTenantProductStore()


@pytest.fixture
def audit_bus() -> CaptureBus:
    return CaptureBus()


@pytest.fixture
def app(monkeypatch, store, audit_bus):
    from qwenpaw.app.routers import platform_tenancy

    monkeypatch.setattr(
        platform_tenancy,
        "TenantProductStore",
        lambda: store,
    )
    app = FastAPI()
    app.state.enterprise_runtime = SimpleNamespace(audit=audit_bus)
    app.include_router(platform_tenancy.router, prefix="/api")
    return app


@pytest.fixture
def client(app):
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_list_tenants_returns_store_records(client):
    async with client:
        resp = await client.get("/api/platform/tenancy/tenants")

    assert resp.status_code == 200
    body = resp.json()
    assert body["tenants"][0]["tenant_id"] == "alice"
    assert body["tenants"][0]["agent_id"] == "wx_alice"


@pytest.mark.asyncio
async def test_upsert_policy_and_list_policies(client, store):
    payload = TenantPolicy(
        policy_id="member-safe",
        display_name="成员安全策略",
        allow_mcp=False,
        allow_tasks=False,
    ).model_dump(mode="json")

    async with client:
        put_resp = await client.put(
            "/api/platform/tenancy/policies/member-safe",
            json=payload,
        )
        list_resp = await client.get("/api/platform/tenancy/policies")

    assert put_resp.status_code == 200
    assert put_resp.json()["policy_id"] == "member-safe"
    assert store.policies[-1].allow_mcp is False
    policies = list_resp.json()["policies"]
    assert any(policy["policy_id"] == "member-safe" for policy in policies)


@pytest.mark.asyncio
async def test_upsert_policy_rejects_path_body_mismatch(client, audit_bus):
    payload = TenantPolicy(policy_id="body-id").model_dump(mode="json")

    async with client:
        resp = await client.put(
            "/api/platform/tenancy/policies/path-id",
            json=payload,
        )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "policy_id mismatch"
    assert len(audit_bus.events) == 1
    event = audit_bus.events[0]
    assert event.event_type == AuditEventType.TENANT_UPDATED
    assert event.action == "upsert_policy"
    assert event.outcome == AuditOutcome.FAILURE
    assert event.resource_type == "tenant_policy"
    assert event.resource_id == "path-id"
    assert event.payload["reason"] == "policy_id_mismatch"
    assert event.payload["policy_id"] == "path-id"
    assert event.payload["body_policy_id"] == "body-id"


@pytest.mark.asyncio
async def test_delete_policy_rejects_default_policy(client):
    async with client:
        resp = await client.delete("/api/platform/tenancy/policies/default")

    assert resp.status_code == 400
    assert resp.json()["detail"] == "default policy cannot be deleted"


@pytest.mark.asyncio
async def test_delete_policy_rejects_in_use_policy(client, store):
    store.tenants[0] = store.tenants[0].model_copy(
        update={"policy_id": "member-safe"},
    )
    store.policies.append(TenantPolicy(policy_id="member-safe"))

    async with client:
        resp = await client.delete("/api/platform/tenancy/policies/member-safe")

    assert resp.status_code == 409
    assert resp.json()["detail"] == "policy is in use"


@pytest.mark.asyncio
async def test_delete_policy_removes_unused_policy(client, store):
    store.policies.append(TenantPolicy(policy_id="member-safe"))

    async with client:
        resp = await client.delete("/api/platform/tenancy/policies/member-safe")

    assert resp.status_code == 200
    assert resp.json()["deleted"] is True
    assert all(policy.policy_id != "member-safe" for policy in store.policies)


@pytest.mark.asyncio
async def test_upsert_template_and_list_templates(client, store):
    payload = TenantTemplate(
        template_id="starter",
        display_name="成员模板",
        default_model="gpt-4o-mini",
        default_tools=["search"],
    ).model_dump(mode="json")

    async with client:
        put_resp = await client.put(
            "/api/platform/tenancy/templates/starter",
            json=payload,
        )
        list_resp = await client.get("/api/platform/tenancy/templates")

    assert put_resp.status_code == 200
    assert put_resp.json()["template_id"] == "starter"
    assert store.templates[-1].default_model == "gpt-4o-mini"
    templates = list_resp.json()["templates"]
    assert any(template["template_id"] == "starter" for template in templates)


@pytest.mark.asyncio
async def test_upsert_template_rejects_path_body_mismatch(client):
    payload = TenantTemplate(template_id="body-id").model_dump(mode="json")

    async with client:
        resp = await client.put(
            "/api/platform/tenancy/templates/path-id",
            json=payload,
        )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "template_id mismatch"


@pytest.mark.asyncio
async def test_delete_template_rejects_default_template(client):
    async with client:
        resp = await client.delete("/api/platform/tenancy/templates/default")

    assert resp.status_code == 400
    assert resp.json()["detail"] == "default template cannot be deleted"


@pytest.mark.asyncio
async def test_delete_template_removes_unused_template(client, store):
    store.templates.append(TenantTemplate(template_id="starter"))

    async with client:
        resp = await client.delete("/api/platform/tenancy/templates/starter")

    assert resp.status_code == 200
    assert resp.json()["deleted"] is True
    assert all(template.template_id != "starter" for template in store.templates)
