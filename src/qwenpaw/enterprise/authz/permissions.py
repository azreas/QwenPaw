# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Tuple

# 公开路径（精确匹配）：不需要 Authz 权限检查
# 与 AuthMiddleware._PUBLIC_PATHS 保持一致
_PUBLIC_EXACT: frozenset[str] = frozenset({
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/status",
    "/api/auth/verify",
    "/api/version",
    "/api/settings/language",
    "/api/enterprise/readiness",
    "/api/mcp/oauth/callback",
})

# 公开路径前缀：不需要 Authz 权限检查
# 与 AuthMiddleware._PUBLIC_PREFIXES 保持一致
_PUBLIC_PREFIXES: frozenset[str] = frozenset({
    "/api/webchat/login",
    "/api/webchat/qrcode",
    "/api/webchat/status",
    "/api/webchat/verify",
})

# 静态资源前缀
_STATIC_PREFIXES: frozenset[str] = frozenset({
    "/assets/",
    "/logo.png",
    "/qwenpaw-symbol.svg",
})

# 受保护路由规则：(path_prefix, read_perm, write_perm)
_ROUTE_RULES: list[Tuple[str, str, str]] = [
    ("/api/audit", "audit", "audit"),
    ("/api/platform", "platform", "platform"),
    ("/api/wecom-tenants", "tenant", "tenant"),
    ("/api/webchat", "webchat", "webchat"),
    ("/api/agents", "agents", "agents"),
    ("/api/agent", "agents", "agents"),
    ("/api/agent-stats", "agents", "agents"),
    ("/api/settings", "settings", "settings"),
    # wecom_tenant 动态租户管理路由必须排在 /api/config 之前，
    # 否则 AuthzMiddleware 会先命中 settings 资源，导致 tenant_admin
    # 即使持有 tenant:* 也被拒（P3-2 路由修正）。
    ("/api/config/channels/wecom_tenant", "tenant", "tenant"),
    ("/api/config", "settings", "settings"),
    ("/api/console", "console", "console"),
    ("/api/chats", "chats", "chats"),
    ("/api/local-models", "models", "models"),
    ("/api/models", "models", "models"),
    ("/api/mcp", "mcp", "mcp"),
    ("/api/messages", "messages", "messages"),
    ("/api/plugins", "plugins", "plugins"),
    ("/api/skills", "skills", "skills"),
    ("/api/tools", "tools", "tools"),
    ("/api/workspace", "workspace", "workspace"),
    ("/api/envs", "envs", "envs"),
    ("/api/token-usage", "usage", "usage"),
    ("/api/auth/users", "auth_users", "auth_users"),
    ("/api/auth", "auth", "auth"),
    ("/api/files", "files", "files"),
    ("/api/backups", "backup", "backup"),
    ("/api/quota", "platform", "platform"),
    ("/api/plan", "plan", "plan"),
    ("/api/approval", "approval", "approval"),
    ("/api/doctor", "diagnostics", "diagnostics"),
    ("/api/cron", "cron", "cron"),
    ("/api/metrics", "platform", "platform"),
    ("/api/compliance", "platform", "platform"),
    ("/api/evaluation", "tenant", "tenant"),
]

_WRITE_METHODS: frozenset[str] = frozenset({
    "POST", "PUT", "PATCH", "DELETE",
})


def resolve_route_permission(
    method: str,
    path: str,
) -> Tuple[str, str] | None:
    """解析路由所需权限，返回 (resource, action) 或 None（公开路由）。"""
    # 非 API 路径不做权限检查
    if not path.startswith("/api/"):
        # 静态资源放行
        if any(path.startswith(p) for p in _STATIC_PREFIXES):
            return None
        if path in ("/", "/docs", "/redoc", "/openapi.json"):
            return None
        return None

    # 精确匹配公开路径
    if path in _PUBLIC_EXACT:
        return None

    # 前缀匹配公开路径
    for prefix in _PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return None

    # 受保护路由匹配
    for route_prefix, read_resource, write_resource in _ROUTE_RULES:
        if path == route_prefix or path.startswith(route_prefix + "/"):
            if method.upper() in _WRITE_METHODS:
                return (write_resource, "write")
            return (read_resource, "read")

    # 未知 API 路由：需要权限
    return ("unknown", "read")
