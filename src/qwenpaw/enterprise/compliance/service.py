from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Iterable, Protocol

from qwenpaw.enterprise.audit.repository import AuditRepository

from .models import AuditExportRequest, ComplianceExportFormat
from .redaction import redact_payload


class AuditRowLike(Protocol):
    id: str
    event_type: str
    action: str
    outcome: str
    tenant_id: str
    actor_id: str
    resource_type: str
    resource_id: str
    request_id: str
    trace_id: str
    payload: dict
    created_at: object


def _row_to_dict(row: AuditRowLike) -> dict:
    return {
        "id": row.id,
        "event_type": row.event_type,
        "action": row.action,
        "outcome": row.outcome,
        "tenant_id": row.tenant_id,
        "actor_id": row.actor_id,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "request_id": row.request_id,
        "trace_id": row.trace_id,
        "payload": redact_payload(row.payload or {}),
        "created_at": str(row.created_at),
    }


def audit_rows_to_json(rows: Iterable[AuditRowLike]) -> tuple[str, str, str]:
    now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    content = json.dumps(
        [_row_to_dict(row) for row in rows],
        ensure_ascii=False,
        indent=2,
    )
    return content, "application/json", f"audit-export-{now}.json"


def audit_rows_to_csv(rows: Iterable[AuditRowLike]) -> tuple[str, str, str]:
    now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    buffer = io.StringIO()
    fieldnames = [
        "event_type",
        "action",
        "outcome",
        "tenant_id",
        "actor_id",
        "resource_type",
        "resource_id",
        "request_id",
        "trace_id",
        "created_at",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        item = _row_to_dict(row)
        writer.writerow({key: item[key] for key in fieldnames})
    return buffer.getvalue(), "text/csv", f"audit-export-{now}.csv"


class ComplianceService:
    def __init__(self, audit_repository: AuditRepository) -> None:
        self._audit_repository = audit_repository

    async def export_audit(
        self, request: AuditExportRequest,
    ) -> tuple[str, str, str]:
        rows = await self._audit_repository.query(
            tenant_id=request.tenant_id,
            actor_id=request.actor_id,
            event_type=request.event_type,
            start_time=request.start_time,
            end_time=request.end_time,
            limit=request.limit,
        )
        if request.format is ComplianceExportFormat.CSV:
            return audit_rows_to_csv(rows)
        return audit_rows_to_json(rows)
