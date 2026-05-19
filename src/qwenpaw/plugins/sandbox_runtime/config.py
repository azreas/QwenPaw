# -*- coding: utf-8 -*-
"""沙箱运行时配置。"""

from pydantic import BaseModel


class SandboxRuntimeConfig(BaseModel):
    """沙箱运行时配置。"""

    enabled: bool = False
    gateway_url: str = ""
    tenant_mode_default: str = "sandbox"
    idle_timeout_seconds: int = 900
    disable_local_tools: tuple[str, ...] = (
        "execute_shell_command",
        "browser_use",
    )
