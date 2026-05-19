# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from qwenpaw.app.agent_resolver import AgentResolver
from qwenpaw.config.agent_config_file import (
    AGENT_CONFIG_FILENAME,
    write_agent_config_to_workspace,
)
from qwenpaw.config.config import AgentProfileConfig


def make_static_config(tmp_path):
    return SimpleNamespace(
        agents=SimpleNamespace(
            active_agent="default",
            profiles={
                "default": SimpleNamespace(
                    workspace_dir=str(tmp_path / "default"),
                    enabled=True,
                ),
                "disabled": SimpleNamespace(
                    workspace_dir=str(tmp_path / "disabled"),
                    enabled=False,
                ),
            },
        ),
    )


def test_resolves_static_profile(tmp_path):
    resolver = AgentResolver(
        config_loader=lambda: make_static_config(tmp_path),
        working_dir=tmp_path,
    )

    resolved = resolver.resolve("default")

    assert resolved is not None
    assert resolved.agent_id == "default"
    assert resolved.workspace_dir == Path(tmp_path) / "default"
    assert resolved.agent_config is None
    assert resolved.source == "static_profile"
    assert resolved.enabled is True


def test_resolves_disabled_static_profile(tmp_path):
    resolver = AgentResolver(
        config_loader=lambda: make_static_config(tmp_path),
        working_dir=tmp_path,
    )

    resolved = resolver.resolve("disabled")

    assert resolved is not None
    assert resolved.enabled is False


def test_resolves_dynamic_tenant_workspace(tmp_path):
    workspace_dir = tmp_path / "tenants" / "wx_alice"
    write_agent_config_to_workspace(
        workspace_dir,
        AgentProfileConfig(
            id="wx_alice",
            name="Alice",
            workspace_dir=str(workspace_dir),
        ),
    )
    resolver = AgentResolver(
        config_loader=lambda: make_static_config(tmp_path),
        working_dir=tmp_path,
    )

    resolved = resolver.resolve("wx_alice")

    assert resolved is not None
    assert resolved.agent_id == "wx_alice"
    assert resolved.workspace_dir == workspace_dir
    assert resolved.agent_config is not None
    assert resolved.agent_config.id == "wx_alice"
    assert resolved.source == "tenant_workspace"
    assert resolved.enabled is True


def test_returns_none_for_missing_dynamic_tenant(tmp_path):
    resolver = AgentResolver(
        config_loader=lambda: make_static_config(tmp_path),
        working_dir=tmp_path,
    )

    assert resolver.resolve("wx_missing") is None


def test_returns_none_for_invalid_dynamic_tenant_id(tmp_path):
    resolver = AgentResolver(
        config_loader=lambda: make_static_config(tmp_path),
        working_dir=tmp_path,
    )

    assert resolver.resolve("wx_../bad") is None


def test_resolves_dynamic_tenant_with_empty_working_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workspace_dir = Path("tenants") / "wx_local"
    write_agent_config_to_workspace(
        workspace_dir,
        AgentProfileConfig(
            id="wx_local",
            name="Local",
            workspace_dir=str(workspace_dir),
        ),
    )
    resolver = AgentResolver(
        config_loader=lambda: make_static_config(tmp_path),
        working_dir="",
    )

    resolved = resolver.resolve("wx_local")

    assert resolved is not None
    assert resolved.workspace_dir == workspace_dir
    assert resolved.workspace_dir.resolve() == (
        tmp_path / "tenants" / "wx_local"
    ).resolve()


def test_tenants_root_env_overrides_injected_working_dir(tmp_path, monkeypatch):
    env_root = tmp_path / "env_root"
    injected_root = tmp_path / "injected_root"
    env_workspace = env_root / "wx_env"
    injected_workspace = injected_root / "tenants" / "wx_env"
    write_agent_config_to_workspace(
        env_workspace,
        AgentProfileConfig(
            id="wx_env",
            name="Env",
            workspace_dir=str(env_workspace),
        ),
    )
    write_agent_config_to_workspace(
        injected_workspace,
        AgentProfileConfig(
            id="wx_env",
            name="Injected",
            workspace_dir=str(injected_workspace),
        ),
    )
    monkeypatch.setenv("QWENPAW_TENANTS_ROOT", str(env_root))
    resolver = AgentResolver(
        config_loader=lambda: make_static_config(tmp_path),
        working_dir=injected_root,
    )

    resolved = resolver.resolve("wx_env")

    assert resolved is not None
    assert resolved.workspace_dir == env_workspace


def test_resolves_static_profile_with_path_workspace_dir(tmp_path):
    config = make_static_config(tmp_path)
    config.agents.profiles["default"].workspace_dir = tmp_path / "default_path_obj"
    resolver = AgentResolver(
        config_loader=lambda: config,
        working_dir=tmp_path,
    )

    resolved = resolver.resolve("default")

    assert resolved is not None
    assert resolved.workspace_dir == tmp_path / "default_path_obj"


def test_resolve_propagates_malformed_agent_json(tmp_path):
    workspace_dir = tmp_path / "tenants" / "wx_broken"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    (workspace_dir / AGENT_CONFIG_FILENAME).write_text(
        "{not-json",
        encoding="utf-8",
    )
    resolver = AgentResolver(
        config_loader=lambda: make_static_config(tmp_path),
        working_dir=tmp_path,
    )

    with pytest.raises(json.JSONDecodeError):
        resolver.resolve("wx_broken")


def test_resolve_propagates_agent_validation_error(tmp_path):
    workspace_dir = tmp_path / "tenants" / "wx_invalid"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    (workspace_dir / AGENT_CONFIG_FILENAME).write_text(
        "{}",
        encoding="utf-8",
    )
    resolver = AgentResolver(
        config_loader=lambda: make_static_config(tmp_path),
        working_dir=tmp_path,
    )

    with pytest.raises(ValidationError):
        resolver.resolve("wx_invalid")
