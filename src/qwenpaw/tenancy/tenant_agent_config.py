# -*- coding: utf-8 -*-
"""动态租户 agent 配置构建与本地持久化 helper。"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from qwenpaw.agents.templates import DEFAULT_AGENT_TEMPLATE, build_agent_template
from qwenpaw.config.agent_config_file import (
    AGENT_CONFIG_FILENAME,
    load_agent_config_from_workspace,
    write_agent_config_to_workspace,
)
from qwenpaw.config.config import (
    AgentProfileConfig,
    AgentsLLMRoutingConfig,
    AgentsRunningConfig,
)
from qwenpaw.config.utils import load_config

_LEGACY_STATE_FILENAME = ".tenant_workspace_state.json"


def build_tenant_agent_config(
    agent_id: str,
    workspace_dir: Path,
) -> AgentProfileConfig:
    """复用原生模板构造动态租户配置。"""
    config = load_config()
    agents_config = getattr(config, "agents", None)
    language = (
        getattr(agents_config, "language", None)
        if agents_config is not None
        and getattr(agents_config, "language", None)
        else "zh"
    )

    template_result = build_agent_template(
        DEFAULT_AGENT_TEMPLATE,
        agent_id=agent_id,
        workspace_dir=Path(workspace_dir).expanduser(),
        fallback_language=language,
        name=agent_id,
        description=f"{agent_id} 动态租户工作区",
    )
    agent_config = template_result.agent_config
    agent_config.channels = None
    agent_config.mcp = getattr(config, "mcp", None)
    agent_config.tools = getattr(config, "tools", None)
    agent_config.security = getattr(config, "security", None)
    agent_config.running = (
        getattr(agents_config, "running", None)
        if agents_config is not None
        and getattr(agents_config, "running", None)
        else AgentsRunningConfig()
    )
    agent_config.llm_routing = (
        getattr(agents_config, "llm_routing", None)
        if agents_config is not None
        and getattr(agents_config, "llm_routing", None)
        else AgentsLLMRoutingConfig()
    )
    if (
        agents_config is not None
        and getattr(agents_config, "system_prompt_files", None)
    ):
        agent_config.system_prompt_files = list(
            getattr(agents_config, "system_prompt_files"),
        )
    return agent_config


def load_tenant_agent_config(
    workspace_dir: Path,
    *,
    fallback_agent_id: str,
) -> AgentProfileConfig:
    """从工作区 agent.json 读取租户配置。"""
    agent_config = load_agent_config_from_workspace(workspace_dir)
    if agent_config is not None:
        return agent_config

    return build_tenant_agent_config(
        agent_id=fallback_agent_id,
        workspace_dir=workspace_dir,
    )


def ensure_tenant_agent_config_file(
    *,
    agent_id: str,
    workspace_dir: Path,
) -> AgentProfileConfig:
    """确保工作区 agent.json 完整；旧版部分配置会被补齐迁移。"""
    try:
        agent_config = load_agent_config_from_workspace(workspace_dir)
    except ValidationError:
        return _migrate_partial_agent_config_file(
            agent_id=agent_id,
            workspace_dir=workspace_dir,
        )
    if agent_config is not None:
        normalized_config = _ensure_authoritative_identity(
            agent_config=agent_config,
            agent_id=agent_id,
            workspace_dir=workspace_dir,
        )
        if normalized_config is not agent_config:
            write_agent_config_to_workspace(workspace_dir, normalized_config)
        return normalized_config

    agent_config = build_tenant_agent_config(
        agent_id=agent_id,
        workspace_dir=workspace_dir,
    )
    legacy_system_prompt_files = _load_legacy_system_prompt_files(workspace_dir)
    if legacy_system_prompt_files is not None:
        agent_config.system_prompt_files = legacy_system_prompt_files

    write_agent_config_to_workspace(workspace_dir, agent_config)
    return agent_config


def _ensure_authoritative_identity(
    *,
    agent_config: AgentProfileConfig,
    agent_id: str,
    workspace_dir: Path,
) -> AgentProfileConfig:
    """动态租户身份以调用方解析结果为准。"""
    resolved_workspace_dir = Path(workspace_dir).expanduser()
    if (
        agent_config.id == agent_id
        and agent_config.workspace_dir == str(resolved_workspace_dir)
    ):
        return agent_config

    return agent_config.model_copy(
        update={
            "id": agent_id,
            "workspace_dir": str(resolved_workspace_dir),
        },
    )


def _migrate_partial_agent_config_file(
    *,
    agent_id: str,
    workspace_dir: Path,
) -> AgentProfileConfig:
    """以完整默认配置为底座，合并旧版 agent.json 中可识别字段。"""
    resolved_workspace_dir = Path(workspace_dir).expanduser()
    agent_config_path = resolved_workspace_dir / AGENT_CONFIG_FILENAME
    with agent_config_path.open("r", encoding="utf-8") as file:
        raw_config = json.load(file)

    if not isinstance(raw_config, dict):
        raise ValueError("agent.json 必须是对象结构")

    merged = build_tenant_agent_config(
        agent_id=agent_id,
        workspace_dir=resolved_workspace_dir,
    ).model_dump(mode="json", exclude_none=True)
    allowed_fields = set(AgentProfileConfig.model_fields)
    for key, value in raw_config.items():
        if key in allowed_fields and key not in {"id", "workspace_dir"}:
            merged[key] = value

    agent_config = AgentProfileConfig.model_validate(merged)
    write_agent_config_to_workspace(resolved_workspace_dir, agent_config)
    return agent_config


def _load_legacy_system_prompt_files(workspace_dir: Path) -> list[str] | None:
    """仅在首次创建 agent.json 时读取旧状态中的 persona 顺序。"""
    state_path = Path(workspace_dir).expanduser() / _LEGACY_STATE_FILENAME
    if not state_path.exists():
        return None

    with state_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        return None

    raw_files = data.get("system_prompt_files")
    if not isinstance(raw_files, list):
        return None

    return [str(item) for item in raw_files]
