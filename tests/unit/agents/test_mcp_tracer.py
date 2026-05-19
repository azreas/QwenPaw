# -*- coding: utf-8 -*-
"""MCP tool 追踪中间件测试。"""
from unittest.mock import MagicMock

import pytest
from agentscope.message import TextBlock
from agentscope.tool import ToolResponse

from qwenpaw.agents.mcp_tracer import McpToolTrace, create_mcp_tracing_middleware


def _make_registered_tool(mcp_name=None):
    """构造一个模拟的 RegisteredToolFunction。"""
    tool = MagicMock()
    tool.mcp_name = mcp_name
    tool.preset_kwargs = {}
    return tool


def _make_toolkit(tools=None):
    """构造一个模拟的 Toolkit。"""
    toolkit = MagicMock()
    toolkit.tools = tools or {}
    return toolkit


def _make_agent():
    """构造一个模拟的 Agent，带 _mcp_tool_traces 列表。"""
    agent = MagicMock()
    agent._mcp_tool_traces = []
    return agent


async def _collect(gen):
    """收集 async generator 的所有输出。"""
    result = []
    async for chunk in gen:
        result.append(chunk)
    return result


@pytest.mark.asyncio
async def test_mcp_tool_success_trace():
    """MCP tool 调用成功时记录追踪。"""
    mcp_tool = _make_registered_tool(mcp_name="my_mcp_server")
    toolkit = _make_toolkit({"search_data": mcp_tool})
    agent = _make_agent()

    middleware = create_mcp_tracing_middleware(toolkit, agent)

    # next_handler 返回 awaitable(async generator)
    async def next_handler(**kwargs):
        async def _gen():
            yield "result_chunk"

        return _gen()

    tool_call = {"name": "search_data", "input": {"query": "test"}}
    # middleware 是 async generator，直接调用返回 async generator
    gen = middleware({"tool_call": tool_call}, next_handler)
    await _collect(gen)

    assert len(agent._mcp_tool_traces) == 1
    trace = agent._mcp_tool_traces[0]
    assert isinstance(trace, McpToolTrace)
    assert trace.tool_name == "search_data"
    assert trace.mcp_name == "my_mcp_server"
    assert trace.status == "success"
    assert trace.duration_ms >= 0
    assert trace.error_reason == ""


@pytest.mark.asyncio
async def test_mcp_tool_failure_trace():
    """MCP tool 调用失败时记录追踪，且异常继续传播。"""
    mcp_tool = _make_registered_tool(mcp_name="my_mcp_server")
    toolkit = _make_toolkit({"broken_tool": mcp_tool})
    agent = _make_agent()

    middleware = create_mcp_tracing_middleware(toolkit, agent)

    async def next_handler(**kwargs):
        async def _gen():
            raise ConnectionError("MCP server unreachable")
            yield  # 使其成为 generator

        return _gen()

    tool_call = {"name": "broken_tool", "input": {}}
    gen = middleware({"tool_call": tool_call}, next_handler)
    with pytest.raises(ConnectionError, match="MCP server unreachable"):
        await _collect(gen)

    assert len(agent._mcp_tool_traces) == 1
    trace = agent._mcp_tool_traces[0]
    assert trace.tool_name == "broken_tool"
    assert trace.status == "failure"
    assert "MCP server unreachable" in trace.error_reason


@pytest.mark.asyncio
async def test_mcp_tool_error_response_marked_failure():
    """Toolkit 将异常包装成 ToolResponse 时，也应记录为失败。"""
    mcp_tool = _make_registered_tool(mcp_name="my_mcp_server")
    toolkit = _make_toolkit({"broken_tool": mcp_tool})
    agent = _make_agent()

    middleware = create_mcp_tracing_middleware(toolkit, agent)

    async def next_handler(**kwargs):
        async def _gen():
            yield ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="Error occurred when calling MCP tool: timeout",
                    ),
                ],
            )

        return _gen()

    tool_call = {"name": "broken_tool", "input": {}}
    gen = middleware({"tool_call": tool_call}, next_handler)
    await _collect(gen)

    assert len(agent._mcp_tool_traces) == 1
    trace = agent._mcp_tool_traces[0]
    assert trace.status == "failure"
    assert "timeout" in trace.error_reason


@pytest.mark.asyncio
async def test_non_mcp_tool_no_trace():
    """非 MCP tool（builtin tool）调用时不记录追踪。"""
    builtin_tool = _make_registered_tool(mcp_name=None)
    toolkit = _make_toolkit({"read_file": builtin_tool})
    agent = _make_agent()

    middleware = create_mcp_tracing_middleware(toolkit, agent)

    async def next_handler(**kwargs):
        async def _gen():
            yield "file_content"

        return _gen()

    tool_call = {"name": "read_file", "input": {"path": "/tmp/test"}}
    gen = middleware({"tool_call": tool_call}, next_handler)
    result = await _collect(gen)

    assert result == ["file_content"]
    assert len(agent._mcp_tool_traces) == 0


@pytest.mark.asyncio
async def test_unknown_tool_no_trace():
    """未注册的 tool 不记录追踪。"""
    toolkit = _make_toolkit({})
    agent = _make_agent()

    middleware = create_mcp_tracing_middleware(toolkit, agent)

    async def next_handler(**kwargs):
        async def _gen():
            yield "result"

        return _gen()

    tool_call = {"name": "unknown_tool", "input": {}}
    gen = middleware({"tool_call": tool_call}, next_handler)
    await _collect(gen)

    assert len(agent._mcp_tool_traces) == 0


@pytest.mark.asyncio
async def test_multiple_mcp_calls_separate_traces():
    """多次 MCP tool 调用分别记录独立追踪。"""
    mcp_tool = _make_registered_tool(mcp_name="data_service")
    toolkit = _make_toolkit({"query_a": mcp_tool, "query_b": mcp_tool})
    agent = _make_agent()

    middleware = create_mcp_tracing_middleware(toolkit, agent)

    async def next_handler(**kwargs):
        async def _gen():
            yield "ok"

        return _gen()

    # 调用 query_a
    gen_a = middleware({"tool_call": {"name": "query_a", "input": {}}}, next_handler)
    await _collect(gen_a)

    # 调用 query_b
    gen_b = middleware({"tool_call": {"name": "query_b", "input": {}}}, next_handler)
    await _collect(gen_b)

    assert len(agent._mcp_tool_traces) == 2
    assert agent._mcp_tool_traces[0].tool_name == "query_a"
    assert agent._mcp_tool_traces[1].tool_name == "query_b"
