# -*- coding: utf-8 -*-
import json

from qwenpaw.config.agent_config_file import (
    load_agent_config_from_workspace,
    write_agent_config_to_workspace,
)
from qwenpaw.config.config import AgentProfileConfig


def test_load_agent_config_from_workspace_returns_none_when_missing(tmp_path):
    assert load_agent_config_from_workspace(tmp_path) is None


def test_write_and_load_agent_config_from_workspace(tmp_path):
    config = AgentProfileConfig(
        id="wx_alice",
        name="wx_alice",
        workspace_dir=str(tmp_path),
        system_prompt_files=["AGENTS.md", "SOUL.md"],
    )

    path = write_agent_config_to_workspace(tmp_path, config)

    assert path == tmp_path / "agent.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["id"] == "wx_alice"
    assert data["system_prompt_files"] == ["AGENTS.md", "SOUL.md"]
    loaded = load_agent_config_from_workspace(tmp_path)
    assert loaded.id == "wx_alice"
