"""测评执行器 — 准确率计算和报告生成。

不依赖外部服务，所有计算均在内存中完成。
测评集和执行记录由调用方持久化（JSON 文件或数据库）。
"""

from __future__ import annotations

from qwenpaw.enterprise.evaluation.models import (
    AccuracyReport,
    EvalAction,
    EvalCategory,
    EvalDataset,
    EvalEntrypoint,
    EvalExecution,
    EvalExecutionItem,
    EvalItem,
    EvalResult,
    IssueOwner,
)


def compute_accuracy(execution: EvalExecution) -> AccuracyReport:
    """从执行记录计算准确率报告。

    blocked 样本不计入可执行样本数；correct_rate = correct / executable。
    """
    total = len(execution.items)
    blocked = sum(1 for i in execution.items if i.result == EvalResult.BLOCKED)
    executable = total - blocked
    correct = sum(1 for i in execution.items if i.result == EvalResult.CORRECT)
    partial = sum(1 for i in execution.items if i.result == EvalResult.PARTIAL)
    wrong = sum(1 for i in execution.items if i.result == EvalResult.WRONG)

    correct_rate = correct / executable if executable > 0 else 0.0
    partial_rate = partial / executable if executable > 0 else 0.0

    issue_distribution: dict[str, int] = {}
    for item in execution.items:
        if item.issue_owner is not None:
            key = item.issue_owner.value
            issue_distribution[key] = issue_distribution.get(key, 0) + 1

    return AccuracyReport(
        dataset_id=execution.dataset_id,
        execution_id=execution.id,
        total=total,
        executable=executable,
        correct=correct,
        partial=partial,
        wrong=wrong,
        blocked=blocked,
        correct_rate=round(correct_rate, 4),
        partial_rate=round(partial_rate, 4),
        issue_distribution=issue_distribution,
    )


def bad_case_to_eval_item(
    case_id: str,
    question: str,
    ability_name: str = "",
    category: str = "",
    entrypoint: str = "",
) -> EvalItem:
    """将 Bad Case 转换为测评题目。

    Bad Case 的 category 映射到 EvalCategory：
    - data_quality -> indicator_query
    - platform_runtime -> knowledge_retrieval
    - permission_config -> permission_boundary
    - product_experience -> product_experience
    """
    _CATEGORY_MAP: dict[str, EvalCategory] = {
        "data_quality": EvalCategory.INDICATOR_QUERY,
        "platform_runtime": EvalCategory.KNOWLEDGE_RETRIEVAL,
        "permission_config": EvalCategory.PERMISSION_BOUNDARY,
        "product_experience": EvalCategory.PRODUCT_EXPERIENCE,
    }

    _ENTRYPOINT_MAP: dict[str, EvalEntrypoint] = {
        "webchat": EvalEntrypoint.WEBCHAT,
        "wecom_bot": EvalEntrypoint.WECOM_BOT,
        "both": EvalEntrypoint.BOTH,
    }

    eval_category = _CATEGORY_MAP.get(category, EvalCategory.KNOWLEDGE_RETRIEVAL)
    eval_entrypoint = _ENTRYPOINT_MAP.get(entrypoint, EvalEntrypoint.BOTH)

    return EvalItem(
        case_id=f"eval-{case_id}",
        category=eval_category,
        question=question,
        expected="",
        entrypoint=eval_entrypoint,
        ability=ability_name,
        owner=category,
        tags=["from_bad_case"],
    )


def create_sample_dataset() -> EvalDataset:
    """创建样例测评集模板。

    数据团队可参照此模板格式填充真实题目和标准答案。
    """
    items = [
        EvalItem(
            category=EvalCategory.INDICATOR_QUERY,
            question="上个月的总营收是多少？",
            expected="返回准确的月度营收指标数值",
            entrypoint=EvalEntrypoint.BOTH,
            ability="indicator_query",
            owner="data_quality",
        ),
        EvalItem(
            category=EvalCategory.JARGON_EXPLAIN,
            question="什么是 DAU？",
            expected="正确解释日活跃用户数定义和计算口径",
            entrypoint=EvalEntrypoint.BOTH,
            ability="jargon_lookup",
            owner="data_quality",
        ),
        EvalItem(
            category=EvalCategory.KNOWLEDGE_RETRIEVAL,
            question="公司报销流程是什么？",
            expected="返回完整的报销流程步骤",
            entrypoint=EvalEntrypoint.WEBCHAT,
            ability="knowledge_search",
            owner="data_quality",
        ),
        EvalItem(
            category=EvalCategory.PERMISSION_BOUNDARY,
            question="我能不能查看其他部门的薪资数据？",
            expected="拒绝访问，提示无权限",
            entrypoint=EvalEntrypoint.BOTH,
            ability="indicator_query",
            owner="permission_config",
        ),
        EvalItem(
            category=EvalCategory.PRODUCT_EXPERIENCE,
            question="帮我查一下昨天的活跃用户数",
            expected="正确返回指标值，响应时间 <5s",
            entrypoint=EvalEntrypoint.WECOM_BOT,
            ability="indicator_query",
            owner="product_experience",
        ),
    ]
    return EvalDataset(
        name="样例测评集",
        description="平台提供的测评集模板，数据团队应替换为真实题目和标准答案",
        items=items,
    )
