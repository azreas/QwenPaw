"""死信队列单元测试。"""

import pytest

from qwenpaw.enterprise.reliability.dead_letter import InMemoryDeadLetterQueue


@pytest.mark.asyncio
async def test_dead_letter_queue_append_list_ack() -> None:
    """死信队列追加、列表、确认流程正常工作。"""
    queue = InMemoryDeadLetterQueue()

    message = await queue.append(
        source="cron",
        payload={"job_id": "j1"},
        error="boom",
    )

    assert message.id is not None
    assert message.source == "cron"
    assert message.payload["job_id"] == "j1"
    assert message.error == "boom"

    messages = await queue.list_messages(source="cron")
    assert len(messages) == 1
    assert messages[0].id == message.id

    assert await queue.ack(message.id) is True
    assert await queue.list_messages(source="cron") == []

    # 重复 ack 应返回 False
    assert await queue.ack(message.id) is False


@pytest.mark.asyncio
async def test_list_messages_filter_by_source() -> None:
    """按 source 过滤消息。"""
    queue = InMemoryDeadLetterQueue()

    await queue.append(source="cron", payload={}, error="e1")
    await queue.append(source="notification", payload={}, error="e2")

    all_messages = await queue.list_messages()
    assert len(all_messages) == 2

    cron_messages = await queue.list_messages(source="cron")
    assert len(cron_messages) == 1
    assert cron_messages[0].source == "cron"
