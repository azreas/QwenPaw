"""测试 ToolPolicyPatch.merge() 和 effective_allowed()。"""

from __future__ import annotations

from qwenpaw.enterprise.interfaces import ToolPolicyPatch


class TestToolPolicyPatchMerge:
    """merge() 合并 disable 和 deny。"""

    def test_merge_disable_and_deny(self) -> None:
        a = ToolPolicyPatch(
            disable_tools=frozenset({"shell"}),
            deny_tools=frozenset({"drop_db"}),
        )
        b = ToolPolicyPatch(
            disable_tools=frozenset({"browser"}),
            deny_tools=frozenset({"rm_rf"}),
        )
        result = a.merge(b)
        assert result.disable_tools == frozenset({"shell", "browser"})
        assert result.deny_tools == frozenset({"drop_db", "rm_rf"})

    def test_merge_allow(self) -> None:
        a = ToolPolicyPatch(allow_tools=frozenset({"read"}))
        b = ToolPolicyPatch(allow_tools=frozenset({"write"}))
        result = a.merge(b)
        assert result.allow_tools == frozenset({"read", "write"})

    def test_deny_overrides_allow(self) -> None:
        """deny 优先于 allow：allow 了 shell 但 deny 了 shell。"""
        a = ToolPolicyPatch(allow_tools=frozenset({"shell"}))
        b = ToolPolicyPatch(deny_tools=frozenset({"shell"}))
        result = a.merge(b)
        assert result.allow_tools == frozenset({"shell"})
        assert result.deny_tools == frozenset({"shell"})
        # effective_allowed 会处理优先级
        effective = result.effective_allowed({"shell", "read"})
        assert "shell" not in effective

    def test_merge_empty(self) -> None:
        """与空 patch 合并不改变原 patch。"""
        a = ToolPolicyPatch(
            disable_tools=frozenset({"shell"}),
            allow_tools=frozenset({"read"}),
            deny_tools=frozenset({"drop_db"}),
        )
        empty = ToolPolicyPatch()
        result = a.merge(empty)
        assert result == a

    def test_merge_symmetric(self) -> None:
        """合并结果与顺序无关。"""
        a = ToolPolicyPatch(disable_tools=frozenset({"a"}))
        b = ToolPolicyPatch(disable_tools=frozenset({"b"}))
        assert a.merge(b) == b.merge(a)


class TestEffectiveAllowed:
    """effective_allowed() 计算实际允许的工具集。"""

    def test_effective_allowed_basic(self) -> None:
        """先从 allow 开始，减去 disable 和 deny。"""
        patch = ToolPolicyPatch(
            disable_tools=frozenset({"shell"}),
            deny_tools=frozenset({"drop_db"}),
        )
        all_tools = {"shell", "browser", "drop_db", "read"}
        result = patch.effective_allowed(all_tools)
        assert result == {"browser", "read"}

    def test_effective_allowed_with_allow_list(self) -> None:
        """allow_tools 非空时，从 allow_tools 开始而不是 all_tools。"""
        patch = ToolPolicyPatch(
            allow_tools=frozenset({"read", "write"}),
            deny_tools=frozenset({"write"}),
        )
        all_tools = {"read", "write", "shell"}
        result = patch.effective_allowed(all_tools)
        # 从 allow 开始：{read, write}，减去 deny：{write}
        assert result == {"read"}

    def test_effective_allowed_deny_priority(self) -> None:
        """deny 优先级最高，即使 allow 和 deny 有交集。"""
        patch = ToolPolicyPatch(
            allow_tools=frozenset({"shell"}),
            deny_tools=frozenset({"shell"}),
        )
        result = patch.effective_allowed({"shell", "read"})
        assert "shell" not in result

    def test_effective_allowed_empty_patch(self) -> None:
        """空 patch 返回 all_tools 本身。"""
        patch = ToolPolicyPatch()
        all_tools = {"shell", "browser", "read"}
        result = patch.effective_allowed(all_tools)
        assert result == all_tools

    def test_effective_allowed_deny_overrides_disable(self) -> None:
        """disable 和 deny 都移除工具，deny 是最终屏障。"""
        patch = ToolPolicyPatch(
            disable_tools=frozenset({"shell"}),
            deny_tools=frozenset({"browser"}),
        )
        all_tools = {"shell", "browser", "read"}
        result = patch.effective_allowed(all_tools)
        assert result == {"read"}
