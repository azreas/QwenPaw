from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ComplianceExportFormat(StrEnum):
    JSON = "json"
    CSV = "csv"


class DataClassification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"


class AuditExportRequest(BaseModel):
    tenant_id: str | None = None
    actor_id: str | None = None
    event_type: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = Field(default=1000, ge=1, le=10000)
    format: ComplianceExportFormat = ComplianceExportFormat.JSON


class RetentionPolicy(BaseModel):
    audit_retention_days: int = Field(default=365, ge=1, le=3650)
    backup_retention_days: int = Field(default=90, ge=1, le=3650)
    spool_retention_days: int = Field(default=30, ge=1, le=365)
