from qwenpaw.enterprise.policy.models import (
    PolicyAction,
    PolicyDecision,
    PolicyEffect,
    PolicyRule,
)


def test_policy_rule_matches_action_and_resource():
    rule = PolicyRule(
        rule_id="deny-shell",
        effect=PolicyEffect.DENY,
        action=PolicyAction.TOOL_CALL,
        resource="execute_shell_command",
    )

    assert rule.matches(PolicyAction.TOOL_CALL, "execute_shell_command")
    assert not rule.matches(PolicyAction.MCP_CALL, "execute_shell_command")


def test_policy_decision_denied_helper():
    decision = PolicyDecision.deny(
        reason="blocked",
        matched_rule_ids=("deny-shell",),
    )

    assert decision.allowed is False
    assert decision.effect is PolicyEffect.DENY
    assert decision.reason == "blocked"
    assert decision.matched_rule_ids == ("deny-shell",)
