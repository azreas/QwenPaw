# -*- coding: utf-8 -*-
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from .context import RequestActor, RequestContext

if TYPE_CHECKING:
    from qwenpaw.app.webchat.session import WebchatIdentity


def build_context_from_webchat_identity(
    request: object,
    identity: "WebchatIdentity",
) -> RequestContext:
    """从 FastAPI request 和 WebchatIdentity 构建 RequestContext。"""
    state = getattr(request, "state", None)
    request_id = getattr(state, "request_id", "") if state else ""
    trace_id = getattr(state, "trace_id", "") if state else ""
    if not request_id:
        request_id = uuid.uuid4().hex
    if not trace_id:
        trace_id = uuid.uuid4().hex

    client_host = ""
    client = getattr(request, "client", None)
    if client:
        client_host = getattr(client, "host", "")

    user_agent = ""
    headers = getattr(request, "headers", {})
    if hasattr(headers, "get"):
        user_agent = headers.get("user-agent", "")
    elif isinstance(headers, dict):
        user_agent = headers.get("user-agent", "")

    return RequestContext(
        request_id=request_id,
        trace_id=trace_id,
        tenant_id=identity.tenant_id,
        agent_id=identity.agent_id,
        user_id=identity.employee_id,
        channel="webchat",
        roles=identity.roles,
        actor=RequestActor(
            actor_id=identity.employee_id,
            actor_type="webchat_user",
            display_name=identity.username,
            source="webchat_sso",
        ),
        metadata={
            "wechat_company_id": identity.wechat_company_id,
            "department": identity.department,
            "station": identity.station,
            "client_host": client_host,
            "user_agent": user_agent,
        },
    )


def build_context_from_runner_payload(
    *,
    request_id: str = "",
    trace_id: str = "",
    agent_id: str = "",
    session_id: str = "",
    root_session_id: str = "",
    user_id: str = "",
    channel: str = "",
    tenant_id: str = "",
    roles: tuple[str, ...] | None = None,
) -> RequestContext:
    """从 runner 请求 payload 构建 RequestContext。

    对于 wx_* 动态租户 agent，如果未显式传入 tenant_id，
    则从 agent_id 中推导（去掉 wx_ 前缀）。

    roles 默认：wx_* agent 为 ("tenant_member",)，使 skills:call /
    mcp:call 等 RBAC 权限在真实调用路径生效；
    非 wx_* agent 为空元组。
    """
    if not request_id:
        request_id = uuid.uuid4().hex
    if not trace_id:
        trace_id = uuid.uuid4().hex

    if not tenant_id and agent_id.startswith("wx_") and agent_id != "wx_":
        tenant_id = agent_id[3:]

    if roles is None:
        roles = ("tenant_member",) if agent_id.startswith("wx_") else ()

    return RequestContext(
        request_id=request_id,
        trace_id=trace_id,
        tenant_id=tenant_id,
        agent_id=agent_id,
        session_id=session_id,
        root_session_id=root_session_id or session_id,
        user_id=user_id,
        channel=channel,
        roles=roles,
        actor=RequestActor(
            actor_id=user_id,
            actor_type="channel_user",
        ),
    )
