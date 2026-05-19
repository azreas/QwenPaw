# -*- coding: utf-8 -*-
from unittest.mock import AsyncMock, MagicMock

import pytest

from qwenpaw.app.channels.wecom_tenant.tenant_adapter import WeComTenantAdapter


def test_resolve_tenant_id_uses_sender_for_single_chat():
    adapter = WeComTenantAdapter(tenant_router=MagicMock())
    body = {"chattype": "single", "from": {"userid": "alice"}, "chatid": "room"}

    assert adapter.resolve_tenant_id(body) == "alice"


def test_resolve_tenant_id_uses_chatid_for_group_chat():
    adapter = WeComTenantAdapter(tenant_router=MagicMock())
    body = {"chattype": "group", "from": {"userid": "alice"}, "chatid": "room"}

    assert adapter.resolve_tenant_id(body) == "room"


@pytest.mark.asyncio
async def test_handle_delegates_to_router():
    router = MagicMock()
    router.handle = AsyncMock()
    adapter = WeComTenantAdapter(tenant_router=router)
    channel = MagicMock()

    await adapter.handle("alice", {"native": True}, channel)

    router.handle.assert_awaited_once_with("alice", {"native": True}, channel)
