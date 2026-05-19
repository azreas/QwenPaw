# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from starlette.middleware.base import BaseHTTPMiddleware

from qwenpaw.app.routers.wecom_tenant_config import router


class _FakeAuthzService:
    """Mock AuthzService that allows everything (for unit tests)."""

    async def check_permission(self, ctx, resource, action):
        from qwenpaw.enterprise.interfaces import AuthzDecision

        return AuthzDecision(allowed=True, reason="test")

    async def check_tenant_access(self, ctx, target_tenant_id):
        from qwenpaw.enterprise.interfaces import AuthzDecision

        return AuthzDecision(allowed=True, reason="test")


class _InjectRequestContextMiddleware(BaseHTTPMiddleware):
    """Inject a minimal request context for RBAC deps in tests."""

    async def dispatch(self, request: Request, call_next):
        from qwenpaw.enterprise.context import RequestContext, RequestActor

        ctx = RequestContext(
            request_id="test-req",
            trace_id="test-trace",
            user_id="test-user",
            tenant_id=request.path_params.get("agent_id", ""),
            agent_id=request.path_params.get("agent_id", ""),
            roles=("platform_admin",),
            actor=RequestActor(actor_id="test-user", actor_type="console_user"),
        )
        request.state.request_context = ctx
        return await call_next(request)


class _InjectCustomRequestContextMiddleware(BaseHTTPMiddleware):
    """Inject a custom request context for tenant-boundary tests."""

    def __init__(self, app, *, tenant_id: str, roles: tuple[str, ...]):
        super().__init__(app)
        self.tenant_id = tenant_id
        self.roles = roles

    async def dispatch(self, request: Request, call_next):
        from qwenpaw.enterprise.context import RequestContext, RequestActor
        from qwenpaw.tenancy.ids import tenant_agent_id

        agent_id = tenant_agent_id(self.tenant_id) if self.tenant_id else ""
        ctx = RequestContext(
            request_id="test-req",
            trace_id="test-trace",
            user_id="test-user",
            tenant_id=self.tenant_id,
            agent_id=agent_id,
            roles=self.roles,
            actor=RequestActor(actor_id="test-user", actor_type="console_user"),
        )
        request.state.request_context = ctx
        return await call_next(request)


class CaptureBus:
    """Capture audit events emitted by route handlers."""

    def __init__(self) -> None:
        self.events = []

    async def emit(self, event):
        self.events.append(event)


class FakeTenantManager:
    def __init__(self) -> None:
        self.loaded: set[str] = set()
        self.started: list[tuple[str, Path]] = []
        self.stopped: list[str] = []
        self.reloaded: list[str] = []
        self.agents: dict[str, object] = {}

    def list_loaded_agents(self) -> list[str]:
        return sorted(self.loaded)

    def is_agent_loaded(self, agent_id: str) -> bool:
        return agent_id in self.loaded

    async def get_or_create_tenant_agent(self, agent_id: str, workspace_dir):
        self.loaded.add(agent_id)
        self.started.append((agent_id, Path(workspace_dir)))
        workspace = SimpleNamespace(
            agent_id=agent_id,
            workspace_dir=Path(workspace_dir),
            cron_manager=None,
        )
        self.agents[agent_id] = workspace
        return workspace

    async def stop_agent(self, agent_id: str) -> bool:
        self.loaded.discard(agent_id)
        self.stopped.append(agent_id)
        self.agents.pop(agent_id, None)
        return True

    async def reload_agent(self, agent_id: str) -> bool:
        self.reloaded.append(agent_id)
        return agent_id in self.loaded


@pytest.fixture(autouse=True)
def _patch_tenants_root(tmp_path, monkeypatch):
    tenants_root = tmp_path / "tenants"
    monkeypatch.setenv("QWENPAW_TENANTS_ROOT", str(tenants_root))
    return tenants_root


@pytest.fixture
def manager() -> FakeTenantManager:
    return FakeTenantManager()


@pytest.fixture
def api_client(manager):
    app = FastAPI()
    app.state.multi_agent_manager = manager
    # 模拟 enterprise_runtime 以支持 RBAC 依赖
    from types import SimpleNamespace as SN

    app.state.enterprise_runtime = SimpleNamespace(authz=_FakeAuthzService())
    app.include_router(router, prefix="/api")
    # 注入请求上下文到每个请求（模拟 AuthzMiddleware 行为）
    app.add_middleware(_InjectRequestContextMiddleware)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def make_api_client(
    manager,
    *,
    tenant_id: str = "",
    roles: tuple[str, ...] = ("platform_admin",),
    audit_bus: CaptureBus | None = None,
):
    app = FastAPI()
    app.state.multi_agent_manager = manager
    app.state.enterprise_runtime = SimpleNamespace(
        authz=_FakeAuthzService(),
        audit=audit_bus or CaptureBus(),
    )
    app.include_router(router, prefix="/api")
    app.add_middleware(
        _InjectCustomRequestContextMiddleware,
        tenant_id=tenant_id,
        roles=roles,
    )
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


