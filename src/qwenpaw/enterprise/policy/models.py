from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PolicyAction(StrEnum):
    HTTP_REQUEST = "http.request"
    AGENT_RUN = "agent.run"
    TOOL_CALL = "tool.call"
    MCP_CALL = "mcp.call"
    SKILL_INSTALL = "skill.install"
    FILE_READ = "file.read"
    FILE_WRITE = "file.write"
    DATA_EXPORT = "data.export"
    QUOTA_CHECK = "quota.check"


class PolicyEffect(StrEnum):
    ALLOW = "allow"
    WARN = "warn"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass(frozen=True, slots=True)
class PolicyRule:
    rule_id: str
    effect: PolicyEffect
    action: PolicyAction
    resource: str = "*"
    roles: frozenset[str] = frozenset()
    tenant_ids: frozenset[str] = frozenset()
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def matches(self, action: PolicyAction, resource: str) -> bool:
        resource_matches = self.resource == "*" or self.resource == resource
        return self.action == action and resource_matches


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    effect: PolicyEffect
    reason: str = ""
    matched_rule_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def allow(cls, reason: str = "allowed") -> "PolicyDecision":
        return cls(allowed=True, effect=PolicyEffect.ALLOW, reason=reason)

    @classmethod
    def deny(
        cls,
        reason: str,
        matched_rule_ids: tuple[str, ...] = (),
    ) -> "PolicyDecision":
        return cls(
            allowed=False,
            effect=PolicyEffect.DENY,
            reason=reason,
            matched_rule_ids=matched_rule_ids,
        )
