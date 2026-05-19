"""测评集和执行记录的 JSON 文件存储。

存储路径（按租户隔离）：
  <working_dir>/evaluation/<tenant_slug>/datasets/<dataset_id>.json
  <working_dir>/evaluation/<tenant_slug>/executions/<execution_id>.json

安全约束：
  - tenant_id 通过 safe_tenant_suffix() 归一化为目录名，支持下划线等合法租户 ID
  - dataset_id / execution_id 必须匹配 ^[a-z0-9-]+$ 格式
  - 所有路径 resolve() 后必须仍在目标目录内
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

from ...tenancy.ids import safe_tenant_suffix
from .models import EvalDataset, EvalExecution

logger = logging.getLogger(__name__)

_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def _eval_root() -> Path:
    """测评数据根目录。"""
    from ...constant import WORKING_DIR

    return WORKING_DIR / "evaluation"


def _tenant_slug(tenant_id: str) -> str:
    """将 tenant_id 归一化为安全的目录名片段。

    使用 tenancy.ids.safe_tenant_suffix 处理含下划线等合法租户 ID，
    含路径穿越字符的 tenant_id 会被哈希化。
    """
    return safe_tenant_suffix(tenant_id)


def _tenant_dir(tenant_id: str) -> Path:
    """租户目录。必须提供非空 tenant_id。"""
    if not tenant_id:
        raise ValueError("tenant_id is required for evaluation storage")
    return _eval_root() / _tenant_slug(tenant_id)


def _datasets_dir(tenant_id: str) -> Path:
    return _tenant_dir(tenant_id) / "datasets"


def _executions_dir(tenant_id: str) -> Path:
    return _tenant_dir(tenant_id) / "executions"


def _validate_id(value: str, field_name: str) -> None:
    """校验对象 ID 格式，防止路径穿越。仅用于 dataset_id / execution_id。"""
    if not _ID_PATTERN.match(value):
        raise ValueError(
            f"Invalid {field_name}: must match [a-z0-9][a-z0-9-]{{0,63}}, "
            f"got '{value}'"
        )


def _safe_path(base_dir: Path, object_id: str, suffix: str = ".json") -> Path:
    """构造安全文件路径，确保 resolve() 后仍在 base_dir 内。"""
    _validate_id(object_id, "id")
    candidate = (base_dir / f"{object_id}{suffix}").resolve()
    resolved_base = base_dir.resolve()
    if not str(candidate).startswith(str(resolved_base)):
        raise ValueError(f"Path traversal detected: {candidate} escapes {resolved_base}")
    return candidate


def _ensure_dirs(tenant_id: str) -> None:
    _datasets_dir(tenant_id).mkdir(parents=True, exist_ok=True)
    _executions_dir(tenant_id).mkdir(parents=True, exist_ok=True)


# ── Dataset CRUD ────────────────────────────────────────


def list_datasets(tenant_id: str) -> list[EvalDataset]:
    """列出指定租户的测评集。"""
    datasets_dir = _datasets_dir(tenant_id)
    if not datasets_dir.is_dir():
        return []
    result = []
    for f in datasets_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            dataset = EvalDataset.model_validate(data)
            if dataset.tenant_id == tenant_id:
                result.append(dataset)
        except Exception:
            logger.warning("读取测评集文件失败: %s", f)
    return sorted(result, key=lambda d: d.created_at, reverse=True)


def get_dataset(
    dataset_id: str, tenant_id: str
) -> Optional[EvalDataset]:
    """获取指定租户的单个测评集。"""
    path = _safe_path(_datasets_dir(tenant_id), dataset_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        dataset = EvalDataset.model_validate(data)
        if dataset.tenant_id != tenant_id:
            return None
        return dataset
    except Exception:
        logger.warning("读取测评集文件失败: %s", path)
        return None


def save_dataset(dataset: EvalDataset) -> EvalDataset:
    """保存测评集（创建或更新）。必须先设置 tenant_id。"""
    if not dataset.tenant_id:
        raise ValueError("Dataset tenant_id must be set before saving")
    _ensure_dirs(dataset.tenant_id)
    path = _safe_path(_datasets_dir(dataset.tenant_id), dataset.id)
    path.write_text(
        dataset.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return dataset


def delete_dataset(dataset_id: str, tenant_id: str) -> bool:
    """删除指定租户的测评集。"""
    path = _safe_path(_datasets_dir(tenant_id), dataset_id)
    if path.is_file():
        path.unlink()
        return True
    return False


# ── Execution CRUD ──────────────────────────────────────


def list_executions(
    tenant_id: str,
    dataset_id: Optional[str] = None,
) -> list[EvalExecution]:
    """列出指定租户的执行记录，可按 dataset_id 过滤。"""
    exec_dir = _executions_dir(tenant_id)
    if not exec_dir.is_dir():
        return []
    result = []
    for f in exec_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            execution = EvalExecution.model_validate(data)
            if execution.tenant_id != tenant_id:
                continue
            if dataset_id and execution.dataset_id != dataset_id:
                continue
            result.append(execution)
        except Exception:
            logger.warning("读取执行记录文件失败: %s", f)
    return sorted(result, key=lambda e: e.created_at, reverse=True)


def get_execution(
    execution_id: str, tenant_id: str
) -> Optional[EvalExecution]:
    """获取指定租户的单条执行记录。"""
    path = _safe_path(_executions_dir(tenant_id), execution_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        execution = EvalExecution.model_validate(data)
        if execution.tenant_id != tenant_id:
            return None
        return execution
    except Exception:
        logger.warning("读取执行记录文件失败: %s", path)
        return None


def save_execution(execution: EvalExecution) -> EvalExecution:
    """保存执行记录。必须先设置 tenant_id。"""
    if not execution.tenant_id:
        raise ValueError("Execution tenant_id must be set before saving")
    _ensure_dirs(execution.tenant_id)
    path = _safe_path(_executions_dir(execution.tenant_id), execution.id)
    path.write_text(
        execution.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return execution
