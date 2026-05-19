# -*- coding: utf-8 -*-
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from qwenpaw.app.crons.models import CronJobSpec, CronJobState
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


class FakeCronManager:
    def __init__(self) -> None:
        self.jobs: dict[str, CronJobSpec] = {}
        self.created: list[CronJobSpec] = []
        self.deleted: list[str] = []
        self.paused: list[str] = []
        self.resumed: list[str] = []
        self.ran: list[str] = []

    async def list_jobs(self) -> list[CronJobSpec]:
        return list(self.jobs.values())

    async def get_job(self, job_id: str) -> CronJobSpec | None:
        return self.jobs.get(job_id)

    def get_state(self, job_id: str) -> CronJobState:
        return CronJobState(last_status="success" if job_id in self.jobs else None)

    async def create_or_replace_job(self, spec: CronJobSpec) -> None:
        assert spec.id is not None
        self.jobs[spec.id] = spec
        self.created.append(spec)

    async def delete_job(self, job_id: str) -> bool:
        self.deleted.append(job_id)
        return self.jobs.pop(job_id, None) is not None

    async def pause_job(self, job_id: str) -> None:
        self.paused.append(job_id)

    async def resume_job(self, job_id: str) -> None:
        self.resumed.append(job_id)

    async def run_job(self, job_id: str) -> None:
        if job_id not in self.jobs:
            raise KeyError(job_id)
        self.ran.append(job_id)


@pytest.fixture
def policy() -> TenantPolicy:
    return TenantPolicy(
        policy_id="default",
        task_timeout_seconds=42,
        max_cron_jobs=5,
    )


@pytest.fixture
def cron_manager() -> FakeCronManager:
    return FakeCronManager()


@pytest.fixture
def app(monkeypatch, policy, cron_manager):
    from qwenpaw.app.routers import webchat_tasks

    store = FakeTenantProductStore(policy)
    monkeypatch.setattr(
        "qwenpaw.app.webchat.session.get_webchat_session_secret",
        lambda: TEST_SECRET,
    )
    monkeypatch.setattr(webchat_tasks, "TenantProductStore", lambda: store)

    async def fake_workspace(request, identity):
        return SimpleNamespace(
            agent_id=identity.agent_id,
            cron_manager=cron_manager,
        )

    monkeypatch.setattr(
        webchat_tasks,
        "get_tenant_workspace_for_identity",
        fake_workspace,
    )

    app = FastAPI()
    app.include_router(webchat_tasks.router, prefix="/api")
    app.state.fake_store = store
    app.state.fake_cron_manager = cron_manager
    return app


@pytest.fixture
def client(app):
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def make_token() -> str:
    return sign_webchat_token(TEST_IDENTITY, secret=TEST_SECRET, ttl_seconds=60)