async def test_rejects_non_wx_agent_id(api_client):
    async with api_client:
        resp = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/default/model",
        )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Only wx_* tenant agent ids are supported"


async def test_rejects_path_injection_agent_id(api_client):
    async with api_client:
        resp = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_a..b/model",
        )

    assert resp.status_code == 400


async def test_missing_workspace_returns_404(api_client):
    async with api_client:
        resp = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_missing/model",
        )

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


async def test_invalid_agent_json_returns_422(api_client, _patch_tenants_root):
    workspace_dir = _patch_tenants_root / "wx_broken"
    workspace_dir.mkdir(parents=True)
    (workspace_dir / "agent.json").write_text("{bad json", encoding="utf-8")

    async with api_client:
        resp = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_broken/model",
        )

    assert resp.status_code == 422


async def test_put_tenant_model_persists_and_reload_when_running(
    api_client,
    manager,
    _patch_tenants_root,
):
    workspace_dir = _patch_tenants_root / "wx_alice"
    write_agent_json(workspace_dir)
    manager.loaded.add("wx_alice")

    async with api_client:
        resp = await api_client.put(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/model",
            json={"provider_id": "dashscope", "model": "qwen3-max"},
        )

    assert resp.status_code == 200
    assert resp.json() == {"provider_id": "dashscope", "model": "qwen3-max"}
    saved = json.loads((workspace_dir / "agent.json").read_text("utf-8"))
    assert saved["active_model"] == {
        "provider_id": "dashscope",
        "model": "qwen3-max",
    }


async def test_feature_config_rejects_missing_tenant_context(
    manager,
    _patch_tenants_root,
):
    workspace_dir = _patch_tenants_root / "wx_alice"
    write_agent_json(workspace_dir)
    client = make_api_client(manager, tenant_id="", roles=("tenant_admin",))

    async with client:
        resp = await client.put(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/model",
            json={"provider_id": "dashscope", "model": "qwen3-max"},
        )

    assert resp.status_code == 403
    assert "Tenant-scoped access requires tenant context" in resp.json()["detail"]


async def test_put_tenant_model_emits_tenant_audit(
    manager,
    _patch_tenants_root,
):
    from qwenpaw.enterprise.audit.models import AuditEventType, AuditOutcome

    workspace_dir = _patch_tenants_root / "wx_alice"
    write_agent_json(workspace_dir)
    audit_bus = CaptureBus()
    client = make_api_client(manager, audit_bus=audit_bus)

    async with client:
        resp = await client.put(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/model",
            json={"provider_id": "dashscope", "model": "qwen3-max"},
        )

    assert resp.status_code == 200
    assert len(audit_bus.events) == 1
    event = audit_bus.events[0]
    assert event.event_type == AuditEventType.TENANT_UPDATED
    assert event.outcome == AuditOutcome.SUCCESS
    assert event.action == "update_model"
    assert event.agent_id == "wx_alice"
    assert event.resource_id == "wx_alice:model"
    assert event.payload["changed_key"] == "active_model"


async def test_put_tenant_llm_routing_persists(api_client, _patch_tenants_root):
    workspace_dir = _patch_tenants_root / "wx_alice"
    write_agent_json(workspace_dir)

    async with api_client:
        resp = await api_client.put(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/llm-routing",
            json={
                "enabled": True,
                "mode": "cloud_first",
                "local": {"provider_id": "ollama", "model": "qwen2.5"},
                "cloud": {"provider_id": "dashscope", "model": "qwen3-max"},
            },
        )

    assert resp.status_code == 200
    assert resp.json()["enabled"] is True
    assert resp.json()["mode"] == "cloud_first"


