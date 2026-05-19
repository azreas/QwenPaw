# -*- coding: utf-8 -*-
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from qwenpaw.app.agent_resolver import ResolvedAgentRef
from qwenpaw.app.multi_agent_manager import MultiAgentManager
from qwenpaw.config.config import AgentProfileConfig


@pytest.mark.asyncio
async def test_get_or_create_tenant_agent_creates_workspace(tmp_path):
    manager = MultiAgentManager()
    mock_ws = MagicMock()
    mock_ws.start = AsyncMock()
    mock_ws.set_manager = MagicMock()
    created = {}

    def make_workspace(**kwargs):
        created.update(kwargs)
        return mock_ws

    with patch(
        "qwenpaw.app.multi_agent_manager.Workspace",
        side_effect=make_workspace,
    ):
        result = await manager.get_or_create_tenant_agent(
            agent_id="wx_alice",
            workspace_dir=tmp_path / "wx_alice",
        )

    assert result is mock_ws
    assert created["agent_id"] == "wx_alice"
    assert created["agent_config"].id == "wx_alice"
    mock_ws.set_manager.assert_called_once_with(manager)
    mock_ws.start.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_or_create_tenant_agent_concurrent_starts_once(tmp_path):
    manager = MultiAgentManager()
    mock_ws = MagicMock()
    mock_ws.start = AsyncMock()
    mock_ws.set_manager = MagicMock()
    count = 0

    def make_workspace(**kwargs):
        nonlocal count
        count += 1
        return mock_ws

    with patch(
        "qwenpaw.app.multi_agent_manager.Workspace",
        side_effect=make_workspace,
    ):
        await asyncio.gather(
            manager.get_or_create_tenant_agent("wx_alice", tmp_path / "wx_alice"),
            manager.get_or_create_tenant_agent("wx_alice", tmp_path / "wx_alice"),
            manager.get_or_create_tenant_agent("wx_alice", tmp_path / "wx_alice"),
        )

    assert count == 1


@pytest.mark.asyncio
async def test_get_agent_loads_dynamic_tenant_from_resolver(tmp_path):
    manager = MultiAgentManager()
    workspace_dir = tmp_path / "tenants" / "wx_alice"
    agent_config = AgentProfileConfig(
        id="wx_alice",
        name="Alice",
        workspace_dir=str(workspace_dir),
    )
    resolved = ResolvedAgentRef(
        agent_id="wx_alice",
        workspace_dir=workspace_dir,
        agent_config=agent_config,
        source="tenant_workspace",
    )
    mock_ws = MagicMock()
    mock_ws.start = AsyncMock()
    mock_ws.set_manager = MagicMock()
    created = {}

    def make_workspace(**kwargs):
        created.update(kwargs)
        return mock_ws

    with patch.object(manager, "_resolve_agent_ref", return_value=resolved):
        with patch(
            "qwenpaw.app.multi_agent_manager.Workspace",
            side_effect=make_workspace,
        ):
            result = await manager.get_agent("wx_alice")

    assert result is mock_ws
    assert created["agent_id"] == "wx_alice"
    assert created["workspace_dir"] == workspace_dir
    assert created["agent_config"] is agent_config
    assert manager._agent_refs["wx_alice"] is resolved


@pytest.mark.asyncio
async def test_get_agent_normalizes_agent_id_cache_key(tmp_path):
    manager = MultiAgentManager()
    workspace_dir = tmp_path / "tenants" / "wx_alice"
    agent_config = AgentProfileConfig(
        id="wx_alice",
        name="Alice",
        workspace_dir=str(workspace_dir),
    )
    resolved = ResolvedAgentRef(
        agent_id="wx_alice",
        workspace_dir=workspace_dir,
        agent_config=agent_config,
        source="tenant_workspace",
    )
    mock_ws = MagicMock()
    mock_ws.start = AsyncMock()
    mock_ws.stop = AsyncMock()
    mock_ws.set_manager = MagicMock()

    with patch.object(manager, "_resolve_agent_ref", return_value=resolved):
        with patch(
            "qwenpaw.app.multi_agent_manager.Workspace",
            return_value=mock_ws,
        ):
            result = await manager.get_agent(" wx_alice ")

    assert result is mock_ws
    assert manager.list_loaded_agents() == ["wx_alice"]
    assert await manager.stop_agent("wx_alice") is True
    mock_ws.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_agent_uses_resolved_agent_id_as_cache_key(tmp_path):
    manager = MultiAgentManager()
    workspace_dir = tmp_path / "tenants" / "wx_alice"
    resolved = ResolvedAgentRef(
        agent_id="wx_alice",
        workspace_dir=workspace_dir,
        agent_config=AgentProfileConfig(
            id="wx_alice",
            name="Alice",
            workspace_dir=str(workspace_dir),
        ),
        source="tenant_workspace",
    )
    mock_ws = MagicMock()
    mock_ws.start = AsyncMock()
    mock_ws.set_manager = MagicMock()
    constructed = 0

    def make_workspace(**kwargs):
        nonlocal constructed
        constructed += 1
        return mock_ws

    with patch.object(manager, "_resolve_agent_ref", return_value=resolved):
        with patch(
            "qwenpaw.app.multi_agent_manager.Workspace",
            side_effect=make_workspace,
        ):
            assert await manager.get_agent("alias") is mock_ws
            assert await manager.get_agent("wx_alice") is mock_ws

    assert constructed == 1
    assert manager.list_loaded_agents() == ["wx_alice"]


