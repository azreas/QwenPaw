# -*- coding: utf-8 -*-
"""Shared helpers for WeCom tenant configuration routers."""
from __future__ import annotations

import logging
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request

from ...multi_agent_manager import MultiAgentManager
from ...utils import schedule_agent_reload
from ....config.agent_config_file import (
    load_agent_config_from_workspace,
    write_agent_config_to_workspace,
)
from ....enterprise.audit.models import AuditEvent, AuditEventType, AuditOutcome
from ....config.config import AgentProfileConfig
from ....enterprise.authz.deps import get_request_context
from ....tenancy.ids import tenant_agent_id
from ....tenancy.paths import (
    tenant_workspace_dir,
    tenants_root as resolve_tenants_root,
    validate_tenant_agent_id,
)

logger = logging.getLogger(__name__)


def tenants_root() -> Path:
    return resolve_tenants_root()


def validate_agent_id(agent_id: str) -> str:
    try:
        return validate_tenant_agent_id(agent_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Only wx_* tenant agent ids are supported",
        ) from exc


def tenant_id_from_agent_id(agent_id: str) -> str:
    """Best-effort reverse mapping for wx_* dynamic tenant agent ids."""
    return agent_id[3:] if agent_id.startswith("wx_") else agent_id


def audit_repository_from_request(request: Request) -> Any | None:
    """Return the enterprise audit repository when the runtime exposes one."""
    runtime = getattr(request.app.state, "enterprise_runtime", None)
    if runtime is None:
        return None
    audit_bus = getattr(runtime, "audit", None)
    if audit_bus is None:
        return None
    return getattr(audit_bus, "_repository", None) or getattr(
        audit_bus,
        "repository",
        None,
    )


def tenant_request_context(request: Request, agent_id: str):
    """Build a RequestContext pinned to the tenant targeted by the route."""
    ctx = get_request_context(request)
    tenant_id = ctx.tenant_id
    if not tenant_id or tenant_agent_id(tenant_id) != agent_id:
        tenant_id = tenant_id_from_agent_id(agent_id)
    return replace(ctx, tenant_id=tenant_id, agent_id=agent_id)


async def emit_tenant_audit_event(
    request: Request,
    agent_id: str,
    event_type: AuditEventType,
    action: str,
    outcome: AuditOutcome,
    *,
    resource_type: str = "",
    resource_id: str = "",
    payload: dict[str, Any] | None = None,
    strict: bool = False,
) -> None:
    """Emit an audit event with row-level tenant/agent fields set to agent_id.

    当 strict=True 时，audit bus 不可用或 emit 失败会抛出 HTTPException(503)，
    用于 Bad Case 等以审计事件为唯一持久化路径的写入接口，避免“保存成功假象”。
    """
    runtime = getattr(request.app.state, "enterprise_runtime", None)
    audit_bus = getattr(runtime, "audit", None) if runtime is not None else None
    if audit_bus is None:
        if strict:
            raise HTTPException(
                status_code=503,
                detail="Audit bus unavailable; event not persisted",
            )
        logger.debug("emit_tenant_audit_event: audit bus unavailable")
        return

    ctx = tenant_request_context(request, agent_id)
    event = AuditEvent.from_context(
        ctx,
        event_type=event_type,
        action=action,
        outcome=outcome,
        resource_type=resource_type,
        resource_id=resource_id,
        payload=payload,
    )
    try:
        await audit_bus.emit(event)
    except Exception as exc:
        logger.exception("租户审计事件发送失败")
        if strict:
            raise HTTPException(
                status_code=503,
                detail="Failed to persist audit event",
            ) from exc


def workspace_for_agent_id(agent_id: str) -> Path:
    return tenant_workspace_dir(validate_agent_id(agent_id))


def require_workspace(agent_id: str) -> Path:
    workspace_dir = workspace_for_agent_id(agent_id)
    if not workspace_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"Tenant workspace '{agent_id}' not found",
        )
    return workspace_dir


