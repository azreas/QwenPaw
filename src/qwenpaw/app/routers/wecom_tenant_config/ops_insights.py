# -*- coding: utf-8 -*-
"""Ops insights endpoints for WeCom tenant workspaces (P3-4)."""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ....enterprise.audit.models import AuditEventType, AuditOutcome
from ....enterprise.authz.deps import get_request_context, require_permission
from .common import (
    audit_repository_from_request,
    emit_tenant_audit_event,
    get_manager,
    require_tenant_boundary,
    tenants_root,
    validate_agent_id,
)
from .ops_schemas import (
    AbilityFailureSummary,
    BadCaseCreateRequest,
    BadCaseItem,
    BadCaseListResponse,
    BadCaseUpdateRequest,
    BusinessTraceListResponse,
    BusinessTraceItem,
    OpsOverviewResponse,
    TenantOpsSummaryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_BUSINESS_EVENT_TYPES = ("skill.called", "mcp.called")
_BAD_CASE_EVENT_TYPES = ("bad_case.marked", "bad_case.updated")


def _get_audit_repo(request: Request) -> Any | None:
    """从 enterprise_runtime 获取 AuditRepository，无则返回 None。"""
    return audit_repository_from_request(request)


def _row_to_trace_item(row: Any) -> BusinessTraceItem:
    """将审计行转为 BusinessTraceItem。"""
    payload = getattr(row, "payload", {}) or {}
    created_at = getattr(row, "created_at", None)
    created_at_str = ""
    if created_at is not None:
        if hasattr(created_at, "isoformat"):
            created_at_str = created_at.isoformat()
        else:
            created_at_str = str(created_at)

    return BusinessTraceItem(
        id=getattr(row, "id", ""),
        tenant_id=getattr(row, "tenant_id", ""),
        agent_id=getattr(row, "agent_id", "") or payload.get("agent_id", ""),
        session_id=getattr(row, "session_id", ""),
        actor_id=getattr(row, "actor_id", ""),
        entrypoint=payload.get("entrypoint", ""),
        ability_type=payload.get("ability_type", ""),
        ability_name=payload.get("ability_name") or getattr(row, "resource_id", ""),
        duration_ms=payload.get("duration_ms") or 0,
        status=payload.get("status") or getattr(row, "outcome", ""),
        error_reason=payload.get("error_reason", ""),
        request_id=getattr(row, "request_id", ""),
        trace_id=getattr(row, "trace_id", ""),
        created_at=created_at_str,
    )


def _bounded_limit(limit: int) -> int:
    return max(1, min(limit, 1000))


def _trace_matches(
    row: Any,
    *,
    ability_type: str | None,
    ability_name: str | None,
    entrypoint: str | None,
    status: str | None,
    error_reason: str | None,
) -> bool:
    payload = getattr(row, "payload", {}) or {}
    row_ability_type = payload.get("ability_type") or getattr(row, "resource_type", "")
    row_ability_name = payload.get("ability_name") or getattr(row, "resource_id", "")
    row_status = payload.get("status") or getattr(row, "outcome", "")
    if ability_type and row_ability_type != ability_type:
        return False
    if ability_name and row_ability_name != ability_name:
        return False
    if entrypoint and payload.get("entrypoint") != entrypoint:
        return False
    if status and row_status != status:
        return False
    if error_reason and error_reason not in str(payload.get("error_reason") or ""):
        return False
    return True


async def _find_business_audit_row_by_id(
    audit_repo: Any,
    *,
    agent_id: str,
    audit_id: str,
) -> Any | None:
    """Best-effort lookup for one business audit row."""
    rows = await audit_repo.query(
        event_types=_BUSINESS_EVENT_TYPES,
        agent_id=agent_id,
        limit=1000,
    )
    for row in rows:
        if getattr(row, "id", "") == audit_id:
            return row
    return None


def _compute_overview(
    rows: list[Any],
    total_tenants: int,
    running_tenants: int,
    unhealthy_tenants: int,
) -> OpsOverviewResponse:
    """从审计行计算全局运营总览。"""
    total_calls = len(rows)
    failed_calls = 0
    entrypoint_counter: Counter[str] = Counter()
    failure_by_ability: dict[str, dict[str, Any]] = {}

    for row in rows:
        payload = getattr(row, "payload", {}) or {}
        outcome = getattr(row, "outcome", "")
        entrypoint = payload.get("entrypoint", "")
        ability_name = payload.get("ability_name", "")
        ability_type = payload.get("ability_type", "")
        error_reason = payload.get("error_reason", "")

        if entrypoint:
            entrypoint_counter[entrypoint] += 1

        if outcome == "failure":
            failed_calls += 1
            if ability_name:
                if ability_name not in failure_by_ability:
                    failure_by_ability[ability_name] = {
                        "ability_name": ability_name,
                        "ability_type": ability_type,
                        "count": 0,
                        "last_error": error_reason,
                    }
                failure_by_ability[ability_name]["count"] += 1
                if error_reason:
                    failure_by_ability[ability_name]["last_error"] = error_reason

    failure_rate = (failed_calls / total_calls) if total_calls > 0 else 0.0

    top_failed = sorted(
        failure_by_ability.values(),
        key=lambda x: x["count"],
        reverse=True,
    )[:10]

    return OpsOverviewResponse(
        total_tenants=total_tenants,
        running_tenants=running_tenants,
        unhealthy_tenants=unhealthy_tenants,
        business_calls_24h=total_calls,
        failed_calls_24h=failed_calls,
        failure_rate=round(failure_rate, 4),
        entrypoints=dict(entrypoint_counter),
        top_failed_abilities=[AbilityFailureSummary(**item) for item in top_failed],
    )


@router.get("/ops/overview", response_model=OpsOverviewResponse)
async def ops_overview(
    request: Request,
    _ctx=Depends(require_permission("tenant", "read")),
) -> OpsOverviewResponse:
    """全局运营总览。需要 tenant:read 权限。"""
    ctx = get_request_context(request)
    if "platform_admin" not in ctx.roles:
        raise HTTPException(
            status_code=403,
            detail="Only platform administrators can view global operations",
        )
    audit_repo = _get_audit_repo(request)
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=24)

    # 统计租户数量
    root = tenants_root()
    tenant_dirs = []
    if root.is_dir():
        tenant_dirs = [
            item
            for item in root.iterdir()
            if item.is_dir() and item.name.startswith("wx_")
        ]
    total_tenants = len(tenant_dirs)

    # 获取运行中/不健康数量
    manager = get_manager(request)
    running_tenants = sum(1 for d in tenant_dirs if manager.is_agent_loaded(d.name))
    unhealthy_tenants = total_tenants - running_tenants

    if audit_repo is None:
        return OpsOverviewResponse(
            total_tenants=total_tenants,
            running_tenants=running_tenants,
            unhealthy_tenants=unhealthy_tenants,
        )

    try:
        rows = await audit_repo.query(
            event_types=_BUSINESS_EVENT_TYPES,
            start_time=start_time,
            limit=10000,
        )
    except Exception:
        logger.exception("查询审计事件失败，返回空值")
        rows = []

    return _compute_overview(rows, total_tenants, running_tenants, unhealthy_tenants)


