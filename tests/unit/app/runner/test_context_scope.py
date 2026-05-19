from qwenpaw.enterprise.context import (
    RequestContext,
    get_current_request_context,
    get_current_tool_policy_patch,
)
from qwenpaw.enterprise.context_scope import enterprise_context_scope
from qwenpaw.enterprise.interfaces import ToolPolicyPatch


def test_runner_scope_pattern_exposes_context_and_policy():
    ctx = RequestContext(
        request_id="req",
        trace_id="trace",
        tenant_id="wx_acme",
        agent_id="wx_acme",
        session_id="s1",
    )
    patch = ToolPolicyPatch(deny_tools=frozenset({"browser_use"}))

    with enterprise_context_scope(ctx, patch):
        assert get_current_request_context().tenant_id == "wx_acme"
        assert "browser_use" in get_current_tool_policy_patch().deny_tools
