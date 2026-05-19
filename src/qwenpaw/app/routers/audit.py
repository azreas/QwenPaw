"""审计查询 API — 受 RBAC 和租户边界保护的只读接口。

路由前缀：/api/audit
权限保护：由 AuthzMiddleware 统一执行（/api/audit → audit 资源）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from qwenpaw.enterprise.authz.deps import get_request_context

router = APIRouter(prefix="/audit", tags=["audit"])

_BUSINESS_EVENT_TYPES = {
    "skill": ("skill.called",),
    "mcp": ("mcp.called",),
    "agent": ("platform.invocation",),
    "builtin_tool": ("platform.invocation",),
    "runtime_extension": ("platform.invocation",),
    "authz": ("platform.invocation",),
    "tenant_boundary": ("platform.invocation",),
    "quota": ("platform.invocation",),
    "policy": ("platform.invocation",),
    "tool_guard": ("platform.invocation",),
}
_ALL_BUSINESS_EVENT_TYPES = ("skill.called", "mcp.called", "platform.invocation")


def _bounded_limit(limit: int) -> int:
    return max(1, min(limit, 1000))


def _audit_repository(request: Request):
    enterprise_runtime = getattr(
        request.app.state, "enterprise_runtime", None
    )
    if enterprise_runtime is None:
        raise HTTPException(status_code=503, detail="Audit service unavailable")

    audit_bus = getattr(enterprise_runtime, "audit", None)
    repository = getattr(audit_bus, "_repository", None)
    if repository is None:
        raise HTTPException(status_code=503, detail="Audit repository unavailable")

    return repository


def _resolve_tenant_filter(
    request: Request,
    requested_tenant_id: str | None,
) -> str | None:
    """返回实际审计查询 tenant_id。

    平台管理员可跨租户查询；租户角色只能查询 RequestContext 中的本租户。
    """
    ctx = get_request_context(request)
    if "platform_admin" in ctx.roles:
        return requested_tenant_id

    if not ctx.tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Tenant context is required for audit query",
        )

    if requested_tenant_id and requested_tenant_id != ctx.tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Tenant boundary denied",
        )

    return ctx.tenant_id


def _serialize_audit_row(row) -> dict:
    return {
        "id": row.id,
        "event_type": row.event_type,
        "action": row.action,
        "outcome": row.outcome,
        "tenant_id": row.tenant_id,
        "agent_id": row.agent_id,
        "session_id": row.session_id,
        "actor_id": row.actor_id,
        "actor_type": row.actor_type,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "request_id": row.request_id,
        "trace_id": row.trace_id,
        "ip_address": row.ip_address,
        "user_agent": row.user_agent,
        "payload": row.payload,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _ability_type_from_row(row) -> str:
    payload = row.payload or {}
    ability_type = payload.get("ability_type")
    if ability_type:
        return str(ability_type)
    call_type = payload.get("call_type")
    if call_type:
        return str(call_type)
    if row.event_type == "skill.called":
        return "skill"
    if row.event_type == "mcp.called":
        return "mcp"
    return str(row.resource_type or "")


def _call_type_from_row(row) -> str:
    payload = row.payload or {}
    call_type = payload.get("call_type")
    if call_type:
        return str(call_type)
    return _ability_type_from_row(row)


def _business_trace_matches(
    row,
    *,
    ability_type: str | None,
    ability_name: str | None,
    call_type: str | None,
    call_name: str | None,
    entrypoint: str | None,
    status: str | None,
    error_code: str | None,
    error_reason: str | None,
) -> bool:
    payload = row.payload or {}
    if ability_type and _ability_type_from_row(row) != ability_type:
        return False
    if call_type and _call_type_from_row(row) != call_type:
        return False
    if ability_name and str(
        payload.get("ability_name") or row.resource_id
    ) != ability_name:
        return False
    if call_name and str(payload.get("call_name") or row.resource_id) != call_name:
        return False
    if entrypoint and str(payload.get("entrypoint") or "") != entrypoint:
        return False
    if status and str(payload.get("status") or row.outcome) != status:
        return False
    if error_code and str(payload.get("error_code") or "") != error_code:
        return False
    if error_reason and error_reason not in str(payload.get("error_reason") or ""):
        return False
    return True


def _serialize_business_trace(row) -> dict:
    payload = row.payload or {}
    call_type = _call_type_from_row(row)
    call_name = payload.get("call_name") or payload.get("ability_name") or row.resource_id
    return {
        "id": row.id,
        "event_type": row.event_type,
        "tenant_id": row.tenant_id,
        "agent_id": row.agent_id or payload.get("agent_id", ""),
        "session_id": row.session_id or payload.get("session_id", ""),
        "actor_id": row.actor_id,
        "entrypoint": payload.get("entrypoint", ""),
        "ability_type": _ability_type_from_row(row),
        "ability_name": payload.get("ability_name") or call_name,
        "call_type": call_type,
        "call_name": call_name,
        "duration_ms": payload.get("duration_ms"),
        "status": payload.get("status") or row.outcome,
        "error_code": payload.get("error_code", ""),
        "error_reason": payload.get("error_reason", ""),
        "request_id": row.request_id,
        "trace_id": row.trace_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/events")
async def list_audit_events(
    request: Request,
    tenant_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    event_type: Optional[str] = None,
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    outcome: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
) -> dict:
    """查询审计事件，非平台角色强制限定为本租户。"""
    repository = _audit_repository(request)
    effective_tenant_id = _resolve_tenant_filter(request, tenant_id)

    rows = await repository.query(
        tenant_id=effective_tenant_id,
        actor_id=actor_id,
        event_type=event_type,
        agent_id=agent_id,
        session_id=session_id,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        start_time=start_time,
        end_time=end_time,
        limit=_bounded_limit(limit),
    )

    return {
        "events": [_serialize_audit_row(row) for row in rows],
        "count": len(rows),
    }


@router.get("/business-calls")
async def list_business_call_traces(
    request: Request,
    tenant_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None,
    ability_type: Optional[str] = None,
    ability_name: Optional[str] = None,
    call_type: Optional[str] = None,
    call_name: Optional[str] = None,
    entrypoint: Optional[str] = None,
    status: Optional[str] = None,
    error_code: Optional[str] = None,
    error_reason: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
) -> dict:
    """查询平台调用追踪，返回兼容业务追踪的产品化字段。"""
    if ability_type and ability_type not in _BUSINESS_EVENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="ability_type must be a supported platform call type",
        )
    if call_type and call_type not in _BUSINESS_EVENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="call_type must be a supported platform call type",
        )

    repository = _audit_repository(request)
    effective_tenant_id = _resolve_tenant_filter(request, tenant_id)
    type_filter = call_type or ability_type
    event_types = (
        _BUSINESS_EVENT_TYPES[type_filter]
        if type_filter
        else _ALL_BUSINESS_EVENT_TYPES
    )
    query_limit = _bounded_limit(limit)
    fetch_limit = 1000 if any(
        (ability_name, call_name, entrypoint, status, error_code, error_reason)
    ) else query_limit

    rows = await repository.query(
        tenant_id=effective_tenant_id,
        actor_id=actor_id,
        agent_id=agent_id,
        session_id=session_id,
        event_types=event_types,
        start_time=start_time,
        end_time=end_time,
        limit=fetch_limit,
    )

    traces = [
        _serialize_business_trace(row)
        for row in rows
        if _business_trace_matches(
            row,
            ability_type=ability_type,
            ability_name=ability_name,
            call_type=call_type,
            call_name=call_name,
            entrypoint=entrypoint,
            status=status,
            error_code=error_code,
            error_reason=error_reason,
        )
    ][:query_limit]

    return {
        "traces": traces,
        "count": len(traces),
    }
