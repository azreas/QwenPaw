# -*- coding: utf-8 -*-
"""测试 Plugin API 注册 runtime extension provider。"""

from qwenpaw.plugins.api import PluginApi
from qwenpaw.plugins.registry import PluginRegistry


class StubProvider:
    """模拟 runtime extension provider。"""

    provider_id = "sandbox"


def test_plugin_api_registers_runtime_extension_provider():
    """PluginApi.register_runtime_extension_provider 应正确注册到 registry。"""
    registry = PluginRegistry()
    registry.clear_for_test()
    api = PluginApi("sandbox-runtime", {}, {})
    api.set_registry(registry)

    api.register_runtime_extension_provider(StubProvider())

    providers = registry.get_runtime_extension_providers()
    assert len(providers) == 1
    assert providers[0].plugin_id == "sandbox-runtime"
    assert providers[0].provider.provider_id == "sandbox"


def test_runtime_extension_providers_sorted_by_priority():
    """provider 应按 priority 从小到大排序。"""
    registry = PluginRegistry()
    registry.clear_for_test()
    api = PluginApi("my-plugin", {}, {})
    api.set_registry(registry)

    class P1:
        provider_id = "p1"

    class P2:
        provider_id = "p2"

    api.register_runtime_extension_provider(P2(), priority=20)
    api.register_runtime_extension_provider(P1(), priority=10)

    providers = registry.get_runtime_extension_providers()
    assert providers[0].provider.provider_id == "p1"
    assert providers[1].provider.provider_id == "p2"


def test_clear_for_test_resets_state():
    """clear_for_test 应清空所有注册状态。"""
    registry = PluginRegistry()
    registry.clear_for_test()
    api = PluginApi("p", {}, {})
    api.set_registry(registry)
    api.register_runtime_extension_provider(StubProvider())
    assert len(registry.get_runtime_extension_providers()) == 1

    registry.clear_for_test()
    assert len(registry.get_runtime_extension_providers()) == 0
