"""审计 Repository 测试。"""

import pytest

from qwenpaw.enterprise.audit.models import AuditEvent, AuditEventType, AuditOutcome
from qwenpaw.enterprise.audit.repository import AuditRepository
from qwenpaw.enterprise.storage.config import StorageConfig
from qwenpaw.enterprise.storage.manager import StorageManager
from qwenpaw.enterprise.storage.models import Base


@pytest.mark.asyncio
async def test_repository_appends_and_queries():
    storage = StorageManager(
        StorageConfig(
            backend="sqlite",
            database_url="sqlite+aiosqlite:///:memory:",
        )
    )
    await storage.start()
    async with storage.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    repo = AuditRepository(storage)
    event = AuditEvent(
        event_type=AuditEventType.AUTH_REGISTER,
        action="register",
        outcome=AuditOutcome.SUCCESS,
    )
    await repo.append_many([event])

    rows = await repo.query(limit=10)
    assert rows[0].event_type == "auth.register"
    await storage.stop()


@pytest.mark.asyncio
async def test_repository_query_filters():
    storage = StorageManager(
        StorageConfig(
            backend="sqlite",
            database_url="sqlite+aiosqlite:///:memory:",
        )
    )
    await storage.start()
    async with storage.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    repo = AuditRepository(storage)
    await repo.append_many([
        AuditEvent(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            action="login",
            outcome=AuditOutcome.SUCCESS,
            tenant_id="wx_acme",
        ),
        AuditEvent(
            event_type=AuditEventType.AUTHZ_DENIED,
            action="audit:read",
            outcome=AuditOutcome.FAILURE,
            tenant_id="wx_other",
        ),
    ])

    rows = await repo.query(tenant_id="wx_acme", limit=10)
    assert len(rows) == 1
    assert rows[0].tenant_id == "wx_acme"
    await storage.stop()


@pytest.mark.asyncio
async def test_repository_query_filters_business_trace_fields():
    storage = StorageManager(
        StorageConfig(
            backend="sqlite",
            database_url="sqlite+aiosqlite:///:memory:",
        )
    )
    await storage.start()
    async with storage.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    repo = AuditRepository(storage)
    await repo.append_many([
        AuditEvent(
            event_type=AuditEventType.SKILL_CALLED,
            action="call",
            outcome=AuditOutcome.SUCCESS,
            tenant_id="wx_acme",
            agent_id="wx_acme",
            session_id="session-1",
            resource_type="skill",
            resource_id="sales_report",
        ),
        AuditEvent(
            event_type=AuditEventType.MCP_CALLED,
            action="call",
            outcome=AuditOutcome.FAILURE,
            tenant_id="wx_acme",
            agent_id="wx_acme",
            session_id="session-2",
            resource_type="mcp",
            resource_id="doris_query",
        ),
        AuditEvent(
            event_type=AuditEventType.AUTHZ_DENIED,
            action="skills:call",
            outcome=AuditOutcome.DENIED,
            tenant_id="wx_other",
            agent_id="wx_other",
            session_id="session-1",
            resource_type="skills",
            resource_id="sales_report",
        ),
    ])

    rows = await repo.query(
        tenant_id="wx_acme",
        agent_id="wx_acme",
        session_id="session-1",
        resource_type="skill",
        resource_id="sales_report",
        outcome="success",
        event_types=("skill.called", "mcp.called"),
        limit=10,
    )

    assert len(rows) == 1
    assert rows[0].event_type == "skill.called"
    assert rows[0].resource_id == "sales_report"
    await storage.stop()
