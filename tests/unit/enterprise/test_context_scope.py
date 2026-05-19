import pytest

from qwenpaw.enterprise.context import (
    RequestContext,
    get_current_request_context,
    get_current_tool_policy_patch,
)
from qwenpaw.enterprise.context_scope import enterprise_context_scope
from qwenpaw.enterprise.interfaces import ToolPolicyPatch


def test_enterprise_context_scope_sets_and_clears_values():
    ctx = RequestContext(request_id="r1", trace_id="t1", tenant_id="wx_acme")
    patch = ToolPolicyPatch(deny_tools=frozenset({"execute_shell_command"}))

    assert get_current_request_context() is None
    assert get_current_tool_policy_patch() is None

    with enterprise_context_scope(ctx, patch):
        assert get_current_request_context() is ctx
        assert get_current_tool_policy_patch() is patch

    assert get_current_request_context() is None
    assert get_current_tool_policy_patch() is None


def test_enterprise_context_scope_clears_after_exception():
    ctx = RequestContext(request_id="r2", trace_id="t2")

    with pytest.raises(RuntimeError, match="boom"):
        with enterprise_context_scope(ctx, None):
            raise RuntimeError("boom")

    assert get_current_request_context() is None
    assert get_current_tool_policy_patch() is None
