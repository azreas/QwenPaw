# -*- coding: utf-8 -*-
"""沙箱会话创建、复用、回收。"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SandboxSessionManager:
    """管理沙箱会话的创建和回收。"""

    def __init__(self, config: Any) -> None:
        self._config = config
        self._sessions: dict[str, Any] = {}

    async def get_or_create(
        self,
        tenant_id: str,
        session_id: str,
    ) -> str:
        """获取或创建沙箱会话标识。"""
        key = f"{tenant_id}:{session_id}"
        if key not in self._sessions:
            self._sessions[key] = key
            logger.info("Created sandbox session: %s", key)
        return self._sessions[key]

    async def cleanup_idle(self) -> int:
        """清理空闲会话（当前为 stub 实现）。"""
        return 0
