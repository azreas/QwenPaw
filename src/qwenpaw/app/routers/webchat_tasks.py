# -*- coding: utf-8 -*-
"""WebChat tenant-aware task APIs."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from qwenpaw.app.crons.models import (
    CronJobSpec,
    DispatchSpec,
    DispatchTarget,
    JobRuntimeSpec,
)
from qwenpaw.app.webchat.session import WebchatIdentity
from qwenpaw.app.webchat.tenant_resolver import get_tenant_workspace_for_identity
from qwenpaw.tenancy.product_models import TenantPolicy
from qwenpaw.tenancy.product_service import ensure_tenant_record, resolve_tenant_policy
from qwenpaw.tenancy.product_store import TenantProductStore

from .webchat import _get_identity_from_request
from .webchat import _webchat_error_detail

router = APIRouter(prefix="/webchat/tasks", tags=["webchat-tasks"])


class WebchatTaskListResponse(BaseModel):
    tasks: list[CronJobSpec]
    states: dict[str, dict[str, Any]]


def _reject_agent_id_query(request: Request) -> None:
    if "agent_id" in request.query_params:
        raise HTTPException(
            status_code=400,
            detail="agent_id query parameter is not allowed",
        )


def _contains_agent_id(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            key == "agent_id" or _contains_agent_id(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_agent_id(item) for item in value)
    return False


def _validate_task_body(payload: dict[str, Any]) -> CronJobSpec:
    if _contains_agent_id(payload):
        raise HTTPException(
            status_code=400,
            detail="agent_id in request body is not allowed",
        )
    return CronJobSpec.model_validate(payload)


def _resolve_policy(identity: WebchatIdentity) -> TenantPolicy:
    store = TenantProductStore()
    tenant = ensure_tenant_record(
        store,
        tenant_id=identity.tenant_id,
        agent_id=identity.agent_id,
        display_name=identity.username,
        source="webchat",
    )
    return resolve_tenant_policy(store, tenant)


async def _resolve_task_context(request: Request):
    identity = _get_identity_from_request(request)
    _reject_agent_id_query(request)
    policy = _resolve_policy(identity)
    if not policy.allow_tasks:
        raise HTTPException(
            status_code=403,
            detail=_webchat_error_detail(
                request,
                identity,
                error_code="WEBCHAT_TASKS_DISABLED",
                message="Tasks are disabled",
            ),
        )

    workspace = await get_tenant_workspace_for_identity(request, identity)
    mgr = getattr(workspace, "cron_manager", None)
    if mgr is None:
        raise HTTPException(
            status_code=500,
            detail=_webchat_error_detail(
                request,
                identity,
                error_code="WEBCHAT_CRON_MANAGER_UNAVAILABLE",
                message="CronManager not initialized",
                recoverable=True,
            ),
        )
    return identity, policy, mgr


def _webchat_target(identity: WebchatIdentity) -> DispatchTarget:
    return DispatchTarget(
        user_id=identity.wechat_company_id,
        session_id=f"webchat:{identity.wechat_company_id}:tasks",
    )


def _reject_reserved_job_id(job_id: str) -> None:
    if job_id.startswith("_"):
        raise HTTPException(
            status_code=400,
            detail="reserved job_id is not allowed",
        )


def _is_webchat_task(identity: WebchatIdentity, task: CronJobSpec) -> bool:
    target = _webchat_target(identity)
    return (
        task.id is not None
        and not task.id.startswith("_")
        and task.dispatch.channel == "webchat"
        and task.dispatch.target.user_id == target.user_id
        and task.dispatch.target.session_id == target.session_id
    )


async def _get_webchat_task_or_404(
    mgr: Any,
    identity: WebchatIdentity,
    job_id: str,
) -> CronJobSpec:
    _reject_reserved_job_id(job_id)
    task = await mgr.get_job(job_id)
    if task is None or not _is_webchat_task(identity, task):
        raise HTTPException(status_code=404, detail="job not found")
    return task


def _sanitize_task_spec(
    spec: CronJobSpec,
    *,
    identity: WebchatIdentity,
    policy: TenantPolicy,
    job_id: str | None = None,
) -> CronJobSpec:
    target = _webchat_target(identity)
    dispatch = DispatchSpec(
        type=spec.dispatch.type,
        channel="webchat",
        target=target,
        mode=spec.dispatch.mode,
        meta=spec.dispatch.meta,
    )
    runtime = JobRuntimeSpec(
        max_concurrency=1,
        timeout_seconds=policy.task_timeout_seconds,
        misfire_grace_seconds=spec.runtime.misfire_grace_seconds,
    )
    payload = spec.model_dump(mode="python")
    payload.update(
        {
            "id": job_id if job_id is not None else spec.id,
            "dispatch": dispatch.model_dump(mode="python"),
            "runtime": runtime.model_dump(mode="python"),
        },
    )
    return CronJobSpec.model_validate(payload)


@router.get("", response_model=WebchatTaskListResponse)
async def list_tasks(request: Request) -> WebchatTaskListResponse:
    identity, _, mgr = await _resolve_task_context(request)
    tasks = [
        task
        for task in await mgr.list_jobs()
        if _is_webchat_task(identity, task)
    ]
    states: dict[str, dict[str, Any]] = {}
    for task in tasks:
        if task.id is None:
            continue
        state = mgr.get_state(task.id)
        states[task.id] = (
            state.model_dump(mode="json") if hasattr(state, "model_dump") else dict(state)
        )
    return WebchatTaskListResponse(tasks=tasks, states=states)


@router.post("", response_model=CronJobSpec)
async def create_task(payload: dict[str, Any], request: Request) -> CronJobSpec:
    spec = _validate_task_body(payload)
    identity, policy, mgr = await _resolve_task_context(request)
    existing_tasks = [
        task
        for task in await mgr.list_jobs()
        if _is_webchat_task(identity, task)
    ]
    if len(existing_tasks) >= policy.max_cron_jobs:
        raise HTTPException(status_code=403, detail="Task limit exceeded")
    job_id = spec.id or str(uuid.uuid4())
    _reject_reserved_job_id(job_id)
    created = _sanitize_task_spec(
        spec,
        identity=identity,
        policy=policy,
        job_id=job_id,
    )
    await mgr.create_or_replace_job(created)
    return created


@router.put("/{job_id}", response_model=CronJobSpec)
async def update_task(
    job_id: str,
    payload: dict[str, Any],
    request: Request,
) -> CronJobSpec:
    spec = _validate_task_body(payload)
    identity, policy, mgr = await _resolve_task_context(request)
    await _get_webchat_task_or_404(mgr, identity, job_id)
    if spec.id is not None and spec.id != job_id:
        raise HTTPException(status_code=400, detail="job_id mismatch")
    updated = _sanitize_task_spec(
        spec,
        identity=identity,
        policy=policy,
        job_id=job_id,
    )
    await mgr.create_or_replace_job(updated)
    return updated


@router.delete("/{job_id}")
async def delete_task(job_id: str, request: Request) -> dict[str, bool]:
    identity, _, mgr = await _resolve_task_context(request)
    await _get_webchat_task_or_404(mgr, identity, job_id)
    deleted = await mgr.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="job not found")
    return {"deleted": True}


@router.post("/{job_id}/pause")
async def pause_task(job_id: str, request: Request) -> dict[str, bool]:
    identity, _, mgr = await _resolve_task_context(request)
    await _get_webchat_task_or_404(mgr, identity, job_id)
    await mgr.pause_job(job_id)
    return {"paused": True}


@router.post("/{job_id}/resume")
async def resume_task(job_id: str, request: Request) -> dict[str, bool]:
    identity, _, mgr = await _resolve_task_context(request)
    await _get_webchat_task_or_404(mgr, identity, job_id)
    await mgr.resume_job(job_id)
    return {"resumed": True}


@router.post("/{job_id}/run")
async def run_task(job_id: str, request: Request) -> dict[str, bool]:
    identity, policy, mgr = await _resolve_task_context(request)
    if not policy.allow_task_run_now:
        raise HTTPException(status_code=403, detail="Run now is disabled")
    await _get_webchat_task_or_404(mgr, identity, job_id)
    try:
        await mgr.run_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc
    return {"started": True}