def make_task_payload(**overrides):
    payload = {
        "id": "client-job",
        "name": "每日提醒",
        "enabled": True,
        "schedule": {"type": "cron", "cron": "0 9 * * *", "timezone": "UTC"},
        "task_type": "agent",
        "request": {
            "input": [{"content": [{"type": "text", "text": "hello"}]}],
            "user_id": "attacker",
            "session_id": "attacker-session",
        },
        "dispatch": {
            "type": "channel",
            "channel": "console",
            "target": {
                "user_id": "attacker",
                "session_id": "console:attacker",
            },
            "mode": "final",
        },
        "runtime": {
            "timeout_seconds": 999,
            "max_concurrency": 9,
            "misfire_grace_seconds": 30,
        },
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_create_task_overrides_untrusted_dispatch_and_runtime(client, cron_manager):
    token = make_token()

    async with client:
        resp = await client.post(
            "/api/webchat/tasks",
            headers={"Authorization": f"Bearer {token}"},
            json=make_task_payload(),
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "client-job"
    assert body["dispatch"]["channel"] == "webchat"
    assert body["dispatch"]["target"]["user_id"] == "test_user"
    assert body["dispatch"]["target"]["session_id"] == "webchat:test_user:tasks"
    assert body["runtime"]["timeout_seconds"] == 42
    assert body["runtime"]["max_concurrency"] == 1
    assert body["request"]["user_id"] == "test_user"
    assert body["request"]["session_id"] == "webchat:test_user:tasks"

    saved = cron_manager.created[-1]
    assert saved.dispatch.channel == "webchat"
    assert saved.dispatch.target.user_id == "test_user"
    assert saved.dispatch.target.session_id == "webchat:test_user:tasks"
    assert saved.runtime.timeout_seconds == 42
    assert saved.runtime.max_concurrency == 1
    assert saved.request is not None
    assert saved.request.user_id == "test_user"
    assert saved.request.session_id == "webchat:test_user:tasks"


@pytest.mark.asyncio
async def test_tasks_reject_agent_id_query(client):
    token = make_token()

    async with client:
        resp = await client.get(
            "/api/webchat/tasks?agent_id=wx_other",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 400
    assert "agent_id" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_tasks_reject_agent_id_body(client):
    token = make_token()

    async with client:
        resp = await client.post(
            "/api/webchat/tasks",
            headers={"Authorization": f"Bearer {token}"},
            json=make_task_payload(agent_id="wx_other"),
        )

    assert resp.status_code == 400
    assert "agent_id" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_tasks_reject_reserved_job_id_create(client):
    token = make_token()

    async with client:
        resp = await client.post(
            "/api/webchat/tasks",
            headers={"Authorization": f"Bearer {token}"},
            json=make_task_payload(id="_heartbeat"),
        )

    assert resp.status_code == 400
    assert "reserved" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_tasks_reject_reserved_job_id_operations(client, cron_manager):
    token = make_token()

    async with client:
        put_resp = await client.put(
            "/api/webchat/tasks/_heartbeat",
            headers={"Authorization": f"Bearer {token}"},
            json=make_task_payload(id="_heartbeat"),
        )
        delete_resp = await client.delete(
            "/api/webchat/tasks/_heartbeat",
            headers={"Authorization": f"Bearer {token}"},
        )
        pause_resp = await client.post(
            "/api/webchat/tasks/_heartbeat/pause",
            headers={"Authorization": f"Bearer {token}"},
        )
        resume_resp = await client.post(
            "/api/webchat/tasks/_heartbeat/resume",
            headers={"Authorization": f"Bearer {token}"},
        )
        run_resp = await client.post(
            "/api/webchat/tasks/_heartbeat/run",
            headers={"Authorization": f"Bearer {token}"},
        )

    for resp in [put_resp, delete_resp, pause_resp, resume_resp, run_resp]:
        assert resp.status_code == 400
        assert "reserved" in resp.json()["detail"]

    assert cron_manager.created == []
    assert cron_manager.deleted == []
    assert cron_manager.paused == []
    assert cron_manager.resumed == []
    assert cron_manager.ran == []


@pytest.mark.asyncio
async def test_list_tasks_filters_non_webchat_jobs(client, cron_manager):
    token = make_token()
    webchat_job = CronJobSpec.model_validate(
        make_task_payload(
            dispatch={
                "type": "channel",
                "channel": "webchat",
                "target": {
                    "user_id": "test_user",
                    "session_id": "webchat:test_user:tasks",
                },
                "mode": "final",
            },
        ),
    )
    internal_job = CronJobSpec.model_validate(
        make_task_payload(
            id="console-job",
            dispatch={
                "type": "channel",
                "channel": "console",
                "target": {
                    "user_id": "admin",
                    "session_id": "console:admin",
                },
                "mode": "final",
            },
        ),
    )
    cron_manager.jobs["client-job"] = webchat_job
    cron_manager.jobs["console-job"] = internal_job

    async with client:
        resp = await client.get(
            "/api/webchat/tasks",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    assert [task["id"] for task in resp.json()["tasks"]] == ["client-job"]


@pytest.mark.asyncio
async def test_tasks_forbidden_when_policy_disables_tasks(client, policy):
    policy.allow_tasks = False
    token = make_token()

    async with client:
        resp = await client.get(
            "/api/webchat/tasks",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_run_forbidden_when_policy_disables_run_now(client, cron_manager, policy):
    policy.allow_task_run_now = False
    existing = CronJobSpec.model_validate(make_task_payload())
    cron_manager.jobs["client-job"] = existing
    token = make_token()

    async with client:
        resp = await client.post(
            "/api/webchat/tasks/client-job/run",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 403
    assert cron_manager.ran == []
