# -*- coding: utf-8 -*-
"""沙箱 Gateway MCP client factory。"""

from typing import Any


def create_sandbox_mcp_client(
    ctx: Any,
    config: Any,
) -> Any:
    """创建指向 sandbox gateway 的 HttpStatefulClient。

    使用项目内 HttpStatefulClient 包装 gateway_url，
    确保 toolkit.register_mcp_client() 可正常调用 list_tools()。
    tenant_id/agent_id/session_id 通过 headers 传递给 gateway，
    同时记录在 _qwenpaw_rebuild_info 中供后续重建使用。
    """
    from qwenpaw.app.mcp import HttpStatefulClient

    name = f"sandbox-{ctx.tenant_id or 'default'}"
    headers = {
        "X-Tenant-Id": ctx.tenant_id,
        "X-Agent-Id": ctx.agent_id,
        "X-Session-Id": ctx.session_id,
    }
    rebuild_info = {
        "transport": "streamable_http",
        "name": name,
        "url": config.gateway_url,
        "headers": headers,
        "contract": "qwenpaw.sandbox_runtime.v1",
    }

    client = HttpStatefulClient(
        name=name,
        transport="streamable_http",
        url=config.gateway_url,
        headers=headers,
    )
    setattr(client, "_qwenpaw_rebuild_info", rebuild_info)
    return client
