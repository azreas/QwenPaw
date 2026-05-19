import pytest

from qwenpaw.app.runner.models import ChatSpec, ChatsFile
from qwenpaw.enterprise.storage.config import StorageConfig
from qwenpaw.enterprise.storage.manager import StorageManager


@pytest.mark.asyncio
async def test_sql_chat_repo_roundtrip():
    manager = StorageManager(
        StorageConfig(
            backend="sqlite",
            database_url="sqlite+aiosqlite:///:memory:",
        ),
    )
    await manager.start()

    repo = manager.get_chat_repository("default")
    await repo.save(
        ChatsFile(
            chats=[
                ChatSpec(
                    id="c1",
                    session_id="s1",
                    user_id="u1",
                    channel="web",
                ),
            ],
        ),
    )

    loaded = await repo.load()
    assert loaded.chats[0].id == "c1"
    assert await repo.get_chat_by_id("s1", "u1", "web")
    await manager.stop()
