import pytest

from qwenpaw.enterprise.context import RequestContext
from qwenpaw.enterprise.policy.models import PolicyAction, PolicyEffect, PolicyRule
from qwenpaw.enterprise.policy.service import PolicyService


@pytest.mark.asyncio
async def test_policy_service_returns_audit_payload():
    service = PolicyService(
        rules=[
            PolicyRule(
                rule_id="deny-export",
                effect=PolicyEffect.DENY,
                action=PolicyAction.DATA_EXPORT,
                resource="csv",
                reason="blocked",
            )
        ]
    )

    decision = await service.evaluate(RequestContext("r", "t"), PolicyAction.DATA_EXPORT, "csv")

    assert decision.metadata["policy_action"] == "data.export"
    assert decision.metadata["resource"] == "csv"
