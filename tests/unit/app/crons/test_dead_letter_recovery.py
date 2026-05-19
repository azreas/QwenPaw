"""CronManager 死信恢复集成测试。"""

import pytest

from qwenpaw.enterprise.reliability import InMemoryDeadLetterQueue
from qwenpaw.enterprise.runtime_registry import clear_enterprise_runtime, set_enterprise_runtime


class MockRuntime:
    def __init__(self, dead_letter):
        self.dead_letter = dead_letter


@pytest.mark.asyncio
async def test_record_cron_failure_via_runtime_registry() -> None:
    """通过 runtime registry 访问死信队列记录失败。"""
    from unittest.mock import AsyncMock, MagicMock

    from qwenpaw.app.crons.manager import CronManager
    from qwenpaw.app.crons.models import (
        CronJobRequest,
        CronJobSpec,
        DispatchSpec,
        DispatchTarget,
        ScheduleSpec,
    )

    queue = InMemoryDeadLetterQueue()
    mock_runtime = MockRuntime(queue)
    set_enterprise_runtime(mock_runtime)
    try:
        # Mock executor that fails
        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(side_effect=RuntimeError("test failure"))

        # Mock repository
        mock_repo = MagicMock()
        mock_repo.append_history = AsyncMock(return_value=[])

        manager = CronManager(
            repo=mock_repo,
            runner=MagicMock(),
            channel_manager=MagicMock(),
            agent_id="wx_test",
        )
        manager._executor = mock_executor

        job = CronJobSpec(
            id="test-job",
            name="Test Job",
            schedule=ScheduleSpec(cron="0 0 * * *"),
            task_type="agent",
            request=CronJobRequest(session_id="s1", user_id="u1"),
            dispatch=DispatchSpec(
                channel="console",
                target=DispatchTarget(user_id="u1", session_id="s1"),
            ),
        )

        with pytest.raises(RuntimeError, match="test failure"):
            await manager._execute_once(job)

        messages = await queue.list_messages(source="cron")
        assert len(messages) == 1
        assert messages[0].payload["job_id"] == "test-job"
        assert messages[0].payload["agent_id"] == "wx_test"
        assert "test failure" in messages[0].error
    finally:
        clear_enterprise_runtime(mock_runtime)