@router.get(
    "/tenants/{agent_id}/ops/summary",
    response_model=TenantOpsSummaryResponse,
)
async def tenant_ops_summary(
    agent_id: str,
    request: Request,
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> TenantOpsSummaryResponse:
    """单租户运营摘要。需要 tenant:read + 租户边界。"""
    validate_agent_id(agent_id)

    audit_repo = _get_audit_repo(request)
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=24)

    # 租户健康状态
    manager = get_manager(request)
    health_status = "unknown"
    if manager.is_agent_loaded(agent_id):
        health_status = "healthy"
    else:
        health_status = "stopped"

    if audit_repo is None:
        return TenantOpsSummaryResponse(
            tenant_id=agent_id,
            agent_id=agent_id,
            health_status=health_status,
        )

    try:
        rows = await audit_repo.query(
            event_types=_BUSINESS_EVENT_TYPES,
            agent_id=agent_id,
            start_time=start_time,
            limit=10000,
        )
    except Exception:
        logger.exception("查询租户审计事件失败，返回空值")
        rows = []

    total_calls = len(rows)
    failed_calls = sum(1 for r in rows if getattr(r, "outcome", "") == "failure")
    recent_failures = [
        _row_to_trace_item(r)
        for r in rows
        if getattr(r, "outcome", "") == "failure"
    ][:10]

    # 最近活动时间
    last_activity_at = None
    if rows:
        latest = rows[0]  # rows 已按 created_at 降序
        latest_time = getattr(latest, "created_at", None)
        if latest_time is not None and hasattr(latest_time, "isoformat"):
            last_activity_at = latest_time.isoformat()

    return TenantOpsSummaryResponse(
        tenant_id=agent_id,
        agent_id=agent_id,
        health_status=health_status,
        last_activity_at=last_activity_at,
        business_calls_24h=total_calls,
        failed_calls_24h=failed_calls,
        recent_failures=recent_failures,
    )


