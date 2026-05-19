# -*- coding: utf-8 -*-
from unittest.mock import AsyncMock, MagicMock

import pytest

from qwenpaw.tenancy.tenant_agent_registry import TenantAgentRegistry


@pytest.mark.asyncio
async def test_get_or_create_maps_tenant_to_wx_agent(tmp_path):
    manager = MagicMock()
    manager.get_or_create_tenant_agent = AsyncMock(return_value="workspace")
    registry = TenantAgentRegistry(manager)

    result = await registry.get_or_create("alice", tmp_path / "wx_alice")

    assert result == "workspace"
    manager.get_or_create_tenant_agent.assert_awaited_once_with(
        agent_id="wx_alice",
        workspace_dir=tmp_path / "wx_alice",
    )
