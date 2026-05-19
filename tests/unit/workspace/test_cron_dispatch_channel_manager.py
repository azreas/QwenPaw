# -*- coding: utf-8 -*-
from __future__ import annotations

from types import SimpleNamespace

import pytest

from qwenpaw.tenancy.cron_dispatch import TenantCronDispatchChannelManager


class FakeChannelManager:
    def __init__(self, channels: set[str]) -> None:
        self.channels = channels
        self.sent_text: list[dict] = []

    async def get_channel(self, channel: str):
        return object() if channel in self.channels else None

    async def send_text(self, **kwargs) -> None:
        self.sent_text.append(kwargs)


@pytest.mark.asyncio
async def test_cron_dispatch_prefers_local_channel_manager():
    local_channel_manager = FakeChannelManager({"console"})
    tenant_workspace = SimpleNamespace(
        _service_manager=SimpleNamespace(
            services={"channel_manager": local_channel_manager},
        ),
    )
    tenant_workspace._manager = SimpleNamespace(agents={})  # noqa: SLF001
    dispatch_manager = TenantCronDispatchChannelManager(tenant_workspace)

    await dispatch_manager.send_text(
        channel="console",
        user_id="admin",
        session_id="console:admin",
        text="hello",
        meta={},
    )

    assert local_channel_manager.sent_text[0]["channel"] == "console"


@pytest.mark.asyncio
async def test_cron_dispatch_delegates_to_loaded_root_channel_manager():
    root_channel_manager = FakeChannelManager({"wecom_tenant"})
    root_workspace = SimpleNamespace(channel_manager=root_channel_manager)
    tenant_workspace = SimpleNamespace(
        _service_manager=SimpleNamespace(services={"channel_manager": None}),
    )
    tenant_workspace._manager = SimpleNamespace(  # noqa: SLF001
        agents={"default": root_workspace, "wx_user": tenant_workspace},
    )
    dispatch_manager = TenantCronDispatchChannelManager(tenant_workspace)

    await dispatch_manager.send_text(
        channel="wecom_tenant",
        user_id="user-1",
        session_id="wecom:user-1",
        text="hello",
        meta={"source": "cron"},
    )

    assert root_channel_manager.sent_text == [
        {
            "channel": "wecom_tenant",
            "user_id": "user-1",
            "session_id": "wecom:user-1",
            "text": "hello",
            "meta": {"source": "cron"},
        },
    ]