@router.get(
    "/tenants/{agent_id}/ops/traces",
    response_model=BusinessTraceListResponse,
)
async def tenant_business_traces(
    agent_id: str,
    request: Request,
    ability_type: str | None = None,
    ability_name: str | None = None,
    entrypoint: str | None = None,
    status: str | None = None,
    error_reason: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(100, ge=1, le=1000),
    _ctx=Depends(require_permission("audit", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> BusinessTraceListResponse:
    """单租户业务调用追踪。需要 audit:read + 租户边界。"""
    validate_agent_id(agent_id)
    if ability_type and ability_type not in ("skill", "mcp"):
        raise HTTPException(
            status_code=400,
            detail="ability_type must be skill or mcp",
        )

    audit_repo = _get_audit_repo(request)
    if audit_repo is None:
        return BusinessTraceListResponse(items=[], total=0)

    event_types = {
        "skill": ("skill.called",),
        "mcp": ("mcp.called",),
    }.get(ability_type, _BUSINESS_EVENT_TYPES)
    query_limit = _bounded_limit(limit)
    fetch_limit = (
        1000
        if any((ability_name, entrypoint, status, error_reason))
        else query_limit
    )

    try:
        rows = await audit_repo.query(
            event_types=event_types,
            agent_id=agent_id,
            start_time=start_time,
            end_time=end_time,
            limit=fetch_limit,
        )
    except Exception:
        logger.exception("查询租户业务调用追踪失败")
        return BusinessTraceListResponse(items=[], total=0)

    items = [
        _row_to_trace_item(row)
        for row in rows
        if _trace_matches(
            row,
            ability_type=ability_type,
            ability_name=ability_name,
            entrypoint=entrypoint,
            status=status,
            error_reason=error_reason,
        )
    ][:query_limit]
    return BusinessTraceListResponse(items=items, total=len(items))


# ---------- Bad Case 事件化管理 ----------


def _created_at_sort_key(row: Any) -> float:
    value = getattr(row, "created_at", None)
    if value is None:
        return 0.0
    if hasattr(value, "timestamp"):
        return float(value.timestamp())
    try:
        return float(datetime.fromisoformat(str(value)).timestamp())
    except ValueError:
        return 0.0


def _aggregate_bad_cases(rows: list[Any]) -> list[BadCaseItem]:
    """将 bad_case.marked + bad_case.updated 事件按 case_id 聚合取最新状态。"""
    cases: dict[str, BadCaseItem] = {}

    for row in sorted(rows, key=_created_at_sort_key):
        payload = getattr(row, "payload", {}) or {}
        case_id = payload.get("case_id", "")
        if not case_id:
            continue

        event_type = getattr(row, "event_type", "")
        created_at_val = getattr(row, "created_at", None)
        created_at_str = ""
        if created_at_val is not None and hasattr(created_at_val, "isoformat"):
            created_at_str = created_at_val.isoformat()

        if event_type == "bad_case.marked":
            # 创建 bad case；若已存在则跳过，防止重复标记覆盖后续更新
            if case_id in cases:
                continue
            cases[case_id] = BadCaseItem(
                case_id=case_id,
                source_audit_id=payload.get("source_audit_id", ""),
                source_request_id=payload.get("source_request_id", ""),
                source_trace_id=payload.get("source_trace_id", ""),
                category=payload.get("category", ""),
                status=payload.get("status", "open"),
                owner=payload.get("owner", ""),
                note=payload.get("note", ""),
                ability_type=payload.get("ability_type", ""),
                ability_name=payload.get("ability_name", ""),
                entrypoint=payload.get("entrypoint", ""),
                created_at=created_at_str,
                updated_at=created_at_str,
            )
        elif event_type == "bad_case.updated":
            # 更新已有 bad case
            if case_id in cases:
                existing = cases[case_id]
                update_data = payload.get("updates", {})
                if update_data.get("status") is not None:
                    existing.status = update_data["status"]
                if update_data.get("category") is not None:
                    existing.category = update_data["category"]
                if update_data.get("owner") is not None:
                    existing.owner = update_data["owner"]
                if update_data.get("note") is not None:
                    existing.note = update_data["note"]
                existing.updated_at = created_at_str
            # 如果 marked 还没到（理论上不会，但做防御）
            elif case_id not in cases:
                updates = payload.get("updates", {})
                cases[case_id] = BadCaseItem(
                    case_id=case_id,
                    source_audit_id=payload.get("source_audit_id", ""),
                    category=payload.get("category", updates.get("category", "")),
                    status=payload.get("status", updates.get("status", "open")),
                    owner=payload.get("owner", updates.get("owner", "")),
                    note=payload.get("note", updates.get("note", "")),
                    created_at=created_at_str,
                    updated_at=created_at_str,
                )

    return sorted(
        cases.values(),
        key=lambda item: item.updated_at or item.created_at,
        reverse=True,
    )


@router.get(
    "/tenants/{agent_id}/bad-cases",
    response_model=BadCaseListResponse,
)
async def list_bad_cases(
    agent_id: str,
    request: Request,
    _ctx=Depends(require_permission("audit", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> BadCaseListResponse:
    """列出 Bad Case。需要 audit:read + 租户边界。"""
    validate_agent_id(agent_id)

    audit_repo = _get_audit_repo(request)
    if audit_repo is None:
        return BadCaseListResponse(items=[], total=0)

    try:
        rows = await audit_repo.query(
            event_types=_BAD_CASE_EVENT_TYPES,
            agent_id=agent_id,
            limit=10000,
        )
    except Exception:
        logger.exception("查询 Bad Case 事件失败")
        return BadCaseListResponse(items=[], total=0)

    items = _aggregate_bad_cases(rows)
    return BadCaseListResponse(items=items, total=len(items))


@router.post(
    "/tenants/{agent_id}/bad-cases",
    response_model=BadCaseItem,
    status_code=201,
)
async def mark_bad_case(
    agent_id: str,
    body: BadCaseCreateRequest,
    request: Request,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> BadCaseItem:
    """标记 Bad Case。需要 tenant:write + 租户边界。"""
    validate_agent_id(agent_id)

    audit_repo = _get_audit_repo(request)
    if audit_repo is None:
        raise HTTPException(
            status_code=503,
            detail="Audit service unavailable",
        )

    case_id = f"case-{body.source_audit_id}"
    now = datetime.now(timezone.utc)

    # 检查是否已存在同名 Bad Case，防止重复标记
    try:
        existing = await audit_repo.query(
            event_types=("bad_case.marked",),
            agent_id=agent_id,
            resource_id=case_id,
            limit=1,
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Bad case {case_id} already exists",
            )
    except HTTPException:
        raise
    except Exception:
        logger.debug("重复标记检查失败，继续执行")

    # 从源审计事件获取额外信息（尽力获取）
    source_request_id = body.source_request_id
    source_trace_id = body.source_trace_id
    ability_type = ""
    ability_name = ""
    entrypoint = ""
    try:
        source_row = await _find_business_audit_row_by_id(
            audit_repo,
            agent_id=agent_id,
            audit_id=body.source_audit_id,
        )
        if source_row is not None:
            payload = getattr(source_row, "payload", {}) or {}
            source_request_id = source_request_id or getattr(
                source_row,
                "request_id",
                "",
            )
            source_trace_id = source_trace_id or getattr(source_row, "trace_id", "")
            ability_type = payload.get("ability_type", "")
            ability_name = payload.get("ability_name", "")
            entrypoint = payload.get("entrypoint", "")
    except Exception:
        logger.debug("查询源审计事件失败，跳过填充")

    payload = {
        "case_id": case_id,
        "source_audit_id": body.source_audit_id,
        "source_request_id": source_request_id,
        "source_trace_id": source_trace_id,
        "category": body.category,
        "status": "open",
        "owner": body.owner,
        "note": body.note,
        "ability_type": ability_type,
        "ability_name": ability_name,
        "entrypoint": entrypoint,
    }

    await emit_tenant_audit_event(
        request,
        agent_id,
        event_type=AuditEventType.BAD_CASE_MARKED,
        action="mark",
        outcome=AuditOutcome.SUCCESS,
        resource_type="bad_case",
        resource_id=case_id,
        payload=payload,
        strict=True,
    )

    return BadCaseItem(
        case_id=case_id,
        source_audit_id=body.source_audit_id,
        source_request_id=source_request_id,
        source_trace_id=source_trace_id,
        category=body.category,
        status="open",
        owner=body.owner,
        note=body.note,
        ability_type=ability_type,
        ability_name=ability_name,
        entrypoint=entrypoint,
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
    )


@router.patch(
    "/tenants/{agent_id}/bad-cases/{case_id}",
    response_model=BadCaseItem,
)
async def update_bad_case(
    agent_id: str,
    case_id: str,
    body: BadCaseUpdateRequest,
    request: Request,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> BadCaseItem:
    """更新 Bad Case。需要 tenant:write + 租户边界。"""
    validate_agent_id(agent_id)

    audit_repo = _get_audit_repo(request)
    if audit_repo is None:
        raise HTTPException(
            status_code=503,
            detail="Audit service unavailable",
        )

    # 查找原始 bad case
    try:
        rows = await audit_repo.query(
            event_types=_BAD_CASE_EVENT_TYPES,
            agent_id=agent_id,
            limit=10000,
        )
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Audit query failed",
        )

    # 聚合找到原始 bad case
    items = _aggregate_bad_cases(rows)
    target = None
    for item in items:
        if item.case_id == case_id:
            target = item
            break

    if target is None:
        raise HTTPException(status_code=404, detail=f"Bad case '{case_id}' not found")

    # 构造更新 payload
    updates: dict[str, Any] = {}
    if body.status is not None:
        updates["status"] = body.status
    if body.category is not None:
        updates["category"] = body.category
    if body.owner is not None:
        updates["owner"] = body.owner
    if body.note is not None:
        updates["note"] = body.note

    now = datetime.now(timezone.utc)

    await emit_tenant_audit_event(
        request,
        agent_id,
        event_type=AuditEventType.BAD_CASE_UPDATED,
        action="update",
        outcome=AuditOutcome.SUCCESS,
        resource_type="bad_case",
        resource_id=case_id,
        payload={
            "case_id": case_id,
            "source_audit_id": target.source_audit_id,
            "category": target.category,
            "status": target.status,
            "owner": target.owner,
            "note": target.note,
            "updates": updates,
        },
        strict=True,
    )

    # 返回更新后的状态
    if body.status is not None:
        target.status = body.status
    if body.category is not None:
        target.category = body.category
    if body.owner is not None:
        target.owner = body.owner
    if body.note is not None:
        target.note = body.note
    target.updated_at = now.isoformat()

    return target
