"""按注册顺序解析 runtime extension provider 并合并结果。"""

from __future__ import annotations

import logging
from typing import Any

from ..context import RequestContext
from ..interfaces import RuntimeExtensionBundle, ToolPolicyPatch

logger = logging.getLogger(__name__)


class RuntimeExtensionResolver:
    """按注册顺序解析 runtime extension provider 并合并结果。"""

    def __init__(self) -> None:
        self._providers: dict[str, Any] = {}
        self._order: list[str] = []

    def register_provider(self, provider: Any) -> None:
        """注册 provider，以 provider.provider_id 去重。"""
        pid = provider.provider_id
        if pid not in self._providers:
            self._order.append(pid)
        self._providers[pid] = provider

    async def resolve(self, ctx: RequestContext) -> RuntimeExtensionBundle:
        """按注册顺序调用所有 provider，单个异常只记录日志不阻断。"""
        merged_mcp_clients: list[Any] = []
        merged_policy = ToolPolicyPatch()
        merged_metadata: dict[str, Any] = {}

        for pid in self._order:
            provider = self._providers[pid]
            try:
                bundle = await provider.resolve(ctx)
                merged_mcp_clients.extend(bundle.mcp_clients)
                merged_policy = merged_policy.merge(bundle.tool_policy)
                # 浅合并 metadata，后注册的 provider 覆盖先注册的同 key
                merged_metadata.update(bundle.metadata)
            except Exception:
                logger.exception(
                    "Runtime extension provider %s failed", pid
                )

        return RuntimeExtensionBundle(
            mcp_clients=merged_mcp_clients,
            tool_policy=merged_policy,
            metadata=merged_metadata,
        )
