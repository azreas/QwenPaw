# -*- coding: utf-8 -*-
"""Pydantic schemas for WeCom tenant ops insights APIs."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BusinessTraceItem(BaseModel):
    id: str
    tenant_id: str = ""
    agent_id: str = ""
    session_id: str = ""
    actor_id: str = ""
    entrypoint: str = ""
    ability_type: str = ""
    ability_name: str = ""
    duration_ms: float = 0
    status: str = ""
    error_reason: str = ""
    request_id: str = ""
    trace_id: str = ""
    created_at: str = ""


class AbilityFailureSummary(BaseModel):
    ability_name: str
    ability_type: str = ""
    count: int = 0
    last_error: str = ""


class OpsOverviewResponse(BaseModel):
    total_tenants: int = 0
    running_tenants: int = 0
    unhealthy_tenants: int = 0
    business_calls_24h: int = 0
    failed_calls_24h: int = 0
    failure_rate: float = 0.0
    entrypoints: dict[str, int] = Field(default_factory=dict)
    top_failed_abilities: list[AbilityFailureSummary] = Field(default_factory=list)


class TenantOpsSummaryResponse(BaseModel):
    tenant_id: str
    agent_id: str
    health_status: str = "unknown"
    last_activity_at: str | None = None
    business_calls_24h: int = 0
    failed_calls_24h: int = 0
    recent_failures: list[BusinessTraceItem] = Field(default_factory=list)


class BusinessTraceListResponse(BaseModel):
    items: list[BusinessTraceItem] = Field(default_factory=list)
    total: int = 0


class BadCaseCreateRequest(BaseModel):
    source_audit_id: str
    source_request_id: str = ""
    source_trace_id: str = ""
    category: Literal[
        "platform_runtime",
        "data_quality",
        "permission_config",
        "product_experience",
    ]
    owner: str = ""
    note: str = ""


class BadCaseUpdateRequest(BaseModel):
    status: Literal[
        "open", "triaged", "transferred", "resolved", "ignored"
    ] | None = None
    category: Literal[
        "platform_runtime",
        "data_quality",
        "permission_config",
        "product_experience",
    ] | None = None
    owner: str | None = None
    note: str | None = None


class BadCaseItem(BaseModel):
    case_id: str
    source_audit_id: str = ""
    source_request_id: str = ""
    source_trace_id: str = ""
    category: str = ""
    status: str = "open"
    owner: str = ""
    note: str = ""
    ability_type: str = ""
    ability_name: str = ""
    entrypoint: str = ""
    created_at: str = ""
    updated_at: str = ""


class BadCaseListResponse(BaseModel):
    items: list[BadCaseItem] = Field(default_factory=list)
    total: int = 0
