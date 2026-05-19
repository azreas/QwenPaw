# -*- coding: utf-8 -*-
from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .permissions import resolve_route_permission

logger = logging.getLogger(__name__)


def _should_skip_console_authz(request: Request) -> bool:
    path = request.url.path
    if path == "/api/webchat" or path.startswith("/api/webchat/"):
        return False

    from ...app import auth as app_auth

    # auth disabled 时跳过 Authz（全局无认证保护）
    # auth enabled 但无用户时不跳过——此时只有 /api/auth/ 公开路由可访问，
    # 受保护路由必须 403，防止未注册用户直接访问 Console API
    return not app_auth.is_auth_enabled()


def _build_context_for_request(request: Request) -> tuple | None:
    """按路径和已有 state 主动构建 RequestContext。

    返回 (RequestContext, roles) 或 None（无法构建时）。
    """
    from ..context import RequestContext, RequestActor

    request_id = getattr(request.state, "request_id", "")
    trace_id = getattr(request.state, "trace_id", "")
    path = request.url.path

    # WebChat 路径：尝试从 token 解析 identity
    if path.startswith("/api/webchat/"):
        cached_identity = getattr(request.state, "webchat_identity", None)
        if cached_identity is not None:
            from ..context_builders import build_context_from_webchat_identity

            ctx = build_context_from_webchat_identity(request, cached_identity)
            return ctx, ctx.roles

        # 未缓存则尝试解析 token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from ...app.webchat.session import (
                    verify_webchat_token as verify_webchat_session_token,
                )

                identity = verify_webchat_session_token(auth_header[7:])
                request.state.webchat_identity = identity
                from ..context_builders import build_context_from_webchat_identity

                ctx = build_context_from_webchat_identity(request, identity)
                request.state.request_context = ctx
                return ctx, ctx.roles
            except Exception:
                logger.debug("AuthzMiddleware: WebChat token 解析失败")
                return None

    # Console 路径：从 request.state.user 和 request.state.roles 获取
    console_user = getattr(request.state, "user", None)
    if console_user:
        roles: tuple[str, ...] = getattr(request.state, "roles", ("platform_admin",))
        tenant_id = getattr(request.state, "tenant_id", "")
        agent_id = ""
        if tenant_id:
            from ...tenancy.ids import tenant_agent_id

            agent_id = tenant_agent_id(tenant_id)
        ctx = RequestContext(
            request_id=request_id,
            trace_id=trace_id,
            tenant_id=tenant_id,
            agent_id=agent_id,
            actor=RequestActor(
                actor_id=console_user,
                actor_type="console_user",
            ),
            roles=roles,
        )
        return ctx, roles

    # BaseHTTPMiddleware 的 call_next 不传播 request.state，
    # 所以 AuthMiddleware 设置的 user/roles 可能读不到。
    # 回退：用与 AuthMiddleware 相同的 token 提取逻辑，直接解析 Console Token。
    from ...app.auth import AuthMiddleware, verify_token_claims

    token = AuthMiddleware._extract_token(request)
    if token:
        try:
            claims = verify_token_claims(token)
            if claims is not None:
                tenant_id = claims.tenant_id
                agent_id = ""
                if tenant_id:
                    from ...tenancy.ids import tenant_agent_id

                    agent_id = tenant_agent_id(tenant_id)
                ctx = RequestContext(
                    request_id=request_id,
                    trace_id=trace_id,
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    actor=RequestActor(
                        actor_id=claims.username,
                        actor_type="console_user",
                    ),
                    roles=claims.roles,
                )
                return ctx, claims.roles
        except Exception:
            logger.debug("AuthzMiddleware: Console token 解析失败")

    return None


class AuthzMiddleware(BaseHTTPMiddleware):
    """按权限矩阵保护 API 路由。"""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        permission = resolve_route_permission(request.method, request.url.path)

        # 公开路由直接放行
        if permission is None:
            return await call_next(request)

        if _should_skip_console_authz(request):
            return await call_next(request)

        resource, action = permission

        # 优先从已有的 request_context 获取角色
        roles: tuple[str, ...] = ()
        request_context = getattr(request.state, "request_context", None)
        if request_context is not None:
            roles = getattr(request_context, "roles", ())

        # 如果没有角色，主动构建 RequestContext
        if not roles:
            result = _build_context_for_request(request)
            if result is not None:
                request_context, roles = result

        # 获取 AuthzService
        enterprise_runtime = getattr(request.app.state, "enterprise_runtime", None)
        if enterprise_runtime is None:
            logger.warning("AuthzMiddleware: enterprise_runtime 未注入，拒绝受保护路由")
            return JSONResponse(
                status_code=403,
                content={"detail": "Authorization service unavailable"},
            )

        authz_service = enterprise_runtime.authz

        # 构造 RequestContext
        from ..context import RequestContext

        if request_context is None:
            request_context = RequestContext(
                request_id=getattr(request.state, "request_id", ""),
                trace_id=getattr(request.state, "trace_id", ""),
                roles=roles,
            )

        decision = await authz_service.check_permission(
            request_context, resource, action,
        )

        if not decision.allowed:
            # 审计：权限拒绝
            try:
                from ..audit.emit import (
                    emit_audit_event,
                    emit_platform_invocation_event,
                )
                from ..audit.models import AuditEventType, AuditOutcome

                await emit_audit_event(
                    request,
                    event_type=AuditEventType.AUTHZ_DENIED,
                    action=f"{resource}:{action}",
                    outcome=AuditOutcome.DENIED,
                    resource_type=resource,
                    resource_id=request.url.path,
                )
                if decision.reason == "tenant_boundary":
                    call_type = "tenant_boundary"
                    error_code = "tenant_boundary.denied"
                else:
                    call_type = "authz"
                    error_code = "authz.denied"
                await emit_platform_invocation_event(
                    request=request,
                    call_type=call_type,
                    call_name=f"{resource}:{action}",
                    status="denied",
                    duration_ms=0.0,
                    error_code=error_code,
                    error_reason=decision.reason
                    or f"Permission denied: {resource}:{action}",
                    resource_type=resource,
                    resource_id=request.url.path,
                )
            except Exception:
                pass
            return JSONResponse(
                status_code=403,
                content={"detail": f"Permission denied: {resource}:{action}"},
            )

        # 将 RequestContext 写入 request.state 供下游使用
        existing = getattr(request.state, "request_context", None)
        if existing is None:
            request.state.request_context = request_context

        return await call_next(request)