def get_manager(request: Request) -> MultiAgentManager:
    manager = getattr(request.app.state, "multi_agent_manager", None)
    if manager is None:
        raise HTTPException(
            status_code=503,
            detail="MultiAgentManager not initialized",
        )
    return manager


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Date must use YYYY-MM-DD format",
        ) from None


def date_range(start_date: str | None, end_date: str | None) -> tuple[date, date]:
    end_d = parse_date(end_date) or date.today()
    start_d = parse_date(start_date) or (end_d - timedelta(days=30))
    if start_d > end_d:
        start_d, end_d = end_d, start_d
    return start_d, end_d


def load_tenant_config(agent_id: str) -> AgentProfileConfig:
    workspace_dir = require_workspace(agent_id)
    try:
        config = load_agent_config_from_workspace(workspace_dir)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Tenant agent.json is invalid: {exc}",
        ) from exc
    if config is None:
        raise HTTPException(
            status_code=404,
            detail=f"Tenant workspace '{agent_id}' has no agent.json",
        )
    return config


def save_tenant_config(agent_id: str, config: AgentProfileConfig) -> None:
    workspace_dir = require_workspace(agent_id)
    write_agent_config_to_workspace(workspace_dir, config)


def maybe_reload(request: Request, agent_id: str) -> None:
    manager = get_manager(request)
    if manager.is_agent_loaded(agent_id):
        schedule_agent_reload(request, agent_id)


def require_tenant_boundary():
    """FastAPI 依赖：验证请求上下文中的租户可以访问目标 agent_id。

    从 request.path_params 中读取 agent_id，
    非 platform_admin 用户只能访问自己租户的 agent。

    P3-2 限制：Console 认证 token 暂无 tenant_id 字段，
    因此无租户上下文的非 platform_admin 请求会被拒绝。
    租户管理员需等 P3-3 补 tenant_id 映射后才能使用 Console 管理接口。
    """
    from ....tenancy.ids import tenant_agent_id

    async def _check(request: Request) -> RequestContext:
        agent_id = request.path_params.get("agent_id", "")
        ctx = get_request_context(request)
        if "platform_admin" in ctx.roles:
            return ctx
        target_tenant_id = ctx.tenant_id
        if not target_tenant_id:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Tenant-scoped access requires tenant context. "
                    "Console users without tenant binding must use "
                    "platform_admin role."
                ),
            )
        expected_agent_id = tenant_agent_id(target_tenant_id)
        if agent_id != expected_agent_id:
            logger.warning(
                "Tenant boundary violation: %s attempted to access %s (own agent: %s)",
                target_tenant_id,
                agent_id,
                expected_agent_id,
            )
            raise HTTPException(
                status_code=403,
                detail=f"Tenant boundary: cannot access agent '{agent_id}'",
            )
        return ctx

    return _check


async def ensure_tenant_boundary_for_agent(
    request: Request,
    agent_id: str,
):
    """Validate tenant boundary for endpoints that do not expose agent_id as a path param.

    Batch operations receive target agent ids in the request body, so the normal
    FastAPI dependency cannot read them from request.path_params.
    """
    from ....enterprise.context import RequestContext
    from ....tenancy.ids import tenant_agent_id

    validate_agent_id(agent_id)
    ctx = get_request_context(request)
    if "platform_admin" in ctx.roles:
        return ctx
    target_tenant_id = ctx.tenant_id
    if not target_tenant_id:
        raise HTTPException(
            status_code=403,
            detail=(
                "Tenant-scoped access requires tenant context. "
                "Console users without tenant binding must use "
                "platform_admin role."
            ),
        )
    expected_agent_id = tenant_agent_id(target_tenant_id)
    if agent_id != expected_agent_id:
        logger.warning(
            "Tenant boundary violation: %s attempted to access %s (own agent: %s)",
            target_tenant_id,
            agent_id,
            expected_agent_id,
        )
        raise HTTPException(
            status_code=403,
            detail=f"Tenant boundary: cannot access agent '{agent_id}'",
        )
    return ctx
