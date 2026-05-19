# -*- coding: utf-8 -*-
"""Path helpers for dynamic tenant workspaces."""
from __future__ import annotations

import os
from pathlib import Path


def tenants_root(working_dir: str | Path | None = None) -> Path:
    """Return the root directory that stores dynamic tenant workspaces."""
    env = os.environ.get("QWENPAW_TENANTS_ROOT")
    if env:
        return Path(env).expanduser().resolve()

    if working_dir is None:
        from qwenpaw.constant import WORKING_DIR

        working_dir = WORKING_DIR

    return Path(working_dir).expanduser() / "tenants"


def validate_tenant_agent_id(agent_id: str) -> str:
    """Validate and return a dynamic WeCom tenant agent id."""
    value = str(agent_id or "").strip()
    if (
        not value.startswith("wx_")
        or value == "wx_"
        or "/" in value
        or "\\" in value
        or ".." in value
    ):
        raise ValueError("Only safe wx_* tenant agent ids are supported")
    return value


def tenant_workspace_dir(
    agent_id: str,
    *,
    working_dir: str | Path | None = None,
) -> Path:
    """Return the workspace directory for a validated tenant agent id."""
    return tenants_root(working_dir) / validate_tenant_agent_id(agent_id)