async def test_entry_config_get_put_and_diagnostics_are_workspace_local(
    manager,
    _patch_tenants_root,
):
    from qwenpaw.enterprise.audit.models import AuditEventType

    workspace_dir = _patch_tenants_root / "wx_alice"
    write_agent_json(
        workspace_dir,
        channels={
            "wecom_tenant": {
                "enabled": True,
                "bot_id": "bot-old",
                "secret": "old-secret",
                "welcome_text": "hello",
                "share_session_in_group": True,
            },
            "webchat": {
                "enabled": False,
                "user_data_dir": "users",
                "media_dir": "media",
            },
        },
    )
    audit_bus = CaptureBus()
    client = make_api_client(manager, audit_bus=audit_bus)

    async with client:
        get_resp = await client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/entry-config",
        )
        put_resp = await client.put(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/entry-config",
            json={
                "wecom": {
                    "enabled": True,
                    "bot_id": "bot-new",
                    "secret": "",
                    "welcome_text": "hi",
                    "share_session_in_group": False,
                    "streaming_enabled": True,
                    "require_mention": True,
                    "allow_from": ["corp-a"],
                    "deny_message": "denied",
                },
                "webchat": {
                    "enabled": True,
                    "user_data_dir": "web-users",
                    "media_dir": "web-media",
                    "dm_policy": "allowlist",
                    "allow_from": ["u1"],
                    "deny_message": "blocked",
                },
            },
        )
        diag_resp = await client.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/entry-config/diagnose",
        )

    assert get_resp.status_code == 200
    assert get_resp.json()["wecom"]["bot_id"] == "bot-old"
    assert get_resp.json()["wecom"]["secret_set"] is True
    assert "secret" not in get_resp.json()["wecom"]
    assert put_resp.status_code == 200
    assert put_resp.json()["wecom"]["bot_id"] == "bot-new"
    assert put_resp.json()["wecom"]["secret_set"] is True
    assert put_resp.json()["webchat"]["enabled"] is True
    assert diag_resp.status_code == 200
    checks = diag_resp.json()["checks"]
    assert checks["workspace_exists"] is True
    assert checks["wecom_bot_id_configured"] is True
    assert checks["wecom_secret_configured"] is True
    assert checks["webchat_enabled"] is True

    saved = json.loads((workspace_dir / "agent.json").read_text("utf-8"))
    assert saved["channels"]["wecom_tenant"]["bot_id"] == "bot-new"
    assert saved["channels"]["wecom_tenant"]["secret"] == "old-secret"
    assert saved["channels"]["webchat"]["user_data_dir"] == "web-users"
    assert "wx_alice" not in saved.get("agents", {}).get("profiles", {})
    assert len(audit_bus.events) == 2
    assert [event.event_type for event in audit_bus.events] == [
        AuditEventType.TENANT_UPDATED,
        AuditEventType.TENANT_UPDATED,
    ]
    assert audit_bus.events[0].action == "update_entry_config"
    assert audit_bus.events[1].action == "diagnose_entry_config"


async def test_tools_toggle_and_async_execution(api_client, _patch_tenants_root):
    workspace_dir = _patch_tenants_root / "wx_alice"
    write_agent_json(workspace_dir)

    async with api_client:
        list_resp = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/tools",
        )
        toggle_resp = await api_client.patch(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/tools/read_file/toggle",
        )
        async_resp = await api_client.patch(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/tools/read_file/async-execution",
            json={"async_execution": True},
        )

    assert list_resp.status_code == 200
    assert any(item["name"] == "read_file" for item in list_resp.json())
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["enabled"] is False
    assert async_resp.status_code == 200
    assert async_resp.json()["async_execution"] is True


