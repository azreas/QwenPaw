from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from qwenpaw.enterprise.audit.emit import (
    emit_audit_event,
    emit_platform_invocation_event,
)
from qwenpaw.enterprise.audit.models import AuditEventType, AuditOutcome
from qwenpaw.enterprise.context import RequestContext
from qwenpaw.enterprise.errors import build_error_envelope

from .models import PolicyAction


def _get_request_context(request: Request) -> RequestContext:
    ctx = getattr(request.state, "request_context", None)
    if ctx is None:
        ctx = RequestContext(
            request_id=getattr(request.state, "request_id", ""),
            trace_id=getattr(request.state, "trace_id", ""),
        )
        request.state.request_context = ctx
    return ctx


def require_policy(action: PolicyAction, resource: str):
    async def dependency(
        request: Request,
        ctx: RequestContext = Depends(_get_request_context),
    ) -> None:
        runtime = getattr(request.app.state, "enterprise_runtime", None)
        policy = getattr(runtime, "policy", None)
        if policy is None:
            message = "Policy service unavailable"
            raise HTTPException(
                status_code=503,
                detail=build_error_envelope(
                    ctx,
                    error_code="policy.unavailable",
                    message=message,
                    recoverable=True,
                    extra={"detail": message},
                ),
            )
        decision = await policy.evaluate(ctx, action, resource)
        if not decision.allowed:
            try:
                await emit_audit_event(
                    request,
                    event_type=AuditEventType.POLICY_DENIED,
                    action=action.value,
                    outcome=AuditOutcome.DENIED,
                    resource_type="policy",
                    resource_id=resource,
                    payload=decision.metadata,
                )
                await emit_platform_invocation_event(
                    request=request,
                    call_type="policy",
                    call_name=action.value,
                    status="denied",
                    duration_ms=0.0,
                    error_code="policy.denied",
                    error_reason=decision.reason,
                    resource_type="policy",
                    resource_id=resource,
                    metadata=decision.metadata,
                )
            except Exception:
                pass
            raise HTTPException(
                status_code=403,
                detail=build_error_envelope(
                    ctx,
                    error_code="policy.denied",
                    message=decision.reason,
                    extra={"detail": decision.reason},
                ),
            )

    return Depends(dependency)
