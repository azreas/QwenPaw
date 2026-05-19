# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from qwenpaw.app.routers.wecom_tenant_management import router


class FakeTenantManager:
    def __init__(self) -> None:
        self.loaded: set[str] = set()
        self.started: list[tuple[str, Path]] = []
        self.stopped: list[str] = []

    def list_loaded_agents(self) -> list[str]:
        return sorted(self.loaded)

    def is_agent_loaded(self, agent_id: str) -> bool:
        return agent_id in self.loaded

    async def get_or_create_tenant_agent(self, agent_id: str, workspace_dir):
        self.loaded.add(agent_id)
        self.started.append((agent_id, Path(workspace_dir)))
        return SimpleNamespace(agent_id=agent_id)

    async def stop_agent(self, agent_id: str) -> bool:
        self.loaded.discard(agent_id)
        self.stopped.append(agent_id)
        return True


@pytest.fixture(autouse=True)
def _patch_working_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "qwenpaw.app.routers.wecom_tenant_management.WORKING_DIR",
        str(tmp_path),
    )
    monkeypatch.setattr(
        "qwenpaw.tenancy.tenant_agent_config.load_config",
        lambda: SimpleNamespace(agents=SimpleNamespace()),
    )
    return tmp_path


@pytest.fixture
def manager() -> FakeTenantManager:
    return FakeTenantManager()


@pytest.fixture
def api_client(manager):
    app = FastAPI()
    app.state.multi_agent_manager = manager
    app.include_router(router, prefix="/api")
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_list_wecom_tenants_returns_workspace_summaries(
    api_client,
    manager,
    _patch_working_dir,
):
    workspace_dir = _patch_working_dir / "tenants" / "wx_alice"
    workspace_dir.mkdir(parents=True)
    (workspace_dir / "agent.json").write_text(
        '{"id":"wx_alice","name":"Alice"}',
        encoding="utf-8",
    )
    (workspace_dir / "chats.json").write_text(
        '{"version":1,"chats":[{},{}]}',
        encoding="utf-8",
    )
    (workspace_dir / "jobs.json").write_text(
        '{"version":1,"jobs":[{}]}',
        encoding="utf-8",
    )
    manager.loaded.add("wx_alice")

    async with api_client:
        resp = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants",
        )

    assert resp.status_code == 200
    tenants = resp.json()["tenants"]
    assert tenants[0]["agent_id"] == "wx_alice"
    assert tenants[0]["tenant_id"] == "alice"
    assert tenants[0]["initialized"] is True
    assert tenants[0]["running"] is True
    assert tenants[0]["chat_count"] == 2
    assert tenants[0]["job_count"] == 1


async def test_list_wecom_tenants_merges_loaded_agents(
    api_client,
    manager,
):
    manager.loaded.add("wx_runtime_only")
    manager.loaded.add("default")

    async with api_client:
        resp = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants",
        )

    assert resp.status_code == 200
    tenants = resp.json()["tenants"]
    assert [item["agent_id"] for item in tenants] == ["wx_runtime_only"]
    assert tenants[0]["running"] is True
    assert tenants[0]["exists"] is False


async def test_create_wecom_tenant_initializes_workspace(
    api_client,
    _patch_working_dir,
):
    async with api_client:
        resp = await api_client.post(
            "/api/config/channels/wecom_tenant/tenants",
            json={"tenant_id": "alice"},
        )

    assert resp.status_code == 201
    payload = resp.json()
    assert payload["agent_id"] == "wx_alice"
    assert payload["initialized"] is True
    assert (
        _patch_working_dir / "tenants" / "wx_alice" / "agent.json"
    ).is_file()


async def test_create_wecom_tenant_can_start_workspace(
    api_client,
    manager,
):
    async with api_client:
        resp = await api_client.post(
            "/api/config/channels/wecom_tenant/tenants",
            json={"tenant_id": "alice", "start": True},
        )

    assert resp.status_code == 201
    assert resp.json()["running"] is True
    assert manager.started[0][0] == "wx_alice"


async def test_start_wecom_tenant_requires_workspace(
    api_client,
):
    async with api_client:
        resp = await api_client.post(
            "/api/config/channels/wecom_tenant/tenants/wx_missing/start",
        )

    assert resp.status_code == 404


async def test_stop_wecom_tenant_updates_running_state(
    api_client,
    manager,
    _patch_working_dir,
):
    workspace_dir = _patch_working_dir / "tenants" / "wx_alice"
    workspace_dir.mkdir(parents=True)
    (workspace_dir / "agent.json").write_text("{}", encoding="utf-8")
    manager.loaded.add("wx_alice")

    async with api_client:
        resp = await api_client.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/stop",
        )

    assert resp.status_code == 200
    assert resp.json()["running"] is False
    assert manager.stopped == ["wx_alice"]


async def test_restart_wecom_tenant_stops_then_starts(
    api_client,
    manager,
    _patch_working_dir,
):
    workspace_dir = _patch_working_dir / "tenants" / "wx_alice"
    workspace_dir.mkdir(parents=True)
    (workspace_dir / "agent.json").write_text("{}", encoding="utf-8")
    manager.loaded.add("wx_alice")

    async with api_client:
        resp = await api_client.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/restart",
        )

    assert resp.status_code == 200
    assert resp.json()["running"] is True
    assert manager.stopped == ["wx_alice"]
    assert manager.started[-1][0] == "wx_alice"


async def test_rejects_non_tenant_agent(api_client):
    async with api_client:
        resp = await api_client.post(
            "/api/config/channels/wecom_tenant/tenants/default/start",
        )

    assert resp.status_code == 400


async def test_returns_503_when_manager_missing():
    app = FastAPI()
    app.include_router(router, prefix="/api")
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        resp = await client.get(
            "/api/config/channels/wecom_tenant/tenants",
        )

    assert resp.status_code == 503
