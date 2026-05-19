# -*- coding: utf-8 -*-
"""P3-2 RBAC 资源权限：skills / mcp / audit 角色权限覆盖。"""
import pytest

from qwenpaw.enterprise.authz.models import (
    DEFAULT_ROLES,
    EnterpriseUser,
    Permission,
    Role,
)


# ── 角色存在性 ──────────────────────────────────────────────

def test_all_roles_present():
    for name in (
        "platform_admin",
        "tenant_admin",
        "tenant_member",
        "tenant_readonly",
    ):
        assert name in DEFAULT_ROLES


# ── platform_admin 保持 *:* ──────────────────────────────────

def test_platform_admin_has_wildcard():
    role = DEFAULT_ROLES["platform_admin"]
    assert any(p.resource == "*" and p.action == "*" for p in role.permissions)


def test_platform_admin_can_call_skills():
    role = DEFAULT_ROLES["platform_admin"]
    assert role.has_permission("skills", "call")


def test_platform_admin_can_call_mcp():
    role = DEFAULT_ROLES["platform_admin"]
    assert role.has_permission("mcp", "call")


def test_platform_admin_can_manage_skills():
    role = DEFAULT_ROLES["platform_admin"]
    assert role.has_permission("skills", "write")
    assert role.has_permission("skills", "read")


def test_platform_admin_can_read_audit():
    role = DEFAULT_ROLES["platform_admin"]
    assert role.has_permission("audit", "read")


# ── tenant_admin Skills/MCP/审计权限 ─────────────────────────

def test_tenant_admin_skills_full():
    role = DEFAULT_ROLES["tenant_admin"]
    assert role.has_permission("skills", "read")
    assert role.has_permission("skills", "write")
    assert role.has_permission("skills", "call")


def test_tenant_admin_mcp_full():
    role = DEFAULT_ROLES["tenant_admin"]
    assert role.has_permission("mcp", "read")
    assert role.has_permission("mcp", "write")
    assert role.has_permission("mcp", "call")
    assert role.has_permission("mcp", "test")


def test_tenant_admin_audit_read():
    role = DEFAULT_ROLES["tenant_admin"]
    assert role.has_permission("audit", "read")


def test_tenant_admin_cannot_write_audit():
    role = DEFAULT_ROLES["tenant_admin"]
    assert not role.has_permission("audit", "write")


# ── tenant_member 调用权限 ───────────────────────────────────

def test_tenant_member_can_call_skills():
    role = DEFAULT_ROLES["tenant_member"]
    assert role.has_permission("skills", "call")


def test_tenant_member_can_call_mcp():
    role = DEFAULT_ROLES["tenant_member"]
    assert role.has_permission("mcp", "call")


def test_tenant_member_cannot_manage_skills():
    role = DEFAULT_ROLES["tenant_member"]
    assert not role.has_permission("skills", "read")
    assert not role.has_permission("skills", "write")


def test_tenant_member_cannot_manage_mcp():
    role = DEFAULT_ROLES["tenant_member"]
    assert not role.has_permission("mcp", "read")
    assert not role.has_permission("mcp", "write")
    assert not role.has_permission("mcp", "test")


def test_tenant_member_cannot_read_audit():
    role = DEFAULT_ROLES["tenant_member"]
    assert not role.has_permission("audit", "read")


# ── tenant_readonly 无 call/manage 权限 ──────────────────────

def test_tenant_readonly_cannot_call_skills():
    role = DEFAULT_ROLES["tenant_readonly"]
    assert not role.has_permission("skills", "call")


def test_tenant_readonly_cannot_call_mcp():
    role = DEFAULT_ROLES["tenant_readonly"]
    assert not role.has_permission("mcp", "call")


def test_tenant_readonly_cannot_manage_skills():
    role = DEFAULT_ROLES["tenant_readonly"]
    assert not role.has_permission("skills", "read")
    assert not role.has_permission("skills", "write")


def test_tenant_readonly_cannot_manage_mcp():
    role = DEFAULT_ROLES["tenant_readonly"]
    assert not role.has_permission("mcp", "read")
    assert not role.has_permission("mcp", "write")
    assert not role.has_permission("mcp", "test")


def test_tenant_readonly_can_read_webchat():
    role = DEFAULT_ROLES["tenant_readonly"]
    assert role.has_permission("webchat", "read")


def test_tenant_readonly_can_read_audit():
    """P3-3 已在审计查询层强制租户过滤，允许只读角色查本租户审计。"""
    role = DEFAULT_ROLES["tenant_readonly"]
    assert role.has_permission("audit", "read")


# ── 权限颗粒度：action 不交叉污染 ─────────────────────────────

def test_call_permission_does_not_imply_write():
    """'skills:call' 不应意外放开 'skills:write'。"""
    call_perm = Permission("skills", "call")
    assert not call_perm.matches("skills", "write")


def test_read_permission_does_not_imply_call():
    """'skills:read' 不应意外放开 'skills:call'。"""
    read_perm = Permission("skills", "read")
    assert not read_perm.matches("skills", "call")


# ── 跨租户拒绝（AuthzService 级别） ──────────────────────────

@pytest.mark.asyncio
async def test_tenant_member_cross_tenant_skills_call_denied():
    """tenant_member 只能调用本租户启用的能力。"""
    from qwenpaw.enterprise.authz.service import AuthzService
    from qwenpaw.enterprise.context import RequestContext

    ctx = RequestContext(
        request_id="req-1",
        trace_id="trace-1",
        user_id="user-a",
        roles=("tenant_member",),
        tenant_id="wx_tenant_1",
        agent_id="wx_tenant_1",
    )
    svc = AuthzService()
    result = await svc.check_tenant_access(ctx, target_tenant_id="wx_tenant_2")
    assert result.allowed is False
    assert result.reason == "tenant_boundary"


@pytest.mark.asyncio
async def test_tenant_admin_cross_tenant_skills_manage_denied():
    """tenant_admin 也不能越过租户边界。"""
    from qwenpaw.enterprise.authz.service import AuthzService
    from qwenpaw.enterprise.context import RequestContext

    ctx = RequestContext(
        request_id="req-2",
        trace_id="trace-2",
        user_id="admin-a",
        roles=("tenant_admin",),
        tenant_id="wx_tenant_1",
        agent_id="wx_tenant_1",
    )
    svc = AuthzService()
    result = await svc.check_tenant_access(ctx, target_tenant_id="wx_tenant_2")
    assert result.allowed is False
    assert result.reason == "tenant_boundary"


@pytest.mark.asyncio
async def test_platform_admin_cross_tenant_allowed():
    """platform_admin 可以访问任意租户。"""
    from qwenpaw.enterprise.authz.service import AuthzService
    from qwenpaw.enterprise.context import RequestContext

    ctx = RequestContext(
        request_id="req-3",
        trace_id="trace-3",
        user_id="pa",
        roles=("platform_admin",),
        tenant_id="wx_tenant_1",
        agent_id="wx_tenant_1",
    )
    svc = AuthzService()
    result = await svc.check_tenant_access(ctx, target_tenant_id="wx_tenant_2")
    assert result.allowed is True
