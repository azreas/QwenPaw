# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any, TYPE_CHECKING

from fastapi import HTTPException, Request

from qwenpaw.constant import WORKING_DIR

from .session import WebchatIdentity

if TYPE_CHECKING:
    from qwenpaw.tenancy.workspace_provisioner import WorkspaceProvisioner


def ensure_requested_agent_allowed(
    identity: WebchatIdentity,
    requested_agent_id: str | None,
) -> str:
    if not requested_agent_id:
        return identity.agent_id
    if requested_agent_id != identity.agent_id:
        raise PermissionError("Cannot access another WebChat tenant")
    return identity.agent_id


def _default_provisioner() -> "WorkspaceProvisioner":
    from qwenpaw.tenancy.workspace_provisioner import WorkspaceProvisioner

    working_dir = Path(WORKING_DIR).expanduser()
    return WorkspaceProvisioner(
        working_dir=working_dir,
        template_dir=working_dir / "_template",
    )


async def get_tenant_workspace_for_identity(
    request: Request,
    identity: WebchatIdentity,
    *,
    provisioner: Any | None = None,
) -> Any:
    if not hasattr(request.app.state, "multi_agent_manager"):
        raise HTTPException(
            status_code=500,
            detail="MultiAgentManager not initialized",
        )
    workspace_provisioner = provisioner or _default_provisioner()
    workspace_dir = workspace_provisioner.ensure(identity.tenant_id)
    manager = request.app.state.multi_agent_manager
    return await manager.get_or_create_tenant_agent(
        identity.agent_id,
        workspace_dir,
    )


def build_webchat_channel_facade(workspace: Any) -> Any:
    from qwenpaw.app.channels.utils import make_process_from_runner
    from qwenpaw.app.channels.webchat.channel import WebchatChannel

    return WebchatChannel(
        process=make_process_from_runner(workspace.runner),
        enabled=True,
        bot_prefix="",
        workspace_dir=workspace.workspace_dir,
    )
