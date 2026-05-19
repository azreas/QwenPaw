"""审计 fallback spool 测试。"""

import pytest

from qwenpaw.enterprise.audit.models import AuditEvent, AuditEventType, AuditOutcome
from qwenpaw.enterprise.audit.spool import AuditSpool


@pytest.mark.asyncio
async def test_spool_writes_and_reads_jsonl(tmp_path):
    spool = AuditSpool(tmp_path)
    event = AuditEvent(
        event_type=AuditEventType.AUTHZ_DENIED,
        action="audit:read",
        outcome=AuditOutcome.FAILURE,
        request_id="req-1",
        trace_id="trace-1",
    )

    await spool.write(event)
    files = list(tmp_path.glob("*.jsonl"))
    assert len(files) == 1

    batch = await spool.read_batch(limit=10)
    assert batch.events[0].request_id == "req-1"


@pytest.mark.asyncio
async def test_spool_ack_moves_file(tmp_path):
    spool = AuditSpool(tmp_path)
    await spool.write(
        AuditEvent(
            event_type=AuditEventType.AUTH_REGISTER,
            action="register",
            outcome=AuditOutcome.SUCCESS,
        )
    )
    batch = await spool.read_batch(limit=10)
    await spool.ack(batch)
    assert list((tmp_path / "sent").glob("*.jsonl"))
