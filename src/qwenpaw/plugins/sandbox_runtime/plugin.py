# -*- coding: utf-8 -*-
"""sandbox-runtime 插件注册入口。"""

from .config import SandboxRuntimeConfig
from .provider import SandboxRuntimeExtensionProvider


class _SandboxPlugin:
    """PluginLoader 要求的 plugin 对象。"""

    def register(self, api):
        """插件注册入口，由 PluginLoader 调用。"""
        config = SandboxRuntimeConfig.model_validate(
            api.config or {}
        )
        api.register_runtime_extension_provider(
            SandboxRuntimeExtensionProvider(config),
            priority=10,
        )


# PluginLoader 通过 module.plugin 访问
plugin = _SandboxPlugin()
