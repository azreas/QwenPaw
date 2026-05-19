"""测评集 JSON 存储的单元测试。"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from qwenpaw.enterprise.evaluation.models import EvalDataset, EvalItem, EvalCategory
from qwenpaw.enterprise.evaluation.store import (
    get_dataset,
    list_datasets,
    save_dataset,
    delete_dataset,
    save_execution,
    get_execution,
    list_executions,
    _validate_id,
    _safe_path,
    _tenant_dir,
    _tenant_slug,
)
from qwenpaw.enterprise.evaluation.models import EvalExecution


def test_save_and_get_dataset(tmp_path):
    """保存后可按租户+ID 读取。"""
    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        dataset = EvalDataset(
            id="ds-001",
            tenant_id="wx-test",
            name="测试测评集",
            items=[
                EvalItem(
                    category=EvalCategory.INDICATOR_QUERY,
                    question="问题1",
                    expected="答案1",
                ),
            ],
        )
        save_dataset(dataset)

        loaded = get_dataset("ds-001", "wx-test")
        assert loaded is not None
        assert loaded.name == "测试测评集"
        assert loaded.tenant_id == "wx-test"
        assert len(loaded.items) == 1


def test_tenant_id_with_underscore(tmp_path):
    """含下划线的租户 ID（如 wx_acme）不会被校验挡住。"""
    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        dataset = EvalDataset(
            id="ds-002",
            tenant_id="wx_acme",
            name="下划线租户",
        )
        save_dataset(dataset)

        loaded = get_dataset("ds-002", "wx_acme")
        assert loaded is not None
        assert loaded.tenant_id == "wx_acme"


def test_tenant_id_with_complex_format(tmp_path):
    """复杂格式租户 ID（如 user_acme_001）可正常存储。"""
    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        dataset = EvalDataset(
            id="ds-003",
            tenant_id="user_acme_001",
            name="复杂租户",
        )
        save_dataset(dataset)

        loaded = get_dataset("ds-003", "user_acme_001")
        assert loaded is not None
        assert loaded.tenant_id == "user_acme_001"


def test_tenant_slug_hashes_path_injection(tmp_path):
    """含路径穿越字符的 tenant_id 被 safe_tenant_suffix 哈希化。"""
    slug = _tenant_slug("../../../etc")
    # safe_tenant_suffix 会对含路径穿越字符的值返回哈希
    assert "/" not in slug
    assert ".." not in slug


def test_get_dataset_wrong_tenant(tmp_path):
    """不同租户无法读取其他租户的测评集。"""
    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        dataset = EvalDataset(
            id="ds-001",
            tenant_id="wx-tenant-a",
            name="租户A数据",
        )
        save_dataset(dataset)

        # 租户 B 看不到
        assert get_dataset("ds-001", "wx-tenant-b") is None


def test_list_datasets_filters_by_tenant(tmp_path):
    """列出测评集时按租户过滤。"""
    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        ds1 = EvalDataset(id="ds-001", tenant_id="wx-tenant-a", name="A集")
        ds2 = EvalDataset(id="ds-002", tenant_id="wx-tenant-b", name="B集")
        save_dataset(ds1)
        save_dataset(ds2)

        a_datasets = list_datasets("wx-tenant-a")
        assert len(a_datasets) == 1
        assert a_datasets[0].name == "A集"


def test_get_dataset_not_found(tmp_path):
    """不存在的 ID 返回 None。"""
    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        assert get_dataset("nonexistent", "wx-test") is None


def test_delete_dataset(tmp_path):
    """删除后不可再读取。"""
    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        dataset = EvalDataset(id="ds-del", tenant_id="wx-test", name="待删除")
        save_dataset(dataset)
        assert get_dataset("ds-del", "wx-test") is not None

        result = delete_dataset("ds-del", "wx-test")
        assert result is True
        assert get_dataset("ds-del", "wx-test") is None


def test_delete_dataset_wrong_tenant(tmp_path):
    """不同租户无法删除其他租户的数据。"""
    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        dataset = EvalDataset(id="ds-001", tenant_id="wx-tenant-a", name="A数据")
        save_dataset(dataset)

        assert delete_dataset("ds-001", "wx-tenant-b") is False
        assert get_dataset("ds-001", "wx-tenant-a") is not None


def test_delete_dataset_not_found(tmp_path):
    """删除不存在的数据集返回 False。"""
    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        assert delete_dataset("nonexistent", "wx-test") is False


# ── 路径穿越防护测试 ──────────────────────────────────


def test_validate_id_rejects_traversal():
    """路径穿越 ID 被拒绝。"""
    with pytest.raises(ValueError):
        _validate_id("../etc", "id")

    with pytest.raises(ValueError):
        _validate_id("..", "id")

    with pytest.raises(ValueError):
        _validate_id("foo/../../bar", "id")


def test_validate_id_rejects_uppercase():
    """大写字母 ID 被拒绝。"""
    with pytest.raises(ValueError):
        _validate_id("DS-001", "id")


def test_validate_id_accepts_valid():
    """合法 ID 通过校验。"""
    _validate_id("dataset-abc123", "id")
    _validate_id("exec-def456", "id")


def test_safe_path_detects_traversal(tmp_path):
    """_safe_path 拒绝路径穿越 ID（在 _validate_id 阶段就被拦截）。"""
    base = tmp_path / "safe-dir"
    base.mkdir()

    with pytest.raises(ValueError):
        _safe_path(base, "../escape")


def test_save_dataset_requires_tenant_id(tmp_path):
    """保存测评集时 tenant_id 不能为空。"""
    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        dataset = EvalDataset(id="ds-notenant", name="无租户")
        with pytest.raises(ValueError, match="tenant_id"):
            save_dataset(dataset)


def test_tenant_dir_requires_tenant_id():
    """_tenant_dir 空租户 ID 被拒绝。"""
    with pytest.raises(ValueError, match="tenant_id"):
        _tenant_dir("")


def test_execution_tenant_isolation(tmp_path):
    """执行记录按租户隔离。"""
    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        exec_a = EvalExecution(
            id="exec-a",
            tenant_id="wx-tenant-a",
            dataset_id="ds-001",
        )
        save_execution(exec_a)

        # 租户 A 可见
        assert get_execution("exec-a", "wx-tenant-a") is not None
        # 租户 B 不可见
        assert get_execution("exec-a", "wx-tenant-b") is None

        # 列表过滤
        a_execs = list_executions("wx-tenant-a")
        b_execs = list_executions("wx-tenant-b")
        assert len(a_execs) == 1
        assert len(b_execs) == 0
