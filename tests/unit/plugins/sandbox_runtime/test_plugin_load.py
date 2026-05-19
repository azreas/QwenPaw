# -*- coding: utf-8 -*-
"""测试 PluginLoader 能真正加载 sandbox-runtime 插件。"""

import sys
from pathlib import Path

import pytest

from qwenpaw.plugins.loader import PluginLoader
from qwenpaw.plugins.registry import PluginRegistry


def _plugin_dir() -> Path:
    return Path(__file__).parents[4] / "src" / "qwenpaw" / "plugins"


@pytest.fixture(autouse=True)
def _clean_registry_and_modules():
    """每个测试前后清理 registry 单例和 sys.modules 中的临时插件模块。"""
    registry = PluginRegistry()
    registry.clear_for_test()

    # 预先记录已存在的模块名
    before = set(sys.modules.keys())

    yield

    registry.clear_for_test()

    # 清理 PluginLoader 注入的临时模块
    after = set(sys.modules.keys())
    for name in after - before:
        if name.startswith("plugin_"):
            del sys.modules[name]


@pytest.mark.asyncio
async def test_loader_discovers_sandbox_runtime():
    """PluginLoader 应能发现 sandbox-runtime 插件。"""
    loader = PluginLoader([_plugin_dir()])
    discovered = loader.discover_plugins()
    ids = [m.id for m, _ in discovered]
    assert "sandbox-runtime" in ids


@pytest.mark.asyncio
async def test_loader_loads_sandbox_runtime_successfully():
    """PluginLoader 应能成功加载 sandbox-runtime 插件到 registry。"""
    loader = PluginLoader([_plugin_dir()])

    configs = {
        "sandbox-runtime": {
            "enabled": True,
            "gateway_url": "http://sandbox-gw",
        },
    }

    loaded = await loader.load_all_plugins(configs)

    assert "sandbox-runtime" in loaded
    record = loaded["sandbox-runtime"]
    assert record.manifest.id == "sandbox-runtime"
    assert record.enabled is True

    # registry 中应注册了运行时扩展 provider
    registry = PluginRegistry()
    providers = registry.get_runtime_extension_providers()
    ids = [p.plugin_id for p in providers]
    assert "sandbox-runtime" in ids

    # 确认 provider 对象类型正确（动态加载模块与正常导入的类不同，用 duck-typing 检查）
    sandbox_reg = next(p for p in providers if p.plugin_id == "sandbox-runtime")
    assert hasattr(sandbox_reg.provider, "resolve")
    assert getattr(sandbox_reg.provider, "provider_id", None) == "sandbox-runtime"
    assert sandbox_reg.priority == 10
