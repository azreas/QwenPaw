"""Sandbox Gateway MCP client contract checks."""

from __future__ import annotations

from inspect import isawaitable
from typing import Any


class SandboxContractError(RuntimeError):
    """Raised when a sandbox MCP client does not satisfy the contract."""


def get_sandbox_client_contract(client: Any) -> dict[str, Any]:
    info = getattr(client, "_qwenpaw_rebuild_info", None)
    if not isinstance(info, dict):
        raise SandboxContractError("missing _qwenpaw_rebuild_info")
    headers = info.get("headers")
    if not isinstance(headers, dict):
        raise SandboxContractError("missing headers")
    return {
        "transport": info.get("transport", ""),
        "name": info.get("name", ""),
        "url": info.get("url", ""),
        "headers": headers,
    }


async def _maybe_await(value: Any) -> Any:
    if isawaitable(value):
        return await value
    return value


async def assert_sandbox_client_contract(
    client: Any,
    *,
    expected_tenant_id: str = "",
    require_list_tools: bool = False,
) -> dict[str, Any]:
    contract = get_sandbox_client_contract(client)
    headers = contract["headers"]
    if expected_tenant_id and headers.get("X-Tenant-Id") != expected_tenant_id:
        raise SandboxContractError("X-Tenant-Id does not match request tenant")
    for header in ("X-Agent-Id", "X-Session-Id"):
        if header not in headers:
            raise SandboxContractError(f"missing {header}")

    tool_count = None
    if require_list_tools:
        list_tools = getattr(client, "list_tools", None)
        if not callable(list_tools):
            raise SandboxContractError("client has no callable list_tools()")
        tools = await _maybe_await(list_tools())
        if not tools:
            raise SandboxContractError("sandbox gateway returned no tools")
        tool_count = len(tools)

    return {**contract, "tool_count": tool_count}
