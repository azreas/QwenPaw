# -*- coding: utf-8 -*-
"""Resolve static and dynamic tenant agents into workspace references."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from qwenpaw.config.config import AgentProfileConfig
from qwenpaw.config.utils import load_config
from qwenpaw.tenancy.paths import (
    tenant_workspace_dir,
    validate_tenant_agent_id,
)
from qwenpaw.tenancy.tenant_agent_config import load_tenant_agent_config


@dataclass(frozen=True)
class ResolvedAgentRef:
    """Workspace reference resolved from static config or tenant workspace."""

    agent_id: str
    workspace_dir: Path
    agent_config: AgentProfileConfig | None
    source: Literal["static_profile", "tenant_workspace"]
    enabled: bool = True


class AgentResolver:
    """Resolve agent ids without forcing tenants into root profiles."""

    def __init__(
        self,
        *,
        config_loader: Callable[[], object] = load_config,
        working_dir: str | Path | None = None,
    ) -> None:
        self._config_loader = config_loader
        self._working_dir = (
            Path(working_dir).expanduser()
            if working_dir is not None
            else None
        )

    def resolve(self, agent_id: str) -> ResolvedAgentRef | None:
        """Resolve an agent id to a workspace reference."""
        target_agent_id = str(agent_id or "").strip()
        if not target_agent_id:
            return None

        config = self._config_loader()
        agents_config = getattr(config, "agents", None)
        profiles = getattr(agents_config, "profiles", {}) or {}
        if target_agent_id in profiles:
            agent_ref = profiles[target_agent_id]
            return ResolvedAgentRef(
                agent_id=target_agent_id,
                workspace_dir=Path(agent_ref.workspace_dir).expanduser(),
                agent_config=None,
                source="static_profile",
                enabled=getattr(agent_ref, "enabled", True),
            )

        return self._resolve_tenant(target_agent_id)

    def active_agent_id(self) -> str:
        """Return configured active agent id with the existing default fallback."""
        config = self._config_loader()
        agents_config = getattr(config, "agents", None)
        return getattr(agents_config, "active_agent", None) or "default"

    def _resolve_tenant(self, agent_id: str) -> ResolvedAgentRef | None:
        try:
            tenant_agent_id = validate_tenant_agent_id(agent_id)
        except ValueError:
            return None

        workspace_dir = tenant_workspace_dir(
            tenant_agent_id,
            working_dir=self._working_dir,
        )
        if not workspace_dir.is_dir():
            return None

        agent_config = load_tenant_agent_config(
            workspace_dir,
            fallback_agent_id=tenant_agent_id,
        )
        return ResolvedAgentRef(
            agent_id=tenant_agent_id,
            workspace_dir=workspace_dir,
            agent_config=agent_config,
            source="tenant_workspace",
            enabled=True,
        )
