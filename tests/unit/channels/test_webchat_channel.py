# -*- coding: utf-8 -*-
from __future__ import annotations

import json

import pytest
from agentscope_runtime.engine.schemas.agent_schemas import (
    AgentResponse,
    ContentType,
    Message,
    MessageType,
    Role,
    RunStatus,
    TextContent,
)

from qwenpaw.app.channels.webchat.channel import WebchatChannel


async def _events(*items):
    for item in items:
        yield item


def _assistant_message(text: str) -> Message:
    return Message(
        type=MessageType.MESSAGE,
        role=Role.ASSISTANT,
        status=RunStatus.Completed,
        content=[TextContent(type=ContentType.TEXT, text=text)],
    )


def _webchat_channel(process):
    return WebchatChannel(
        process=process,
        enabled=True,
        bot_prefix="",
    )


@pytest.mark.asyncio
async def test_stream_one_does_not_emit_empty_completed_response_after_message():
    """An empty response.completed must not clear the frontend output."""
    message = _assistant_message("WebChat 回复")
    response = AgentResponse(
        status=RunStatus.Completed,
        output=[],
    )
    channel = _webchat_channel(lambda _request: _events(message, response))

    payload = {
        "channel_id": "webchat",
        "sender_id": "alice",
        "session_id": "s1",
        "content_parts": [TextContent(type=ContentType.TEXT, text="你好")],
        "meta": {"session_id": "s1"},
    }

    events = []
    async for chunk in channel.stream_one(payload):
        assert chunk.startswith("data: ")
        events.append(json.loads(chunk[len("data: ") :].strip()))

    assert any(event.get("object") == "message" for event in events)
    assert not any(
        event.get("object") == "response"
        and event.get("status") == RunStatus.Completed
        and not event.get("output")
        for event in events
    )
