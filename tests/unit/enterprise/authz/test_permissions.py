# -*- coding: utf-8 -*-
from qwenpaw.enterprise.authz.permissions import resolve_route_permission


def test_public_auth_routes_are_unprotected():
    assert resolve_route_permission("POST", "/api/auth/login") is None
    assert resolve_route_permission("GET", "/api/auth/status") is None


def test_public_webchat_login_routes():
    assert resolve_route_permission("POST", "/api/webchat/login") is None
    assert resolve_route_permission("POST", "/api/webchat/login/qrcode") is None
    assert resolve_route_permission("GET", "/api/webchat/qrcode/config") is None
    assert resolve_route_permission("GET", "/api/webchat/status") is None


def test_platform_routes_require_platform_permission():
    permission = resolve_route_permission("GET", "/api/platform/tenants")
    assert permission == ("platform", "read")


def test_audit_routes_require_audit_read():
    permission = resolve_route_permission("GET", "/api/audit/events")
    assert permission == ("audit", "read")


def test_quota_routes_are_platform_only():
    assert resolve_route_permission("GET", "/api/quota/summary") == (
        "platform",
        "read",
    )
    assert resolve_route_permission("POST", "/api/quota/adjustments") == (
        "platform",
        "write",
    )


def test_platform_policy_routes_are_platform_only():
    assert resolve_route_permission(
        "GET", "/api/platform/tenancy/policies",
    ) == ("platform", "read")
    assert resolve_route_permission(
        "PUT", "/api/platform/tenancy/policies/default",
    ) == ("platform", "write")
    assert resolve_route_permission(
        "DELETE", "/api/platform/tenancy/policies/default",
    ) == ("platform", "write")


def test_permission_denial_review_keeps_audit_read_protection():
    assert resolve_route_permission("GET", "/api/audit/events") == (
        "audit",
        "read",
    )
    assert resolve_route_permission("GET", "/api/audit/business-calls") == (
        "audit",
        "read",
    )


def test_auth_user_management_routes_use_auth_users_resource():
    assert resolve_route_permission("GET", "/api/auth/users") == (
        "auth_users",
        "read",
    )
    assert resolve_route_permission("POST", "/api/auth/users") == (
        "auth_users",
        "write",
    )
    assert resolve_route_permission("PATCH", "/api/auth/users/acme-admin") == (
        "auth_users",
        "write",
    )
    assert resolve_route_permission("POST", "/api/auth/revoke-all-tokens") == (
        "auth",
        "write",
    )


def test_agents_routes():
    assert resolve_route_permission("GET", "/api/agents") == ("agents", "read")
    assert resolve_route_permission("POST", "/api/agents") == ("agents", "write")


def test_wecom_tenants_routes():
    assert resolve_route_permission("GET", "/api/wecom-tenants") == ("tenant", "read")
    assert resolve_route_permission("POST", "/api/wecom-tenants") == ("tenant", "write")


def test_non_api_routes_are_unprotected():
    assert resolve_route_permission("GET", "/") is None
    assert resolve_route_permission("GET", "/assets/main.js") is None
    assert resolve_route_permission("GET", "/webchat") is None


def test_health_and_docs_unprotected():
    assert resolve_route_permission("GET", "/api/version") is None
    assert resolve_route_permission("GET", "/docs") is None
    assert resolve_route_permission("GET", "/openapi.json") is None


# --- 对齐 AuthMiddleware 公共路径 ---

def test_settings_language_unprotected():
    """AuthMiddleware _PUBLIC_PATHS 中的 /api/settings/language 必须放行。"""
    assert resolve_route_permission("GET", "/api/settings/language") is None


def test_mcp_oauth_callback_unprotected():
    """/api/mcp/oauth/callback 必须放行（第三方 OAuth redirect）。"""
    assert resolve_route_permission("GET", "/api/mcp/oauth/callback") is None


def test_plugins_routes_protected():
    """/api/plugins 现在受 RBAC 保护（install/upload/delete 是写操作）。"""
    assert resolve_route_permission("GET", "/api/plugins") == ("plugins", "read")
    assert resolve_route_permission("POST", "/api/plugins/install") == ("plugins", "write")
    assert resolve_route_permission("DELETE", "/api/plugins/foo") == ("plugins", "write")


def test_settings_write_protected():
    """/api/settings 非公开子路径需要权限。"""
    assert resolve_route_permission("PUT", "/api/settings/other") == ("settings", "write")


def test_platform_settings_summary_protected():
    """GET /api/settings/platform-summary 必须受 RBAC 保护。"""
    assert resolve_route_permission(
        "GET",
        "/api/settings/platform-summary",
    ) == ("settings", "read")


def test_static_assets_unprotected():
    """AuthMiddleware _PUBLIC_PREFIXES 中的静态资源放行。"""
    assert resolve_route_permission("GET", "/assets/main.js") is None
    assert resolve_route_permission("GET", "/logo.png") is None
    assert resolve_route_permission("GET", "/qwenpaw-symbol.svg") is None


# ── P3-2: wecom_tenant 路由修正 ─────────────────────────────


def test_wecom_tenant_config_routes_map_to_tenant_resource():
    """/api/config/channels/wecom_tenant 必须映射到 tenant 资源（非 settings）。"""
    assert resolve_route_permission(
        "GET", "/api/config/channels/wecom_tenant/tenants/wx_acme/skills",
    ) == ("tenant", "read")
    assert resolve_route_permission(
        "POST", "/api/config/channels/wecom_tenant/tenants/wx_acme/mcp",
    ) == ("tenant", "write")
    assert resolve_route_permission(
        "PATCH", "/api/config/channels/wecom_tenant/tenants/wx_acme/skills/demo/toggle",
    ) == ("tenant", "write")


def test_wecom_tenant_health_maps_to_tenant():
    """wecom_tenant health 也应映射到 tenant 资源。"""
    assert resolve_route_permission(
        "GET", "/api/config/channels/wecom_tenant/tenants/wx_acme/health",
    ) == ("tenant", "read")


def test_other_config_routes_still_map_to_settings():
    """只有 wecom_tenant 前缀路由映射到 tenant；其他 /api/config/* 仍在 settings。"""
    assert resolve_route_permission("GET", "/api/config/agents") == (
        "settings", "read",
    )
    assert resolve_route_permission("PUT", "/api/config/agents/default") == (
        "settings", "write",
    )


def test_core_api_groups_are_explicitly_protected():
    assert resolve_route_permission("GET", "/api/config/agents") == (
        "settings",
        "read",
    )
    assert resolve_route_permission("PUT", "/api/config/agents/default") == (
        "settings",
        "write",
    )
    assert resolve_route_permission("GET", "/api/mcp/clients") == ("mcp", "read")
    assert resolve_route_permission("POST", "/api/skills") == ("skills", "write")
    assert resolve_route_permission("POST", "/api/approval/approve") == (
        "approval",
        "write",
    )
    assert resolve_route_permission("GET", "/api/doctor/runtime") == (
        "diagnostics",
        "read",
    )
