from qwenpaw.agents.tool_guard_mixin import _create_quota_guard_result


def test_quota_guard_result_is_auto_deny_result():
    result = _create_quota_guard_result(
        "execute_shell_command",
        {"command": "pwd"},
        reason="quota exceeded",
    )

    assert result.is_safe is False
    assert result.findings[0].rule_id == "quota_policy_deny"
    assert result.findings[0].tool_name == "execute_shell_command"
