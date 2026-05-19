"""emit_audit_event() — 从 request 上下文提取信息并写入审计总线。

缺失 runtime 或 audit bus 时写 debug 日志并返回，不影响主业务。
"""

from __future__ import annotations

import logging
from typing import Any

from qwenpaw.enterprise.audit.models import AuditEvent, AuditEventType, AuditOutcome
from qwenpaw.enterprise.tracing.models import InvocationCallType, InvocationStatus

logger = logging.getLogger(__name__)


async def emit_audit_event(
    request: Any,
    event_type: AuditEventType,
    action: str,
    outcome: AuditOutcome,
    resource_type: str = "",
    resource_id: str = "",
    payload: dict[str, Any] | None = None,
) -> None:
    """向运行时审计总线发送事件。

    从 request.state.request_context 提取上下文字段；
    缺失时使用 request id / trace id 构造最小上下文。
    """
    enterprise_runtime = getattr(
        getattr(request, "app", None), "state", None,
    )
    if enterprise_runtime is None:
        logger.debug("emit_audit_event: 无 app.state，跳过")
        return

    runtime = getattr(enterprise_runtime, "enterprise_runtime", None)
    if runtime is None:
        logger.debug("emit_audit_event: 无 enterprise_runtime，跳过")
        return

    audit_bus = getattr(runtime, "audit", None)
    if audit_bus is None:
        logger.debug("emit_audit_event: 无 audit bus，跳过")
        return

    # 从 request context 提取字段
    ctx = getattr(request.state, "request_context", None)
    if ctx is not None:
        event = AuditEvent.from_context(
            ctx,
            event_type=event_type,
            action=action,
            outcome=outcome,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=payload,
        )
    else:
        # 最小上下文
        request_id = getattr(request.state, "request_id", "")
        trace_id = getattr(request.state, "trace_id", "")
        event = AuditEvent(
            event_type=event_type,
            action=action,
            outcome=outcome,
            request_id=request_id,
            trace_id=trace_id,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=payload or {},
        )

    try:
        await audit_bus.emit(event)
    except Exception:
        logger.exception("审计事件发送失败")


async def emit_business_call_event(
    *,
    request: Any,
    ability_type: str,
    ability_name: str,
    status: str,
    duration_ms: float,
    error_reason: str = "",
    entrypoint: str = "",
) -> None:
    """发送业务能力调用追踪事件（skill.call / mcp.call）。

    事件 payload 至少包含：
    entrypoint, tenant_id, agent_id, session_id,
    ability_type, ability_name, duration_ms, status, error_reason。
    """
    if ability_type not in {"mcp", "skill"}:
        logger.debug("emit_business_call_event: 未知能力类型 %s", ability_type)
        return

    await emit_platform_invocation_event(
        request=request,
        call_type=ability_type,
        call_name=ability_name,
        status=status,
        duration_ms=duration_ms,
        error_reason=error_reason,
        entrypoint=entrypoint,
        legacy_business_event=True,
    )


async def emit_platform_invocation_event(
    *,
    request: Any,
    call_type: str | InvocationCallType,
    call_name: str,
    status: str | InvocationStatus,
    duration_ms: float,
    error_code: str = "",
    error_reason: str = "",
    entrypoint: str = "",
    resource_type: str = "",
    resource_id: str = "",
    metadata: dict[str, Any] | None = None,
    legacy_business_event: bool = False,
) -> None:
    """发送平台调用追踪事件，覆盖 agent / tool / mcp / 拒绝类调用。"""
    call_type_value = (
        call_type.value if isinstance(call_type, InvocationCallType) else str(call_type)
    )
    status_value = (
        status.value if isinstance(status, InvocationStatus) else str(status)
    )

    if legacy_business_event and call_type_value == "mcp":
        event_type = AuditEventType.MCP_CALLED
    elif legacy_business_event and call_type_value == "skill":
        event_type = AuditEventType.SKILL_CALLED
    else:
        event_type = AuditEventType.PLATFORM_INVOCATION

    if status_value == "success":
        outcome = AuditOutcome.SUCCESS
    elif status_value == "denied":
        outcome = AuditOutcome.DENIED
    else:
        outcome = AuditOutcome.FAILURE

    # 从 request 提取身份/租户/会话上下文
    ctx = getattr(getattr(request, "state", None), "request_context", None)
    if ctx is not None:
        payload = {
            "entrypoint": entrypoint or ctx.channel,
            "tenant_id": ctx.tenant_id,
            "agent_id": ctx.agent_id,
            "session_id": ctx.session_id,
            "call_type": call_type_value,
            "call_name": call_name,
            "ability_type": call_type_value,
            "ability_name": call_name,
            "duration_ms": duration_ms,
            "status": status_value,
            "error_code": error_code,
            "error_reason": error_reason,
            "request_id": ctx.request_id,
            "trace_id": ctx.trace_id,
        }
    else:
        payload = {
            "entrypoint": entrypoint,
            "tenant_id": "",
            "agent_id": "",
            "session_id": "",
            "call_type": call_type_value,
            "call_name": call_name,
            "ability_type": call_type_value,
            "ability_name": call_name,
            "duration_ms": duration_ms,
            "status": status_value,
            "error_code": error_code,
            "error_reason": error_reason,
        }
    if metadata:
        payload.update(metadata)
        payload["metadata"] = metadata

    await emit_audit_event(
        request,
        event_type=event_type,
        action="call",
        outcome=outcome,
        resource_type=resource_type or call_type_value,
        resource_id=resource_id or call_name,
        payload=payload,
    )
