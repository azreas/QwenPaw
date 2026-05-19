# -*- coding: utf-8 -*-
"""Operations endpoints for WeCom tenant workspaces."""
from __future__ import annotations

import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ...crons.models import CronJobSpec
from ...crons.repo.json_repo import JsonJobRepository
from ...utils import schedule_agent_reload
from ....enterprise.audit.models import AuditEventType, AuditOutcome
from ....enterprise.authz.deps import require_permission
from .common import (
    emit_tenant_audit_event,
    ensure_tenant_boundary_for_agent,
    get_manager,
    maybe_reload,
    require_tenant_boundary,
    require_workspace,
    tenants_root,
    validate_agent_id,
    workspace_for_agent_id,
)
from .schemas import BatchOperationResponse, MessageResponse, OperationResult

router = APIRouter()


class DeleteTenantRequest(BaseModel):
    confirm: bool = False


class BatchTenantRequest(BaseModel):
    agent_ids: list[str] = Field(default_factory=list)
    all: bool = False


class FileInfo(BaseModel):
    filename: str
    size: int
    updated_at: str | None = None


class FileListResponse(BaseModel):
    files: list[FileInfo]


class FileContentRequest(BaseModel):
    content: str


class FileContentResponse(BaseModel):
    filename: str
    content: str


class TenantHealthResponse(BaseModel):
    agent_id: str
    status: str
    checks: dict[str, Any]


class AllTenantHealthResponse(BaseModel):
    tenants: list[TenantHealthResponse]


def _list_workspace_agent_ids() -> list[str]:
    root = tenants_root()
    if not root.is_dir():
        return []
    return sorted(
        item.name
        for item in root.iterdir()
        if item.is_dir() and item.name.startswith("wx_")
    )


def _batch_agent_ids(body: BatchTenantRequest) -> list[str]:
    if body.all:
        return _list_workspace_agent_ids()
    return [validate_agent_id(agent_id) for agent_id in body.agent_ids]


def _safe_filename(filename: str) -> str:
    value = str(filename or "").strip()
    if (
        not value
        or "/" in value
        or "\\" in value
        or ".." in value
        or not value.endswith((".md", ".json"))
    ):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return value


def _file_info(path: Path) -> FileInfo:
    updated_at = None
    if path.exists():
        updated_at = datetime.fromtimestamp(
            path.stat().st_mtime,
            tz=timezone.utc,
        ).isoformat()
    return FileInfo(
        filename=path.name,
        size=path.stat().st_size,
        updated_at=updated_at,
    )


def _list_safe_files(root: Path) -> FileListResponse:
    if not root.is_dir():
        return FileListResponse(files=[])
    paths = sorted(
        (
            path
            for path in root.iterdir()
            if path.is_file() and path.suffix in {".md", ".json"}
        ),
        key=lambda item: item.name,
    )
    files = [_file_info(path) for path in paths]
    return FileListResponse(files=files)


def _safe_zip_member(name: str) -> Path:
    rel = Path(name)
    if (
        not name
        or rel.is_absolute()
        or any(part in {"", ".", ".."} for part in rel.parts)
    ):
        raise HTTPException(status_code=400, detail="Invalid zip member path")
    return rel


def _job_repo(agent_id: str) -> JsonJobRepository:
    return JsonJobRepository(require_workspace(agent_id) / "jobs.json")


async def _emit_tenant_updated(
    request: Request,
    agent_id: str,
    action: str,
    *,
    resource_type: str,
    resource_id: str,
    outcome: AuditOutcome = AuditOutcome.SUCCESS,
    payload: dict[str, Any] | None = None,
) -> None:
    await emit_tenant_audit_event(
        request,
        agent_id,
        AuditEventType.TENANT_UPDATED,
        action,
        outcome,
        resource_type=resource_type,
        resource_id=resource_id,
        payload={"agent_id": agent_id, **(payload or {})},
    )


def _running_workspace(request: Request, agent_id: str):
    manager = get_manager(request)
    return getattr(manager, "agents", {}).get(agent_id)