@pytest.mark.asyncio
async def test_get_agent_constructor_failure_cleans_pending(tmp_path):
    manager = MultiAgentManager()
    workspace_dir = tmp_path / "tenants" / "wx_alice"
    resolved = ResolvedAgentRef(
        agent_id="wx_alice",
        workspace_dir=workspace_dir,
        agent_config=AgentProfileConfig(
            id="wx_alice",
            name="Alice",
            workspace_dir=str(workspace_dir),
        ),
        source="tenant_workspace",
    )

    with patch.object(manager, "_resolve_agent_ref", return_value=resolved):
        with patch(
            "qwenpaw.app.multi_agent_manager.Workspace",
            side_effect=RuntimeError("boom"),
        ):
            with pytest.raises(RuntimeError, match="boom"):
                await manager.get_agent("wx_alice")

    assert "wx_alice" not in manager._pending_starts

    mock_ws = MagicMock()
    mock_ws.start = AsyncMock()
    mock_ws.set_manager = MagicMock()
    with patch.object(manager, "_resolve_agent_ref", return_value=resolved):
        with patch(
            "qwenpaw.app.multi_agent_manager.Workspace",
            return_value=mock_ws,
        ):
            assert await manager.get_agent("wx_alice") is mock_ws


@pytest.mark.asyncio
async def test_reload_agent_uses_dynamic_agent_config(tmp_path):
    manager = MultiAgentManager()
    workspace_dir = tmp_path / "tenants" / "wx_alice"
    old_ws = MagicMock()
    old_ws.task_tracker.has_active_tasks = AsyncMock(return_value=False)
    old_ws.stop = AsyncMock()
    old_ws._service_manager.get_reusable_services.return_value = {}
    manager.agents["wx_alice"] = old_ws
    agent_config = AgentProfileConfig(
        id="wx_alice",
        name="Alice",
        workspace_dir=str(workspace_dir),
    )
    resolved = ResolvedAgentRef(
        agent_id="wx_alice",
        workspace_dir=workspace_dir,
        agent_config=agent_config,
        source="tenant_workspace",
    )
    new_ws = MagicMock()
    new_ws.start = AsyncMock()
    new_ws.stop = AsyncMock()
    new_ws.set_manager = MagicMock()
    new_ws.set_reusable_components = AsyncMock()
    created = {}

    def make_workspace(**kwargs):
        created.update(kwargs)
        return new_ws

    with patch.object(manager, "_resolve_agent_ref", return_value=resolved):
        with patch(
            "qwenpaw.app.multi_agent_manager.Workspace",
            side_effect=make_workspace,
        ):
            reloaded = await manager.reload_agent("wx_alice")

    assert reloaded is True
    assert created["agent_config"] is agent_config
    assert manager.agents["wx_alice"] is new_ws
    old_ws.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_reload_agent_constructor_failure_returns_false(tmp_path):
    manager = MultiAgentManager()
    workspace_dir = tmp_path / "tenants" / "wx_alice"
    old_ws = MagicMock()
    old_ws.task_tracker.has_active_tasks = AsyncMock(return_value=False)
    old_ws.stop = AsyncMock()
    manager.agents["wx_alice"] = old_ws
    resolved = ResolvedAgentRef(
        agent_id="wx_alice",
        workspace_dir=workspace_dir,
        agent_config=AgentProfileConfig(
            id="wx_alice",
            name="Alice",
            workspace_dir=str(workspace_dir),
        ),
        source="tenant_workspace",
    )

    with patch.object(manager, "_resolve_agent_ref", return_value=resolved):
        with patch(
            "qwenpaw.app.multi_agent_manager.Workspace",
            side_effect=RuntimeError("boom"),
        ):
            assert await manager.reload_agent("wx_alice") is False

    assert manager.agents["wx_alice"] is old_ws
    old_ws.stop.assert_not_called()
