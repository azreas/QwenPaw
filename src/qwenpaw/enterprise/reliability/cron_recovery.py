"""Cron 失败恢复辅助函数。"""

from __future__ import annotations

from typing import Any


async def record_cron_failure(
    queue: Any,
    *,
    agent_id: str,
    job_id: str,
    job_name: str,
    error: Exception,
) -> None:
    """记录 Cron 任务失败到死信队列。

    Args:
        queue: 死信队列（InMemoryDeadLetterQueue 或 None）
        agent_id: Agent ID
        job_id: Cron 任务 ID
        job_name: Cron 任务名称
        error: 异常对象
    """
    if queue is None:
        return

    await queue.append(
        source="cron",
        payload={
            "agent_id": agent_id,
            "job_id": job_id,
            "job_name": job_name,
        },
        error=str(error),
    )
