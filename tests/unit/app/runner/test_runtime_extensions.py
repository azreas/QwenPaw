# -*- coding: utf-8 -*-
"""Runner 运行时扩展解析的单元测试。"""
import pytest

from qwenpaw.enterprise.context import RequestContext
from qwenpaw.enterprise.interfaces import (
    RuntimeExtensionBundle,
    ToolPolicyPatch,
)
from qwenpaw.app.runner.runner import _resolve_runtime_extensions


class StubResolver:
    """成功解析的 stub resolver。"""

    async def resolve(self, ctx: RequestContext):
        assert ctx.agent_id == "default"
        return RuntimeExtensionBundle(
            mcp_clients=["sandbox-client"],
            tool_policy=ToolPolicyPatch(
                disable_tools=frozenset({"execute_shell_command"}),
            ),
        )


class StubRuntime:
    extensions = StubResolver()


@pytest.mark.asyncio
async def test_resolver_receives_context_and_returns_bundle():
    """正常 resolver 应返回完整 bundle。"""
    bundle = await _resolve_runtime_extensions(
        StubRuntime(),
        RequestContext(
            request_id="r",
            trace_id="t",
            agent_id="default",
        ),
    )
    assert bundle.mcp_clients == ["sandbox-client"]
    assert "execute_shell_command" in bundle.tool_policy.disable_tools


@pytest.mark.asyncio
async def test_none_runtime_returns_empty_bundle():
    """runtime 为 None 时应返回空 bundle。"""
    bundle = await _resolve_runtime_extensions(
        None,
        RequestContext(request_id="r", trace_id="t"),
    )
    assert bundle.mcp_clients == []
    assert bundle.tool_policy == ToolPolicyPatch()


@pytest.mark.asyncio
async def test_resolver_failure_returns_empty_bundle():
    """resolver 抛异常时应返回空 bundle，不向上传播。"""

    class FailingResolver:
        async def resolve(self, ctx):
            raise RuntimeError("boom")

    class FailingRuntime:
        extensions = FailingResolver()

    bundle = await _resolve_runtime_extensions(
        FailingRuntime(),
        RequestContext(request_id="r", trace_id="t"),
    )
    assert bundle.mcp_clients == []
    assert bundle.tool_policy == ToolPolicyPatch()


@pytest.mark.asyncio
async def test_runtime_without_extensions_returns_empty():
    """runtime 没有 extensions 属性时应返回空 bundle。"""

    class NoExtensionsRuntime:
        pass

    bundle = await _resolve_runtime_extensions(
        NoExtensionsRuntime(),
        RequestContext(request_id="r", trace_id="t"),
    )
    assert bundle.mcp_clients == []


@pytest.mark.asyncio
async def test_runtime_with_none_extensions_returns_empty():
    """runtime.extensions 为 None 时应返回空 bundle。"""

    class NoneExtensionsRuntime:
        extensions = None

    bundle = await _resolve_runtime_extensions(
        NoneExtensionsRuntime(),
        RequestContext(request_id="r", trace_id="t"),
    )
    assert bundle.mcp_clients == []
    assert bundle.tool_policy == ToolPolicyPatch()


@pytest.mark.asyncio
async def test_runner_has_enterprise_runtime_attribute():
    """AgentRunner 应初始化 _enterprise_runtime 为 None。"""
    from qwenpaw.app.runner.runner import AgentRunner

    runner = AgentRunner(agent_id="test")
    assert runner._enterprise_runtime is None
