from __future__ import annotations

from collections.abc import Sequence

from qwenpaw.enterprise.context import RequestContext

from .models import PolicyAction, PolicyDecision, PolicyEffect, PolicyRule


class PolicyService:
    """Evaluate request-scoped enterprise policy rules."""

    def __init__(self, rules: Sequence[PolicyRule] | None = None) -> None:
        self._rules: list[PolicyRule] = list(rules or [])

    def replace_rules(self, rules: Sequence[PolicyRule]) -> None:
        self._rules = list(rules)

    def add_rule(self, rule: PolicyRule) -> None:
        self._rules.append(rule)

    async def evaluate(
        self,
        ctx: RequestContext,
        action: PolicyAction,
        resource: str,
    ) -> PolicyDecision:
        matched = [
            rule
            for rule in self._rules
            if rule.matches(action, resource)
            and self._matches_roles(ctx, rule)
            and self._matches_tenant(ctx, rule)
        ]
        if not matched:
            return self._with_metadata(PolicyDecision.allow(), action, resource)

        deny = [rule for rule in matched if rule.effect is PolicyEffect.DENY]
        if deny:
            return self._with_metadata(
                PolicyDecision.deny(
                    reason=deny[0].reason or "denied by policy",
                    matched_rule_ids=tuple(rule.rule_id for rule in deny),
                ),
                action,
                resource,
            )

        require_approval = [
            rule for rule in matched if rule.effect is PolicyEffect.REQUIRE_APPROVAL
        ]
        if require_approval:
            return self._with_metadata(
                PolicyDecision(
                    allowed=False,
                    effect=PolicyEffect.REQUIRE_APPROVAL,
                    reason=require_approval[0].reason or "approval required",
                    matched_rule_ids=tuple(rule.rule_id for rule in require_approval),
                ),
                action,
                resource,
            )

        warn = [rule for rule in matched if rule.effect is PolicyEffect.WARN]
        if warn:
            return self._with_metadata(
                PolicyDecision(
                    allowed=True,
                    effect=PolicyEffect.WARN,
                    reason=warn[0].reason or "allowed with warning",
                    matched_rule_ids=tuple(rule.rule_id for rule in warn),
                ),
                action,
                resource,
            )

        return self._with_metadata(PolicyDecision.allow(), action, resource)

    def _with_metadata(
        self,
        decision: PolicyDecision,
        action: PolicyAction,
        resource: str,
    ) -> PolicyDecision:
        return PolicyDecision(
            allowed=decision.allowed,
            effect=decision.effect,
            reason=decision.reason,
            matched_rule_ids=decision.matched_rule_ids,
            metadata={
                **decision.metadata,
                "policy_action": action.value,
                "resource": resource,
            },
        )

    @staticmethod
    def _matches_roles(ctx: RequestContext, rule: PolicyRule) -> bool:
        if not rule.roles:
            return True
        return bool(set(ctx.roles) & set(rule.roles))

    @staticmethod
    def _matches_tenant(ctx: RequestContext, rule: PolicyRule) -> bool:
        if not rule.tenant_ids:
            return True
        return ctx.tenant_id in rule.tenant_ids
