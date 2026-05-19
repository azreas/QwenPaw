# -*- coding: utf-8 -*-
"""MCP tool 调用追踪中间件。

注册到 Toolkit 的 onion-style middleware 链中，
在每次 MCP tool 实际调用时记录 tool name、耗时、成功/失败，
写入 agent._mcp_tool_traces 供 runner 读取后发送审计事件。
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Callable

logger = logging.getLogger(__name__)


@dataclass
class McpToolTrace:
    """单次 MCP tool 调用追踪记录。"""

    tool_name: str
    mcp_name: str
    duration_ms: float = 0.0
    status: str = "success"
    error_reason: str = ""


@dataclass
class BuiltinToolTrace:
    """单次非 MCP built-in tool 调用追踪记录。"""

    tool_name: str
    duration_ms: float = 0.0
    status: str = "success"
    error_reason: str = ""


def _text_from_block(block: Any) -> str:
    if isinstance(block, dict):
        return str(block.get("text") or "")
    return str(getattr(block, "text", "") or "")


def _extract_tool_error(response: Any) -> str:
    """Extract standard Toolkit error text from a ToolResponse chunk."""
    for block in getattr(response, "content", []) or []:
        text = _text_from_block(block).strip()
        if (
            text.startswith("Error occurred when calling MCP tool:")
            or text.startswith("Error:")
            or text.startswith("FunctionNotFoundError:")
            or text.startswith("FunctionInactiveError:")
        ):
            return text[:200]
    return ""


def create_mcp_tracing_middleware(
    toolkit: Any,
    agent: Any,
) -> Callable[
    [dict, Callable],
    AsyncGenerator[Any, None],
]:
    """创建 MCP tool 追踪中间件并注册到 toolkit。

    Args:
        toolkit: Agent Toolkit 实例，用于查询 tool 是否为 MCP tool
        agent: QwenPawAgent 实例，trace 记录写入 agent._mcp_tool_traces
    """

    async def mcp_tracing_middleware(
        kwargs: dict,
        next_handler: Callable,
    ) -> AsyncGenerator[Any, None]:
        tool_call = kwargs.get("tool_call", {})
        tool_name = tool_call.get("name", "")

        # 查询是否为 MCP tool
        registered_tool = toolkit.tools.get(tool_name) if toolkit else None
        is_mcp = (
            registered_tool is not None
            and getattr(registered_tool, "mcp_name", None) is not None
        )

        if not is_mcp:
            # 非 MCP tool，直接放行
            async for chunk in await next_handler(**kwargs):
                yield chunk
            return

        mcp_name = registered_tool.mcp_name
        start = time.monotonic()
        trace = McpToolTrace(
            tool_name=tool_name,
            mcp_name=mcp_name,
        )

        try:
            async for chunk in await next_handler(**kwargs):
                if not trace.error_reason:
                    trace.error_reason = _extract_tool_error(chunk)
                yield chunk
            trace.duration_ms = (time.monotonic() - start) * 1000
            trace.status = "failure" if trace.error_reason else "success"
        except Exception as e:
            trace.duration_ms = (time.monotonic() - start) * 1000
            trace.status = "failure"
            trace.error_reason = str(e)[:200]
            raise
        finally:
            # 追加到 agent 的追踪列表
            _traces = getattr(agent, "_mcp_tool_traces", None)
            if _traces is not None and isinstance(_traces, list):
                _traces.append(trace)

    return mcp_tracing_middleware


def create_builtin_tool_tracing_middleware(
    toolkit: Any,
    agent: Any,
) -> Callable[
    [dict, Callable],
    AsyncGenerator[Any, None],
]:
    """创建非 MCP tool 追踪中间件，记录安全摘要级别的调用状态。"""

    async def builtin_tool_tracing_middleware(
        kwargs: dict,
        next_handler: Callable,
    ) -> AsyncGenerator[Any, None]:
        tool_call = kwargs.get("tool_call", {})
        tool_name = str(tool_call.get("name") or "")
        registered_tool = toolkit.tools.get(tool_name) if toolkit else None
        is_mcp = (
            registered_tool is not None
            and getattr(registered_tool, "mcp_name", None) is not None
        )

        if not registered_tool or is_mcp:
            async for chunk in await next_handler(**kwargs):
                yield chunk
            return

        start = time.monotonic()
        trace = BuiltinToolTrace(tool_name=tool_name)
        try:
            async for chunk in await next_handler(**kwargs):
                if not trace.error_reason:
                    trace.error_reason = _extract_tool_error(chunk)
                yield chunk
            trace.duration_ms = (time.monotonic() - start) * 1000
            trace.status = "failure" if trace.error_reason else "success"
        except Exception as e:
            trace.duration_ms = (time.monotonic() - start) * 1000
            trace.status = "failure"
            trace.error_reason = str(e)[:200]
            raise
        finally:
            traces = getattr(agent, "_builtin_tool_traces", None)
            if isinstance(traces, list):
                traces.append(trace)

    return builtin_tool_tracing_middleware
