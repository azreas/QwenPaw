# -*- coding: utf-8 -*-
import json
from types import SimpleNamespace

from qwenpaw.tenancy.tenant_agent_config import (
    build_tenant_agent_config,
    ensure_tenant_agent_config_file,
)


def test_build_tenant_agent_config_sets_dynamic_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "qwenpaw.tenancy.tenant_agent_config.load_config",
        lambda: SimpleNamespace(agents=SimpleNamespace()),
    )

    config = build_tenant_agent_config("wx_alice", tmp_path)

    assert config.id == "wx_alice"
    assert config.name == "wx_alice"
    assert config.workspace_dir == str(tmp_path)
    assert config.channels is None
    assert config.system_prompt_files == ["AGENTS.md", "SOUL.md", "PROFILE.md"]


def test_ensure_tenant_agent_config_file_preserves_existing_persona_order(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        "qwenpaw.tenancy.tenant_agent_config.load_config",
        lambda: SimpleNamespace(agents=SimpleNamespace()),
    )
    (tmp_path / "agent.json").write_text(
        json.dumps(
            {
                "id": "old",
                "name": "old",
                "workspace_dir": "old-dir",
                "system_prompt_files": ["PROFILE.md", "SOUL.md"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    config = ensure_tenant_agent_config_file(
        agent_id="wx_alice",
        workspace_dir=tmp_path,
    )

    assert config.id == "wx_alice"
    assert config.workspace_dir == str(tmp_path)
    assert config.system_prompt_files == ["PROFILE.md", "SOUL.md"]
