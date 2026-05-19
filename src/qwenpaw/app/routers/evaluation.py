"""企业化验收测评 API 路由。

提供测评集 CRUD、执行记录管理、准确率报告和 Bad Case 转测评题能力。
所有操作均按 tenant_id 做租户边界校验。

产品契约：
  - 测评是纯租户能力，所有操作必须指定租户
  - 非 platform_admin 必须通过租户路径操作
  - platform_admin 也必须选择租户后操作（不存在全局测评集）
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ...enterprise.authz.deps import get_request_context, require_permission
from ...enterprise.audit.models import AuditEventType, AuditOutcome
from ...enterprise.evaluation.executor import (
    bad_case_to_eval_item,
    compute_accuracy,
    create_sample_dataset,
)
from ...enterprise.evaluation.models import (
    AccuracyReport,
    AcceptanceEvidenceExport,
    BadCaseToEvalRequest,
    BadCaseToEvalResult,
    EvalDataset,
    EvalExecution,
    EvalExecutionItem,
    EvalItem,
)
from ...enterprise.evaluation.store import (
    delete_dataset,
    get_dataset,
    get_execution,
    list_datasets,
    list_executions,
    save_dataset,
    save_execution,
)
from ..routers.wecom_tenant_config.common import (
    emit_tenant_audit_event,
    require_tenant_boundary,
    tenant_id_from_agent_id,
    validate_agent_id,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


# ── 租户边界辅助 ──────────────────────────────────────


def _require_tenant_id(request: Request) -> str:
    """从请求上下文解析 tenant_id，空则 400。

    测评是纯租户能力，不存在全局测评集。
    platform_admin 也必须选择租户后操作。
    """
    ctx = get_request_context(request)
    tenant_id = getattr(ctx, "tenant_id", "") or ""
    if not tenant_id:
        raise HTTPException(
            status_code=400,
            detail="Evaluation requires tenant context. Specify a tenant to operate on.",
        )
    return tenant_id


# ── 请求/响应模型 ──────────────────────────────────────


class CreateDatasetRequest(BaseModel):
    name: str
    description: str = ""
    items: list[EvalItem] = []


class UpdateDatasetRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    items: Optional[list[EvalItem]] = None


class AddItemRequest(BaseModel):
    items: list[EvalItem]


class CreateExecutionRequest(BaseModel):
    dataset_id: str
    items: list[EvalExecutionItem]


class DatasetListResponse(BaseModel):
    items: list[EvalDataset]
    total: int


class ExecutionListResponse(BaseModel):
    items: list[EvalExecution]
    total: int


def _tenant_id_from_agent_path(agent_id: str) -> str:
    validate_agent_id(agent_id)
    return tenant_id_from_agent_id(agent_id)


def _agent_id_from_tenant_id(tenant_id: str) -> str:
    from ...tenancy.ids import tenant_agent_id

    if str(tenant_id).startswith("wx_"):
        return str(tenant_id)
    return tenant_agent_id(tenant_id)


async def _emit_evaluation_audit(
    request: Request,
    *,
    agent_id: str,
    action: str,
    resource_kind: str,
    resource_id: str,
    payload: dict | None = None,
) -> None:
    await emit_tenant_audit_event(
        request,
        agent_id,
        AuditEventType.TENANT_UPDATED,
        action,
        AuditOutcome.SUCCESS,
        resource_type=f"evaluation_{resource_kind}",
        resource_id=f"{agent_id}:evaluation:{resource_kind}:{resource_id}",
        payload={"agent_id": agent_id, **(payload or {})},
    )


def _get_dataset_or_404(dataset_id: str, tenant_id: str) -> EvalDataset:
    try:
        dataset = get_dataset(dataset_id, tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


def _get_execution_or_404(execution_id: str, tenant_id: str) -> EvalExecution:
    try:
        execution = get_execution(execution_id, tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


def _delete_dataset_or_404(dataset_id: str, tenant_id: str) -> None:
    try:
        deleted = delete_dataset(dataset_id, tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")


# ── 测评集 CRUD ────────────────────────────────────────


@router.get("/datasets", response_model=DatasetListResponse)
async def api_list_datasets(
    request: Request,
    _ctx=Depends(require_permission("tenant", "read")),
) -> DatasetListResponse:
    """列出当前租户的测评集。"""
    tenant_id = _require_tenant_id(request)
    datasets = list_datasets(tenant_id)
    return DatasetListResponse(items=datasets, total=len(datasets))


@router.post("/datasets", response_model=EvalDataset, status_code=201)
async def api_create_dataset(
    body: CreateDatasetRequest,
    request: Request,
    _ctx=Depends(require_permission("tenant", "write")),
) -> EvalDataset:
    """创建测评集。自动绑定当前租户。"""
    tenant_id = _require_tenant_id(request)
    dataset = EvalDataset(
        tenant_id=tenant_id,
        name=body.name,
        description=body.description,
        items=body.items,
    )
    saved = save_dataset(dataset)
    await _emit_evaluation_audit(
        request,
        agent_id=_agent_id_from_tenant_id(tenant_id),
        action="create_eval_dataset",
        resource_kind="dataset",
        resource_id=saved.id,
        payload={"tenant_id": tenant_id, "name": saved.name},
    )
    return saved


@router.get("/datasets/sample", response_model=EvalDataset)
async def api_get_sample_dataset(
    _ctx=Depends(require_permission("tenant", "read")),
) -> EvalDataset:
    """获取样例测评集模板（不持久化，不绑定租户）。"""
    return create_sample_dataset()


@router.get("/datasets/{dataset_id}", response_model=EvalDataset)
async def api_get_dataset(
    dataset_id: str,
    request: Request,
    _ctx=Depends(require_permission("tenant", "read")),
) -> EvalDataset:
    """获取当前租户的单个测评集。"""
    tenant_id = _require_tenant_id(request)
    dataset = get_dataset(dataset_id, tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.patch("/datasets/{dataset_id}", response_model=EvalDataset)
async def api_update_dataset(
    dataset_id: str,
    body: UpdateDatasetRequest,
    request: Request,
    _ctx=Depends(require_permission("tenant", "write")),
) -> EvalDataset:
    """更新当前租户的测评集。"""
    tenant_id = _require_tenant_id(request)
    dataset = get_dataset(dataset_id, tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.description is not None:
        updates["description"] = body.description
    if body.items is not None:
        updates["items"] = body.items

    if updates:
        dataset = dataset.model_copy(update=updates)
        from datetime import datetime, timezone

        dataset.updated_at = datetime.now(timezone.utc)

    saved = save_dataset(dataset)
    await _emit_evaluation_audit(
        request,
        agent_id=_agent_id_from_tenant_id(tenant_id),
        action="update_eval_dataset",
        resource_kind="dataset",
        resource_id=saved.id,
        payload={"tenant_id": tenant_id, "changed_keys": sorted(updates)},
    )
    return saved


@router.post("/datasets/{dataset_id}/items", response_model=EvalDataset)
async def api_add_dataset_items(
    dataset_id: str,
    body: AddItemRequest,
    request: Request,
    _ctx=Depends(require_permission("tenant", "write")),
) -> EvalDataset:
    """向当前租户的测评集追加题目。"""
    tenant_id = _require_tenant_id(request)
    dataset = get_dataset(dataset_id, tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    existing_ids = {item.case_id for item in dataset.items}
    new_items = [i for i in body.items if i.case_id not in existing_ids]
    dataset.items.extend(new_items)

    from datetime import datetime, timezone

    dataset.updated_at = datetime.now(timezone.utc)
    saved = save_dataset(dataset)
    await _emit_evaluation_audit(
        request,
        agent_id=_agent_id_from_tenant_id(tenant_id),
        action="add_eval_dataset_items",
        resource_kind="dataset",
        resource_id=saved.id,
        payload={"tenant_id": tenant_id, "added_count": len(new_items)},
    )
    return saved


@router.delete("/datasets/{dataset_id}", status_code=204)
async def api_delete_dataset(
    dataset_id: str,
    request: Request,
    _ctx=Depends(require_permission("tenant", "write")),
) -> None:
    """删除当前租户的测评集。"""
    tenant_id = _require_tenant_id(request)
    if not delete_dataset(dataset_id, tenant_id):
        raise HTTPException(status_code=404, detail="Dataset not found")
    await _emit_evaluation_audit(
        request,
        agent_id=_agent_id_from_tenant_id(tenant_id),
        action="delete_eval_dataset",
        resource_kind="dataset",
        resource_id=dataset_id,
        payload={"tenant_id": tenant_id},
    )


# ── 执行记录 ──────────────────────────────────────────


@router.get("/executions", response_model=ExecutionListResponse)
async def api_list_executions(
    request: Request,
    dataset_id: Optional[str] = None,
    _ctx=Depends(require_permission("tenant", "read")),
) -> ExecutionListResponse:
    """列出当前租户的执行记录，可按 dataset_id 过滤。"""
    tenant_id = _require_tenant_id(request)
    executions = list_executions(tenant_id, dataset_id=dataset_id)
    return ExecutionListResponse(items=executions, total=len(executions))


@router.post("/executions", response_model=EvalExecution, status_code=201)
async def api_create_execution(
    body: CreateExecutionRequest,
    request: Request,
    _ctx=Depends(require_permission("tenant", "write")),
) -> EvalExecution:
    """创建执行记录。自动绑定当前租户。"""
    tenant_id = _require_tenant_id(request)
    dataset = get_dataset(body.dataset_id, tenant_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    execution = EvalExecution(
        tenant_id=tenant_id,
        dataset_id=body.dataset_id,
        items=body.items,
    )
    saved = save_execution(execution)
    await _emit_evaluation_audit(
        request,
        agent_id=_agent_id_from_tenant_id(tenant_id),
        action="create_eval_execution",
        resource_kind="execution",
        resource_id=saved.id,
        payload={"tenant_id": tenant_id, "dataset_id": body.dataset_id},
    )
    return saved


@router.get("/executions/{execution_id}", response_model=EvalExecution)
async def api_get_execution(
    execution_id: str,
    request: Request,
    _ctx=Depends(require_permission("tenant", "read")),
) -> EvalExecution:
    """获取当前租户的单条执行记录。"""
    tenant_id = _require_tenant_id(request)
    execution = get_execution(execution_id, tenant_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


# ── 准确率报告 ────────────────────────────────────────


@router.get("/executions/{execution_id}/report", response_model=AccuracyReport)
async def api_get_accuracy_report(
    execution_id: str,
    request: Request,
    _ctx=Depends(require_permission("tenant", "read")),
) -> AccuracyReport:
    """从当前租户的执行记录生成准确率报告。"""
    tenant_id = _require_tenant_id(request)
    execution = get_execution(execution_id, tenant_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return compute_accuracy(execution)


# ── 租户路径别名 ───────────────────────────────────────


@router.get("/tenants/{agent_id}/datasets", response_model=DatasetListResponse)
async def api_list_tenant_datasets(
    agent_id: str,
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> DatasetListResponse:
    """按租户 agent 路径列出测评集。"""
    tenant_id = _tenant_id_from_agent_path(agent_id)
    datasets = list_datasets(tenant_id)
    return DatasetListResponse(items=datasets, total=len(datasets))


@router.post("/tenants/{agent_id}/datasets", response_model=EvalDataset, status_code=201)
async def api_create_tenant_dataset(
    agent_id: str,
    body: CreateDatasetRequest,
    request: Request,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> EvalDataset:
    """按租户 agent 路径创建测评集。"""
    tenant_id = _tenant_id_from_agent_path(agent_id)
    dataset = EvalDataset(
        tenant_id=tenant_id,
        name=body.name,
        description=body.description,
        items=body.items,
    )
    saved = save_dataset(dataset)
    await _emit_evaluation_audit(
        request,
        agent_id=agent_id,
        action="create_eval_dataset",
        resource_kind="dataset",
        resource_id=saved.id,
        payload={"tenant_id": tenant_id, "name": saved.name},
    )
    return saved


@router.get("/tenants/{agent_id}/datasets/{dataset_id}", response_model=EvalDataset)
async def api_get_tenant_dataset(
    agent_id: str,
    dataset_id: str,
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> EvalDataset:
    """按租户 agent 路径获取单个测评集。"""
    tenant_id = _tenant_id_from_agent_path(agent_id)
    return _get_dataset_or_404(dataset_id, tenant_id)


@router.patch("/tenants/{agent_id}/datasets/{dataset_id}", response_model=EvalDataset)
async def api_update_tenant_dataset(
    agent_id: str,
    dataset_id: str,
    body: UpdateDatasetRequest,
    request: Request,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> EvalDataset:
    """按租户 agent 路径更新测评集。"""
    tenant_id = _tenant_id_from_agent_path(agent_id)
    dataset = _get_dataset_or_404(dataset_id, tenant_id)

    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.description is not None:
        updates["description"] = body.description
    if body.items is not None:
        updates["items"] = body.items

    if updates:
        dataset = dataset.model_copy(update=updates)
        from datetime import datetime, timezone

        dataset.updated_at = datetime.now(timezone.utc)

    saved = save_dataset(dataset)
    await _emit_evaluation_audit(
        request,
        agent_id=agent_id,
        action="update_eval_dataset",
        resource_kind="dataset",
        resource_id=saved.id,
        payload={"tenant_id": tenant_id, "changed_keys": sorted(updates)},
    )
    return saved


@router.post("/tenants/{agent_id}/datasets/{dataset_id}/items", response_model=EvalDataset)
async def api_add_tenant_dataset_items(
    agent_id: str,
    dataset_id: str,
    body: AddItemRequest,
    request: Request,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> EvalDataset:
    """按租户 agent 路径向测评集追加题目。"""
    tenant_id = _tenant_id_from_agent_path(agent_id)
    dataset = _get_dataset_or_404(dataset_id, tenant_id)

    existing_ids = {item.case_id for item in dataset.items}
    new_items = [item for item in body.items if item.case_id not in existing_ids]
    dataset.items.extend(new_items)

    from datetime import datetime, timezone

    dataset.updated_at = datetime.now(timezone.utc)
    saved = save_dataset(dataset)
    await _emit_evaluation_audit(
        request,
        agent_id=agent_id,
        action="add_eval_dataset_items",
        resource_kind="dataset",
        resource_id=saved.id,
        payload={"tenant_id": tenant_id, "added_count": len(new_items)},
    )
    return saved


@router.delete("/tenants/{agent_id}/datasets/{dataset_id}", status_code=204)
async def api_delete_tenant_dataset(
    agent_id: str,
    dataset_id: str,
    request: Request,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> None:
    """按租户 agent 路径删除测评集。"""
    tenant_id = _tenant_id_from_agent_path(agent_id)
    _delete_dataset_or_404(dataset_id, tenant_id)
    await _emit_evaluation_audit(
        request,
        agent_id=agent_id,
        action="delete_eval_dataset",
        resource_kind="dataset",
        resource_id=dataset_id,
        payload={"tenant_id": tenant_id},
    )


@router.get("/tenants/{agent_id}/executions", response_model=ExecutionListResponse)
async def api_list_tenant_executions(
    agent_id: str,
    dataset_id: Optional[str] = Query(default=None),
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> ExecutionListResponse:
    """按租户 agent 路径列出执行记录。"""
    tenant_id = _tenant_id_from_agent_path(agent_id)
    executions = list_executions(tenant_id, dataset_id=dataset_id)
    return ExecutionListResponse(items=executions, total=len(executions))


@router.post("/tenants/{agent_id}/executions", response_model=EvalExecution, status_code=201)
async def api_create_tenant_execution(
    agent_id: str,
    body: CreateExecutionRequest,
    request: Request,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> EvalExecution:
    """按租户 agent 路径创建执行记录。"""
    tenant_id = _tenant_id_from_agent_path(agent_id)
    _get_dataset_or_404(body.dataset_id, tenant_id)

    execution = EvalExecution(
        tenant_id=tenant_id,
        dataset_id=body.dataset_id,
        items=body.items,
    )
    saved = save_execution(execution)
    await _emit_evaluation_audit(
        request,
        agent_id=agent_id,
        action="create_eval_execution",
        resource_kind="execution",
        resource_id=saved.id,
        payload={"tenant_id": tenant_id, "dataset_id": body.dataset_id},
    )
    return saved


@router.get("/tenants/{agent_id}/executions/{execution_id}", response_model=EvalExecution)
async def api_get_tenant_execution(
    agent_id: str,
    execution_id: str,
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> EvalExecution:
    """按租户 agent 路径获取单条执行记录。"""
    tenant_id = _tenant_id_from_agent_path(agent_id)
    return _get_execution_or_404(execution_id, tenant_id)


@router.get(
    "/tenants/{agent_id}/executions/{execution_id}/report",
    response_model=AccuracyReport,
)
async def api_get_tenant_accuracy_report(
    agent_id: str,
    execution_id: str,
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> AccuracyReport:
    """按租户 agent 路径生成准确率报告。"""
    tenant_id = _tenant_id_from_agent_path(agent_id)
    execution = _get_execution_or_404(execution_id, tenant_id)
    return compute_accuracy(execution)


@router.get(
    "/tenants/{agent_id}/executions/{execution_id}/evidence",
    response_model=AcceptanceEvidenceExport,
)
async def api_export_tenant_acceptance_evidence(
    agent_id: str,
    execution_id: str,
    request: Request,
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> AcceptanceEvidenceExport:
    """按租户导出验收证据 JSON，并记录审计事件。"""
    tenant_id = _tenant_id_from_agent_path(agent_id)
    execution = _get_execution_or_404(execution_id, tenant_id)
    dataset = _get_dataset_or_404(execution.dataset_id, tenant_id)
    report = compute_accuracy(execution)
    evidence = AcceptanceEvidenceExport(
        tenant_id=tenant_id,
        agent_id=agent_id,
        dataset=dataset,
        execution=execution,
        report=report,
    )
    await _emit_evaluation_audit(
        request,
        agent_id=agent_id,
        action="export_acceptance_evidence",
        resource_kind="evidence",
        resource_id=execution.id,
        payload={
            "tenant_id": tenant_id,
            "dataset_id": dataset.id,
            "execution_id": execution.id,
            "evidence_version": evidence.evidence_version,
        },
    )
    return evidence


# ── Bad Case 转测评题 ─────────────────────────────────


@router.post(
    "/tenants/{agent_id}/bad-case-to-eval",
    response_model=BadCaseToEvalResult,
)
async def api_bad_case_to_eval(
    agent_id: str,
    body: BadCaseToEvalRequest,
    request: Request,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> BadCaseToEvalResult:
    """将指定租户的 Bad Case 转换为测评题。

    路径参数 agent_id 确定租户边界，复用 require_tenant_boundary 校验。
    从审计仓库读取该租户的 Bad Case 事件，转换为测评题目并加入测评集。
    """
    from ..routers.wecom_tenant_config.common import audit_repository_from_request
    from ..routers.wecom_tenant_config.ops_insights import _aggregate_bad_cases

    validate_agent_id(agent_id)
    # agent_id 是 wx_* 格式，从中推导 tenant_id
    tenant_id = tenant_id_from_agent_id(agent_id)

    audit_repo = audit_repository_from_request(request)
    if audit_repo is None:
        raise HTTPException(
            status_code=503,
            detail="Audit service unavailable",
        )

    # 按 agent_id 查询该租户的 Bad Case 事件
    bad_case_types = ("bad_case.marked", "bad_case.updated")
    try:
        rows = await audit_repo.query(
            event_types=bad_case_types,
            tenant_id=tenant_id,
            agent_id=agent_id,
            limit=10000,
        )
    except Exception:
        logger.exception("查询 Bad Case 事件失败")
        raise HTTPException(
            status_code=503,
            detail="Failed to query audit events",
        )

    all_cases = _aggregate_bad_cases(rows)

    # 按请求的 case_ids 筛选
    requested_ids = set(body.case_ids)
    matched_cases = [c for c in all_cases if c.case_id in requested_ids]

    # 转换为测评题
    eval_items: list[EvalItem] = []
    for case in matched_cases:
        question = (
            f"[Bad Case {case.case_id}] "
            f"{case.ability_name or '未知能力'} "
            f"调用失败: {case.note or case.category}"
        )
        item = bad_case_to_eval_item(
            case_id=case.case_id,
            question=question,
            ability_name=case.ability_name,
            category=case.category,
            entrypoint=case.entrypoint,
        )
        eval_items.append(item)

    # 创建或追加到该租户的测评集
    dataset: Optional[EvalDataset] = None
    if body.dataset_id:
        dataset = get_dataset(body.dataset_id, tenant_id)
        if dataset is None:
            raise HTTPException(
                status_code=404,
                detail=f"Dataset '{body.dataset_id}' not found",
            )
    elif not body.dataset_name:
        raise HTTPException(
            status_code=400,
            detail="Either dataset_id or dataset_name is required",
        )

    if dataset is None and body.dataset_name:
        dataset = EvalDataset(
            tenant_id=tenant_id,
            name=body.dataset_name,
            description="从 Bad Case 转换生成的测评集",
        )

    existing_ids = {item.case_id for item in dataset.items}
    new_items = [i for i in eval_items if i.case_id not in existing_ids]
    dataset.items.extend(new_items)
    from datetime import datetime, timezone

    dataset.updated_at = datetime.now(timezone.utc)
    save_dataset(dataset)

    # skipped = 未找到的 case_id + 已存在被去重的 case
    not_found = len(requested_ids) - len(matched_cases)
    duplicate = len(eval_items) - len(new_items)
    skipped = not_found + duplicate

    return BadCaseToEvalResult(
        dataset_id=dataset.id if dataset else "",
        converted=len(new_items),
        skipped=skipped,
        items=eval_items,
    )
