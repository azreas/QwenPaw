# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Permission:
    resource: str
    action: str

    def matches(self, resource: str, action: str) -> bool:
        if self.resource == "*" and self.action == "*":
            return True
        if self.resource == "*" and self.action == action:
            return True
        if self.resource == resource and self.action == "*":
            return True
        return self.resource == resource and self.action == action


@dataclass(frozen=True, slots=True)
class Role:
    name: str
    permissions: frozenset[Permission] = frozenset()

    def has_permission(self, resource: str, action: str) -> bool:
        return any(p.matches(resource, action) for p in self.permissions)


@dataclass(frozen=True, slots=True)
class EnterpriseUser:
    user_id: str
    roles: tuple[str, ...] = ()
    tenant_id: str = ""


def _p(resource: str, action: str) -> Permission:
    return Permission(resource=resource, action=action)


_DEFAULT_ROLE_DEFINITIONS: dict[str, tuple[str, ...]] = {
    "platform_admin": ("*:*",),
    "tenant_admin": (
        "tenant:*",
        "agents:*",
        "webchat:*",
        "skills:*",
        "mcp:*",
        "audit:read",
        "auth_users:read",
        "auth_users:write",
        "tasks:*",
    ),
    "tenant_member": (
        "webchat:read",
        "webchat:write",
        "skills:call",
        "mcp:call",
        "tasks:read",
    ),
    "tenant_readonly": (
        "webchat:read",
        "audit:read",
        "tasks:read",
    ),
}


def _parse_permission(spec: str) -> Permission:
    resource, _, action = spec.partition(":")
    return _p(resource, action)


def _build_default_roles() -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for name, specs in _DEFAULT_ROLE_DEFINITIONS.items():
        perms = frozenset(_parse_permission(s) for s in specs)
        roles[name] = Role(name=name, permissions=perms)
    return roles


DEFAULT_ROLES: dict[str, Role] = _build_default_roles()
