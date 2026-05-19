# -*- coding: utf-8 -*-
"""Tests for WeCom tenant ops insights APIs (P3-4)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from starlette.middleware.base import BaseHTTPMiddleware

from qwenpaw.app.routers.wecom_tenant_config import router

# 从 URL path 中提取 agent_id 的正则
_AGENT_ID_RE = re.compile(r"/tenants/(wx_[^/]+)")


def _extract_agent_id(path: str) -> str:
    """从请求路径中提取 agent_id（BaseHTTPMiddleware 中 path_params 不可用）。"""
    m = _AGENT_ID_RE.search(path)
    return m.group(1) if m else ""


class _FakeAuthzService:
    """Mock AuthzService that allows everything (for unit tests)."""

    async def check_permission(self, ctx, resource, action):
        from qwenpaw.enterprise.interfaces import AuthzDecision

        return AuthzDecision(allowed=True, reason="test")

    async def check_tenant_access(self, ctx, target_tenant_id):
        from qwenpaw.enterprise.interfaces import AuthzDecision

        return AuthzDecision(allowed=True, reason="test")


class _DenyWriteAuthzService:
    """Mock AuthzService that denies write actions."""

    async def check_permission(self, ctx, resource, action):
        from qwenpaw.enterprise.interfaces import AuthzDecision

        if action == "write":
            return AuthzDecision(allowed=False, reason="write denied")
        return AuthzDecision(allowed=True, reason="test")

    async def check_tenant_access(self, ctx, target_tenant_id):
        from qwenpaw.enterprise.interfaces import AuthzDecision

        return AuthzDecision(allowed=True, reason="test")


class _InjectRequestContextMiddleware(BaseHTTPMiddleware):
    """Inject a minimal request context for RBAC deps in tests."""

    async def dispatch(self, request: Request, call_next):
        from qwenpaw.enterprise.context import RequestContext, RequestActor

        agent_id = _extract_agent_id(str(request.url.path))
        ctx = RequestContext(
            request_id="test-req",
            trace_id="test-trace",
            user_id="test-user",
            tenant_id=agent_id,
            agent_id=agent_id,
            roles=("platform_admin",),
            actor=RequestActor(actor_id="test-user", actor_type="console_user"),
        )
        request.state.request_context = ctx
        return await call_next(request)


class _NonPlatformAdminMiddleware(BaseHTTPMiddleware):
    """Inject context with no platform_admin role — simulates tenant boundary check."""

    async def dispatch(self, request: Request, call_next):
        from qwenpaw.enterprise.context import RequestContext, RequestActor

        ctx = RequestContext(
            request_id="test-req",
            trace_id="test-trace",
            user_id="tenant-user",
            tenant_id="other_tenant",
            agent_id="wx_other",
            roles=("tenant_user",),
            actor=RequestActor(actor_id="tenant-user", actor_type="console_user"),
        )
        request.state.request_context = ctx
        return await call_next(request)


class _PlatformAdminNoTenantMiddleware(BaseHTTPMiddleware):
    """Inject platform_admin without route-derived tenant fields."""

    async def dispatch(self, request: Request, call_next):
        from qwenpaw.enterprise.context import RequestContext, RequestActor

        ctx = RequestContext(
            request_id="test-req",
            trace_id="test-trace",
            user_id="platform-user",
            roles=("platform_admin",),
            actor=RequestActor(actor_id="platform-user", actor_type="console_user"),
        )
        request.state.request_context = ctx
        return await call_next(request)


class _FakeAuditRow:
    """Mimics AuditLogRow with payload attribute."""

    def __init__(self, **kwargs: Any) -> None:
        self.id = kwargs.get("id", "row-1")
        self.event_type = kwargs.get("event_type", "skill.called")
        self.action = kwargs.get("action", "call")
        self.outcome = kwargs.get("outcome", "success")
        self.tenant_id = kwargs.get("tenant_id", "")
        self.agent_id = kwargs.get("agent_id", "")
        self.session_id = kwargs.get("session_id", "")
        self.actor_id = kwargs.get("actor_id", "")
        self.resource_type = kwargs.get("resource_type", "")
        self.resource_id = kwargs.get("resource_id", "")
        self.request_id = kwargs.get("request_id", "")
        self.trace_id = kwargs.get("trace_id", "")
        self.payload = kwargs.get("payload", {})
        self.created_at = kwargs.get(
            "created_at",
            datetime.now(timezone.utc),
        )


class FakeTenantManager:
    def __init__(self) -> None:
        self.loaded: set[str] = set()
        self.agents: dict[str, object] = {}

    def list_loaded_agents(self) -> list[str]:
        return sorted(self.loaded)

    def is_agent_loaded(self, agent_id: str) -> bool:
        return agent_id in self.loaded


class _FakeAuditRepository:
    """In-memory audit repository for tests."""

    def __init__(self) -> None:
        self._rows: list[_FakeAuditRow] = []

    def add_row(self, **kwargs: Any) -> None:
        self._rows.append(_FakeAuditRow(**kwargs))

    async def append_many(self, events: list[Any]) -> None:
        for event in events:
            self._rows.append(
                _FakeAuditRow(
                    id=event.id,
                    event_type=str(event.event_type),
                    action=event.action,
                    outcome=str(event.outcome),
                    tenant_id=event.tenant_id,
                    agent_id=event.agent_id,
                    session_id=event.session_id,
                    actor_id=event.actor_id,
                    resource_type=event.resource_type,
                    resource_id=event.resource_id,
                    request_id=event.request_id,
                    trace_id=event.trace_id,
                    payload=event.payload,
                    created_at=event.created_at,
                )
            )

    async def query(self, **kwargs: Any) -> list[_FakeAuditRow]:
        results = list(self._rows)
        event_types = kwargs.get("event_types")
        if event_types:
            results = [r for r in results if r.event_type in event_types]
        agent_id = kwargs.get("agent_id")
        if agent_id:
            results = [r for r in results if r.agent_id == agent_id]
        resource_id = kwargs.get("resource_id")
        if resource_id:
            results = [r for r in results if r.resource_id == resource_id]
        limit = kwargs.get("limit", 100)
        results.sort(key=lambda r: r.created_at, reverse=True)
        return results[:limit]


class _FakeAuditBus:
    """Mock audit bus that delegates emit to the fake repository."""

    def __init__(self, repo: _FakeAuditRepository) -> None:
        self._repo = repo
        self._repository = repo

    async def emit(self, event: Any) -> None:
        await self._repo.append_many([event])


@pytest.fixture(autouse=True)
def _patch_tenants_root(tmp_path, monkeypatch):
    tenants_root = tmp_path / "tenants"
    monkeypatch.setenv("QWENPAW_TENANTS_ROOT", str(tenants_root))
    return tenants_root


@pytest.fixture
def manager() -> FakeTenantManager:
    return FakeTenantManager()


@pytest.fixture
def audit_repo() -> _FakeAuditRepository:
    return _FakeAuditRepository()


@pytest.fixture
def api_client(manager, audit_repo):
    """构建测试 API 客户端，带完整 enterprise_runtime mock。"""
    audit_bus = _FakeAuditBus(audit_repo)
    app = FastAPI()
    app.state.multi_agent_manager = manager
    app.state.enterprise_runtime = SimpleNamespace(
        authz=_FakeAuthzService(),
        audit=audit_bus,
        storage=SimpleNamespace(session_factory=None),
    )
    app.include_router(router, prefix="/api")
    app.add_middleware(_InjectRequestContextMiddleware)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def write_agent_json(workspace_dir: Path, **overrides) -> None:
    workspace_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": workspace_dir.name,
        "name": workspace_dir.name,
        "workspace_dir": str(workspace_dir),
    }
    payload.update(overrides)
    (workspace_dir / "agent.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------- Task 1: Ops Overview & Tenant Summary ----------


async def test_ops_overview_returns_default_when_no_audit(manager, _patch_tenants_root):
    """无 audit repository 时返回零值，不抛异常。"""
    app = FastAPI()
    app.state.multi_agent_manager = manager
    # 有 enterprise_runtime 但 audit 没有 repository
    app.state.enterprise_runtime = SimpleNamespace(
        authz=_FakeAuthzService(),
        audit=SimpleNamespace(),
        storage=SimpleNamespace(session_factory=None),
    )
    app.include_router(router, prefix="/api")
    app.add_middleware(_InjectRequestContextMiddleware)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/config/channels/wecom_tenant/ops/overview")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_tenants"] == 0
    assert data["business_calls_24h"] == 0
    assert data["failed_calls_24h"] == 0
    assert data["failure_rate"] == 0.0


async def test_ops_overview_counts_business_calls(
    api_client, audit_repo, manager, _patch_tenants_root
):
    """有审计事件时统计调用量和失败率。"""
    for agent_id in ["wx_a", "wx_b"]:
        write_agent_json(_patch_tenants_root / agent_id)
    manager.loaded.add("wx_a")

    # 添加 skill.called 成功事件
    audit_repo.add_row(
        event_type="skill.called",
        action="call",
        outcome="success",
        agent_id="wx_a",
        payload={
            "entrypoint": "wecom",
            "ability_type": "skill",
            "ability_name": "demo",
        },
    )
    # 添加 mcp.called 失败事件
    audit_repo.add_row(
        event_type="mcp.called",
        action="call",
        outcome="failure",
        agent_id="wx_b",
        payload={
            "entrypoint": "webchat",
            "ability_type": "mcp",
            "ability_name": "local",
            "error_reason": "connection refused",
        },
    )

    async with api_client:
        resp = await api_client.get("/api/config/channels/wecom_tenant/ops/overview")

    assert resp.status_code == 200
    data = resp.json()
    assert data["business_calls_24h"] == 2
    assert data["failed_calls_24h"] == 1
    assert data["failure_rate"] == 0.5
    # 入口分布
    assert data["entrypoints"]["wecom"] == 1
    assert data["entrypoints"]["webchat"] == 1
    # Top 失败能力
    assert len(data["top_failed_abilities"]) >= 1
    assert data["top_failed_abilities"][0]["ability_name"] == "local"


async def test_tenant_ops_summary_filters_by_agent(
    api_client, audit_repo, manager, _patch_tenants_root
):
    """单租户运营摘要按 agent_id 过滤。"""
    write_agent_json(_patch_tenants_root / "wx_alice")
    write_agent_json(_patch_tenants_root / "wx_bob")
    manager.loaded.add("wx_alice")

    audit_repo.add_row(
        event_type="skill.called",
        action="call",
        outcome="success",
        agent_id="wx_alice",
        payload={"entrypoint": "wecom", "ability_type": "skill", "ability_name": "demo"},
    )
    audit_repo.add_row(
        event_type="mcp.called",
        action="call",
        outcome="failure",
        agent_id="wx_bob",
        payload={
            "entrypoint": "wecom",
            "ability_type": "mcp",
            "ability_name": "local",
            "error_reason": "timeout",
        },
    )

    async with api_client:
        resp = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/ops/summary"
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_id"] == "wx_alice"
    assert data["business_calls_24h"] == 1
    assert data["failed_calls_24h"] == 0


async def test_tenant_ops_summary_requires_tenant_boundary(
    manager, _patch_tenants_root
):
    """非平台管理员访问其他租户被拒。"""
    write_agent_json(_patch_tenants_root / "wx_alice")

    app = FastAPI()
    app.state.multi_agent_manager = manager
    app.state.enterprise_runtime = SimpleNamespace(
        authz=_FakeAuthzService(),
        storage=SimpleNamespace(session_factory=None),
    )
    app.include_router(router, prefix="/api")
    app.add_middleware(_NonPlatformAdminMiddleware)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/ops/summary"
        )

    assert resp.status_code == 403


async def test_ops_overview_requires_platform_admin(manager, _patch_tenants_root):
    """全局运营总览只允许 platform_admin 查看。"""
    write_agent_json(_patch_tenants_root / "wx_alice")

    app = FastAPI()
    app.state.multi_agent_manager = manager
    app.state.enterprise_runtime = SimpleNamespace(
        authz=_FakeAuthzService(),
        storage=SimpleNamespace(session_factory=None),
    )
    app.include_router(router, prefix="/api")
    app.add_middleware(_NonPlatformAdminMiddleware)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/config/channels/wecom_tenant/ops/overview")

    assert resp.status_code == 403


async def test_tenant_business_traces_returns_filtered_items(
    api_client, audit_repo, _patch_tenants_root
):
    """单租户追踪接口按状态和 agent_id 过滤业务调用。"""
    write_agent_json(_patch_tenants_root / "wx_alice")
    audit_repo.add_row(
        id="trace-1",
        event_type="skill.called",
        outcome="success",
        agent_id="wx_alice",
        resource_type="skill",
        resource_id="demo",
        payload={
            "entrypoint": "webchat",
            "ability_type": "skill",
            "ability_name": "demo",
            "status": "success",
            "duration_ms": 50,
        },
    )
    audit_repo.add_row(
        id="trace-2",
        event_type="mcp.called",
        outcome="failure",
        agent_id="wx_alice",
        resource_type="mcp",
        resource_id="local/query",
        payload={
            "entrypoint": "wecom",
            "ability_type": "mcp",
            "ability_name": "local/query",
            "status": "failure",
            "duration_ms": 120,
            "error_reason": "timeout",
        },
    )
    audit_repo.add_row(
        id="trace-other",
        event_type="mcp.called",
        outcome="failure",
        agent_id="wx_bob",
        payload={"status": "failure"},
    )

    async with api_client:
        resp = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/ops/traces",
            params={"status": "failure"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == "trace-2"
    assert body["items"][0]["ability_name"] == "local/query"


# ---------- Task 3: Bad Case Event Management ----------


async def test_mark_bad_case_emits_audit_event(
    api_client, audit_repo, _patch_tenants_root
):
    """POST 创建 Bad Case 返回 201 并写入审计事件。"""
    write_agent_json(_patch_tenants_root / "wx_alice")

    async with api_client:
        resp = await api_client.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/bad-cases",
            json={
                "source_audit_id": "audit-001",
                "source_request_id": "req-001",
                "source_trace_id": "trace-001",
                "category": "data_quality",
                "owner": "admin",
                "note": "wrong answer",
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["case_id"] == "case-audit-001"
    assert data["category"] == "data_quality"
    assert data["status"] == "open"
    # 验证审计事件被写入（通过 _FakeAuditBus.emit → _FakeAuditRepository.append_many）
    bad_case_events = [
        r for r in audit_repo._rows if r.event_type == "bad_case.marked"
    ]
    assert len(bad_case_events) == 1


async def test_failed_business_trace_bad_case_round_trip_is_visible(
    api_client, audit_repo, _patch_tenants_root
):
    """本地失败业务样本可标记为 Bad Case，并在列表和状态流转中可见。"""
    write_agent_json(_patch_tenants_root / "wx_alice")
    audit_repo.add_row(
        id="audit-real-failure",
        event_type="mcp.called",
        action="call",
        outcome="failure",
        agent_id="wx_alice",
        tenant_id="alice",
        resource_type="mcp",
        resource_id="doris.query",
        request_id="req-real-failure",
        trace_id="trace-real-failure",
        payload={
            "entrypoint": "webchat",
            "ability_type": "mcp",
            "ability_name": "doris.query",
            "status": "failure",
            "duration_ms": 880,
            "error_reason": "Doris query timeout",
        },
    )

    async with api_client:
        create_resp = await api_client.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/bad-cases",
            json={
                "source_audit_id": "audit-real-failure",
                "category": "platform_runtime",
                "owner": "ops",
                "note": "timeout",
            },
        )
        assert create_resp.status_code == 201

        list_resp = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/bad-cases"
        )
        assert list_resp.status_code == 200

        update_resp = await api_client.patch(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/bad-cases/"
            "case-audit-real-failure",
            json={"status": "resolved", "owner": "data-team"},
        )
        assert update_resp.status_code == 200

        final_resp = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/bad-cases"
        )
        assert final_resp.status_code == 200

    created = create_resp.json()
    assert created["source_request_id"] == "req-real-failure"
    assert created["source_trace_id"] == "trace-real-failure"
    assert created["ability_type"] == "mcp"
    assert created["ability_name"] == "doris.query"
    assert created["entrypoint"] == "webchat"

    listed = list_resp.json()["items"][0]
    assert listed["source_audit_id"] == "audit-real-failure"
    assert listed["source_request_id"] == "req-real-failure"
    assert listed["source_trace_id"] == "trace-real-failure"
    assert listed["ability_name"] == "doris.query"
    assert listed["status"] == "open"

    final = final_resp.json()["items"][0]
    assert final["status"] == "resolved"
    assert final["owner"] == "data-team"
    assert final["ability_name"] == "doris.query"


async def test_mark_bad_case_backfills_source_metadata_beyond_recent_window(
    api_client,
    audit_repo,
    _patch_tenants_root,
):
    """较早的失败调用仍应回填源 request/trace，避免最近 100 条截断。"""
    write_agent_json(_patch_tenants_root / "wx_alice")
    audit_repo.add_row(
        id="audit-old-failure",
        event_type="skill.called",
        action="call",
        outcome="failure",
        agent_id="wx_alice",
        tenant_id="alice",
        resource_type="skill",
        resource_id="sales_report",
        request_id="req-old-failure",
        trace_id="trace-old-failure",
        payload={
            "entrypoint": "wecom_tenant",
            "ability_type": "skill",
            "ability_name": "sales_report",
            "status": "failure",
            "error_reason": "skill timeout",
        },
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    for index in range(120):
        audit_repo.add_row(
            id=f"audit-newer-{index}",
            event_type="mcp.called",
            action="call",
            outcome="success",
            agent_id="wx_alice",
            tenant_id="alice",
            resource_type="mcp",
            resource_id=f"mock.{index}",
            created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )

    async with api_client:
        resp = await api_client.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/bad-cases",
            json={
                "source_audit_id": "audit-old-failure",
                "category": "data_quality",
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["source_request_id"] == "req-old-failure"
    assert data["source_trace_id"] == "trace-old-failure"
    assert data["ability_type"] == "skill"
    assert data["ability_name"] == "sales_report"
    assert data["entrypoint"] == "wecom_tenant"


async def test_mark_bad_case_pins_platform_admin_event_to_target_agent(
    manager, audit_repo, _patch_tenants_root
):
    """platform_admin 标记租户 Bad Case 时，审计行仍写入目标 agent_id。"""
    write_agent_json(_patch_tenants_root / "wx_alice")
    app = FastAPI()
    app.state.multi_agent_manager = manager
    app.state.enterprise_runtime = SimpleNamespace(
        authz=_FakeAuthzService(),
        audit=_FakeAuditBus(audit_repo),
        storage=SimpleNamespace(session_factory=None),
    )
    app.include_router(router, prefix="/api")
    app.add_middleware(_PlatformAdminNoTenantMiddleware)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/bad-cases",
            json={
                "source_audit_id": "audit-tenant-agent",
                "category": "platform_runtime",
            },
        )

    assert resp.status_code == 201
    bad_case_events = [
        r for r in audit_repo._rows if r.event_type == "bad_case.marked"
    ]
    assert bad_case_events[0].agent_id == "wx_alice"
    assert bad_case_events[0].tenant_id == "alice"


async def test_bad_case_update_uses_latest_event(
    api_client, audit_repo, _patch_tenants_root
):
    """PATCH 更新后 GET 看到最新状态。"""
    write_agent_json(_patch_tenants_root / "wx_alice")

    async with api_client:
        # 先创建
        create_resp = await api_client.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/bad-cases",
            json={
                "source_audit_id": "audit-002",
                "category": "platform_runtime",
                "note": "crash",
            },
        )
        assert create_resp.status_code == 201

        # 再更新
        update_resp = await api_client.patch(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/bad-cases/case-audit-002",
            json={"status": "triaged", "owner": "ops-team"},
        )
        assert update_resp.status_code == 200

        # 读取列表
        resp = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/bad-cases"
        )

    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["case_id"] == "case-audit-002"
    assert items[0]["status"] == "triaged"
    assert items[0]["owner"] == "ops-team"


async def test_list_bad_cases_returns_empty_without_audit(
    manager, _patch_tenants_root
):
    """无审计仓储时返回空列表。"""
    write_agent_json(_patch_tenants_root / "wx_alice")

    app = FastAPI()
    app.state.multi_agent_manager = manager
    # 有 enterprise_runtime 但 audit 没有 repository
    app.state.enterprise_runtime = SimpleNamespace(
        authz=_FakeAuthzService(),
        audit=SimpleNamespace(),
        storage=SimpleNamespace(session_factory=None),
    )
    app.include_router(router, prefix="/api")
    app.add_middleware(_InjectRequestContextMiddleware)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/bad-cases"
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_bad_case_post_requires_tenant_write(
    manager, _patch_tenants_root
):
    """非 tenant:write 权限被拒。"""
    write_agent_json(_patch_tenants_root / "wx_alice")

    app = FastAPI()
    app.state.multi_agent_manager = manager
    app.state.enterprise_runtime = SimpleNamespace(
        authz=_DenyWriteAuthzService(),
        storage=SimpleNamespace(session_factory=None),
    )
    app.include_router(router, prefix="/api")
    app.add_middleware(_InjectRequestContextMiddleware)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/bad-cases",
            json={
                "source_audit_id": "audit-003",
                "category": "permission_config",
            },
        )

    assert resp.status_code == 403


async def test_mark_bad_case_rejects_duplicate(
    api_client, audit_repo, _patch_tenants_root
):
    """重复标记同一 audit_id 返回 409。"""
    write_agent_json(_patch_tenants_root / "wx_alice")

    async with api_client:
        resp1 = await api_client.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/bad-cases",
            json={
                "source_audit_id": "audit-dup",
                "category": "platform_runtime",
            },
        )
        assert resp1.status_code == 201

        resp2 = await api_client.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/bad-cases",
            json={
                "source_audit_id": "audit-dup",
                "category": "data_quality",
            },
        )
        assert resp2.status_code == 409


async def test_aggregate_bad_cases_skips_duplicate_marked(
    audit_repo, _patch_tenants_root
):
    """聚合时后续 bad_case.marked 不覆盖已更新的状态。"""
    from qwenpaw.app.routers.wecom_tenant_config.ops_insights import (
        _aggregate_bad_cases,
    )

    base = datetime(2026, 5, 12, 10, 0, 0, tzinfo=timezone.utc)
    rows = [
        _FakeAuditRow(
            event_type="bad_case.marked",
            payload={
                "case_id": "case-001",
                "category": "platform_runtime",
                "status": "open",
            },
            created_at=base,
        ),
        _FakeAuditRow(
            event_type="bad_case.updated",
            payload={
                "case_id": "case-001",
                "updates": {"status": "resolved", "owner": "ops"},
            },
            created_at=base + timedelta(minutes=5),
        ),
        # 重复标记——应被忽略
        _FakeAuditRow(
            event_type="bad_case.marked",
            payload={
                "case_id": "case-001",
                "category": "data_quality",
                "status": "open",
            },
            created_at=base + timedelta(minutes=10),
        ),
    ]
    items = _aggregate_bad_cases(rows)
    assert len(items) == 1
    assert items[0].status == "resolved"
    assert items[0].owner == "ops"
    assert items[0].category == "platform_runtime"


class _FailingAuditBus:
    """Audit bus whose emit always fails — for strict path tests."""

    def __init__(self, repo: _FakeAuditRepository) -> None:
        self._repo = repo
        self._repository = repo

    async def emit(self, event: Any) -> None:
        raise RuntimeError("audit backend down")


async def test_mark_bad_case_returns_503_when_emit_fails(
    manager, audit_repo, _patch_tenants_root
):
    """audit emit 抛异常时 POST 返回 503，避免“保存成功假象”。"""
    write_agent_json(_patch_tenants_root / "wx_alice")
    app = FastAPI()
    app.state.multi_agent_manager = manager
    app.state.enterprise_runtime = SimpleNamespace(
        authz=_FakeAuthzService(),
        audit=_FailingAuditBus(audit_repo),
        storage=SimpleNamespace(session_factory=None),
    )
    app.include_router(router, prefix="/api")
    app.add_middleware(_InjectRequestContextMiddleware)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/bad-cases",
            json={
                "source_audit_id": "audit-fail",
                "category": "platform_runtime",
            },
        )

    assert resp.status_code == 503
    # 没有事件被持久化
    assert not [r for r in audit_repo._rows if r.event_type == "bad_case.marked"]


async def test_update_bad_case_returns_503_when_emit_fails(
    manager, audit_repo, _patch_tenants_root
):
    """PATCH 更新时 emit 失败也返回 503。"""
    write_agent_json(_patch_tenants_root / "wx_alice")
    # 先用正常 bus 创建一个 case
    good_bus = _FakeAuditBus(audit_repo)
    app = FastAPI()
    app.state.multi_agent_manager = manager
    app.state.enterprise_runtime = SimpleNamespace(
        authz=_FakeAuthzService(),
        audit=good_bus,
        storage=SimpleNamespace(session_factory=None),
    )
    app.include_router(router, prefix="/api")
    app.add_middleware(_InjectRequestContextMiddleware)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp1 = await client.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/bad-cases",
            json={
                "source_audit_id": "audit-patch-fail",
                "category": "platform_runtime",
            },
        )
        assert resp1.status_code == 201

    # 切换为失败 bus 再 PATCH
    app.state.enterprise_runtime = SimpleNamespace(
        authz=_FakeAuthzService(),
        audit=_FailingAuditBus(audit_repo),
        storage=SimpleNamespace(session_factory=None),
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp2 = await client.patch(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/bad-cases/"
            "case-audit-patch-fail",
            json={"status": "resolved"},
        )

    assert resp2.status_code == 503
    # 没有 bad_case.updated 事件落库
    assert not [r for r in audit_repo._rows if r.event_type == "bad_case.updated"]
