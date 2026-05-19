import pytest

from qwenpaw.enterprise.context import RequestContext
from qwenpaw.enterprise.policy.models import PolicyAction, PolicyEffect, PolicyRule
from qwenpaw.enterprise.policy.service import PolicyService


@pytest.mark.asyncio
async def test_policy_service_denies_matching_rule():
    service = PolicyService(
        rules=[
            PolicyRule(
                rule_id="deny-shell",
                effect=PolicyEffect.DENY,
                action=PolicyAction.TOOL_CALL,
                resource="execute_shell_command",
                reason="shell disabled",
            )
        ]
    )

    decision = await service.evaluate(
        RequestContext(request_id="r", trace_id="t", tenant_id="wx_acme"),
        PolicyAction.TOOL_CALL,
        "execute_shell_command",
    )

    assert decision.allowed is False
    assert decision.reason == "shell disabled"
    assert decision.matched_rule_ids == ("deny-shell",)


@pytest.mark.asyncio
async def test_policy_service_skips_role_mismatch():
    service = PolicyService(
        rules=[
            PolicyRule(
                rule_id="admin-only",
                effect=PolicyEffect.DENY,
                action=PolicyAction.FILE_WRITE,
                resource="agent.json",
                roles=frozenset({"tenant_readonly"}),
            )
        ]
    )

    decision = await service.evaluate(
        RequestContext(
            request_id="r",
            trace_id="t",
            roles=("tenant_member",),
        ),
        PolicyAction.FILE_WRITE,
        "agent.json",
    )

    assert decision.allowed is True
