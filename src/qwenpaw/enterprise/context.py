from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RequestActor:
    actor_id: str = ""
    actor_type: str = "anonymous"
    display_name: str = ""
    source: str = ""


@dataclass(frozen=True, slots=True)
class RequestContext:
    request_id: str
    trace_id: str
    tenant_id: str = ""
    agent_id: str = ""
    user_id: str = ""
    session_id: str = ""
    root_session_id: str = ""
    channel: str = ""
    roles: tuple[str, ...] = ()
    actor: RequestActor = field(default_factory=RequestActor)
    metadata: dict[str, Any] = field(default_factory=dict)


_current_request_context: ContextVar[RequestContext | None] = ContextVar(
    "qwenpaw_enterprise_request_context",
    default=None,
)


def get_current_request_context() -> RequestContext | None:
    return _current_request_context.get()


def set_current_request_context(ctx: RequestContext) -> Token:
    return _current_request_context.set(ctx)


def clear_current_request_context(token: Token) -> None:
    _current_request_context.reset(token)


# ------------------------------------------------------------------
# Per-request tool policy patch ContextVar
# ------------------------------------------------------------------

_current_tool_policy_patch: ContextVar[Any | None] = ContextVar(
    "_current_tool_policy_patch",
    default=None,
)


def get_current_tool_policy_patch() -> Any | None:
    """获取当前请求级别的 ToolPolicyPatch。"""
    return _current_tool_policy_patch.get()


def set_current_tool_policy_patch(
    patch: Any | None,
) -> Token:
    """设置当前请求级别的 ToolPolicyPatch，返回 Token 用于重置。"""
    return _current_tool_policy_patch.set(patch)


def clear_current_tool_policy_patch(token: Token) -> None:
    """重置 ToolPolicyPatch ContextVar。"""
    _current_tool_policy_patch.reset(token)
