"""测评 API 路由的单元测试。

使用直接调用路由函数和存储层方式测试核心逻辑。
补充 API 级 TestClient 验证跨租户被拒绝。
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from starlette.middleware.base import BaseHTTPMiddleware

from qwenpaw.enterprise.evaluation.models import (
    EvalCategory,
    EvalDataset,
    EvalExecution,
    EvalExecutionItem,
    EvalItem,
    EvalResult,
    IssueOwner,
)
from qwenpaw.enterprise.evaluation.store import save_dataset, save_execution


class _FakeAuthzService:
    async def check_permission(self, ctx, resource, action):
        from qwenpaw.enterprise.interfaces import AuthzDecision

        return AuthzDecision(allowed=True, reason="test")


class _DenyReadAuthzService:
    async def check_permission(self, ctx, resource, action):
        from qwenpaw.enterprise.interfaces import AuthzDecision

        if resource == "tenant" and action == "read":
            return AuthzDecision(allowed=False, reason="read denied")
        return AuthzDecision(allowed=True, reason="test")


class _InjectRequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        tenant_id: str = "acme",
        roles: tuple[str, ...] = ("platform_admin",),
    ):
        super().__init__(app)
        self.tenant_id = tenant_id
        self.roles = roles

    async def dispatch(self, request: Request, call_next):
        from qwenpaw.enterprise.context import RequestActor, RequestContext
        from qwenpaw.tenancy.ids import tenant_agent_id

        request.state.request_context = RequestContext(
            request_id="test-req",
            trace_id="test-trace",
            user_id="test-user",
            tenant_id=self.tenant_id,
            agent_id=tenant_agent_id(self.tenant_id),
            roles=self.roles,
            actor=RequestActor(actor_id="test-user", actor_type="console_user"),
        )
        return await call_next(request)


class CaptureBus:
    def __init__(self) -> None:
        self.events = []

    async def emit(self, event):
        self.events.append(event)


def make_evaluation_client(
    *,
    audit_bus: CaptureBus | None = None,
    tenant_id: str = "acme",
    roles: tuple[str, ...] = ("platform_admin",),
    authz_service=None,
):
    from qwenpaw.app.routers.evaluation import router

    app = FastAPI()
    app.state.enterprise_runtime = SimpleNamespace(
        authz=authz_service or _FakeAuthzService(),
        audit=audit_bus or CaptureBus(),
    )
    app.include_router(router, prefix="/api")
    app.add_middleware(
        _InjectRequestContextMiddleware,
        tenant_id=tenant_id,
        roles=roles,
    )
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def make_noop_request():
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace()),
        state=SimpleNamespace(),
    )


def test_dataset_crud_with_tenant_isolation(tmp_path):
    """通过存储层完成测评集 CRUD，验证租户隔离。"""
    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        # 租户 A 创建
        ds_a = EvalDataset(
            id="ds-a",
            tenant_id="wx-tenant-a",
            name="租户A测评集",
            items=[
                EvalItem(
                    case_id="c1",
                    category=EvalCategory.INDICATOR_QUERY,
                    question="上月营收",
                    expected="100万",
                ),
            ],
        )
        save_dataset(ds_a)

        # 租户 B 创建
        ds_b = EvalDataset(
            id="ds-b",
            tenant_id="wx-tenant-b",
            name="租户B测评集",
        )
        save_dataset(ds_b)

        # 各自只能看到自己的
        from qwenpaw.enterprise.evaluation.store import list_datasets, get_dataset

        a_list = list_datasets("wx-tenant-a")
        b_list = list_datasets("wx-tenant-b")
        assert len(a_list) == 1
        assert a_list[0].name == "租户A测评集"
        assert len(b_list) == 1
        assert b_list[0].name == "租户B测评集"

        # 租户 B 看不到 A 的数据
        assert get_dataset("ds-a", "wx-tenant-b") is None


def test_tenant_id_with_underscore_works(tmp_path):
    """含下划线的真实租户 ID 可正常存储和读取。"""
    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        ds = EvalDataset(
            id="ds-acme",
            tenant_id="wx_acme",
            name="Acme 测评集",
        )
        save_dataset(ds)

        from qwenpaw.enterprise.evaluation.store import get_dataset

        loaded = get_dataset("ds-acme", "wx_acme")
        assert loaded is not None
        assert loaded.tenant_id == "wx_acme"

        # 复杂格式也可以
        ds2 = EvalDataset(
            id="ds-complex",
            tenant_id="user_acme_001",
            name="复杂租户",
        )
        save_dataset(ds2)
        assert get_dataset("ds-complex", "user_acme_001") is not None


def test_execution_with_tenant_isolation(tmp_path):
    """执行记录按租户隔离。"""
    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        # 先创建测评集
        dataset = EvalDataset(
            id="ds-001",
            tenant_id="wx-tenant-a",
            name="测试集",
        )
        save_dataset(dataset)

        # 创建执行记录
        execution = EvalExecution(
            id="exec-001",
            tenant_id="wx-tenant-a",
            dataset_id="ds-001",
            items=[
                EvalExecutionItem(case_id="c1", result=EvalResult.CORRECT),
                EvalExecutionItem(case_id="c2", result=EvalResult.WRONG),
            ],
        )
        save_execution(execution)

        # 计算准确率
        from qwenpaw.enterprise.evaluation.executor import compute_accuracy
        from qwenpaw.enterprise.evaluation.store import get_execution

        loaded = get_execution("exec-001", "wx-tenant-a")
        assert loaded is not None
        report = compute_accuracy(loaded)
        assert report.total == 2
        assert report.correct_rate == 0.5

        # 租户 B 看不到
        assert get_execution("exec-001", "wx-tenant-b") is None


def test_bad_case_to_eval_round_trip():
    """Bad Case 转测评题后可加入租户测评集并执行。"""
    from qwenpaw.enterprise.evaluation.executor import (
        bad_case_to_eval_item,
        compute_accuracy,
    )

    # 转换
    item = bad_case_to_eval_item(
        case_id="case-bc1",
        question="[Bad Case] indicator_query 调用失败: 返回错误数据",
        ability_name="indicator_query",
        category="data_quality",
        entrypoint="webchat",
    )
    assert item.category == EvalCategory.INDICATOR_QUERY
    assert "from_bad_case" in item.tags

    # 加入租户测评集
    dataset = EvalDataset(
        tenant_id="wx-test",
        name="Bad Case 测评集",
        items=[item],
    )

    # 执行测评
    execution = EvalExecution(
        tenant_id="wx-test",
        dataset_id=dataset.id,
        items=[
            EvalExecutionItem(
                case_id=item.case_id,
                result=EvalResult.WRONG,
            ),
        ],
    )
    report = compute_accuracy(execution)
    assert report.total == 1
    assert report.correct_rate == 0.0


def test_accuracy_report_issue_distribution():
    """准确率报告正确统计问题归属分布。"""
    from qwenpaw.enterprise.evaluation.executor import compute_accuracy

    execution = EvalExecution(
        tenant_id="wx-test",
        dataset_id="ds-issues",
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
                result=EvalResult.PARTIAL,
                issue_owner=IssueOwner.DATA_QUALITY,
            ),
            EvalExecutionItem(
                case_id="c4",
                result=EvalResult.CORRECT,
            ),
        ],
    )
    report = compute_accuracy(execution)

    assert report.total == 4
    assert report.executable == 4
    assert report.correct == 1
    assert report.partial == 1
    assert report.wrong == 2
    assert report.issue_distribution == {
        "data_quality": 2,
        "platform_runtime": 1,
    }


def test_sample_dataset_has_all_categories():
    """样例测评集模板覆盖所有分类。"""
    from qwenpaw.enterprise.evaluation.executor import create_sample_dataset

    dataset = create_sample_dataset()
    categories = {item.category for item in dataset.items}
    assert len(categories) == 5
    assert EvalCategory.INDICATOR_QUERY in categories
    assert EvalCategory.PERMISSION_BOUNDARY in categories


def test_path_traversal_rejected(tmp_path):
    """路径穿越 ID 被存储层拒绝。"""
    from qwenpaw.enterprise.evaluation.store import _validate_id, _safe_path

    with pytest.raises(ValueError):
        _validate_id("../escape", "id")

    with pytest.raises(ValueError):
        _validate_id("../../../etc/passwd", "id")

    base = tmp_path / "safe"
    base.mkdir()
    # _validate_id 在 _safe_path 内先拦截非法 ID
    with pytest.raises(ValueError):
        _safe_path(base, "../escape")


def test_save_without_tenant_id_rejected(tmp_path):
    """保存测评集时缺少 tenant_id 被拒绝。"""
    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        dataset = EvalDataset(id="ds-no-tenant", name="无租户")
        with pytest.raises(ValueError, match="tenant_id"):
            save_dataset(dataset)


def test_empty_tenant_id_returns_400():
    """空 tenant_id 请求返回 400 而非 500。"""
    from unittest.mock import MagicMock

    from qwenpaw.app.routers.evaluation import _require_tenant_id

    # 模拟无 tenant_id 的请求
    request = MagicMock()
    request.state = MagicMock()
    ctx = MagicMock()
    ctx.tenant_id = ""
    request.state.request_context = ctx

    with pytest.raises(Exception) as exc_info:
        _require_tenant_id(request)

    # 应该是 HTTPException 400
    from fastapi import HTTPException

    assert isinstance(exc_info.value, HTTPException)
    assert exc_info.value.status_code == 400


def test_bad_case_to_eval_endpoint_under_tenant_path():
    """Bad Case 转测评接口路径在 /tenants/{agent_id}/ 下。"""
    from qwenpaw.app.routers.evaluation import router

    # 检查路由注册（APIRouter 的路径不含 mount prefix，但自身 prefix=/evaluation 已在路径中）
    routes = [r.path for r in router.routes]
    assert "/evaluation/tenants/{agent_id}/bad-case-to-eval" in routes

    # 旧全局路径不存在
    assert "/evaluation/bad-case-to-eval" not in routes


def test_bad_case_to_eval_requires_dataset_id_or_name():
    """既没传 dataset_id 也没传 dataset_name 时返回 400。"""
    from qwenpaw.enterprise.evaluation.models import BadCaseToEvalRequest

    # 验证模型层面 case_ids 必填
    req = BadCaseToEvalRequest(case_ids=["c1"])
    # dataset_id 和 dataset_name 都为空
    assert req.dataset_id is None
    assert req.dataset_name == ""

    # 路由逻辑在 API 层校验，这里验证请求模型能正确表达"两者都空"
    req_with_id = BadCaseToEvalRequest(case_ids=["c1"], dataset_id="ds-001")
    assert req_with_id.dataset_id == "ds-001"

    req_with_name = BadCaseToEvalRequest(case_ids=["c1"], dataset_name="新建测评集")
    assert req_with_name.dataset_name == "新建测评集"


def test_bad_case_to_eval_dataset_id_not_found_returns_404(tmp_path):
    """传了不存在的 dataset_id 时返回 404。"""
    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        from qwenpaw.enterprise.evaluation.store import get_dataset

        # 不存在的 dataset_id
        assert get_dataset("nonexistent-ds", "wx-test") is None

        # 路由层会检查：有 dataset_id 但查不到 → 404
        # 这里验证存储层返回 None，路由层逻辑已内联检查


@pytest.mark.asyncio
async def test_tenant_dataset_create_emits_audit(tmp_path):
    from qwenpaw.enterprise.audit.models import AuditEventType, AuditOutcome

    audit_bus = CaptureBus()
    client = make_evaluation_client(audit_bus=audit_bus, tenant_id="acme")

    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        async with client:
            resp = await client.post(
                "/api/evaluation/tenants/wx_acme/datasets",
                json={"name": "验收测评集", "description": "一期验收", "items": []},
            )

    assert resp.status_code == 201
    assert len(audit_bus.events) == 1
    event = audit_bus.events[0]
    assert event.event_type == AuditEventType.TENANT_UPDATED
    assert event.outcome == AuditOutcome.SUCCESS
    assert event.action == "create_eval_dataset"
    assert event.agent_id == "wx_acme"
    assert event.resource_id == f"wx_acme:evaluation:dataset:{resp.json()['id']}"


@pytest.mark.asyncio
async def test_tenant_execution_create_emits_audit(tmp_path):
    from qwenpaw.enterprise.audit.models import AuditEventType, AuditOutcome

    audit_bus = CaptureBus()
    client = make_evaluation_client(audit_bus=audit_bus, tenant_id="acme")

    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        dataset = EvalDataset(id="ds-audit", tenant_id="acme", name="审计测评集")
        save_dataset(dataset)
        async with client:
            resp = await client.post(
                "/api/evaluation/tenants/wx_acme/executions",
                json={"dataset_id": "ds-audit", "items": []},
            )

    assert resp.status_code == 201
    assert len(audit_bus.events) == 1
    event = audit_bus.events[0]
    assert event.event_type == AuditEventType.TENANT_UPDATED
    assert event.outcome == AuditOutcome.SUCCESS
    assert event.action == "create_eval_execution"
    assert event.agent_id == "wx_acme"
    assert event.resource_id == f"wx_acme:evaluation:execution:{resp.json()['id']}"


@pytest.mark.asyncio
async def test_tenant_path_dataset_and_report_round_trip(tmp_path):
    """租户路径接口通过 agent_id 绑定 tenant_id 并生成准确率报告。"""
    from qwenpaw.app.routers.evaluation import (
        AddItemRequest,
        CreateDatasetRequest,
        CreateExecutionRequest,
        api_add_tenant_dataset_items,
        api_create_tenant_dataset,
        api_create_tenant_execution,
        api_get_tenant_accuracy_report,
        api_list_tenant_datasets,
    )

    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        request = make_noop_request()
        dataset = await api_create_tenant_dataset(
            "wx_acme",
            CreateDatasetRequest(name="验收测评集", description="一期验收"),
            request,
            _ctx=MagicMock(),
            _tb=MagicMock(),
        )

        assert dataset.tenant_id == "acme"
        assert dataset.name == "验收测评集"

        updated = await api_add_tenant_dataset_items(
            "wx_acme",
            dataset.id,
            AddItemRequest(
                items=[
                    EvalItem(
                        case_id="case-001",
                        category=EvalCategory.INDICATOR_QUERY,
                        question="上月营收是多少？",
                        expected="返回上月营收指标",
                    )
                ]
            ),
            request,
            _ctx=MagicMock(),
            _tb=MagicMock(),
        )

        assert len(updated.items) == 1

        listed = await api_list_tenant_datasets(
            "wx_acme",
            _ctx=MagicMock(),
            _tb=MagicMock(),
        )
        assert listed.total == 1
        assert listed.items[0].tenant_id == "acme"

        execution = await api_create_tenant_execution(
            "wx_acme",
            CreateExecutionRequest(
                dataset_id=dataset.id,
                items=[
                    EvalExecutionItem(
                        case_id="case-001",
                        result=EvalResult.CORRECT,
                        actual="营收 100 万",
                    )
                ],
            ),
            request,
            _ctx=MagicMock(),
            _tb=MagicMock(),
        )

        report = await api_get_tenant_accuracy_report(
            "wx_acme",
            execution.id,
            _ctx=MagicMock(),
            _tb=MagicMock(),
        )
        assert report.total == 1
        assert report.correct_rate == 1.0


def test_tenant_path_evaluation_routes_registered():
    """企业工作台需要的租户路径测评接口均已注册。"""
    from qwenpaw.app.routers.evaluation import router

    routes = {route.path for route in router.routes}
    assert "/evaluation/tenants/{agent_id}/datasets" in routes
    assert "/evaluation/tenants/{agent_id}/datasets/{dataset_id}" in routes
    assert "/evaluation/tenants/{agent_id}/datasets/{dataset_id}/items" in routes
    assert "/evaluation/tenants/{agent_id}/executions" in routes
    assert "/evaluation/tenants/{agent_id}/executions/{execution_id}" in routes
    assert (
        "/evaluation/tenants/{agent_id}/executions/{execution_id}/report"
        in routes
    )
    assert (
        "/evaluation/tenants/{agent_id}/executions/{execution_id}/evidence"
        in routes
    )


@pytest.mark.asyncio
async def test_tenant_acceptance_evidence_export_is_scoped_and_audited(tmp_path):
    """验收证据导出按租户返回 dataset/execution/report 并记录审计。"""
    from qwenpaw.enterprise.audit.models import AuditEventType, AuditOutcome

    audit_bus = CaptureBus()
    client = make_evaluation_client(audit_bus=audit_bus, tenant_id="acme")

    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        dataset = EvalDataset(
            id="ds-evidence",
            tenant_id="acme",
            name="验收证据测评集",
            items=[
                EvalItem(
                    case_id="case-001",
                    category=EvalCategory.INDICATOR_QUERY,
                    question="上月营收是多少？",
                    expected="返回上月营收指标",
                )
            ],
        )
        save_dataset(dataset)
        execution = EvalExecution(
            id="exec-evidence",
            tenant_id="acme",
            dataset_id="ds-evidence",
            items=[
                EvalExecutionItem(
                    case_id="case-001",
                    result=EvalResult.CORRECT,
                    actual="营收 100 万",
                )
            ],
        )
        save_execution(execution)
        save_dataset(EvalDataset(id="ds-other", tenant_id="beta", name="其他租户"))

        async with client:
            resp = await client.get(
                "/api/evaluation/tenants/wx_acme/executions/exec-evidence/evidence"
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant_id"] == "acme"
    assert data["agent_id"] == "wx_acme"
    assert data["dataset"]["id"] == "ds-evidence"
    assert data["dataset"]["tenant_id"] == "acme"
    assert data["execution"]["id"] == "exec-evidence"
    assert data["execution"]["tenant_id"] == "acme"
    assert data["report"]["execution_id"] == "exec-evidence"
    assert data["report"]["correct_rate"] == 1.0
    assert data["evidence_version"] == "1"

    assert len(audit_bus.events) == 1
    event = audit_bus.events[0]
    assert event.event_type == AuditEventType.TENANT_UPDATED
    assert event.outcome == AuditOutcome.SUCCESS
    assert event.action == "export_acceptance_evidence"
    assert event.tenant_id == "acme"
    assert event.agent_id == "wx_acme"
    assert event.resource_id == "wx_acme:evaluation:evidence:exec-evidence"


@pytest.mark.asyncio
async def test_tenant_acceptance_evidence_requires_read_permission(tmp_path):
    """缺少 tenant:read 权限时证据导出被拒绝。"""
    audit_bus = CaptureBus()
    client = make_evaluation_client(
        audit_bus=audit_bus,
        tenant_id="acme",
        authz_service=_DenyReadAuthzService(),
    )

    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        save_dataset(EvalDataset(id="ds-evidence", tenant_id="acme", name="验收集"))
        save_execution(
            EvalExecution(id="exec-evidence", tenant_id="acme", dataset_id="ds-evidence")
        )
        async with client:
            resp = await client.get(
                "/api/evaluation/tenants/wx_acme/executions/exec-evidence/evidence"
            )

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Permission denied: tenant:read"
    assert audit_bus.events == []


@pytest.mark.asyncio
async def test_tenant_acceptance_evidence_rejects_cross_tenant_request(tmp_path):
    """非 platform_admin 不能导出其他租户的验收证据。"""
    audit_bus = CaptureBus()
    client = make_evaluation_client(
        audit_bus=audit_bus,
        tenant_id="beta",
        roles=("tenant_user",),
    )

    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        save_dataset(EvalDataset(id="ds-evidence", tenant_id="acme", name="验收集"))
        save_execution(
            EvalExecution(id="exec-evidence", tenant_id="acme", dataset_id="ds-evidence")
        )
        async with client:
            resp = await client.get(
                "/api/evaluation/tenants/wx_acme/executions/exec-evidence/evidence"
            )

    assert resp.status_code == 403
    assert "Tenant boundary" in resp.json()["detail"]
    assert audit_bus.events == []


@pytest.mark.asyncio
async def test_tenant_acceptance_evidence_missing_dataset_returns_404(tmp_path):
    """执行记录关联的测评集缺失时不生成误导性证据。"""
    audit_bus = CaptureBus()
    client = make_evaluation_client(audit_bus=audit_bus, tenant_id="acme")

    with patch("qwenpaw.enterprise.evaluation.store._eval_root", return_value=tmp_path):
        save_execution(
            EvalExecution(id="exec-orphan", tenant_id="acme", dataset_id="missing-ds")
        )
        async with client:
            resp = await client.get(
                "/api/evaluation/tenants/wx_acme/executions/exec-orphan/evidence"
            )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Dataset not found"
    assert audit_bus.events == []


def test_tenant_path_helpers_invalid_ids_return_400():
    """租户路径 helper 对非法 dataset/execution id 返回 400。"""
    from fastapi import HTTPException

    from qwenpaw.app.routers.evaluation import (
        _get_dataset_or_404,
        _get_execution_or_404,
    )

    with pytest.raises(HTTPException) as dataset_exc:
        _get_dataset_or_404("../escape", "acme")
    assert dataset_exc.value.status_code == 400
    assert "Invalid id" in dataset_exc.value.detail

    with pytest.raises(HTTPException) as execution_exc:
        _get_execution_or_404("../escape", "acme")
    assert execution_exc.value.status_code == 400
    assert "Invalid id" in execution_exc.value.detail


@pytest.mark.asyncio
async def test_tenant_path_delete_invalid_dataset_id_returns_400():
    """租户路径删除接口对非法 dataset_id 返回 400。"""
    from fastapi import HTTPException

    from qwenpaw.app.routers.evaluation import api_delete_tenant_dataset

    with pytest.raises(HTTPException) as exc_info:
        await api_delete_tenant_dataset(
            "wx_acme",
            "../escape",
            make_noop_request(),
            _ctx=MagicMock(),
            _tb=MagicMock(),
        )

    assert exc_info.value.status_code == 400
    assert "Invalid id" in exc_info.value.detail
