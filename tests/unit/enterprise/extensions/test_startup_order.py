"""测试 enterprise runtime 在插件加载前已有真正的 extension resolver。"""

import os

from qwenpaw.enterprise.runtime import create_enterprise_runtime
from qwenpaw.enterprise.extensions.resolver import RuntimeExtensionResolver


def test_enterprise_runtime_has_extension_resolver_before_plugin_startup():
    """create_enterprise_runtime() 应创建 RuntimeExtensionResolver。"""
    runtime = create_enterprise_runtime()
    assert runtime.extensions is not None
    assert isinstance(runtime.extensions, RuntimeExtensionResolver)


def test_resolver_is_not_noop():
    """create_enterprise_runtime() 应创建真正的 resolver，而非 Noop。"""
    from qwenpaw.enterprise.noop import NoopRuntimeExtensionResolver

    runtime = create_enterprise_runtime()
    assert not isinstance(
        runtime.extensions, NoopRuntimeExtensionResolver
    )


def test_resolver_accepts_providers():
    """resolver 可以注册 provider。"""

    class StubProvider:
        provider_id = "test"

    runtime = create_enterprise_runtime()
    runtime.extensions.register_provider(StubProvider())
    assert "test" in runtime.extensions._providers


def test_sandbox_provider_preregistered_when_env_enabled(monkeypatch):
    """环境变量启用沙箱时，resolver 预注册 SandboxProvider。"""
    monkeypatch.setenv("QWENPAW_SANDBOX_ENABLED", "true")
    monkeypatch.setenv(
        "QWENPAW_SANDBOX_GATEWAY_URL", "http://sandbox-gw"
    )
    runtime = create_enterprise_runtime()
    assert "sandbox-runtime" in runtime.extensions._providers


def test_sandbox_provider_not_preregistered_when_disabled():
    """沙箱未启用时，resolver 不预注册 provider。"""
    runtime = create_enterprise_runtime()
    assert "sandbox-runtime" not in runtime.extensions._providers
