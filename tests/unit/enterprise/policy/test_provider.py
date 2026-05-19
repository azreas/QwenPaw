import pytest

from qwenpaw.enterprise.context import RequestContext
from qwenpaw.enterprise.policy.models import PolicyAction, PolicyEffect, PolicyRule
from qwenpaw.enterprise.policy.provider import PolicyRuntimeExtensionProvider
from qwenpaw.enterprise.policy.service import PolicyService


@pytest.mark.asyncio
async def test_policy_provider_turns_tool_denies_into_patch():
    service = PolicyService(
        rules=[
            PolicyRule(
                rule_id="deny-shell",
                effect=PolicyEffect.DENY,
                action=PolicyAction.TOOL_CALL,
                resource="execute_shell_command",
            )
        ]
    )
    provider = PolicyRuntimeExtensionProvider(
        service,
        tool_resources=("execute_shell_command", "browser_use"),
    )

    bundle = await provider.resolve(
        RequestContext(request_id="r", trace_id="t", tenant_id="wx_acme")
    )

    assert "execute_shell_command" in bundle.tool_policy.deny_tools
    assert "browser_use" not in bundle.tool_policy.deny_tools
    assert bundle.metadata["policy"]["denied_tools"] == ["execute_shell_command"]
