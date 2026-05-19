# -*- coding: utf-8 -*-
from qwenpaw.tenancy.ids import safe_tenant_suffix, tenant_agent_id


def test_safe_tenant_suffix_keeps_plain_ids():
    assert safe_tenant_suffix("alice_123") == "alice_123"


def test_safe_tenant_suffix_hashes_path_injection():
    value = safe_tenant_suffix("../alice")

    assert value != "../alice"
    assert len(value) == 16


def test_tenant_agent_id_prefixes_safe_suffix():
    assert tenant_agent_id("alice") == "wx_alice"
    assert tenant_agent_id("../alice").startswith("wx_")
