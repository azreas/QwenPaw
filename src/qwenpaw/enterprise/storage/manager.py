"""StorageManager — 企业存储生命周期所有者。

json 后端不创建 engine；sqlite/postgres 后端在 start() 创建唯一 async engine、
session_factory，在 stop() 释放。禁止其他模块私有创建 DB engine。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .config import StorageConfig

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import (
        AsyncEngine,
        AsyncSession,
        async_sessionmaker,
    )


class StorageManager:
    """存储生命周期管理器，唯一 DB engine 所有者。"""

    def __init__(self, config: StorageConfig) -> None:
        self._config = config
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def engine(self) -> AsyncEngine | None:
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession] | None:
        return self._session_factory

    async def start(self) -> None:
        if not self._config.enabled:
            return

        from sqlalchemy.ext.asyncio import (
            create_async_engine,
            async_sessionmaker,
        )

        kwargs: dict[str, Any] = {"echo": self._config.echo}

        # SQLite 内存模式不支持 pool_size，需用 StaticPool
        if self._config.database_url.startswith("sqlite"):
            from sqlalchemy.pool import StaticPool

            kwargs["poolclass"] = StaticPool
            kwargs["connect_args"] = {"check_same_thread": False}
        else:
            kwargs["pool_size"] = self._config.pool_size

        self._engine = create_async_engine(
            self._config.database_url, **kwargs,
        )
        self._session_factory = async_sessionmaker(
            self._engine, expire_on_commit=False,
        )

        # 运行 Alembic 迁移
        from .migration_runner import MigrationRunner

        await MigrationRunner().upgrade(self._engine)

    async def stop(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    async def healthcheck(self) -> dict[str, Any]:
        if not self._config.enabled:
            return {"status": "disabled", "backend": self._config.backend}

        if self._engine is None:
            return {"status": "error", "backend": self._config.backend,
                    "message": "engine not started"}

        async with self._engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        return {"status": "ok", "backend": self._config.backend}

    def get_chat_repository(self, agent_id: str, workspace_dir: str = ""):
        """获取会话仓储。SQL 后端返回 SqlChatRepository，否则 JSON。"""
        if self._config.enabled and self._session_factory is not None:
            from .repos.chat import SqlChatRepository

            return SqlChatRepository(
                self._session_factory, agent_id,
            )

        from pathlib import Path

        from ...app.runner.repo.json_repo import JsonChatRepository

        return JsonChatRepository(Path(workspace_dir) / "chats.json")

    def get_job_repository(self, agent_id: str, workspace_dir: str = ""):
        """获取任务仓储。SQL 后端返回 SqlJobRepository，否则 JSON。"""
        if self._config.enabled and self._session_factory is not None:
            from .repos.job import SqlJobRepository

            return SqlJobRepository(
                self._session_factory, agent_id,
            )

        from pathlib import Path

        from ...app.crons.repo.json_repo import JsonJobRepository

        return JsonJobRepository(Path(workspace_dir) / "jobs.json")


def get_storage_manager_from_app(app: object) -> StorageManager | None:
    """从 Starlette app.state 获取 StorageManager。"""
    runtime = getattr(
        getattr(app, "state", None), "enterprise_runtime", None,
    )
    storage = getattr(runtime, "storage", None)
    if isinstance(storage, StorageManager):
        return storage
    return None
