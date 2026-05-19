# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pytest

from qwenpaw.tenancy.paths import (
    tenant_workspace_dir,
    tenants_root,
    validate_tenant_agent_id,
)


def test_tenants_root_defaults_to_working_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("QWENPAW_TENANTS_ROOT", raising=False)

    assert tenants_root(tmp_path) == tmp_path / "tenants"


def test_tenants_root_prefers_env(tmp_path, monkeypatch):
    configured = tmp_path / "custom-tenants"
    monkeypatch.setenv("QWENPAW_TENANTS_ROOT", str(configured))

    assert tenants_root(tmp_path) == configured.resolve()


def test_validate_tenant_agent_id_accepts_wx_id():
    assert validate_tenant_agent_id("wx_alice") == "wx_alice"


@pytest.mark.parametrize(
    "agent_id",
    ["default", "wx_../alice", "wx_a/b", "wx_a\\b", "wx_"],
)
def test_validate_tenant_agent_id_rejects_unsafe_values(agent_id):
    with pytest.raises(ValueError):
        validate_tenant_agent_id(agent_id)


def test_tenant_workspace_dir_uses_validated_agent_id(tmp_path):
    assert tenant_workspace_dir(
        "wx_alice",
        working_dir=tmp_path,
    ) == Path(tmp_path) / "tenants" / "wx_alice"
