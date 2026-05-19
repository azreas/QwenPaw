"""审计 emit 路由级测试 — 验证 config.updated / tenant.updated 事件。

通过 monkeypatch + CaptureBus 验证端点成功写入后 emit 了正确的事件类型、
action 和 resource_id。
"""

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qwenpaw.enterprise.audit.models import AuditEventType, AuditOutcome


class CaptureBus:
    """捕获 emit 到审计总线的事件。"""

    def __init__(self):
        self.events = []

    async def emit(self, event):
        self.events.append(event)


def _make_app_with_audit(router, capture_bus: CaptureBus) -> FastAPI:
    """创建带 mock enterprise_runtime.audit 的测试 FastAPI app。"""
    runtime = MagicMock()
    runtime.audit = capture_bus
    app = FastAPI()
    app.state.enterprise_runtime = runtime
    app.include_router(router, prefix="/api")
    return app


# ── Config 写端点 ──────────────────────────────────────────────────────────


class TestConfigRouteAuditEmit:
    """配置变更路由的审计事件 emit 测试。"""

    def test_put_tool_guard_emits_config_updated(self, monkeypatch):
        """PUT /config/security/tool-guard → CONFIG_UPDATED。"""
        from qwenpaw.app.routers.config import router as config_router
        from qwenpaw.config.config import ToolGuardConfig

        # Mock load/save config + engine
        mock_cfg = MagicMock()
        mock_cfg.security.tool_guard = ToolGuardConfig(enabled=True, rules=[])
        monkeypatch.setattr(
            "qwenpaw.app.routers.config.load_config",
            lambda: mock_cfg,
        )
        monkeypatch.setattr(
            "qwenpaw.app.routers.config.save_config",
            lambda config, config_path=None: None,
        )
        monkeypatch.setattr(
            "qwenpaw.security.tool_guard.engine.get_guard_engine",
            lambda: MagicMock(),
        )

        bus = CaptureBus()
        app = _make_app_with_audit(config_router, bus)
        client = TestClient(app)

        resp = client.put(
            "/api/config/security/tool-guard",
            json={"enabled": True, "rules": []},
        )
        assert resp.status_code == 200
        assert len(bus.events) == 1
        e = bus.events[0]
        assert e.event_type == AuditEventType.CONFIG_UPDATED
        assert e.action == "update_tool_guard"
        assert e.resource_id == "security.tool_guard"
        assert e.payload.get("changed_key") == "security.tool_guard"

    def test_put_file_guard_emits_config_updated(self, monkeypatch):
        """PUT /config/security/file-guard → CONFIG_UPDATED。"""
        from qwenpaw.app.routers.config import router as config_router

        mock_cfg = MagicMock()
        monkeypatch.setattr(
            "qwenpaw.app.routers.config.load_config",
            lambda: mock_cfg,
        )
        monkeypatch.setattr(
            "qwenpaw.app.routers.config.save_config",
            lambda config, config_path=None: None,
        )
        monkeypatch.setattr(
            "qwenpaw.security.tool_guard.engine.get_guard_engine",
            lambda: MagicMock(),
        )

        bus = CaptureBus()
        app = _make_app_with_audit(config_router, bus)
        client = TestClient(app)

        resp = client.put(
            "/api/config/security/file-guard",
            json={"enabled": False, "paths": ["/etc/passwd"]},
        )
        assert resp.status_code == 200
        assert len(bus.events) == 1
        e = bus.events[0]
        assert e.event_type == AuditEventType.CONFIG_UPDATED
        assert e.action == "update_file_guard"
        assert e.resource_id == "security.file_guard"

    def test_put_skill_scanner_emits_config_updated(self, monkeypatch):
        """PUT /config/security/skill-scanner → CONFIG_UPDATED。"""
        from qwenpaw.app.routers.config import router as config_router
        from qwenpaw.config.config import SkillScannerConfig

        mock_cfg = MagicMock()
        mock_cfg.security.skill_scanner = SkillScannerConfig(enabled=True)
        monkeypatch.setattr(
            "qwenpaw.app.routers.config.load_config",
            lambda: mock_cfg,
        )
        monkeypatch.setattr(
            "qwenpaw.app.routers.config.save_config",
            lambda config, config_path=None: None,
        )

        bus = CaptureBus()
        app = _make_app_with_audit(config_router, bus)
        client = TestClient(app)

        resp = client.put(
            "/api/config/security/skill-scanner",
            json={"enabled": True},
        )
        assert resp.status_code == 200
        assert len(bus.events) == 1
        e = bus.events[0]
        assert e.event_type == AuditEventType.CONFIG_UPDATED
        assert e.action == "update_skill_scanner"
        assert e.resource_id == "security.skill_scanner"

    def test_put_allow_no_auth_hosts_emits_config_updated(self, monkeypatch):
        """PUT /config/security/allow-no-auth-hosts → CONFIG_UPDATED。"""
        from qwenpaw.app.routers.config import router as config_router

        mock_cfg = MagicMock()
        monkeypatch.setattr(
            "qwenpaw.app.routers.config.load_config",
            lambda: mock_cfg,
        )
        monkeypatch.setattr(
            "qwenpaw.app.routers.config.save_config",
            lambda config, config_path=None: None,
        )

        bus = CaptureBus()
        app = _make_app_with_audit(config_router, bus)
        client = TestClient(app)

        resp = client.put(
            "/api/config/security/allow-no-auth-hosts",
            json={"hosts": ["192.168.1.1"]},
        )
        assert resp.status_code == 200
        assert len(bus.events) == 1
        e = bus.events[0]
        assert e.event_type == AuditEventType.CONFIG_UPDATED
        assert e.action == "update_allow_no_auth_hosts"
        assert e.resource_id == "security.allow_no_auth_hosts"

    def test_put_user_timezone_emits_config_updated(self, monkeypatch):
        """PUT /config/user-timezone → CONFIG_UPDATED。"""
        from qwenpaw.app.routers.config import router as config_router

        mock_cfg = MagicMock()
        monkeypatch.setattr(
            "qwenpaw.app.routers.config.load_config",
            lambda: mock_cfg,
        )
        monkeypatch.setattr(
            "qwenpaw.app.routers.config.save_config",
            lambda config, config_path=None: None,
        )

        bus = CaptureBus()
        app = _make_app_with_audit(config_router, bus)
        client = TestClient(app)

        resp = client.put(
            "/api/config/user-timezone",
            json={"timezone": "Asia/Shanghai"},
        )
        assert resp.status_code == 200
        assert len(bus.events) == 1
        e = bus.events[0]
        assert e.event_type == AuditEventType.CONFIG_UPDATED
        assert e.action == "update_timezone"
        assert e.resource_id == "user_timezone"

    def test_add_to_whitelist_emits_config_updated(self, monkeypatch):
        """POST /config/security/skill-scanner/whitelist → CONFIG_UPDATED。"""
        from qwenpaw.app.routers.config import router as config_router
        from qwenpaw.config.config import SkillScannerConfig

        scanner_cfg = SkillScannerConfig(enabled=True)
        mock_cfg = MagicMock()
        mock_cfg.security.skill_scanner = scanner_cfg
        monkeypatch.setattr(
            "qwenpaw.app.routers.config.load_config",
            lambda: mock_cfg,
        )
        monkeypatch.setattr(
            "qwenpaw.app.routers.config.save_config",
            lambda config, config_path=None: None,
        )

        bus = CaptureBus()
        app = _make_app_with_audit(config_router, bus)
        client = TestClient(app)

        resp = client.post(
            "/api/config/security/skill-scanner/whitelist",
            json={"skill_name": "my-custom-skill", "content_hash": "abc123"},
        )
        assert resp.status_code == 200
        assert len(bus.events) == 1
        e = bus.events[0]
        assert e.event_type == AuditEventType.CONFIG_UPDATED
        assert e.action == "whitelist_add"
        assert e.resource_id == "security.skill_scanner.whitelist"
        assert e.payload.get("skill_name") == "my-custom-skill"
        assert e.payload.get("has_content_hash") is True

    def test_remove_from_whitelist_emits_config_updated(self, monkeypatch):
        """DELETE /config/security/skill-scanner/whitelist/{name} → CONFIG_UPDATED。"""
        from qwenpaw.app.routers.config import router as config_router
        from qwenpaw.config.config import (
            SkillScannerConfig,
            SkillScannerWhitelistEntry,
        )

        scanner_cfg = SkillScannerConfig(enabled=True)
        scanner_cfg.whitelist.append(
            SkillScannerWhitelistEntry(
                skill_name="old-skill",
                content_hash="",
                added_at="2026-01-01T00:00:00+00:00",
            )
        )
        mock_cfg = MagicMock()
        mock_cfg.security.skill_scanner = scanner_cfg
        monkeypatch.setattr(
            "qwenpaw.app.routers.config.load_config",
            lambda: mock_cfg,
        )
        monkeypatch.setattr(
            "qwenpaw.app.routers.config.save_config",
            lambda config, config_path=None: None,
        )

        bus = CaptureBus()
        app = _make_app_with_audit(config_router, bus)
        client = TestClient(app)

        resp = client.delete(
            "/api/config/security/skill-scanner/whitelist/old-skill",
        )
        assert resp.status_code == 200
        assert len(bus.events) == 1
        e = bus.events[0]
        assert e.event_type == AuditEventType.CONFIG_UPDATED
        assert e.action == "whitelist_remove"
        assert e.resource_id == "security.skill_scanner.whitelist"
        assert e.payload.get("skill_name") == "old-skill"


