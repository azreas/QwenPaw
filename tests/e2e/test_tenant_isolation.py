# -*- coding: utf-8 -*-
"""租户路径隔离测试。"""
from __future__ import annotations

from qwenpaw.tenancy.paths import tenant_workspace_dir


def test_wx_tenant_workspace_paths_are_isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("QWENPAW_TENANTS_ROOT", str(tmp_path))

    alice = tenant_workspace_dir("wx_alice")
    bob = tenant_workspace_dir("wx_bob")

    assert alice != bob
    assert alice.parent == bob.parent
    assert alice.name == "wx_alice"
    assert bob.name == "wx_bob"


def test_tenant_path_rejects_traversal(tmp_path, monkeypatch):
    monkeypatch.setenv("QWENPAW_TENANTS_ROOT", str(tmp_path))

    try:
        tenant_workspace_dir("../evil")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for path traversal")


def test_tenant_path_rejects_non_wx_prefix(tmp_path, monkeypatch):
    monkeypatch.setenv("QWENPAW_TENANTS_ROOT", str(tmp_path))

    try:
        tenant_workspace_dir("evil_tenant")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for non-wx_ prefix")