async def test_skills_list_toggle_install_delete(
    api_client,
    _patch_tenants_root,
    monkeypatch,
):
    workspace_dir = _patch_tenants_root / "wx_alice"
    write_agent_json(workspace_dir)
    skill_dir = workspace_dir / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: demo\n---\n# demo\n", "utf-8")
    (workspace_dir / "skill.json").write_text(
        json.dumps(
            {
                "version": 1,
                "skills": {
                    "demo": {
                        "enabled": False,
                        "channels": ["wecom_tenant"],
                        "tags": ["demo"],
                        "requirements": ["requests"],
                        "updated_at": "2026-04-28T00:00:00Z",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    class FakePool:
        def download_to_workspace(self, skill_name, target_workspace, overwrite=False):
            assert skill_name == "demo"
            assert Path(target_workspace) == workspace_dir
            return {"success": True, "name": skill_name}

    monkeypatch.setattr(
        "qwenpaw.app.routers.wecom_tenant_config.feature_config.SkillPoolService",
        lambda: FakePool(),
    )

    async with api_client:
        list_resp = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/skills",
        )
        toggle_resp = await api_client.patch(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/skills/demo/toggle",
        )
        install_resp = await api_client.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/skills/install",
            json={"skill_id": "demo", "overwrite": False},
        )
        delete_resp = await api_client.delete(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/skills/demo",
        )

    assert list_resp.status_code == 200
    assert list_resp.json()[0]["name"] == "demo"
    assert list_resp.json()[0]["channels"] == ["wecom_tenant"]
    assert list_resp.json()[0]["tags"] == ["demo"]
    assert list_resp.json()[0]["requirements"] == ["requests"]
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["enabled"] is True
    assert install_resp.status_code == 200
    assert install_resp.json()["success"] is True
    assert delete_resp.status_code == 200


async def test_uploaded_media_skill_can_be_discovered_and_installed(
    api_client,
    _patch_tenants_root,
    monkeypatch,
):
    workspace_dir = _patch_tenants_root / "wx_alice"
    write_agent_json(workspace_dir)
    media_skill_dir = workspace_dir / "media" / "data-analysis"
    media_skill_dir.mkdir(parents=True)
    (media_skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: Data Analysis\n"
        "description: 数据分析与可视化\n"
        "---\n"
        "# Data Analysis\n",
        encoding="utf-8",
    )

    class FakePool:
        def download_to_workspace(self, skill_name, target_workspace, overwrite=False):
            return {"success": False, "reason": "not_found", "name": skill_name}

    monkeypatch.setattr(
        "qwenpaw.app.routers.wecom_tenant_config.feature_config.SkillPoolService",
        lambda: FakePool(),
    )

    async with api_client:
        list_resp = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/skills",
        )
        install_resp = await api_client.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/skills/install",
            json={"skill_id": "Data Analysis", "overwrite": False},
        )
        installed_resp = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/skills",
        )

    assert list_resp.status_code == 200
    assert list_resp.json() == [
        {
            "name": "Data Analysis",
            "description": "数据分析与可视化",
            "source": "uploaded_media",
            "enabled": False,
            "installed": False,
            "installable": True,
            "channels": [],
            "tags": [],
            "requirements": [],
            "updated_at": None,
            "last_call_at": None,
            "last_call_status": None,
            "last_error_reason": None,
            "last_duration_ms": None,
        }
    ]
    assert install_resp.status_code == 200
    assert install_resp.json()["success"] is True
    installed_skill = installed_resp.json()[0]
    assert installed_skill["name"] == "Data Analysis"
    assert installed_skill["installed"] is True
    assert installed_skill["enabled"] is True
    assert (workspace_dir / "skills" / "Data Analysis" / "SKILL.md").exists()


async def test_mcp_security_and_system_prompts(api_client, _patch_tenants_root):
    workspace_dir = _patch_tenants_root / "wx_alice"
    write_agent_json(workspace_dir)

    async with api_client:
        create_mcp = await api_client.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/mcp",
            json={
                "client_key": "local",
                "client": {
                    "name": "local",
                    "command": "uvx",
                    "args": ["demo"],
                    "env": {"TOKEN": "secret"},
                    "headers": {"Authorization": "Bearer token"},
                },
            },
        )
        toggle_mcp = await api_client.patch(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/mcp/local/toggle",
        )
        put_security = await api_client.put(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/security",
            json={
                "approval_level": "SMART",
                "tool_guard_rules": [{"pattern": "rm -rf.*", "action": "deny"}],
            },
        )
        put_prompts = await api_client.put(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/system-prompts",
            json={"files": ["AGENTS.md", "SOUL.md"]},
        )

    assert create_mcp.status_code == 201
    assert create_mcp.json()["env"] == {"TOKEN": "secret"}
    assert create_mcp.json()["headers"] == {"Authorization": "Bearer token"}
    assert toggle_mcp.status_code == 200
    assert toggle_mcp.json()["enabled"] is False
    assert put_security.status_code == 200
    assert put_security.json()["approval_level"] == "SMART"
    assert put_prompts.status_code == 200
    assert put_prompts.json()["files"] == ["AGENTS.md", "SOUL.md"]


async def test_global_stats_uses_only_wx_tenant_dirs(api_client, _patch_tenants_root):
    (_patch_tenants_root / "wx_a").mkdir(parents=True)
    (_patch_tenants_root / "wx_b").mkdir(parents=True)
    (_patch_tenants_root / "default").mkdir(parents=True)

    async with api_client:
        resp = await api_client.get(
            "/api/config/channels/wecom_tenant/stats/dashboard",
        )

    assert resp.status_code == 200
    assert resp.json()["total_tenants"] == 2


async def test_single_and_global_token_usage(api_client, _patch_tenants_root, monkeypatch):
    for agent_id in ["wx_a", "wx_b"]:
        write_agent_json(_patch_tenants_root / agent_id)

    class FakeTokenManager:
        async def get_summary(
            self,
            start_date=None,
            end_date=None,
            model_name=None,
            provider_id=None,
            agent_id=None,
        ):
            from qwenpaw.token_usage.manager import TokenUsageStats, TokenUsageSummary

            calls = 1 if agent_id == "wx_a" else 2
            return TokenUsageSummary(
                total_prompt_tokens=10 * calls,
                total_completion_tokens=5 * calls,
                total_calls=calls,
                by_date={
                    "2026-04-27": TokenUsageStats(
                        prompt_tokens=10 * calls,
                        completion_tokens=5 * calls,
                        call_count=calls,
                    ),
                },
            )

    monkeypatch.setattr(
        "qwenpaw.app.routers.wecom_tenant_config.monitoring.get_token_usage_manager",
        lambda: FakeTokenManager(),
    )

    async with api_client:
        single = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_a/stats/token-usage",
        )
        global_resp = await api_client.get(
            "/api/config/channels/wecom_tenant/stats/token-usage?agent_ids=wx_a,wx_b",
        )

    assert single.status_code == 200
    assert single.json()["total_calls"] == 1
    assert global_resp.status_code == 200
    assert global_resp.json()["total_calls"] == 3


