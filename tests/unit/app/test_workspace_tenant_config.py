# -*- coding: utf-8 -*-
from unittest.mock import AsyncMock, patch

import pytest

from qwenpaw.app.workspace.workspace import Workspace
from qwenpaw.config.config import AgentProfileConfig


@pytest.mark.asyncio
async def test_workspace_uses_preloaded_agent_config(tmp_path):
    config = AgentProfileConfig(
        id="wx_alice",
        name="wx_alice",
        workspace_dir=str(tmp_path),
    )
    workspace = Workspace(
        agent_id="wx_alice",
        workspace_dir=tmp_path,
        agent_config=config,
    )

    with patch(
        "qwenpaw.app.workspace.workspace.load_agent_config",
        side_effect=AssertionError("should not load static profile"),
    ), patch(
        "qwenpaw.agents.skill_system.registry.ensure_skill_pool_initialized",
        return_value=None,
    ), patch(
        "qwenpaw.app.workspace.service_manager.ServiceManager.start_all",
        new=AsyncMock(),
    ):
        await workspace.start()

    assert workspace.config is config
