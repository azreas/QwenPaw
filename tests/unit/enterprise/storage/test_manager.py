import pytest

from qwenpaw.enterprise.storage.config import StorageConfig
from qwenpaw.enterprise.storage.manager import StorageManager


@pytest.mark.asyncio
async def test_json_backend_has_disabled_health():
    manager = StorageManager(StorageConfig(backend="json"))
    await manager.start()
    assert await manager.healthcheck() == {"status": "disabled", "backend": "json"}
    await manager.stop()


@pytest.mark.asyncio
async def test_sqlite_backend_owns_single_engine():
    manager = StorageManager(
        StorageConfig(
            backend="sqlite",
            database_url="sqlite+aiosqlite:///:memory:",
        ),
    )
    await manager.start()
    assert manager.engine is not None
    assert manager.session_factory is not None
    assert (await manager.healthcheck())["status"] == "ok"
    await manager.stop()
    assert manager.engine is None


@pytest.mark.asyncio
async def test_storage_manager_uses_migration_runner(monkeypatch):
    from qwenpaw.enterprise.storage.migration_runner import MigrationRunner
    from qwenpaw.enterprise.storage.models import Base

    calls = []

    async def fake_upgrade(self, engine):
        calls.append(engine)

    def fail_create_all(*args, **kwargs):
        raise AssertionError("StorageManager must not call create_all()")

    monkeypatch.setattr(MigrationRunner, "upgrade", fake_upgrade)
    monkeypatch.setattr(Base.metadata, "create_all", fail_create_all)

    manager = StorageManager(
        StorageConfig(
            backend="sqlite",
            database_url="sqlite+aiosqlite:///:memory:",
        )
    )
    await manager.start()
    try:
        assert calls == [manager.engine]
    finally:
        await manager.stop()