async def test_agent_stats_single_and_global(api_client, _patch_tenants_root, monkeypatch):
    for agent_id in ["wx_a", "wx_b"]:
        write_agent_json(_patch_tenants_root / agent_id)

    class FakeStatsService:
        async def get_summary(self, workspace_dir, start_date, end_date):
            from qwenpaw.agent_stats.models import AgentStatsSummary

            multiplier = 1 if Path(workspace_dir).name == "wx_a" else 2
            return AgentStatsSummary(
                total_active_sessions=multiplier,
                total_messages=10 * multiplier,
                total_user_messages=6 * multiplier,
                total_assistant_messages=4 * multiplier,
                total_prompt_tokens=0,
                total_completion_tokens=0,
                total_llm_calls=0,
                total_tool_calls=0,
                by_date=[],
                channel_stats=[],
                start_date=str(start_date),
                end_date=str(end_date),
            )

    monkeypatch.setattr(
        "qwenpaw.app.routers.wecom_tenant_config.monitoring.get_agent_stats_service",
        lambda: FakeStatsService(),
    )

    async with api_client:
        single = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_a/stats/agent",
        )
        global_resp = await api_client.get(
            "/api/config/channels/wecom_tenant/stats/agent",
        )

    assert single.status_code == 200
    assert single.json()["total_messages"] == 10
    assert global_resp.status_code == 200
    assert global_resp.json()["total_messages"] == 30


