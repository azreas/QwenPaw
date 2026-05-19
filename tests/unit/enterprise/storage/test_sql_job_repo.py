import pytest

from qwenpaw.app.crons.models import (
    CronJobRequest,
    CronJobSpec,
    DispatchSpec,
    DispatchTarget,
    JobsFile,
    ScheduleSpec,
)
from qwenpaw.enterprise.storage.config import StorageConfig
from qwenpaw.enterprise.storage.manager import StorageManager


@pytest.mark.asyncio
async def test_sql_job_repo_roundtrip():
    manager = StorageManager(
        StorageConfig(
            backend="sqlite",
            database_url="sqlite+aiosqlite:///:memory:",
        ),
    )
    await manager.start()

    repo = manager.get_job_repository("default")
    spec = CronJobSpec(
        id="j1",
        name="job",
        schedule=ScheduleSpec(cron="0 8 * * *"),
        request=CronJobRequest(query="hello"),
        dispatch=DispatchSpec(
            target=DispatchTarget(user_id="u1", session_id="s1"),
        ),
    )
    await repo.save(JobsFile(jobs=[spec]))

    loaded = await repo.load()
    assert loaded.jobs[0].id == "j1"
    assert await repo.get_job("j1")
    await manager.stop()
