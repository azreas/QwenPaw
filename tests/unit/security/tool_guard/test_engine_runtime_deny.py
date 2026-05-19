# -*- coding: utf-8 -*-
"""测试 ToolGuardEngine.guard() 的 per-request runtime deny。"""

from qwenpaw.enterprise.context import (
    get_current_tool_policy_patch,
    set_current_tool_policy_patch,
)
from qwenpaw.enterprise.interfaces import ToolPolicyPatch
from qwenpaw.security.tool_guard.engine import ToolGuardEngine


def _make_engine() -> ToolGuardEngine:
    return ToolGuardEngine(guardians=[], enabled=True)


def test_runtime_deny_returns_unsafe_result():
    """deny_tools 中的工具应返回 is_safe=False 的结果。"""
    engine = _make_engine()
    patch = ToolPolicyPatch(
        deny_tools=frozenset({"execute_shell_command"})
    )
    set_current_tool_policy_patch(patch)
    try:
        result = engine.guard(
            "execute_shell_command", {"command": "ls"}
        )
        assert result is not None
        assert not result.is_safe
        assert any(
            f.rule_id == "runtime_policy_deny"
            for f in result.findings
        )
        assert "RuntimePolicy" in result.guardians_used
    finally:
        set_current_tool_policy_patch(None)


def test_runtime_deny_does_not_affect_other_tools():
    """不在 deny_tools 中的工具不受影响。"""
    engine = _make_engine()
    patch = ToolPolicyPatch(
        deny_tools=frozenset({"execute_shell_command"})
    )
    set_current_tool_policy_patch(patch)
    try:
        result = engine.guard("read_file", {"path": "/tmp/x"})
        # 无 guardians 且不在 deny 中 → result 无 findings
        assert result is not None
        assert result.is_safe
    finally:
        set_current_tool_policy_patch(None)


def test_runtime_deny_no_patch_returns_normal():
    """无 ToolPolicyPatch 时行为不变。"""
    set_current_tool_policy_patch(None)
    engine = _make_engine()
    result = engine.guard("read_file", {"path": "/tmp/x"})
    assert result is not None
    assert result.is_safe


def test_runtime_deny_does_not_pollute_global_denied():
    """per-request deny 不写入全局 _denied_tools。"""
    engine = _make_engine()
    patch = ToolPolicyPatch(
        deny_tools=frozenset({"execute_shell_command"})
    )
    set_current_tool_policy_patch(patch)
    try:
        engine.guard("execute_shell_command", {"command": "ls"})
        assert "execute_shell_command" not in engine.denied_tools
    finally:
        set_current_tool_policy_patch(None)
