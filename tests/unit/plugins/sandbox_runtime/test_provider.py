# -*- coding: utf-8 -*-
"""测试 sandbox-runtime provider。"""

import pytest

from qwenpaw.enterprise.context import RequestContext
from qwenpaw.enterprise.interfaces import RuntimeExtensionBundle
from qwenpaw.plugins.sandbox_runtime.config import SandboxRuntimeConfig
from qwenpaw.plugins.sandbox_runtime.provider import (
    SandboxRuntimeExtensionProvider,
)


@pytest.mark.asyncio
async def test_sandbox_provider_disabled_returns_empty():
    """enabled=False 时应返回空 bundle。"""
    provider = SandboxRuntimeExtensionProvider(
        SandboxRuntimeConfig(enabled=False, gateway_url="http://gw"),
    )
    bundle = await provider.resolve(
        RequestContext(request_id="r", trace_id="t", tenant_id="wx_acme"),
    )
    assert bundle.mcp_clients == []
    assert bundle.tool_policy.disable_tools == frozenset()


@pytest.mark.asyncio
async def test_sandbox_provider_disables_local_dangerous_tools():
    """有 tenant_id 时应 disable 本机危险工具并提供 MCP client。"""
    provider = SandboxRuntimeExtensionProvider(
        SandboxRuntimeConfig(enabled=True, gateway_url="http://sandbox-gw"),
    )
    bundle = await provider.resolve(
        RequestContext(
            request_id="r",
            trace_id="t",
            tenant_id="wx_acme",
            agent_id="wx_acme",
            session_id="s1",
        ),
    )
    assert "execute_shell_command" in bundle.tool_policy.disable_tools
    assert "browser_use" in bundle.tool_policy.disable_tools
    assert bundle.mcp_clients


@pytest.mark.asyncio
async def test_sandbox_provider_no_tenant_local_mode():
    """无 tenant_id 且 tenant_mode_default=local 时返回空 bundle。"""
    provider = SandboxRuntimeExtensionProvider(
        SandboxRuntimeConfig(
            enabled=True,
            gateway_url="http://gw",
            tenant_mode_default="local",
        ),
    )
    bundle = await provider.resolve(
        RequestContext(request_id="r", trace_id="t"),
    )
    assert bundle.mcp_clients == []
    assert bundle.tool_policy.disable_tools == frozenset()


@pytest.mark.asyncio
async def test_sandbox_provider_no_tenant_sandbox_mode():
    """无 tenant_id 且 tenant_mode_default=sandbox 时不提供沙箱。"""
    provider = SandboxRuntimeExtensionProvider(
        SandboxRuntimeConfig(
            enabled=True,
            gateway_url="http://gw",
            tenant_mode_default="sandbox",
        ),
    )
    bundle = await provider.resolve(
        RequestContext(request_id="r", trace_id="t"),
    )
    # sandbox 模式下无 tenant 不提供沙箱（policy 也为空）
    assert bundle.tool_policy.disable_tools == frozenset()


@pytest.mark.asyncio
async def test_sandbox_provider_custom_disable_tools():
    """自定义 disable_local_tools 应生效。"""
    config = SandboxRuntimeConfig(
        enabled=True,
        gateway_url="http://gw",
        disable_local_tools=("shell", "browser", "file_write"),
    )
    provider = SandboxRuntimeExtensionProvider(config)
    bundle = await provider.resolve(
        RequestContext(
            request_id="r",
            trace_id="t",
            tenant_id="wx_test",
        ),
    )
    assert "shell" in bundle.tool_policy.disable_tools
    assert "browser" in bundle.tool_policy.disable_tools
    assert "file_write" in bundle.tool_policy.disable_tools


@pytest.mark.asyncio
async def test_sandbox_mcp_client_is_http_stateful():
    """MCP client 应为 HttpStatefulClient 实例。"""
    from qwenpaw.app.mcp import HttpStatefulClient

    provider = SandboxRuntimeExtensionProvider(
        SandboxRuntimeConfig(enabled=True, gateway_url="http://gw"),
    )
    bundle = await provider.resolve(
        RequestContext(
            request_id="r",
            trace_id="t",
            tenant_id="wx_acme",
            agent_id="wx_acme_agent",
            session_id="s1",
        ),
    )
    client = bundle.mcp_clients[0]
    assert isinstance(client, HttpStatefulClient)
    assert client.name == "sandbox-wx_acme"
    # rebuild_info 包含 tenant/agent/session
    info = getattr(client, "_qwenpaw_rebuild_info", {})
    assert info.get("headers", {}).get("X-Tenant-Id") == "wx_acme"
    assert info.get("url") == "http://gw"


@pytest.mark.asyncio
async def test_sandbox_provider_client_satisfies_metadata_contract():
    from qwenpaw.plugins.sandbox_runtime.contract import (
        assert_sandbox_client_contract,
    )

    provider = SandboxRuntimeExtensionProvider(
        SandboxRuntimeConfig(enabled=True, gateway_url="http://gw"),
    )
    bundle = await provider.resolve(
        RequestContext(
            request_id="r",
            trace_id="t",
            tenant_id="wx_acme",
            agent_id="wx_acme",
            session_id="s1",
        ),
    )

    contract = await assert_sandbox_client_contract(
        bundle.mcp_clients[0],
        expected_tenant_id="wx_acme",
        require_list_tools=False,
    )
    assert contract["headers"]["X-Agent-Id"] == "wx_acme"