async def test_chat_list_global_and_session_detail(api_client, _patch_tenants_root):
    workspace_dir = _patch_tenants_root / "wx_a"
    write_agent_json(workspace_dir)
    (workspace_dir / "sessions").mkdir()
    (workspace_dir / "sessions" / "s1.json").write_text(
        json.dumps({"messages": [{"role": "user", "content": "hi"}]}),
        encoding="utf-8",
    )
    (workspace_dir / "chats.json").write_text(
        json.dumps(
            {
                "version": 1,
                "chats": [
                    {
                        "id": "c1",
                        "name": "Alice",
                        "session_id": "s1",
                        "user_id": "u1",
                        "channel": "wecom",
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    async with api_client:
        single = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_a/stats/chats",
        )
        detail = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_a/stats/chats/s1",
        )
        global_resp = await api_client.get(
            "/api/config/channels/wecom_tenant/stats/chats",
        )

    assert single.status_code == 200
    assert single.json()["items"][0]["agent_id"] == "wx_a"
    assert detail.status_code == 200
    assert detail.json()["session_id"] == "s1"
    assert global_resp.status_code == 200


async def test_chat_session_detail_resolves_wecom_prefixed_session_file(
    api_client,
    _patch_tenants_root,
):
    workspace_dir = _patch_tenants_root / "wx_6149770745679136778"
    write_agent_json(workspace_dir)
    sessions_dir = workspace_dir / "sessions"
    sessions_dir.mkdir()
    sessions_dir.joinpath(
        "6149770745679136778_wecom--6149770745679136778.json",
    ).write_text(
        json.dumps({"messages": [{"role": "user", "content": "hello"}]}),
        encoding="utf-8",
    )
    (workspace_dir / "chats.json").write_text(
        json.dumps(
            {
                "version": 1,
                "chats": [
                    {
                        "id": "chat-1",
                        "name": "WeCom User",
                        "session_id": "wecom:6149770745679136778",
                        "user_id": "6149770745679136778",
                        "channel": "wecom",
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    async with api_client:
        detail = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/"
            "wx_6149770745679136778/stats/chats/"
            "wecom%3A6149770745679136778",
        )

    assert detail.status_code == 200
    assert detail.json()["session_id"] == "wecom:6149770745679136778"


async def test_delete_tenant_requires_confirm_and_stops_running(
    api_client,
    manager,
    _patch_tenants_root,
):
    workspace_dir = _patch_tenants_root / "wx_alice"
    write_agent_json(workspace_dir)
    manager.loaded.add("wx_alice")

    async with api_client:
        missing_confirm = await api_client.request(
            "DELETE",
            "/api/config/channels/wecom_tenant/tenants/wx_alice",
            json={"confirm": False},
        )
        deleted = await api_client.request(
            "DELETE",
            "/api/config/channels/wecom_tenant/tenants/wx_alice",
            json={"confirm": True},
        )

    assert missing_confirm.status_code == 400
    assert deleted.status_code == 200
    assert manager.stopped == ["wx_alice"]
    assert not workspace_dir.exists()


async def test_batch_start_stop_restart(api_client, manager, _patch_tenants_root):
    for agent_id in ["wx_a", "wx_b"]:
        write_agent_json(_patch_tenants_root / agent_id)

    async with api_client:
        start = await api_client.post(
            "/api/config/channels/wecom_tenant/tenants/batch/start",
            json={"agent_ids": ["wx_a", "wx_b"], "all": False},
        )
        stop = await api_client.post(
            "/api/config/channels/wecom_tenant/tenants/batch/stop",
            json={"all": True},
        )

    assert start.status_code == 200
    assert [item["success"] for item in start.json()["results"]] == [True, True]
    assert stop.status_code == 200


async def test_operations_rejects_cross_tenant_file_write(
    manager,
    _patch_tenants_root,
):
    write_agent_json(_patch_tenants_root / "wx_alice")
    write_agent_json(_patch_tenants_root / "wx_bob")
    client = make_api_client(
        manager,
        tenant_id="alice",
        roles=("tenant_admin",),
    )

    async with client:
        resp = await client.put(
            "/api/config/channels/wecom_tenant/tenants/wx_bob/files/AGENTS.md",
            json={"content": "# hacked"},
        )

    assert resp.status_code == 403
    assert "Tenant boundary" in resp.json()["detail"]
    assert not (_patch_tenants_root / "wx_bob" / "AGENTS.md").exists()


async def test_batch_start_rejects_cross_tenant_for_tenant_admin(
    manager,
    _patch_tenants_root,
):
    write_agent_json(_patch_tenants_root / "wx_alice")
    write_agent_json(_patch_tenants_root / "wx_bob")
    client = make_api_client(
        manager,
        tenant_id="alice",
        roles=("tenant_admin",),
    )

    async with client:
        resp = await client.post(
            "/api/config/channels/wecom_tenant/tenants/batch/start",
            json={"agent_ids": ["wx_alice", "wx_bob"], "all": False},
        )

    assert resp.status_code == 200
    results = {item["agent_id"]: item for item in resp.json()["results"]}
    assert results["wx_alice"]["success"] is True
    assert results["wx_bob"]["success"] is False
    assert "Tenant boundary" in results["wx_bob"]["error"]
    assert manager.started == [("wx_alice", _patch_tenants_root / "wx_alice")]


async def test_workspace_files_and_memory_files_are_path_safe(
    api_client,
    _patch_tenants_root,
):
    workspace_dir = _patch_tenants_root / "wx_alice"
    write_agent_json(workspace_dir)
    (workspace_dir / "AGENTS.md").write_text("# agent", "utf-8")
    (workspace_dir / "memory").mkdir()
    (workspace_dir / "memory" / "profile.json").write_text("{}", "utf-8")

    async with api_client:
        files = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/files",
        )
        read_file = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/files/AGENTS.md",
        )
        blocked = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/files/..%2Fsecret.md",
        )
        memory = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/memory",
        )

    assert files.status_code == 200
    assert files.json()["files"][0]["filename"] == "AGENTS.md"
    assert read_file.json()["content"] == "# agent"
    assert blocked.status_code == 400
    assert memory.json()["files"][0]["filename"] == "profile.json"


async def test_export_and_import_workspace_zip(api_client, _patch_tenants_root):
    workspace_dir = _patch_tenants_root / "wx_alice"
    write_agent_json(workspace_dir)
    (workspace_dir / "AGENTS.md").write_text("# hello", "utf-8")

    async with api_client:
        exported = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/export",
        )

    assert exported.status_code == 200
    assert exported.headers["content-type"] in {
        "application/zip",
        "application/x-zip-compressed",
    }


def cron_payload():
    return {
        "name": "hello",
        "enabled": True,
        "schedule": {"type": "cron", "cron": "*/5 * * * *", "timezone": "UTC"},
        "task_type": "text",
        "text": "hello",
        "dispatch": {
            "type": "channel",
            "channel": "wecom",
            "target": {"user_id": "u1", "session_id": "s1"},
            "mode": "final",
        },
    }


async def test_cron_crud_offline(api_client, _patch_tenants_root):
    workspace_dir = _patch_tenants_root / "wx_alice"
    write_agent_json(workspace_dir)

    async with api_client:
        created = await api_client.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/cron",
            json=cron_payload(),
        )
        job_id = created.json()["id"]
        listed = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/cron",
        )
        deleted = await api_client.delete(
            f"/api/config/channels/wecom_tenant/tenants/wx_alice/cron/{job_id}",
        )

    assert created.status_code == 200
    assert listed.json()[0]["id"] == job_id
    assert deleted.json()["deleted"] is True


