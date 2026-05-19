"""测试 RuntimeExtensionResolver 合并和异常隔离。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from qwenpaw.enterprise.context import RequestContext
from qwenpaw.enterprise.extensions import RuntimeExtensionResolver
from qwenpaw.enterprise.interfaces import (
    RuntimeExtensionBundle,
    ToolPolicyPatch,
)


def _make_ctx() -> RequestContext:
    return RequestContext(request_id="r1", trace_id="t1")


@dataclass
class StubProvider:
    """用于测试的 provider stub。"""

    provider_id: str
    bundle: RuntimeExtensionBundle = field(
        default_factory=RuntimeExtensionBundle
    )
    should_fail: bool = False

    async def resolve(self, ctx: RequestContext) -> RuntimeExtensionBundle:
        if self.should_fail:
            raise RuntimeError(f"provider {self.provider_id} failed")
        return self.bundle


class TestResolverMergesProviderResults:
    """单个和多个 provider 的合并行为。"""

    @pytest.mark.asyncio
    async def test_single_provider(self) -> None:
        provider = StubProvider(
            provider_id="p1",
            bundle=RuntimeExtensionBundle(
                mcp_clients=["mcp_a"],
                tool_policy=ToolPolicyPatch(
                    disable_tools=frozenset({"shell"}),
                ),
            ),
        )
        resolver = RuntimeExtensionResolver()
        resolver.register_provider(provider)
        result = await resolver.resolve(_make_ctx())
        assert result.mcp_clients == ["mcp_a"]
        assert result.tool_policy.disable_tools == frozenset({"shell"})

    @pytest.mark.asyncio
    async def test_multiple_providers(self) -> None:
        p1 = StubProvider(
            provider_id="p1",
            bundle=RuntimeExtensionBundle(
                mcp_clients=["mcp_a"],
                tool_policy=ToolPolicyPatch(
                    deny_tools=frozenset({"drop_db"}),
                ),
            ),
        )
        p2 = StubProvider(
            provider_id="p2",
            bundle=RuntimeExtensionBundle(
                mcp_clients=["mcp_b"],
                tool_policy=ToolPolicyPatch(
                    deny_tools=frozenset({"rm_rf"}),
                ),
            ),
        )
        resolver = RuntimeExtensionResolver()
        resolver.register_provider(p1)
        resolver.register_provider(p2)
        result = await resolver.resolve(_make_ctx())
        assert result.mcp_clients == ["mcp_a", "mcp_b"]
        assert result.tool_policy.deny_tools == frozenset(
            {"drop_db", "rm_rf"}
        )


class TestResolverDeduplicatesByProviderId:
    """同一 provider_id 重复注册去重，保留最后一次。"""

    @pytest.mark.asyncio
    async def test_duplicate_provider_id(self) -> None:
        p1 = StubProvider(
            provider_id="p1",
            bundle=RuntimeExtensionBundle(
                mcp_clients=["old"],
            ),
        )
        p2 = StubProvider(
            provider_id="p1",
            bundle=RuntimeExtensionBundle(
                mcp_clients=["new"],
            ),
        )
        resolver = RuntimeExtensionResolver()
        resolver.register_provider(p1)
        resolver.register_provider(p2)
        result = await resolver.resolve(_make_ctx())
        # 去重：同一 provider_id 只出现一次，使用最后注册的
        assert result.mcp_clients == ["new"]

    @pytest.mark.asyncio
    async def test_order_preserved_after_dedup(self) -> None:
        """去重后仍保持注册顺序。"""
        pa = StubProvider(provider_id="a")
        pb = StubProvider(provider_id="b")
        pa2 = StubProvider(
            provider_id="a",
            bundle=RuntimeExtensionBundle(
                mcp_clients=["a_v2"],
            ),
        )
        resolver = RuntimeExtensionResolver()
        resolver.register_provider(pa)
        resolver.register_provider(pb)
        resolver.register_provider(pa2)  # 覆盖 a
        # 顺序应该是 a, b（a 在前），但 a 用 pa2 的值
        assert list(resolver._providers.keys()) == ["a", "b"]
        assert resolver._order == ["a", "b"]


class TestResolverSingleFailureDoesntBlockOthers:
    """单个 provider 异常不阻断其他 provider。"""

    @pytest.mark.asyncio
    async def test_failing_provider_skipped(self) -> None:
        p_ok = StubProvider(
            provider_id="ok",
            bundle=RuntimeExtensionBundle(
                mcp_clients=["mcp_ok"],
                tool_policy=ToolPolicyPatch(
                    allow_tools=frozenset({"read"}),
                ),
            ),
        )
        p_bad = StubProvider(
            provider_id="bad",
            should_fail=True,
        )
        resolver = RuntimeExtensionResolver()
        resolver.register_provider(p_ok)
        resolver.register_provider(p_bad)
        result = await resolver.resolve(_make_ctx())
        assert result.mcp_clients == ["mcp_ok"]
        assert result.tool_policy.allow_tools == frozenset({"read"})


class TestResolverEmptyReturnsEmptyBundle:
    """无 provider 返回空 bundle。"""

    @pytest.mark.asyncio
    async def test_no_providers(self) -> None:
        resolver = RuntimeExtensionResolver()
        result = await resolver.resolve(_make_ctx())
        assert result.mcp_clients == []
        assert result.tool_policy == ToolPolicyPatch()


class CaptureBus:
    def __init__(self):
        self.events = []

    async def emit(self, event):
        self.events.append(event)


class TestRunnerRuntimeExtensionTrace:
    @pytest.mark.asyncio
    async def test_resolve_runtime_extensions_emits_success_trace(self) -> None:
        from qwenpaw.app.runner.runner import _resolve_runtime_extensions

        provider = StubProvider(
            provider_id="p1",
            bundle=RuntimeExtensionBundle(metadata={"provider": "p1"}),
        )
        resolver = RuntimeExtensionResolver()
        resolver.register_provider(provider)
        bus = CaptureBus()
        runtime = type(
            "Runtime",
            (),
            {"extensions": resolver, "audit": bus},
        )()

        result = await _resolve_runtime_extensions(runtime, _make_ctx())

        assert result.metadata == {"provider": "p1"}
        assert len(bus.events) == 1
        event = bus.events[0]
        assert event.payload["call_type"] == "runtime_extension"
        assert event.payload["call_name"] == "runtime_extension.resolve"
        assert event.payload["status"] == "success"
