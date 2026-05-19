# -*- coding: utf-8 -*-
from qwenpaw.enterprise.authz.models import Permission, DEFAULT_ROLES


def test_permission_wildcard_matches():
    assert Permission("agents", "*").matches("agents", "read")
    assert Permission("*", "*").matches("audit", "read")
    assert not Permission("agents", "read").matches("agents", "write")


def test_permission_exact_match():
    assert Permission("agents", "read").matches("agents", "read")
    assert not Permission("agents", "read").matches("agents", "write")
    assert not Permission("agents", "read").matches("webchat", "read")


def test_default_roles_exist():
    assert "platform_admin" in DEFAULT_ROLES
    assert "tenant_admin" in DEFAULT_ROLES
    assert "tenant_member" in DEFAULT_ROLES
    assert "tenant_readonly" in DEFAULT_ROLES


def test_platform_admin_has_wildcard():
    role = DEFAULT_ROLES["platform_admin"]
    assert any(p.resource == "*" and p.action == "*" for p in role.permissions)


def test_tenant_admin_permissions():
    role = DEFAULT_ROLES["tenant_admin"]
    resources = {p.resource for p in role.permissions}
    assert "tenant" in resources
    assert "agents" in resources
