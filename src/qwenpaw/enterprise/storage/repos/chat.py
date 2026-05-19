"""SQL 会话仓储 — 继承 BaseChatRepository，使用 SQLAlchemy async session。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from ....app.runner.models import ChatSpec, ChatsFile
from ....app.runner.repo.base import BaseChatRepository
from ..models import ChatRow

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlChatRepository(BaseChatRepository):
    """基于 SQLAlchemy 的会话仓储实现。

    持有 async_sessionmaker，每个方法内部 with session 确保连接生命周期。
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        agent_id: str,
    ) -> None:
        self._session_factory = session_factory
        self._agent_id = agent_id

    async def load(self) -> ChatsFile:
        async with self._session_factory() as session:
            stmt = select(ChatRow).where(
                ChatRow.agent_id == self._agent_id,
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            chats = [ChatSpec.model_validate(r.payload) for r in rows]
            return ChatsFile(chats=chats)

    async def save(self, chats_file: ChatsFile) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                stmt = delete(ChatRow).where(
                    ChatRow.agent_id == self._agent_id,
                )
                await session.execute(stmt)

                for spec in chats_file.chats:
                    row = ChatRow(
                        id=spec.id,
                        agent_id=self._agent_id,
                        session_id=spec.session_id,
                        user_id=spec.user_id,
                        channel=spec.channel,
                        payload=spec.model_dump(mode="json"),
                    )
                    session.add(row)
