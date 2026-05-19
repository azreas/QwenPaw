# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException, Request

from qwenpaw.app.agent_context import get_agent_for_request
from qwenpaw.app.agent_resolver import ResolvedAgentRef
from qwenpaw.config.config import AgentProfileConfig


def make_request(agent_id: str, manager) -> Request:
    app = FastAPI()
    app.state.multi_agent_manager = manager
    scope = {
        "type": "http",
        "method": "GET",
        "path": f"/api/agents/{agent_id}/skills",
        "headers": [],
        "app": app,
    }
    request = Request(scope)
    request.state.agent_id = agent_id
    return request


def make_header_request(agent_id: str, manager) -> Request:
    app = FastAPI()
    app.state.multi_agent_manager = manager
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/skills",
        "headers": [(b"x-agent-id", agent_id.encode("utf-8"))],
        "app": app,
    }
    return Request(scope)


def resolved_ref(
    *,
    agent_id: str = "wx_alice",
    workspace_dir: Path | None = None,
    enabled: bool = True,
) -> ResolvedAgentRef:
    workspace_path = workspace_dir or Path("/tmp/tenants/wx_alice")
    return ResolvedAgentRef(
        agent_id=agent_id,
        workspace_dir=workspace_path,
        agent_config=AgentProfileConfig(
            id=agent_id,
            name=agent_id,
            workspace_dir=str(workspace_path),
        ),
        source="tenant_workspace",
        enabled=enabled,
    )


@pytest.mark.asyncio
async def test_get_agent_for_request_accepts_dynamic_tenant(monkeypatch, tmp_path):
    workspace = SimpleNamespace(
        agent_id="wx_alice",
        workspace_dir=tmp_path / "tenants" / "wx_alice",
    )
    manager = SimpleNamespace(get_agent=AsyncMock(return_value=workspace))
    resolved = resolved_ref(workspace_dir=Path(workspace.workspace_dir))

    monkeypatch.setattr(
        "qwenpaw.app.agent_context.AgentResolver",
        lambda: SimpleNamespace(resolve=lambda agent_id: resolved),
    )

    result = await get_agent_for_request(make_request("wx_alice", manager))

    assert result is workspace
    manager.get_agent.assert_awaited_once_with("wx_alice")


@pytest.mark.asyncio
async def test_get_agent_for_request_rejects_missing_dynamic_tenant(monkeypatch):
    manager = SimpleNamespace(get_agent=AsyncMock())

    monkeypatch.setattr(
        "qwenpaw.app.agent_context.AgentResolver",
        lambda: SimpleNamespace(resolve=lambda agent_id: None),
    )

    with pytest.raises(Exception) as exc_info:
        await get_agent_for_request(make_request("wx_missing", manager))

    assert getattr(exc_info.value, "status_code", None) == 404
    manager.get_agent.assert_not_called()


@pytest.mark.asyncio
async def test_get_agent_for_request_rejects_disabled_agent(monkeypatch):
    manager = SimpleNamespace(get_agent=AsyncMock())

    monkeypatch.setattr(
        "qwenpaw.app.agent_context.AgentResolver",
        lambda: SimpleNamespace(
            resolve=lambda agent_id: resolved_ref(
                agent_id=agent_id,
                enabled=False,
            ),
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_agent_for_request(make_request("disabled", manager))

    assert exc_info.value.status_code == 403
    manager.get_agent.assert_not_called()


@pytest.mark.asyncio
async def test_get_agent_for_request_accepts_x_agent_id_header(monkeypatch):
    workspace = SimpleNamespace(
        agent_id="wx_header",
        workspace_dir=Path("/tmp/tenants/wx_header"),
    )
    manager = SimpleNamespace(get_agent=AsyncMock(return_value=workspace))

    monkeypatch.setattr(
        "qwenpaw.app.agent_context.AgentResolver",
        lambda: SimpleNamespace(
            resolve=lambda agent_id: resolved_ref(agent_id=agent_id),
        ),
    )

    result = await get_agent_for_request(make_header_request("wx_header", manager))

    assert result is workspace
    manager.get_agent.assert_awaited_once_with("wx_header")


@pytest.mark.asyncio
async def test_get_agent_for_request_requires_manager(monkeypatch):
    app = FastAPI()
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/agents/wx_alice/skills",
            "headers": [],
            "app": app,
        }
    )
    request.state.agent_id = "wx_alice"

    monkeypatch.setattr(
        "qwenpaw.app.agent_context.AgentResolver",
        lambda: SimpleNamespace(resolve=lambda agent_id: resolved_ref()),
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_agent_for_request(request)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "MultiAgentManager not initialized"


@pytest.mark.asyncio
async def test_get_agent_for_request_preserves_manager_http_exception(monkeypatch):
    manager = SimpleNamespace(
        get_agent=AsyncMock(side_effect=HTTPException(status_code=404, detail="gone"))
    )

    monkeypatch.setattr(
        "qwenpaw.app.agent_context.AgentResolver",
        lambda: SimpleNamespace(resolve=lambda agent_id: resolved_ref()),
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_agent_for_request(make_request("wx_alice", manager))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "gone"


@pytest.mark.asyncio
async def test_get_agent_for_request_returns_404_when_manager_returns_none(
    monkeypatch,
):
    manager = SimpleNamespace(get_agent=AsyncMock(return_value=None))

    monkeypatch.setattr(
        "qwenpaw.app.agent_context.AgentResolver",
        lambda: SimpleNamespace(resolve=lambda agent_id: resolved_ref()),
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_agent_for_request(make_request("wx_alice", manager))

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_agent_for_request_translates_invalid_agent_config(monkeypatch):
    manager = SimpleNamespace(get_agent=AsyncMock())

    monkeypatch.setattr(
        "qwenpaw.app.agent_context.AgentResolver",
        lambda: SimpleNamespace(
            resolve=lambda agent_id: (_ for _ in ()).throw(ValueError("bad config")),
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_agent_for_request(make_request("wx_broken", manager))

    assert exc_info.value.status_code == 422
    assert "invalid" in exc_info.value.detail.lower()
    manager.get_agent.assert_not_called()