def _running_cron_manager(request: Request, agent_id: str):
    workspace = _running_workspace(request, agent_id)
    return getattr(workspace, "cron_manager", None) if workspace else None


async def _get_job(request: Request, agent_id: str, job_id: str) -> CronJobSpec | None:
    mgr = _running_cron_manager(request, agent_id)
    if mgr is not None:
        return await mgr.get_job(job_id)
    return await _job_repo(agent_id).get_job(job_id)


async def _upsert_job(request: Request, agent_id: str, spec: CronJobSpec) -> None:
    mgr = _running_cron_manager(request, agent_id)
    if mgr is not None:
        await mgr.create_or_replace_job(spec)
        return
    await _job_repo(agent_id).upsert_job(spec)


async def _tenant_health(request: Request, agent_id: str) -> TenantHealthResponse:
    validate_agent_id(agent_id)
    workspace_dir = workspace_for_agent_id(agent_id)
    agent_json = workspace_dir / "agent.json"
    checks: dict[str, Any] = {
        "workspace_exists": workspace_dir.is_dir(),
        "agent_json_valid": False,
        "running": False,
        "last_activity": None,
        "memory_dir_exists": (workspace_dir / "memory").is_dir(),
        "sessions_dir_exists": (workspace_dir / "sessions").is_dir(),
    }
    if agent_json.is_file():
        try:
            import json

            json.loads(agent_json.read_text(encoding="utf-8"))
            checks["agent_json_valid"] = True
            checks["last_activity"] = datetime.fromtimestamp(
                agent_json.stat().st_mtime,
                tz=timezone.utc,
            ).isoformat()
        except Exception:
            checks["agent_json_valid"] = False
    manager = get_manager(request)
    checks["running"] = manager.is_agent_loaded(agent_id)
    if not checks["workspace_exists"] or not checks["agent_json_valid"]:
        status = "unhealthy"
    elif all(
        bool(checks[key])
        for key in [
            "running",
            "memory_dir_exists",
            "sessions_dir_exists",
        ]
    ):
        status = "healthy"
    else:
        status = "degraded"
    return TenantHealthResponse(agent_id=agent_id, status=status, checks=checks)