# ── Tenant 写端点 ───────────────────────────────────────────────────────────


class TestTenantRouteAuditEmit:
    """租户操作路由的审计事件 emit 测试。"""

    def test_upsert_policy_emits_tenant_updated(self, monkeypatch):
        """PUT /platform/tenancy/policies/{id} → TENANT_UPDATED。"""
        from qwenpaw.app.routers.platform_tenancy import router as tenant_router
        from qwenpaw.tenancy.product_models import TenantPolicy
        from qwenpaw.tenancy.product_store import TenantProductStore

        # Mock store
        mock_policy = TenantPolicy(policy_id="test-policy", name="test")
        mock_store = MagicMock(spec=TenantProductStore)
        mock_store.upsert_policy.return_value = mock_policy
        monkeypatch.setattr(
            "qwenpaw.app.routers.platform_tenancy.TenantProductStore",
            lambda: mock_store,
        )

        bus = CaptureBus()
        app = _make_app_with_audit(tenant_router, bus)
        client = TestClient(app)

        resp = client.put(
            "/api/platform/tenancy/policies/test-policy",
            json={"policy_id": "test-policy", "name": "test"},
        )
        assert resp.status_code == 200
        assert len(bus.events) == 1
        e = bus.events[0]
        assert e.event_type == AuditEventType.TENANT_UPDATED
        assert e.action == "upsert_policy"
        assert e.resource_id == "test-policy"

    def test_delete_policy_emits_tenant_updated(self, monkeypatch):
        """DELETE /platform/tenancy/policies/{id} → TENANT_UPDATED。"""
        from qwenpaw.app.routers.platform_tenancy import router as tenant_router
        from qwenpaw.tenancy.product_models import TenantPolicy
        from qwenpaw.tenancy.product_store import TenantProductStore

        mock_store = MagicMock(spec=TenantProductStore)
        mock_store.list_tenants.return_value = []
        mock_store.delete_policy.return_value = True
        monkeypatch.setattr(
            "qwenpaw.app.routers.platform_tenancy.TenantProductStore",
            lambda: mock_store,
        )

        bus = CaptureBus()
        app = _make_app_with_audit(tenant_router, bus)
        client = TestClient(app)

        resp = client.delete("/api/platform/tenancy/policies/custom-policy")
        assert resp.status_code == 200
        assert len(bus.events) == 1
        e = bus.events[0]
        assert e.event_type == AuditEventType.TENANT_UPDATED
        assert e.action == "delete_policy"
        assert e.resource_id == "custom-policy"

    def test_upsert_template_emits_tenant_updated(self, monkeypatch):
        """PUT /platform/tenancy/templates/{id} → TENANT_UPDATED。"""
        from qwenpaw.app.routers.platform_tenancy import router as tenant_router
        from qwenpaw.tenancy.product_models import TenantTemplate
        from qwenpaw.tenancy.product_store import TenantProductStore

        mock_template = TenantTemplate(template_id="test-tpl", name="test")
        mock_store = MagicMock(spec=TenantProductStore)
        mock_store.upsert_template.return_value = mock_template
        monkeypatch.setattr(
            "qwenpaw.app.routers.platform_tenancy.TenantProductStore",
            lambda: mock_store,
        )

        bus = CaptureBus()
        app = _make_app_with_audit(tenant_router, bus)
        client = TestClient(app)

        resp = client.put(
            "/api/platform/tenancy/templates/test-tpl",
            json={"template_id": "test-tpl", "name": "test"},
        )
        assert resp.status_code == 200
        assert len(bus.events) == 1
        e = bus.events[0]
        assert e.event_type == AuditEventType.TENANT_UPDATED
        assert e.action == "upsert_template"
        assert e.resource_id == "test-tpl"
