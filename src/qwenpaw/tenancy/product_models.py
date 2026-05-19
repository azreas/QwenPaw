# -*- coding: utf-8 -*-
"""Product-domain tenant overlay models."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    """Return a timezone-aware UTC ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()


TenantStatus = Literal["active", "frozen", "archived"]
TenantSource = Literal["webchat", "wecom", "manual"]


class TenantPolicy(BaseModel):
    policy_id: str = "default"
    display_name: str = "默认成员策略"
    allow_model_switch: bool = True
    allowed_models: list[str] = Field(default_factory=list)
    allow_skill_create: bool = True
    allow_skill_upload_zip: bool = True
    allow_skill_hub_import: bool = True
    allow_tools: bool = True
    allowed_tools: list[str] = Field(default_factory=list)
    allow_mcp: bool = True
    allowed_mcp_transports: list[str] = Field(
        default_factory=lambda: ["sse", "http"],
    )
    allow_tasks: bool = True
    max_cron_jobs: int = Field(default=20, ge=0)
    min_cron_interval_minutes: int = Field(default=5, ge=1)
    allow_task_run_now: bool = True
    allow_task_tools: bool = True
    task_timeout_seconds: int = Field(default=120, ge=1)
    file_upload_limit_mb: int = Field(default=100, ge=1)
    token_quota_monthly: int | None = None
    advanced_config_enabled: bool = False


class TenantTemplate(BaseModel):
    template_id: str = "default"
    display_name: str = "默认成员模板"
    default_model: str | None = None
    default_prompt_files: list[str] = Field(default_factory=list)
    default_skills: list[str] = Field(default_factory=list)
    default_tools: list[str] = Field(default_factory=list)
    default_task_templates: list[dict[str, Any]] = Field(default_factory=list)


class TenantRecord(BaseModel):
    tenant_id: str
    display_name: str
    agent_id: str
    status: TenantStatus = "active"
    source: TenantSource = "manual"
    policy_id: str = "default"
    template_id: str = "default"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


def _default_policies() -> list[TenantPolicy]:
    return [TenantPolicy()]


def _default_templates() -> list[TenantTemplate]:
    return [TenantTemplate()]


class TenantProductData(BaseModel):
    version: int = 1
    tenants: list[TenantRecord] = Field(default_factory=list)
    policies: list[TenantPolicy] = Field(default_factory=_default_policies)
    templates: list[TenantTemplate] = Field(
        default_factory=_default_templates,
    )
