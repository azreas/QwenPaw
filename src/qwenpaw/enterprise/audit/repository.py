"""审计 Repository — DB 写入和查询。

所有 DB session 通过 StorageManager.session_factory 获取，
不创建私有 engine。仅提供 append_many 和 query，不提供 UPDATE/DELETE。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select

from qwenpaw.enterprise.audit.models import AuditEvent
from qwenpaw.enterprise.storage.manager import StorageManager
from qwenpaw.enterprise.storage.models import AuditLogRow


class AuditRepository:
    """审计日志 DB 仓储，追加写入 + 条件查询。"""

    def __init__(self, storage: StorageManager) -> None:
        self._storage = storage

    async def append_many(self, events: list[AuditEvent]) -> None:
        """一次事务插入多条审计日志。"""
        sf = self._storage.session_factory
        if sf is None:
            return

        rows = [_event_to_row(e) for e in events]
        async with sf() as session:
            async with session.begin():
                session.add_all(rows)

    async def query(
        self,
        *,
        tenant_id: str | None = None,
        actor_id: str | None = None,
        event_type: str | None = None,
        event_types: tuple[str, ...] | list[str] | None = None,
        agent_id: str | None = None,
        session_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        outcome: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditLogRow]:
        """条件查询审计日志，按 created_at 降序。"""
        sf = self._storage.session_factory
        if sf is None:
            return []

        stmt = select(AuditLogRow).order_by(AuditLogRow.created_at.desc())

        if tenant_id is not None:
            stmt = stmt.where(AuditLogRow.tenant_id == tenant_id)
        if actor_id is not None:
            stmt = stmt.where(AuditLogRow.actor_id == actor_id)
        if event_type is not None:
            stmt = stmt.where(AuditLogRow.event_type == event_type)
        if event_types:
            stmt = stmt.where(AuditLogRow.event_type.in_(tuple(event_types)))
        if agent_id is not None:
            stmt = stmt.where(AuditLogRow.agent_id == agent_id)
        if session_id is not None:
            stmt = stmt.where(AuditLogRow.session_id == session_id)
        if resource_type is not None:
            stmt = stmt.where(AuditLogRow.resource_type == resource_type)
        if resource_id is not None:
            stmt = stmt.where(AuditLogRow.resource_id == resource_id)
        if outcome is not None:
            stmt = stmt.where(AuditLogRow.outcome == outcome)
        if start_time is not None:
            stmt = stmt.where(AuditLogRow.created_at >= start_time)
        if end_time is not None:
            stmt = stmt.where(AuditLogRow.created_at <= end_time)

        stmt = stmt.limit(limit)

        async with sf() as session:
            result = await session.execute(stmt)
            return list(result.scalars().all())


def _event_to_row(event: AuditEvent) -> AuditLogRow:
    return AuditLogRow(
        id=event.id,
        event_type=event.event_type,
        action=event.action,
        outcome=event.outcome,
        tenant_id=event.tenant_id,
        agent_id=event.agent_id,
        session_id=event.session_id,
        actor_id=event.actor_id,
        actor_type=event.actor_type,
        resource_type=event.resource_type,
        resource_id=event.resource_id,
        request_id=event.request_id,
        trace_id=event.trace_id,
        ip_address=event.ip_address,
        user_agent=event.user_agent,
        payload=event.payload,
        created_at=event.created_at,
    )