async def test_cron_create_emits_tenant_audit(
    manager,
    _patch_tenants_root,
):
    from qwenpaw.enterprise.audit.models import AuditEventType, AuditOutcome

    workspace_dir = _patch_tenants_root / "wx_alice"
    write_agent_json(workspace_dir)
    audit_bus = CaptureBus()
    client = make_api_client(manager, audit_bus=audit_bus)

    async with client:
        resp = await client.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/cron",
            json=cron_payload(),
        )

    assert resp.status_code == 200
    assert len(audit_bus.events) == 1
    event = audit_bus.events[0]
    assert event.event_type == AuditEventType.TENANT_UPDATED
    assert event.outcome == AuditOutcome.SUCCESS
    assert event.action == "create_cron_job"
    assert event.agent_id == "wx_alice"
    assert event.resource_id == f"wx_alice:cron:{resp.json()['id']}"


async def test_health_and_reload(api_client, manager, _patch_tenants_root):
    workspace_dir = _patch_tenants_root / "wx_alice"
    write_agent_json(workspace_dir)
    (workspace_dir / "memory").mkdir()
    (workspace_dir / "sessions").mkdir()
    manager.loaded.add("wx_alice")

    async with api_client:
        health = await api_client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/health",
        )
        all_health = await api_client.get(
            "/api/config/channels/wecom_tenant/health",
        )
        reload_resp = await api_client.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/reload",
        )

    assert health.status_code == 200
    assert health.json()["status"] == "healthy"
    assert all_health.status_code == 200
    assert reload_resp.status_code == 200


async def test_main_router_includes_wecom_tenant_config(manager, _patch_tenants_root):
    from qwenpaw.app.routers import router as main_router

    workspace_dir = _patch_tenants_root / "wx_alice"
    write_agent_json(workspace_dir)
    app = FastAPI()
    app.state.multi_agent_manager = manager
    app.state.enterprise_runtime = SimpleNamespace(authz=_FakeAuthzService())
    app.include_router(main_router, prefix="/api")
    app.add_middleware(_InjectRequestContextMiddleware)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/model",
        )

    assert resp.status_code == 200


# ---------- P3-4: Skills/MCP 最近状态字段 ----------


class _FakeAuditRepoForFeature:
    """In-memory audit repo for feature_config tests."""

    def __init__(self) -> None:
        self._rows: list[SimpleNamespace] = []

    def add_row(self, **kwargs: Any) -> None:
        self._rows.append(SimpleNamespace(**kwargs))

    async def query(self, **kwargs: Any) -> list[SimpleNamespace]:
        results = list(self._rows)
        event_types = kwargs.get("event_types")
        if event_types:
            results = [r for r in results if r.event_type in event_types]
        agent_id = kwargs.get("agent_id")
        if agent_id:
            results = [r for r in results if r.agent_id == agent_id]
        resource_id = kwargs.get("resource_id")
        if resource_id:
            results = [r for r in results if getattr(r, "resource_id", "") == resource_id]
        limit = kwargs.get("limit", 100)
        results.sort(key=lambda r: getattr(r, "created_at", datetime.min), reverse=True)
        return results[:limit]


@pytest.fixture
def audit_repo_for_feature():
    return _FakeAuditRepoForFeature()


@pytest.fixture
def api_client_with_audit(manager, audit_repo_for_feature):
    """带审计仓储的 API 客户端，用于 Skills/MCP 最近状态测试。"""
    app = FastAPI()
    app.state.multi_agent_manager = manager
    app.state.enterprise_runtime = SimpleNamespace(
        authz=_FakeAuthzService(),
        audit=SimpleNamespace(_repository=audit_repo_for_feature),
        storage=SimpleNamespace(session_factory=None),
    )
    app.include_router(router, prefix="/api")
    app.add_middleware(_InjectRequestContextMiddleware)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_list_skills_includes_recent_call_status(
    api_client_with_audit, audit_repo_for_feature, _patch_tenants_root
):
    """Skill 列表包含最近调用状态。"""
    workspace_dir = _patch_tenants_root / "wx_alice"
    write_agent_json(workspace_dir)
    skill_dir = workspace_dir / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: demo\n---\n# demo\n", "utf-8")
    (workspace_dir / "skill.json").write_text(
        json.dumps(
            {
                "version": 1,
                "skills": {"demo": {"enabled": True}},
            }
        ),
        encoding="utf-8",
    )

    # 添加一个 skill.called 审计事件
    audit_repo_for_feature.add_row(
        event_type="skill.called",
        action="call",
        outcome="success",
        agent_id="wx_alice",
        resource_id="demo",
        payload={
            "ability_name": "demo",
            "ability_type": "skill",
            "status": "success",
            "duration_ms": 150.0,
            "error_reason": "",
        },
        created_at=datetime.now(timezone.utc),
    )

    async with api_client_with_audit:
        resp = await api_client_with_audit.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/skills",
        )

    assert resp.status_code == 200
    skills = resp.json()
    demo_skill = next(s for s in skills if s["name"] == "demo")
    assert demo_skill["last_call_status"] == "success"
    assert demo_skill["last_duration_ms"] == 150.0
    assert demo_skill["last_error_reason"] is None


