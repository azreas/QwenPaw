import pytest
from sqlalchemy import text

from qwenpaw.enterprise.storage.config import StorageConfig
from qwenpaw.enterprise.storage.manager import StorageManager


@pytest.mark.asyncio
async def test_sqlite_storage_start_runs_alembic_migrations(tmp_path):
    db_path = tmp_path / "qwenpaw.db"
    manager = StorageManager(
        StorageConfig(
            backend="sqlite",
            database_url=f"sqlite+aiosqlite:///{db_path}",
        )
    )

    await manager.start()
    try:
        async with manager.engine.connect() as conn:
            version = (
                await conn.execute(text("select version_num from alembic_version"))
            ).scalar_one()
            tables = {
                row[0]
                for row in (
                    await conn.execute(
                        text(
                            "select name from sqlite_master "
                            "where type='table' order by name"
                        )
                    )
                )
            }

        assert version == "002"
        assert "enterprise_chats" in tables
        assert "enterprise_jobs" in tables
        assert "enterprise_audit_logs" in tables
    finally:
        await manager.stop()
