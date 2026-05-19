# -*- coding: utf-8 -*-
"""端到端模拟：企业微信多租户路由集成测试。"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from qwenpaw.app.channels.wecom_tenant.channel import WecomTenantChannel


def _frame(sender_id: str, chatid: str, chattype: str):
    return {
        "body": {
            "from": {"userid": sender_id},
            "chatid": chatid,
            "chattype": chattype,
            "msgid": f"{sender_id}-{chatid}-{chattype}",
            "send_time": "123",
            "msgtype": "text",
            "text": {"content": "你好"},
        }
    }


@pytest.mark.asyncio
async def test_single_and_group_messages_route_to_different_tenants(tmp_path):
    """单聊和群聊消息分别路由到不同租户，channel_id 统一为 wecom_tenant。"""
    channel = WecomTenantChannel(
        process=AsyncMock(),
        enabled=True,
        bot_id="bot",
        secret="secret",
        media_dir=str(tmp_path / "media"),
    )
    captured = []

    class Adapter:
        def resolve_tenant_id(self, body):
            return body["chatid"] if body["chattype"] == "group" else body["from"]["userid"]

        def get_media_dir(self, tenant_id):
            return tmp_path / "tenants" / f"wx_{tenant_id}" / "media"

        async def handle(self, tenant_id, native, ch):
            captured.append((tenant_id, native["session_id"], native["channel_id"]))

    channel._tenant_adapter = Adapter()

    await channel._on_message(_frame("alice", "room-a", "single"))
    await channel._on_message(_frame("alice", "group-1", "group"))

    assert captured[0][0] == "alice"
    assert captured[1][0] == "group-1"
    assert captured[0][2] == "wecom_tenant"
    assert captured[1][2] == "wecom_tenant"
