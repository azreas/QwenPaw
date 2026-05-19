# -*- coding: utf-8 -*-
"""WebChat tenant capability APIs."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from qwenpaw.tenancy.product_models import TenantPolicy
from qwenpaw.tenancy.product_service import ensure_tenant_record, resolve_tenant_policy
from qwenpaw.tenancy.product_store import TenantProductStore

from .webchat import _get_identity_from_request

router = APIRouter(prefix="/webchat", tags=["webchat-capabilities"])


class WebchatCapabilitiesResponse(BaseModel):
    tenant_id: str
    agent_id: str
    policy_id: str
    capabilities: dict[str, bool]
    limits: dict[str, Any]


def _capabilities_from_policy(policy: TenantPolicy) -> dict[str, bool]:
    return {
        "chat": True,
        "sessions": True,
        "files": True,
        "skills": True,
        "skill_create": policy.allow_skill_create,
        "skill_upload_zip": policy.allow_skill_upload_zip,
        "skill_hub_import": policy.allow_skill_hub_import,
        "tools": policy.allow_tools,
        "model_switch": policy.allow_model_switch,
        "mcp": policy.allow_mcp,
        "tasks": policy.allow_tasks,
        "task_run_now": policy.allow_tasks and policy.allow_task_run_now,
        "usage": True,
        "advanced_config": policy.advanced_config_enabled,
        "platform_ops": False,
    }


def _limits_from_policy(policy: TenantPolicy) -> dict[str, Any]:
    return {
        "allowed_models": policy.allowed_models,
        "allowed_tools": policy.allowed_tools,
        "allowed_mcp_transports": policy.allowed_mcp_transports,
        "max_cron_jobs": policy.max_cron_jobs,
        "min_cron_interval_minutes": policy.min_cron_interval_minutes,
        "task_timeout_seconds": policy.task_timeout_seconds,
        "file_upload_limit_mb": policy.file_upload_limit_mb,
        "token_quota_monthly": policy.token_quota_monthly,
    }


@router.get("/capabilities", response_model=WebchatCapabilitiesResponse)
async def get_webchat_capabilities(request: Request) -> WebchatCapabilitiesResponse:
    identity = _get_identity_from_request(request)
    store = TenantProductStore()
    tenant = ensure_tenant_record(
        store,
        tenant_id=identity.tenant_id,
        agent_id=identity.agent_id,
        display_name=identity.username,
        source="webchat",
    )
    policy = resolve_tenant_policy(store, tenant)
    return WebchatCapabilitiesResponse(
        tenant_id=identity.tenant_id,
        agent_id=identity.agent_id,
        policy_id=policy.policy_id,
        capabilities=_capabilities_from_policy(policy),
        limits=_limits_from_policy(policy),
    )
