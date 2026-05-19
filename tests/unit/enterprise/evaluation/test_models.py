"""测评执行器模型和核心逻辑的单元测试。"""

from qwenpaw.enterprise.evaluation.executor import (
    bad_case_to_eval_item,
    compute_accuracy,
    create_sample_dataset,
)
from qwenpaw.enterprise.evaluation.models import (
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


def test_compute_accuracy_all_correct():
    """全部正确时 correct_rate = 1.0。"""
    execution = EvalExecution(
        dataset_id="ds-test",
        items=[
            EvalExecutionItem(case_id="c1", result=EvalResult.CORRECT),
            EvalExecutionItem(case_id="c2", result=EvalResult.CORRECT),
        ],
    )
    report = compute_accuracy(execution)

    assert report.total == 2
    assert report.executable == 2
    assert report.correct == 2
    assert report.correct_rate == 1.0
    assert report.partial_rate == 0.0


def test_compute_accuracy_with_blocked():
    """blocked 样本不计入可执行数。"""
    execution = EvalExecution(
        dataset_id="ds-test",
        items=[
            EvalExecutionItem(case_id="c1", result=EvalResult.CORRECT),
            EvalExecutionItem(case_id="c2", result=EvalResult.BLOCKED),
            EvalExecutionItem(case_id="c3", result=EvalResult.WRONG),
        ],
    )
    report = compute_accuracy(execution)

    assert report.total == 3
    assert report.executable == 2
    assert report.correct == 1
    assert report.wrong == 1
    assert report.blocked == 1
    assert report.correct_rate == 0.5


def test_compute_accuracy_issue_distribution():
    """问题归属分布正确统计。"""
    execution = EvalExecution(
        dataset_id="ds-test",
        items=[
            EvalExecutionItem(
                case_id="c1",
                result=EvalResult.WRONG,
                issue_owner=IssueOwner.DATA_QUALITY,
            ),
            EvalExecutionItem(
                case_id="c2",
                result=EvalResult.WRONG,
                issue_owner=IssueOwner.PLATFORM_RUNTIME,
            ),
            EvalExecutionItem(
                case_id="c3",
                result=EvalResult.WRONG,
                issue_owner=IssueOwner.DATA_QUALITY,
            ),
        ],
    )
    report = compute_accuracy(execution)

    assert report.issue_distribution == {
        "data_quality": 2,
        "platform_runtime": 1,
    }


def test_compute_accuracy_empty():
    """空执行记录返回零值。"""
    execution = EvalExecution(dataset_id="ds-test", items=[])
    report = compute_accuracy(execution)

    assert report.total == 0
    assert report.executable == 0
    assert report.correct_rate == 0.0


def test_bad_case_to_eval_item_maps_category():
    """Bad Case category 正确映射到 EvalCategory。"""
    item = bad_case_to_eval_item(
        case_id="case-abc",
        question="指标查询返回错误",
        ability_name="indicator_query",
        category="data_quality",
        entrypoint="webchat",
    )

    assert item.category == EvalCategory.INDICATOR_QUERY
    assert item.entrypoint == EvalEntrypoint.WEBCHAT
    assert item.ability == "indicator_query"
    assert item.owner == "data_quality"
    assert "from_bad_case" in item.tags


def test_bad_case_to_eval_item_unknown_category():
    """未知 category 映射到 knowledge_retrieval。"""
    item = bad_case_to_eval_item(
        case_id="case-xyz",
        question="未知问题",
        category="unknown_type",
    )

    assert item.category == EvalCategory.KNOWLEDGE_RETRIEVAL


def test_create_sample_dataset():
    """样例测评集包含 5 个题目，覆盖所有分类。"""
    dataset = create_sample_dataset()

    assert len(dataset.items) == 5
    categories = {item.category for item in dataset.items}
    assert EvalCategory.INDICATOR_QUERY in categories
    assert EvalCategory.JARGON_EXPLAIN in categories
    assert EvalCategory.KNOWLEDGE_RETRIEVAL in categories
    assert EvalCategory.PERMISSION_BOUNDARY in categories
    assert EvalCategory.PRODUCT_EXPERIENCE in categories


def test_eval_item_default_case_id():
    """EvalItem 默认生成以 eval- 开头的 case_id。"""
    item = EvalItem(
        category=EvalCategory.INDICATOR_QUERY,
        question="测试问题",
        expected="预期答案",
    )
    assert item.case_id.startswith("eval-")


def test_eval_dataset_has_tenant_id():
    """EvalDataset 包含 tenant_id 字段。"""
    dataset = EvalDataset(
        tenant_id="wx-test-tenant",
        name="带租户的测评集",
    )
    assert dataset.tenant_id == "wx-test-tenant"


def test_eval_execution_has_tenant_id():
    """EvalExecution 包含 tenant_id 字段。"""
    execution = EvalExecution(
        tenant_id="wx-test-tenant",
        dataset_id="ds-001",
    )
    assert execution.tenant_id == "wx-test-tenant"
