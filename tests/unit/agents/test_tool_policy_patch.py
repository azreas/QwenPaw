# -*- coding: utf-8 -*-
"""测试 QwenPawAgent 运行时工具策略（ToolPolicyPatch）应用。"""

from __future__ import annotations

import pytest

from qwenpaw.enterprise.interfaces import ToolPolicyPatch


# ------------------------------------------------------------------
# _is_tool_enabled_by_runtime_policy 静态方法
# ------------------------------------------------------------------


def test_is_tool_enabled_by_runtime_policy_disabled():
    """disable_tools 中的工具应被禁用。"""
    from qwenpaw.agents.react_agent import QwenPawAgent

    patch = ToolPolicyPatch(
        disable_tools=frozenset(
            {"execute_shell_command", "browser_use"}
        )
    )
    assert (
        QwenPawAgent._is_tool_enabled_by_runtime_policy(
            "execute_shell_command", patch
        )
        is False
    )
    assert (
        QwenPawAgent._is_tool_enabled_by_runtime_policy(
            "browser_use", patch
        )
        is False
    )


def test_is_tool_enabled_by_runtime_policy_allowed():
    """不在 disable_tools 中的工具应被允许。"""
    from qwenpaw.agents.react_agent import QwenPawAgent

    patch = ToolPolicyPatch(
        disable_tools=frozenset({"execute_shell_command"})
    )
    assert (
        QwenPawAgent._is_tool_enabled_by_runtime_policy(
            "read_file", patch
        )
        is True
    )


def test_is_tool_enabled_by_runtime_policy_none_patch():
    """patch 为 None 时所有工具应被允许。"""
    from qwenpaw.agents.react_agent import QwenPawAgent

    assert (
        QwenPawAgent._is_tool_enabled_by_runtime_policy(
            "execute_shell_command", None
        )
        is True
    )


# ------------------------------------------------------------------
# tool_policy_patch ContextVar
# ------------------------------------------------------------------


def test_tool_policy_patch_context_var():
    """ContextVar 设置和读取应正确。"""
    from qwenpaw.enterprise.context import (
        get_current_tool_policy_patch,
        set_current_tool_policy_patch,
    )

    assert get_current_tool_policy_patch() is None

    patch = ToolPolicyPatch(deny_tools=frozenset({"shell"}))
    token = set_current_tool_policy_patch(patch)
    assert get_current_tool_policy_patch() is patch

    # 清理
    set_current_tool_policy_patch(None)
    assert get_current_tool_policy_patch() is None


def test_tool_policy_patch_context_var_reset():
    """ContextVar reset 应恢复先前值。"""
    from qwenpaw.enterprise.context import (
        get_current_tool_policy_patch,
        set_current_tool_policy_patch,
    )

    assert get_current_tool_policy_patch() is None

    patch1 = ToolPolicyPatch(deny_tools=frozenset({"a"}))
    token1 = set_current_tool_policy_patch(patch1)

    patch2 = ToolPolicyPatch(deny_tools=frozenset({"b"}))
    token2 = set_current_tool_policy_patch(patch2)
    assert get_current_tool_policy_patch() is patch2

    # reset token2 恢复 patch1
    from qwenpaw.enterprise.context import (
        _current_tool_policy_patch,
    )

    _current_tool_policy_patch.reset(token2)
    assert get_current_tool_policy_patch() is patch1

    # reset token1 恢复 None
    _current_tool_policy_patch.reset(token1)
    assert get_current_tool_policy_patch() is None


def test_enterprise_context_scope_with_tool_policy_patch():
    from qwenpaw.enterprise.context import RequestContext
    from qwenpaw.enterprise.context_scope import enterprise_context_scope
    from qwenpaw.enterprise.context import get_current_tool_policy_patch
    from qwenpaw.enterprise.interfaces import ToolPolicyPatch

    patch = ToolPolicyPatch(deny_tools=frozenset({"execute_shell_command"}))
    with enterprise_context_scope(RequestContext("r", "t"), patch):
        assert get_current_tool_policy_patch() is patch
