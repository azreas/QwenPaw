# -*- coding: utf-8 -*-
"""SandboxRuntimeExtensionProvider — 为租户请求提供沙箱 MCP client 和工具策略。"""

from __future__ import annotations

import logging
from typing import Any

from qwenpaw.enterprise.context import RequestContext
from qwenpaw.enterprise.interfaces import (
    RuntimeExtensionBundle,
    ToolPolicyPatch,
)
from .config import SandboxRuntimeConfig
from .gateway_client import create_sandbox_mcp_client

logger = logging.getLogger(__name__)


class SandboxRuntimeExtensionProvider:
    """沙箱运行时扩展 provider。

    规则：
    - enabled=False 返回空 bundle。
    - 无 tenant_id 且 tenant_mode_default="local" 时返回空 bundle。
    - 有 tenant_id 时返回 sandbox MCP client，并 disable 本机危险工具。
    - provider 不读取 self.agent_id；只使用 ctx.agent_id。
    """

    provider_id = "sandbox-runtime"

    def __init__(self, config: SandboxRuntimeConfig) -> None:
        self._config = config

    async def resolve(
        self, ctx: RequestContext
    ) -> RuntimeExtensionBundle:
        if not self._config.enabled:
            return RuntimeExtensionBundle()

        # 无 tenant_id 时，按 tenant_mode_default 决定
        if not ctx.tenant_id:
            if self._config.tenant_mode_default == "local":
                return RuntimeExtensionBundle()
            # sandbox 模式下无 tenant 也不提供沙箱
            return RuntimeExtensionBundle()

        # 有 tenant_id：提供沙箱 MCP client + disable 本机工具
        mcp_clients = []
        try:
            client = create_sandbox_mcp_client(
                ctx, self._config
            )
            mcp_clients.append(client)
        except Exception:
            logger.exception(
                "Failed to create sandbox MCP client for tenant %s",
                ctx.tenant_id,
            )

        tool_policy = ToolPolicyPatch(
            disable_tools=frozenset(self._config.disable_local_tools),
            deny_tools=frozenset(self._config.disable_local_tools),
        )

        return RuntimeExtensionBundle(
            mcp_clients=mcp_clients,
            tool_policy=tool_policy,
        )
