# -*- coding: utf-8 -*-
"""Cron dispatch adapter for dynamic tenant workspaces."""
from __future__ import annotations

from typing import Any


class TenantCronDispatchChannelManager:
    """Resolve cron dispatch channels at execution time.

    Dynamic tenant workspaces often do not own WeCom/WebChat channel
    instances. Their cron jobs still dispatch through the already loaded
    root workspace channel manager that owns the actual channel client.
    """

    def __init__(self, workspace: Any) -> None:
        self._workspace = workspace

    async def _has_channel(self, manager: Any, channel: str) -> bool:
        if manager is None or not hasattr(manager, "get_channel"):
            return False
        return await manager.get_channel(channel.lower()) is not None

    async def _resolve_manager(self, channel: str) -> Any:
        service_manager = (  # pylint: disable=protected-access
            self._workspace._service_manager
        )
        local = service_manager.services.get("channel_manager")
        if await self._has_channel(local, channel):
            return local

        multi_agent_manager = getattr(self._workspace, "_manager", None)
        for workspace in getattr(multi_agent_manager, "agents", {}).values():
            if workspace is self._workspace:
                continue
            manager = getattr(workspace, "channel_manager", None)
            if await self._has_channel(manager, channel):
                return manager

        return local

    async def send_text(self, **kwargs) -> None:
        channel = str(kwargs.get("channel") or "")
        manager = await self._resolve_manager(channel)
        if manager is None:
            raise KeyError(f"channel manager not initialized: {channel}")
        await manager.send_text(**kwargs)

    async def send_event(self, **kwargs) -> None:
        channel = str(kwargs.get("channel") or "")
        manager = await self._resolve_manager(channel)
        if manager is None:
            raise KeyError(f"channel manager not initialized: {channel}")
        await manager.send_event(**kwargs)
