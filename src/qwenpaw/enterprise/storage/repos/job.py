"""SQL 任务仓储 — 继承 BaseJobRepository，使用 SQLAlchemy async session。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from ....app.crons.models import CronExecutionRecord, CronJobSpec, JobsFile
from ....app.crons.repo.base import BaseJobRepository
from ..models import JobRow

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlJobRepository(BaseJobRepository):
    """基于 SQLAlchemy 的任务仓储实现。

    持有 async_sessionmaker，每个方法内部 with session 确保连接生命周期。
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        agent_id: str,
    ) -> None:
        self._session_factory = session_factory
        self._agent_id = agent_id

    async def load(self) -> JobsFile:
        async with self._session_factory() as session:
            stmt = select(JobRow).where(
                JobRow.agent_id == self._agent_id,
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            jobs = [CronJobSpec.model_validate(r.payload) for r in rows]
            return JobsFile(jobs=jobs)

    async def save(self, jobs_file: JobsFile) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                stmt = delete(JobRow).where(
                    JobRow.agent_id == self._agent_id,
                )
                await session.execute(stmt)

                for spec in jobs_file.jobs:
                    row = JobRow(
                        id=spec.id,
                        agent_id=self._agent_id,
                        payload=spec.model_dump(mode="json"),
                    )
                    session.add(row)

    async def get_history(self, job_id: str) -> list[CronExecutionRecord]:
        # SQL 存储暂不支持历史记录，返回空列表
        return []

    async def append_history(
        self,
        job_id: str,
        record: CronExecutionRecord,
        *,
        limit: int = 50,
    ) -> list[CronExecutionRecord]:
        # SQL 存储暂不支持历史记录，返回空列表
        return []

    async def delete_history(self, job_id: str) -> None:
        # SQL 存储暂不支持历史记录
        pass

    async def prune_orphan_history(self, valid_job_ids: set[str]) -> None:
        # SQL 存储暂不支持历史记录
        pass
