"""Cron 恢复辅助函数单元测试。"""

import pytest

from qwenpaw.enterprise.reliability.cron_recovery import record_cron_failure
from qwenpaw.enterprise.reliability.dead_letter import InMemoryDeadLetterQueue


@pytest.mark.asyncio
async def test_record_cron_failure_writes_dead_letter() -> None:
    """记录 Cron 失败应写入死信队列。"""
    queue = InMemoryDeadLetterQueue()

    await record_cron_failure(
        queue,
        agent_id="wx_acme",
        job_id="job-1",
        job_name="Daily Sync",
        error=RuntimeError("boom"),
    )

    messages = await queue.list_messages(source="cron")
    assert len(messages) == 1
    assert messages[0].payload["job_id"] == "job-1"
    assert messages[0].payload["agent_id"] == "wx_acme"
    assert messages[0].error == "boom"


@pytest.mark.asyncio
async def test_record_cron_failure_no_queue_no_op() -> None:
    """没有死信队列时应是 no-op，不抛异常。"""
    await record_cron_failure(
        None,
        agent_id="wx_acme",
        job_id="job-1",
        job_name="Daily Sync",
        error=RuntimeError("boom"),
    )
    # 不抛异常即为成功
