"""测评集和执行结果的数据模型。

测评集由数据团队提供题目和标准答案，平台侧提供模板、执行记录和报告结构。
Bad Case 可转换为测评题目，形成优化闭环。
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ── 测评集模型 ──────────────────────────────────────────


class EvalCategory(StrEnum):
    """测评题目分类。"""

    INDICATOR_QUERY = "indicator_query"
    JARGON_EXPLAIN = "jargon_explain"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    PERMISSION_BOUNDARY = "permission_boundary"
    PRODUCT_EXPERIENCE = "product_experience"


class EvalEntrypoint(StrEnum):
    """测评入口。"""

    WEBCHAT = "webchat"
    WECOM_BOT = "wecom_bot"
    BOTH = "both"


class EvalItem(BaseModel):
    """测评集单条题目。"""

    case_id: str = Field(default_factory=lambda: f"eval-{uuid4().hex[:8]}")
    category: EvalCategory
    question: str
    expected: str
    entrypoint: EvalEntrypoint = EvalEntrypoint.BOTH
    ability: str = ""
    owner: str = ""
    tags: list[str] = Field(default_factory=list)


class EvalDataset(BaseModel):
    """测评集。"""

    id: str = Field(default_factory=lambda: f"dataset-{uuid4().hex[:8]}")
    tenant_id: str = ""
    name: str
    description: str = ""
    items: list[EvalItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── 执行结果模型 ──────────────────────────────────────


class EvalResult(StrEnum):
    """单条测评结果。"""

    CORRECT = "correct"
    PARTIAL = "partial"
    WRONG = "wrong"
    BLOCKED = "blocked"


class IssueOwner(StrEnum):
    """问题归属团队。"""

    DATA_QUALITY = "data_quality"
    PLATFORM_RUNTIME = "platform_runtime"
    PERMISSION_CONFIG = "permission_config"
    PRODUCT_EXPERIENCE = "product_experience"


class EvalAction(StrEnum):
    """问题处理动作。"""

    FIX = "fix"
    TRANSFER = "transfer"
    BACKLOG = "backlog"
    CLOSE = "close"


class EvalExecutionItem(BaseModel):
    """单条测评执行记录。"""

    case_id: str
    actual: str = ""
    trace_id: str = ""
    request_id: str = ""
    result: EvalResult = EvalResult.BLOCKED
    issue_owner: Optional[IssueOwner] = None
    action: Optional[EvalAction] = None
    note: str = ""
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvalExecution(BaseModel):
    """一次测评执行。"""

    id: str = Field(default_factory=lambda: f"exec-{uuid4().hex[:8]}")
    tenant_id: str = ""
    dataset_id: str
    items: list[EvalExecutionItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── 准确率报告模型 ────────────────────────────────────


class AccuracyReport(BaseModel):
    """准确率报告。"""

    dataset_id: str
    execution_id: str
    total: int = 0
    executable: int = 0
    correct: int = 0
    partial: int = 0
    wrong: int = 0
    blocked: int = 0
    correct_rate: float = 0.0
    partial_rate: float = 0.0
    issue_distribution: dict[str, int] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AcceptanceEvidenceExport(BaseModel):
    """租户验收证据导出。"""

    tenant_id: str
    agent_id: str
    dataset: EvalDataset
    execution: EvalExecution
    report: AccuracyReport
    exported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    evidence_version: str = "1"


# ── Bad Case 转测评题模型 ─────────────────────────────


class BadCaseToEvalRequest(BaseModel):
    """Bad Case 转测评题请求。"""

    case_ids: list[str]
    dataset_id: Optional[str] = None
    dataset_name: str = ""


class BadCaseToEvalResult(BaseModel):
    """Bad Case 转测评题结果。"""

    dataset_id: str
    converted: int = 0
    skipped: int = 0
    items: list[EvalItem] = Field(default_factory=list)
