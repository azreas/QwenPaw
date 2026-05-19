# -*- coding: utf-8 -*-
from unittest.mock import AsyncMock, MagicMock

import pytest
from agentscope_runtime.engine.schemas.agent_schemas import ContentType

from qwenpaw.tenancy.wx_tenant_router import WxTenantRouter


async def _one_event(event):
    yield event


def _native():
    return {
        "channel_id": "wecom_tenant",
        "sender_id": "alice",
        "user_id": "alice",
        "session_id": "wecom:alice",
        "content_parts": [],
        "meta": {"wecom_frame": {}},
    }


def _channel():
    ch = MagicMock()
    request = MagicMock()
    request.user_id = "alice"
    request.session_id = "wecom:alice"
    ch.build_agent_request_from_native.return_value = request
    ch.send_event = AsyncMock()
    ch.send_content_parts = AsyncMock()
    ch.get_to_handle_from_request.return_value = "wecom:alice"
    return ch


@pytest.mark.asyncio
async def test_handle_routes_to_tenant_runner(tmp_path):
    provisioner = MagicMock()
    provisioner.ensure.return_value = tmp_path / "tenants" / "wx_alice"
    workspace = MagicMock()
    event = MagicMock()
    workspace.runner.stream_query = lambda request: _one_event(event)
    registry = MagicMock()
    registry.get_or_create = AsyncMock(return_value=workspace)
    router = WxTenantRouter(registry=registry, provisioner=provisioner)
    ch = _channel()

    await router.handle("alice", _native(), ch)

    provisioner.ensure.assert_called_once_with("alice")
    registry.get_or_create.assert_awaited_once_with(
        "alice",
        tmp_path / "tenants" / "wx_alice",
    )
    ch.send_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_sends_degrade_message_on_workspace_failure(tmp_path):
    provisioner = MagicMock()
    provisioner.ensure.side_effect = RuntimeError("init failed")
    registry = MagicMock()
    router = WxTenantRouter(registry=registry, provisioner=provisioner)
    ch = _channel()

    await router.handle("alice", _native(), ch)

    ch.send_content_parts.assert_awaited_once_with(
        to_handle="wecom:alice",
        parts=[
            {
                "type": ContentType.TEXT,
                "text": "助手工作区初始化失败，请稍后重试或联系管理员。",
            },
        ],
        meta={"wecom_frame": {}, "roles": ["tenant_member"]},
    )