async def test_list_mcp_includes_last_connection_test(
    api_client_with_audit, audit_repo_for_feature, _patch_tenants_root
):
    """MCP 列表包含最近连接测试结果。"""
    workspace_dir = _patch_tenants_root / "wx_alice"
    write_agent_json(workspace_dir)

    # 添加 mcp.connection_test 审计事件（在请求前准备好）
    audit_repo_for_feature.add_row(
        event_type="mcp.connection_test",
        action="test",
        outcome="success",
        agent_id="wx_alice",
        resource_id="local",
        payload={
            "status": "ok",
            "duration_ms": 300.0,
            "detail": "",
        },
        created_at=datetime.now(timezone.utc),
    )

    async with api_client_with_audit:
        # 创建 MCP 客户端
        create_resp = await api_client_with_audit.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/mcp",
            json={
                "client_key": "local",
                "client": {
                    "name": "local",
                    "command": "uvx",
                    "args": ["demo"],
                },
            },
        )
        assert create_resp.status_code == 201

        # 获取列表
        resp = await api_client_with_audit.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/mcp",
        )

    assert resp.status_code == 200
    mcps = resp.json()
    local_mcp = next(m for m in mcps if m["client_key"] == "local")
    assert local_mcp["last_test_status"] == "ok"


async def test_list_mcp_includes_recent_call_status_by_mcp_name(
    api_client_with_audit, audit_repo_for_feature, _patch_tenants_root
):
    """MCP 列表按 mcp_name/resource_id 前缀匹配最近调用状态。"""
    workspace_dir = _patch_tenants_root / "wx_alice"
    write_agent_json(workspace_dir)
    audit_repo_for_feature.add_row(
        event_type="mcp.called",
        action="call",
        outcome="failure",
        agent_id="wx_alice",
        resource_id="local/query",
        payload={
            "mcp_name": "local",
            "ability_name": "local/query",
            "ability_type": "mcp",
            "status": "failure",
            "duration_ms": 120.0,
            "error_reason": "timeout",
        },
        created_at=datetime.now(timezone.utc),
    )

    async with api_client_with_audit:
        create_resp = await api_client_with_audit.post(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/mcp",
            json={
                "client_key": "local",
                "client": {
                    "name": "local",
                    "command": "uvx",
                    "args": ["demo"],
                },
            },
        )
        assert create_resp.status_code == 201

        resp = await api_client_with_audit.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/mcp",
        )

    assert resp.status_code == 200
    local_mcp = next(m for m in resp.json() if m["client_key"] == "local")
    assert local_mcp["last_call_status"] == "failure"
    assert local_mcp["last_error_reason"] == "timeout"


async def test_list_skills_without_runtime_returns_none_fields(
    manager, _patch_tenants_root
):
    """无 runtime 时字段为 None，不阻断页面。"""
    workspace_dir = _patch_tenants_root / "wx_alice"
    write_agent_json(workspace_dir)
    skill_dir = workspace_dir / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: demo\n---\n# demo\n", "utf-8")
    (workspace_dir / "skill.json").write_text(
        json.dumps(
            {
                "version": 1,
                "skills": {"demo": {"enabled": True}},
            }
        ),
        encoding="utf-8",
    )

    app = FastAPI()
    app.state.multi_agent_manager = manager
    app.state.enterprise_runtime = SimpleNamespace(authz=_FakeAuthzService())
    app.include_router(router, prefix="/api")
    app.add_middleware(_InjectRequestContextMiddleware)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/config/channels/wecom_tenant/tenants/wx_alice/skills",
        )

    assert resp.status_code == 200
    skills = resp.json()
    demo_skill = next(s for s in skills if s["name"] == "demo")
    assert demo_skill["last_call_at"] is None
    assert demo_skill["last_call_status"] is None
    assert demo_skill["last_error_reason"] is None
    assert demo_skill["last_duration_ms"] is None