@router.delete("/tenants/{agent_id}", response_model=MessageResponse)
async def delete_tenant(
    request: Request,
    agent_id: str,
    body: DeleteTenantRequest,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> MessageResponse:
    workspace_dir = require_workspace(agent_id)
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm=true is required")
    manager = get_manager(request)
    if manager.is_agent_loaded(agent_id):
        await manager.stop_agent(agent_id)
    shutil.rmtree(workspace_dir)
    await _emit_tenant_updated(
        request,
        agent_id,
        "delete_tenant",
        resource_type="tenant",
        resource_id=agent_id,
    )
    return MessageResponse(message=f"Tenant '{agent_id}' deleted successfully")


async def _run_batch_item(
    request: Request,
    agent_id: str,
    action: str,
) -> OperationResult:
    try:
        await ensure_tenant_boundary_for_agent(request, agent_id)
        workspace_dir = require_workspace(agent_id)
        manager = get_manager(request)
        if action == "start":
            await manager.get_or_create_tenant_agent(agent_id, workspace_dir)
        elif action == "stop":
            if manager.is_agent_loaded(agent_id):
                await manager.stop_agent(agent_id)
        elif action == "restart":
            if manager.is_agent_loaded(agent_id):
                await manager.stop_agent(agent_id)
            await manager.get_or_create_tenant_agent(agent_id, workspace_dir)
        else:
            raise ValueError(f"Unknown action: {action}")
        await _emit_tenant_updated(
            request,
            agent_id,
            f"batch_{action}",
            resource_type="tenant_runtime",
            resource_id=f"{agent_id}:{action}",
        )
        return OperationResult(agent_id=agent_id, success=True)
    except Exception as exc:
        return OperationResult(agent_id=agent_id, success=False, error=str(exc))


@router.post("/tenants/batch/start", response_model=BatchOperationResponse)
async def batch_start(
    request: Request,
    body: BatchTenantRequest,
    _ctx=Depends(require_permission("tenant", "write")),
) -> BatchOperationResponse:
    return BatchOperationResponse(
        results=[
            await _run_batch_item(request, agent_id, "start")
            for agent_id in _batch_agent_ids(body)
        ],
    )


@router.post("/tenants/batch/stop", response_model=BatchOperationResponse)
async def batch_stop(
    request: Request,
    body: BatchTenantRequest,
    _ctx=Depends(require_permission("tenant", "write")),
) -> BatchOperationResponse:
    return BatchOperationResponse(
        results=[
            await _run_batch_item(request, agent_id, "stop")
            for agent_id in _batch_agent_ids(body)
        ],
    )


@router.post("/tenants/batch/restart", response_model=BatchOperationResponse)
async def batch_restart(
    request: Request,
    body: BatchTenantRequest,
    _ctx=Depends(require_permission("tenant", "write")),
) -> BatchOperationResponse:
    return BatchOperationResponse(
        results=[
            await _run_batch_item(request, agent_id, "restart")
            for agent_id in _batch_agent_ids(body)
        ],
    )


@router.get("/tenants/{agent_id}/files", response_model=FileListResponse)
async def list_workspace_files(
    agent_id: str,
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> FileListResponse:
    return _list_safe_files(require_workspace(agent_id))


@router.get("/tenants/{agent_id}/files/{filename:path}", response_model=FileContentResponse)
async def get_workspace_file(
    agent_id: str,
    filename: str,
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> FileContentResponse:
    workspace_dir = require_workspace(agent_id)
    safe_name = _safe_filename(filename)
    path = workspace_dir / safe_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"File '{safe_name}' not found")
    return FileContentResponse(
        filename=safe_name,
        content=path.read_text(encoding="utf-8"),
    )


@router.put("/tenants/{agent_id}/files/{filename:path}", response_model=FileContentResponse)
async def put_workspace_file(
    request: Request,
    agent_id: str,
    filename: str,
    body: FileContentRequest,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> FileContentResponse:
    workspace_dir = require_workspace(agent_id)
    safe_name = _safe_filename(filename)
    path = workspace_dir / safe_name
    path.write_text(body.content, encoding="utf-8")
    maybe_reload(request, agent_id)
    await _emit_tenant_updated(
        request,
        agent_id,
        "put_workspace_file",
        resource_type="tenant_file",
        resource_id=f"{agent_id}:files:{safe_name}",
    )
    return FileContentResponse(filename=safe_name, content=body.content)


@router.get("/tenants/{agent_id}/memory", response_model=FileListResponse)
async def list_memory_files(
    agent_id: str,
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> FileListResponse:
    return _list_safe_files(require_workspace(agent_id) / "memory")


@router.get("/tenants/{agent_id}/memory/{filename:path}", response_model=FileContentResponse)
async def get_memory_file(
    agent_id: str,
    filename: str,
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> FileContentResponse:
    memory_dir = require_workspace(agent_id) / "memory"
    safe_name = _safe_filename(filename)
    path = memory_dir / safe_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"File '{safe_name}' not found")
    return FileContentResponse(
        filename=safe_name,
        content=path.read_text(encoding="utf-8"),
    )


@router.put("/tenants/{agent_id}/memory/{filename:path}", response_model=FileContentResponse)
async def put_memory_file(
    request: Request,
    agent_id: str,
    filename: str,
    body: FileContentRequest,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> FileContentResponse:
    memory_dir = require_workspace(agent_id) / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(filename)
    path = memory_dir / safe_name
    path.write_text(body.content, encoding="utf-8")
    maybe_reload(request, agent_id)
    await _emit_tenant_updated(
        request,
        agent_id,
        "put_memory_file",
        resource_type="tenant_memory",
        resource_id=f"{agent_id}:memory:{safe_name}",
    )
    return FileContentResponse(filename=safe_name, content=body.content)


@router.delete("/tenants/{agent_id}/memory/{filename:path}", response_model=MessageResponse)
async def delete_memory_file(
    request: Request,
    agent_id: str,
    filename: str,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> MessageResponse:
    memory_dir = require_workspace(agent_id) / "memory"
    safe_name = _safe_filename(filename)
    path = memory_dir / safe_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"File '{safe_name}' not found")
    path.unlink()
    maybe_reload(request, agent_id)
    await _emit_tenant_updated(
        request,
        agent_id,
        "delete_memory_file",
        resource_type="tenant_memory",
        resource_id=f"{agent_id}:memory:{safe_name}",
    )
    return MessageResponse(message=f"File '{safe_name}' deleted successfully")


@router.get("/tenants/{agent_id}/export")
async def export_tenant_workspace(
    agent_id: str,
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> FileResponse:
    workspace_dir = require_workspace(agent_id)
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()
    with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in workspace_dir.rglob("*"):
            if path.is_file() and not path.name.endswith(".tmp"):
                archive.write(path, path.relative_to(workspace_dir).as_posix())
    return FileResponse(
        tmp_path,
        media_type="application/zip",
        filename=f"{agent_id}.zip",
    )


@router.post("/tenants/{agent_id}/import", response_model=MessageResponse)
async def import_tenant_workspace(
    request: Request,
    agent_id: str,
    file: UploadFile = File(...),
    overwrite: bool = Query(False),
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> MessageResponse:
    workspace_dir = require_workspace(agent_id)
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        with zipfile.ZipFile(tmp_path) as archive:
            for member in archive.infolist():
                rel = _safe_zip_member(member.filename)
                target = workspace_dir / rel
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if target.exists() and not overwrite:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, target.open("wb") as dest:
                    shutil.copyfileobj(source, dest)
    finally:
        tmp_path.unlink(missing_ok=True)
    maybe_reload(request, agent_id)
    await _emit_tenant_updated(
        request,
        agent_id,
        "import_workspace",
        resource_type="tenant_workspace",
        resource_id=f"{agent_id}:import",
        payload={"overwrite": overwrite},
    )
    return MessageResponse(message=f"Tenant '{agent_id}' imported successfully")


@router.get("/tenants/{agent_id}/cron", response_model=list[CronJobSpec])
async def list_cron_jobs(
    request: Request,
    agent_id: str,
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> list[CronJobSpec]:
    require_workspace(agent_id)
    mgr = _running_cron_manager(request, agent_id)
    if mgr is not None:
        return await mgr.list_jobs()
    return await _job_repo(agent_id).list_jobs()


@router.post("/tenants/{agent_id}/cron", response_model=CronJobSpec)
async def create_cron_job(
    request: Request,
    agent_id: str,
    body: CronJobSpec,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> CronJobSpec:
    require_workspace(agent_id)
    created = body.model_copy(update={"id": str(uuid.uuid4())})
    await _upsert_job(request, agent_id, created)
    await _emit_tenant_updated(
        request,
        agent_id,
        "create_cron_job",
        resource_type="tenant_cron",
        resource_id=f"{agent_id}:cron:{created.id}",
    )
    return created


@router.put("/tenants/{agent_id}/cron/{job_id}", response_model=CronJobSpec)
async def update_cron_job(
    request: Request,
    agent_id: str,
    job_id: str,
    body: CronJobSpec,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> CronJobSpec:
    require_workspace(agent_id)
    if body.id is None:
        body.id = job_id
    elif body.id != job_id:
        raise HTTPException(status_code=400, detail="job_id mismatch")
    await _upsert_job(request, agent_id, body)
    await _emit_tenant_updated(
        request,
        agent_id,
        "update_cron_job",
        resource_type="tenant_cron",
        resource_id=f"{agent_id}:cron:{job_id}",
    )
    return body


@router.delete("/tenants/{agent_id}/cron/{job_id}")
async def delete_cron_job(
    request: Request,
    agent_id: str,
    job_id: str,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
):
    require_workspace(agent_id)
    mgr = _running_cron_manager(request, agent_id)
    deleted = (
        await mgr.delete_job(job_id)
        if mgr is not None
        else await _job_repo(agent_id).delete_job(job_id)
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="job not found")
    await _emit_tenant_updated(
        request,
        agent_id,
        "delete_cron_job",
        resource_type="tenant_cron",
        resource_id=f"{agent_id}:cron:{job_id}",
    )
    return {"deleted": True}


@router.post("/tenants/{agent_id}/cron/{job_id}/pause")
async def pause_cron_job(
    request: Request,
    agent_id: str,
    job_id: str,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
):
    mgr = _running_cron_manager(request, agent_id)
    if mgr is not None:
        await mgr.pause_job(job_id)
        await _emit_tenant_updated(
            request,
            agent_id,
            "pause_cron_job",
            resource_type="tenant_cron",
            resource_id=f"{agent_id}:cron:{job_id}",
        )
        return {"paused": True}
    job = await _get_job(request, agent_id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    job.enabled = False
    await _upsert_job(request, agent_id, job)
    await _emit_tenant_updated(
        request,
        agent_id,
        "pause_cron_job",
        resource_type="tenant_cron",
        resource_id=f"{agent_id}:cron:{job_id}",
    )
    return {"paused": True}


@router.post("/tenants/{agent_id}/cron/{job_id}/resume")
async def resume_cron_job(
    request: Request,
    agent_id: str,
    job_id: str,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
):
    mgr = _running_cron_manager(request, agent_id)
    if mgr is not None:
        await mgr.resume_job(job_id)
        await _emit_tenant_updated(
            request,
            agent_id,
            "resume_cron_job",
            resource_type="tenant_cron",
            resource_id=f"{agent_id}:cron:{job_id}",
        )
        return {"resumed": True}
    job = await _get_job(request, agent_id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    job.enabled = True
    await _upsert_job(request, agent_id, job)
    await _emit_tenant_updated(
        request,
        agent_id,
        "resume_cron_job",
        resource_type="tenant_cron",
        resource_id=f"{agent_id}:cron:{job_id}",
    )
    return {"resumed": True}


@router.post("/tenants/{agent_id}/cron/{job_id}/run")
async def run_cron_job(
    request: Request,
    agent_id: str,
    job_id: str,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
):
    mgr = _running_cron_manager(request, agent_id)
    if mgr is None:
        raise HTTPException(status_code=409, detail="Tenant is not running")
    await mgr.run_job(job_id)
    await _emit_tenant_updated(
        request,
        agent_id,
        "run_cron_job",
        resource_type="tenant_cron",
        resource_id=f"{agent_id}:cron:{job_id}",
    )
    return {"started": True}


@router.get("/tenants/{agent_id}/health", response_model=TenantHealthResponse)
async def get_tenant_health(
    request: Request,
    agent_id: str,
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> TenantHealthResponse:
    return await _tenant_health(request, agent_id)


@router.get("/health", response_model=AllTenantHealthResponse)
async def get_all_tenant_health(
    request: Request,
    _ctx=Depends(require_permission("tenant", "read")),
) -> AllTenantHealthResponse:
    agent_ids = _list_workspace_agent_ids()
    if "platform_admin" not in _ctx.roles:
        if not _ctx.tenant_id:
            raise HTTPException(
                status_code=403,
                detail="Tenant-scoped access requires tenant context.",
            )
        from ....tenancy.ids import tenant_agent_id

        agent_ids = [tenant_agent_id(_ctx.tenant_id)]
    return AllTenantHealthResponse(
        tenants=[
            await _tenant_health(request, agent_id)
            for agent_id in agent_ids
        ],
    )


@router.post("/tenants/{agent_id}/reload", response_model=MessageResponse)
async def reload_tenant(
    request: Request,
    agent_id: str,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> MessageResponse:
    require_workspace(agent_id)
    manager = get_manager(request)
    if not manager.is_agent_loaded(agent_id):
        raise HTTPException(status_code=409, detail="Tenant is not running")
    schedule_agent_reload(request, agent_id)
    await _emit_tenant_updated(
        request,
        agent_id,
        "reload_tenant",
        resource_type="tenant_runtime",
        resource_id=f"{agent_id}:reload",
    )
    return MessageResponse(message="Reload scheduled")
