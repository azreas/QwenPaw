# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from ..audit.emit import emit_platform_invocation_event
from ..context import RequestContext
from ..errors import build_error_envelope


def get_request_context(request: Request) -> RequestContext:
    """从 request.state 获取 RequestContext，用于 FastAPI 依赖注入。"""
    ctx = getattr(request.state, "request_context", None)
    if ctx is not None:
        return ctx
    # 兜底：构造最小匿名上下文
    return RequestContext(
        request_id=getattr(request.state, "request_id", ""),
        trace_id=getattr(request.state, "trace_id", ""),
    )


def require_role(*role_names: str):
    """FastAPI 依赖：要求请求上下文包含指定角色之一。"""
    async def _check(request: Request) -> RequestContext:
        ctx = get_request_context(request)
        if not any(r in ctx.roles for r in role_names):
            message = f"Required role: {'|'.join(role_names)}"
            try:
                await emit_platform_invocation_event(
                    request=request,
                    call_type="authz",
                    call_name=f"role:{'|'.join(role_names)}",
                    status="denied",
                    duration_ms=0.0,
                    error_code="authz.role_required",
                    error_reason=message,
                    resource_type="role",
                    resource_id="|".join(role_names),
                )
            except Exception:
                pass
            raise HTTPException(
                status_code=403,
                detail=build_error_envelope(
                    ctx,
                    error_code="authz.role_required",
                    message=message,
                    extra={"detail": message},
                ),
            )
        return ctx
    return _check


def require_permission(resource: str, action: str):
    """FastAPI 依赖：要求请求上下文具有指定权限。"""
    async def _check(request: Request) -> RequestContext:
        ctx = get_request_context(request)
        enterprise_runtime = getattr(request.app.state, "enterprise_runtime", None)
        if enterprise_runtime is None:
            message = "Authorization service unavailable"
            raise HTTPException(
                status_code=403,
                detail=build_error_envelope(
                    ctx,
                    error_code="authz.unavailable",
                    message=message,
                    extra={"detail": message},
                ),
            )
        decision = await enterprise_runtime.authz.check_permission(
            ctx, resource, action,
        )
        if not decision.allowed:
            message = f"Permission denied: {resource}:{action}"
            if decision.reason == "tenant_boundary":
                call_type = "tenant_boundary"
                error_code = "tenant_boundary.denied"
            else:
                call_type = "authz"
                error_code = "authz.denied"
            try:
                await emit_platform_invocation_event(
                    request=request,
                    call_type=call_type,
                    call_name=f"{resource}:{action}",
                    status="denied",
                    duration_ms=0.0,
                    error_code=error_code,
                    error_reason=decision.reason or message,
                    resource_type=resource,
                    resource_id=action,
                )
            except Exception:
                pass
            raise HTTPException(
                status_code=403,
                detail=build_error_envelope(
                    ctx,
                    error_code="authz.denied",
                    message=message,
                    extra={"detail": message},
                ),
            )
        return ctx
    return _check
