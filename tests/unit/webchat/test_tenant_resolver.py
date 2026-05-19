# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, Request

from qwenpaw.app.webchat.session import WebchatIdentity
from qwenpaw.app.webchat.tenant_resolver import (
    build_webchat_channel_facade,
    ensure_requested_agent_allowed,
    get_tenant_workspace_for_identity,
)


class FakeProvisioner:
    def __init__(self, workspace_dir: Path) -> None:
        self.workspace_dir = workspace_dir
        self.tenant_ids = []

    def ensure(self, tenant_id: str) -> Path:
        self.tenant_ids.append(tenant_id)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        return self.workspace_dir


class FakeManager:
    def __init__(self) -> None:
        self.calls = []

    async def get_or_create_tenant_agent(self, agent_id: str, workspace_dir):
        self.calls.append((agent_id, Path(workspace_dir)))
        return SimpleNamespace(agent_id=agent_id, workspace_dir=Path(workspace_dir))


def make_request(manager: FakeManager) -> Request:
    app = FastAPI()
    app.state.multi_agent_manager = manager
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/webchat/me",
        "headers": [],
        "app": app,
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_get_tenant_workspace_for_identity_uses_wx_agent(tmp_path):
    manager = FakeManager()
    provisioner = FakeProvisioner(tmp_path / "tenants" / "wx_test_user")
    identity = WebchatIdentity(
        employee_id="E000001",
        username="测试员工",
        wechat_company_id="test_user",
        tenant_id="test_user",
        agent_id="wx_test_user",
    )

    workspace = await get_tenant_workspace_for_identity(
        make_request(manager),
        identity,
        provisioner=provisioner,
    )

    assert workspace.agent_id == "wx_test_user"
    assert provisioner.tenant_ids == ["test_user"]
    assert manager.calls == [("wx_test_user", tmp_path / "tenants" / "wx_test_user")]


def test_ensure_requested_agent_allowed_accepts_current_agent():
    identity = WebchatIdentity(
        employee_id="E000001",
        username="测试员工",
        wechat_company_id="test_user",
        tenant_id="test_user",
        agent_id="wx_test_user",
    )

    assert ensure_requested_agent_allowed(identity, "wx_test_user") == "wx_test_user"
    assert ensure_requested_agent_allowed(identity, None) == "wx_test_user"


def test_ensure_requested_agent_allowed_rejects_other_agent():
    identity = WebchatIdentity(
        employee_id="E000001",
        username="测试员工",
        wechat_company_id="test_user",
        tenant_id="test_user",
        agent_id="wx_test_user",
    )

    with pytest.raises(PermissionError):
        ensure_requested_agent_allowed(identity, "wx_other")
