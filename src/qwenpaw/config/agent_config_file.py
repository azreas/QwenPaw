# -*- coding: utf-8 -*-
"""工作区本地 agent.json 读写工具。"""
from __future__ import annotations

import json
from pathlib import Path

from .config import AgentProfileConfig

AGENT_CONFIG_FILENAME = "agent.json"


def load_agent_config_from_workspace(
    workspace_dir: Path,
) -> AgentProfileConfig | None:
    """读取工作区本地 agent.json；不存在时返回 None。"""
    agent_config_path = Path(workspace_dir).expanduser() / AGENT_CONFIG_FILENAME
    if not agent_config_path.exists():
        return None

    with agent_config_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return AgentProfileConfig.model_validate(data)


def write_agent_config_to_workspace(
    workspace_dir: Path,
    agent_config: AgentProfileConfig,
) -> Path:
    """不依赖 root profiles，直接写工作区 agent.json。"""
    resolved_workspace_dir = Path(workspace_dir).expanduser()
    resolved_workspace_dir.mkdir(parents=True, exist_ok=True)
    agent_config_path = resolved_workspace_dir / AGENT_CONFIG_FILENAME

    with agent_config_path.open("w", encoding="utf-8") as file:
        json.dump(
            agent_config.model_dump(mode="json", exclude_none=True),
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")

    return agent_config_path
