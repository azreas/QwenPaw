# -*- coding: utf-8 -*-
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from qwenpaw.app.channels.wecom_tenant.channel import WecomTenantChannel


def _frame(sender_id="alice", chatid="room", chattype="single"):
    return {
        "body": {
            "from": {"userid": sender_id},
            "chatid": chatid,
            "chattype": chattype,
            "msgid": f"msg-{sender_id}-{chatid}",
            "send_time": "123",
            "msgtype": "text",
            "text": {"content": "你好"},
        }
    }


def test_wecom_tenant_channel_contract():
    assert WecomTenantChannel.channel == "wecom_tenant"
    assert WecomTenantChannel.uses_manager_queue is False


@pytest.mark.asyncio
async def test_on_message_routes_to_adapter_without_enqueue(tmp_path):
    channel = WecomTenantChannel(
        process=AsyncMock(),
        enabled=True,
        bot_id="bot",
        secret="secret",
        media_dir=str(tmp_path / "media"),
    )
    adapter = MagicMock()
    adapter.resolve_tenant_id.return_value = "alice"
    adapter.get_media_dir.return_value = None
    adapter.handle = AsyncMock()
    channel._tenant_adapter = adapter
    enqueued = []
    channel._enqueue = lambda native: enqueued.append(native)

    with patch.object(channel, "_is_duplicate", return_value=False), patch.object(
        channel,
        "_check_allowlist",
        return_value=(True, ""),
    ):
        await channel._on_message(_frame())

    assert enqueued == []
    adapter.handle.assert_awaited_once()
    native = adapter.handle.await_args.args[1]
    assert native["channel_id"] == "wecom_tenant"
    assert native["sender_id"] == "alice"


@pytest.mark.asyncio
async def test_on_message_preserves_employee_entry_context(tmp_path):
    channel = WecomTenantChannel(
        process=AsyncMock(),
        enabled=True,
        bot_id="bot",
        secret="secret",
        media_dir=str(tmp_path / "media"),
    )
    adapter = MagicMock()
    adapter.resolve_tenant_id.return_value = "alice"
    adapter.get_media_dir.return_value = None
    adapter.handle = AsyncMock()
    channel._tenant_adapter = adapter
    enqueued = []
    channel._enqueue = lambda native: enqueued.append(native)

    with patch.object(channel, "_is_duplicate", return_value=False), patch.object(
        channel,
        "_check_allowlist",
        return_value=(True, ""),
    ):
        await channel._on_message(_frame())

    native = adapter.handle.await_args.args[1]
    assert native["channel_id"] == "wecom_tenant"
    assert native["sender_id"] == "alice"
    assert native["user_id"] == "alice"
    assert native["session_id"] == "wecom:alice"
    assert native["tenant_id"] == "alice"
    assert native["agent_id"] == "wx_alice"
    meta = native["meta"]
    assert meta["entrypoint"] == "wecom_tenant"
    assert meta["tenant_id"] == "alice"
    assert meta["agent_id"] == "wx_alice"
    assert meta["wechat_company_id"] == "alice"
    assert meta["employee_id"] == "alice"
    assert meta["request_id"]
    assert meta["trace_id"]
    assert "webchat_workspace_dir" not in meta


@pytest.mark.asyncio
async def test_on_message_drops_when_router_missing(tmp_path):
    channel = WecomTenantChannel(
        process=AsyncMock(),
        enabled=True,
        bot_id="bot",
        secret="secret",
        media_dir=str(tmp_path / "media"),
    )
    enqueued = []
    channel._enqueue = lambda native: enqueued.append(native)

    await channel._on_message(_frame())

    assert enqueued == []


def test_wecom_single_chat_session_id_stays_wecom_userid(tmp_path):
    channel = WecomTenantChannel(
        process=AsyncMock(),
        enabled=True,
        bot_id="bot",
        secret="secret",
        media_dir=str(tmp_path / "media"),
    )

    assert (
        channel.resolve_session_id(
            "alice",
            {"wecom_chatid": "alice", "wecom_chat_type": "single"},
        )
        == "wecom:alice"
    )


@pytest.mark.asyncio
async def test_on_message_sends_degrade_when_get_media_dir_fails(tmp_path):
    """get_media_dir 调用 provisioner.ensure 失败时，员工应收到降级提示。"""
    channel = WecomTenantChannel(
        process=AsyncMock(),
        enabled=True,
        bot_id="bot",
        secret="secret",
        media_dir=str(tmp_path / "media"),
    )
    adapter = MagicMock()
    adapter.resolve_tenant_id.return_value = "alice"
    adapter.get_media_dir.side_effect = RuntimeError("workspace init failed")
    channel._tenant_adapter = adapter
    channel.send_content_parts = AsyncMock()

    await channel._on_message(_frame())

    adapter.get_media_dir.assert_called_once_with("alice")
    # 不应走到 handle
    adapter.handle.assert_not_called()
    # 应发送降级提示给员工
    channel.send_content_parts.assert_awaited_once()
    kwargs = channel.send_content_parts.await_args.kwargs
    assert kwargs["to_handle"] == "wecom:alice"
    parts = kwargs["parts"]
    assert len(parts) == 1
    assert "初始化失败" in parts[0]["text"]
