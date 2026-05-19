"""审计事件领域模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from qwenpaw.enterprise.context import RequestContext


class AuditEventType(StrEnum):
    AUTH_LOGIN_SUCCESS = "auth.login_success"
    AUTH_LOGIN_FAILED = "auth.login_failed"
    AUTH_REGISTER = "auth.register"
    AUTH_TOKEN_REVOKED = "auth.token_revoked"
    AUTH_USER_CREATED = "auth.user_created"
    AUTH_USER_UPDATED = "auth.user_updated"
    AUTH_SECURITY_REJECTED = "auth.security_rejected"
    AUTHZ_DENIED = "authz.denied"
    TOOL_GUARD_EVALUATED = "tool.guard_evaluated"
    CONFIG_UPDATED = "config.updated"
    TENANT_UPDATED = "tenant.updated"
    POLICY_EVALUATED = "policy.evaluated"
    POLICY_DENIED = "policy.denied"
    QUOTA_WARNED = "quota.warned"
    QUOTA_DENIED = "quota.denied"
    QUOTA_CONSUMED = "quota.consumed"
    COMPLIANCE_EXPORTED = "compliance.exported"
    SKILL_INSTALLED = "skill.installed"
    SKILL_ENABLED = "skill.enabled"
    SKILL_DISABLED = "skill.disabled"
    SKILL_DELETED = "skill.deleted"
    SKILL_CALLED = "skill.called"
    MCP_CREATED = "mcp.created"
    MCP_UPDATED = "mcp.updated"
    MCP_ENABLED = "mcp.enabled"
    MCP_DISABLED = "mcp.disabled"
    MCP_DELETED = "mcp.deleted"
    MCP_CONNECTION_TEST = "mcp.connection_test"
    MCP_CALLED = "mcp.called"
    PLATFORM_INVOCATION = "platform.invocation"
    BAD_CASE_MARKED = "bad_case.marked"
    BAD_CASE_UPDATED = "bad_case.updated"
    BACKUP_OPERATION = "backup.operation"


class AuditOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_type: AuditEventType
    action: str
    outcome: AuditOutcome
    id: str = field(default_factory=lambda: uuid4().hex)
    tenant_id: str = ""
    agent_id: str = ""
    session_id: str = ""
    actor_id: str = ""
    actor_type: str = ""
    resource_type: str = ""
    resource_id: str = ""
    request_id: str = ""
    trace_id: str = ""
    ip_address: str = ""
    user_agent: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @classmethod
    def from_context(
        cls,
        ctx: RequestContext,
        event_type: AuditEventType,
        action: str,
        outcome: AuditOutcome,
        resource_type: str = "",
        resource_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        payload: dict[str, Any] | None = None,
    ) -> AuditEvent:
        return cls(
            event_type=event_type,
            action=action,
            outcome=outcome,
            tenant_id=ctx.tenant_id,
            agent_id=ctx.agent_id,
            session_id=ctx.session_id,
            actor_id=ctx.actor.actor_id,
            actor_type=ctx.actor.actor_type,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=ctx.request_id,
            trace_id=ctx.trace_id,
            ip_address=ip_address or ctx.metadata.get("client_host", ""),
            user_agent=user_agent or ctx.metadata.get("user_agent", ""),
            payload=payload or {},
        )
