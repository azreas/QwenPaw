from __future__ import annotations

from dataclasses import replace

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from qwenpaw.enterprise.audit.emit import emit_platform_invocation_event
from qwenpaw.enterprise.context import RequestContext
from qwenpaw.enterprise.errors import build_error_envelope

from .models import QuotaDimension


class QuotaMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        runtime = getattr(request.app.state, "enterprise_runtime", None)
        quota = getattr(runtime, "quota", None)
        if quota is None:
            return await call_next(request)

        # 获取 agent_id：state.agent_id → X-Agent-Id header → ""
        agent_id = getattr(request.state, "agent_id", "") or ""
        if not agent_id:
            agent_id = request.headers.get("X-Agent-Id", "")

        ctx = getattr(request.state, "request_context", None)
        if ctx is None:
            # 没有 context，新建一个
            ctx = RequestContext(
                request_id=getattr(request.state, "request_id", ""),
                trace_id=getattr(request.state, "trace_id", ""),
                tenant_id=agent_id,
                agent_id=agent_id,
            )
            request.state.request_context = ctx
        elif not ctx.tenant_id and agent_id:
            # 已有 context 但 tenant_id 为空，此时 agent_id 已被后置注入（如 AgentContext）
            # 用 replace 补全 tenant_id 和 agent_id，避免匹配不到租户级配额
            ctx = replace(ctx, tenant_id=agent_id, agent_id=agent_id)
            request.state.request_context = ctx

        decision = await quota.consume(
            ctx,
            QuotaDimension.HTTP_REQUEST,
            resource=f"{request.method}:{request.url.path}",
        )
        if not decision.allowed:
            retry_after = 60
            try:
                await emit_platform_invocation_event(
                    request=request,
                    call_type="quota",
                    call_name=QuotaDimension.HTTP_REQUEST.value,
                    status="denied",
                    duration_ms=0.0,
                    error_code="quota.denied",
                    error_reason=decision.reason,
                    resource_type="quota",
                    resource_id=f"{request.method}:{request.url.path}",
                )
            except Exception:
                pass
            return JSONResponse(
                status_code=429,
                content=build_error_envelope(
                    ctx,
                    error_code="quota.denied",
                    message=decision.reason,
                    recoverable=True,
                    retry_after=retry_after,
                    extra={"detail": decision.reason},
                ),
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)
