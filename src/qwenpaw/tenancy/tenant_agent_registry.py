# -*- coding: utf-8 -*-
"""TenantAgentRegistry：管理企业微信租户 Workspace 实例。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .ids import tenant_agent_id


class TenantAgentRegistry:
    """将 tenant_id 映射到动态 wx_* Workspace。"""

    def __init__(self, multi_agent_manager: Any):
        self._mam = multi_agent_manager

    async def get_or_create(self, tenant_id: str, workspace_dir: Path) -> Any:
        return await self._mam.get_or_create_tenant_agent(
            agent_id=tenant_agent_id(tenant_id),
            workspace_dir=workspace_dir,
        )
