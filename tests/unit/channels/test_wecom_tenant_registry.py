# -*- coding: utf-8 -*-
from qwenpaw.app.channels.registry import clear_builtin_channel_cache
from qwenpaw.app.channels.registry import get_channel_registry


def test_wecom_tenant_is_registered_as_builtin_channel():
    clear_builtin_channel_cache()
    registry = get_channel_registry()

    assert "wecom_tenant" in registry
    assert registry["wecom_tenant"].channel == "wecom_tenant"
