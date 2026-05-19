# -*- coding: utf-8 -*-
"""Console management API for WeCom tenant workspaces."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from ...constant import WORKING_DIR
from ...enterprise.audit.emit import emit_audit_event
from ...enterprise.audit.models import AuditEventType, AuditOutcome
from ...tenancy.ids import tenant_agent_id
from ...tenancy.paths import (
    tenant_workspace_dir,
    tenants_root as resolve_tenants_root,
    validate_tenant_agent_id,
)
from ..multi_agent_manager import MultiAgentManager

router = APIRouter(
    prefix="/config/channels/wecom_tenant",
    tags=["wecom-tenant"],
)


class WecomTenantSummary(BaseModel):
    """租户工作区在控制台中的管理摘要。"""

    tenant_id: str
    agent_id: str
    workspace_dir: str
    exists: bool
    initialized: bool
    running: bool
    updated_at: str | None = None
    chat_count: int = 0
    job_count: int = 0
    source: str = "workspace"


class WecomTenantListResponse(BaseModel):
    tenants: list[WecomTenantSummary]


class CreateWecomTenantRequest(BaseModel):
    tenant_id: str = Field(min_length=1)
    start: bool = False

    @field_validator("tenant_id", mode="before")
    @classmethod
    def strip_tenant_id(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value


def _get_manager(request: Request) -> MultiAgentManager:
    manager = getattr(request.app.state, "multi_agent_manager", None)
    if manager is None:
        raise HTTPException(
            status_code=503,
            detail="MultiAgentManager not initialized",
        )
    return manager


def _tenants_root() -> Path:
    return resolve_tenants_root(WORKING_DIR)


def _new_provisioner():
    from ...tenancy.workspace_provisioner import WorkspaceProvisioner

    working_dir = Path(WORKING_DIR).expanduser()
    return WorkspaceProvisioner(
        working_dir=working_dir,
        template_dir=working_dir / "_template",
    )


def _validate_agent_id(agent_id: str) -> str:
    try:
        return validate_tenant_agent_id(agent_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Only wx_* tenant agent ids are supported",
        ) from exc


def _workspace_for_agent_id(agent_id: str) -> Path:
    return tenant_workspace_dir(
        _validate_agent_id(agent_id),
        working_dir=WORKING_DIR,
    )


def _read_json_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _count_json_items(path: Path, key: str) -> int:
    data = _read_json_file(path)
    items = data.get(key)
    return len(items) if isinstance(items, list) else 0


def _iso_mtime(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(
        path.stat().st_mtime,
        tz=timezone.utc,
    ).isoformat()


def _summary_sort_key(summary: WecomTenantSummary) -> tuple[str, str]:
    return (summary.updated_at or "", summary.agent_id)


def _summarize_tenant(
    agent_id: str,
    manager: MultiAgentManager,
) -> WecomTenantSummary:
    workspace_dir = _workspace_for_agent_id(agent_id)
    agent_config = _read_json_file(workspace_dir / "agent.json")
    tenant_id = str(agent_config.get("tenant_id") or agent_id[3:])
    exists = workspace_dir.is_dir()
    return WecomTenantSummary(
        tenant_id=tenant_id,
        agent_id=agent_id,
        workspace_dir=str(workspace_dir),
        exists=exists,
        initialized=(workspace_dir / "agent.json").is_file(),
        running=manager.is_agent_loaded(agent_id),
        updated_at=_iso_mtime(workspace_dir / "agent.json")
        or _iso_mtime(workspace_dir),
        chat_count=_count_json_items(workspace_dir / "chats.json", "chats"),
        job_count=_count_json_items(workspace_dir / "jobs.json", "jobs"),
        source="workspace" if exists else "runtime",
    )


def _list_tenant_agent_ids(manager: MultiAgentManager) -> list[str]:
    agent_ids: set[str] = set()
    root = _tenants_root()
    if root.is_dir():
        agent_ids.update(
            item.name
            for item in root.iterdir()
            if item.is_dir() and item.name.startswith("wx_")
        )
    agent_ids.update(
        agent_id
        for agent_id in manager.list_loaded_agents()
        if agent_id.startswith("wx_")
    )
    return sorted(agent_ids)


@router.get("/tenants", response_model=WecomTenantListResponse)
async def list_wecom_tenants(request: Request) -> WecomTenantListResponse:
    """List tenant workspaces created by the WeCom tenant channel."""
    manager = _get_manager(request)
    tenants = [
        _summarize_tenant(agent_id, manager)
        for agent_id in _list_tenant_agent_ids(manager)
    ]
    tenants.sort(key=_summary_sort_key, reverse=True)
    return WecomTenantListResponse(tenants=tenants)


@router.post(
    "/tenants",
    response_model=WecomTenantSummary,
    status_code=201,
)
async def create_wecom_tenant(
    request: Request,
    body: CreateWecomTenantRequest = Body(...),
) -> WecomTenantSummary:
    """Manually initialize a WeCom tenant workspace from the console."""
    manager = _get_manager(request)
    workspace_dir = _new_provisioner().ensure(body.tenant_id)
    agent_id = tenant_agent_id(body.tenant_id)

    if body.start:
        await manager.get_or_create_tenant_agent(agent_id, workspace_dir)

    await emit_audit_event(
        request,
        event_type=AuditEventType.TENANT_UPDATED,
        action="create_tenant",
        outcome=AuditOutcome.SUCCESS,
        resource_type="tenant",
        resource_id=body.tenant_id,
        payload={"changed_key": "tenant", "tenant_id": body.tenant_id},
    )
    return _summarize_tenant(agent_id, manager)


@router.post(
    "/tenants/{agent_id}/start",
    response_model=WecomTenantSummary,
)
async def start_wecom_tenant(
    request: Request,
    agent_id: str,
) -> WecomTenantSummary:
    """Start an existing dynamic tenant workspace."""
    manager = _get_manager(request)
    workspace_dir = _workspace_for_agent_id(agent_id)
    if not workspace_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"Tenant workspace '{agent_id}' not found",
        )
    await manager.get_or_create_tenant_agent(agent_id, workspace_dir)
    await emit_audit_event(
        request,
        event_type=AuditEventType.TENANT_UPDATED,
        action="start_tenant",
        outcome=AuditOutcome.SUCCESS,
        resource_type="tenant",
        resource_id=agent_id,
        payload={"changed_key": "tenant", "agent_id": agent_id},
    )
    return _summarize_tenant(agent_id, manager)


@router.post(
    "/tenants/{agent_id}/stop",
    response_model=WecomTenantSummary,
)
async def stop_wecom_tenant(
    request: Request,
    agent_id: str,
) -> WecomTenantSummary:
    """Stop a running dynamic tenant workspace without deleting files."""
    manager = _get_manager(request)
    workspace_dir = _workspace_for_agent_id(agent_id)
    if not workspace_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"Tenant workspace '{agent_id}' not found",
        )
    if manager.is_agent_loaded(agent_id):
        await manager.stop_agent(agent_id)
    await emit_audit_event(
        request,
        event_type=AuditEventType.TENANT_UPDATED,
        action="stop_tenant",
        outcome=AuditOutcome.SUCCESS,
        resource_type="tenant",
        resource_id=agent_id,
        payload={"changed_key": "tenant", "agent_id": agent_id},
    )
    return _summarize_tenant(agent_id, manager)


@router.post(
    "/tenants/{agent_id}/restart",
    response_model=WecomTenantSummary,
)
async def restart_wecom_tenant(
    request: Request,
    agent_id: str,
) -> WecomTenantSummary:
    """Restart a dynamic tenant workspace."""
    manager = _get_manager(request)
    workspace_dir = _workspace_for_agent_id(agent_id)
    if not workspace_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"Tenant workspace '{agent_id}' not found",
        )
    if manager.is_agent_loaded(agent_id):
        await manager.stop_agent(agent_id)
    await manager.get_or_create_tenant_agent(agent_id, workspace_dir)
    await emit_audit_event(
        request,
        event_type=AuditEventType.TENANT_UPDATED,
        action="restart_tenant",
        outcome=AuditOutcome.SUCCESS,
        resource_type="tenant",
        resource_id=agent_id,
        payload={"changed_key": "tenant", "agent_id": agent_id},
    )
    return _summarize_tenant(agent_id, manager)
