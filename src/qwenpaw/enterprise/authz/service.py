# -*- coding: utf-8 -*-
from __future__ import annotations

from ..context import RequestContext
from ..interfaces import AuthzDecision
from .models import DEFAULT_ROLES


class AuthzService:
    """RBAC 权限评估和租户边界判断。"""

    async def check_permission(
        self,
        ctx: RequestContext,
        resource: str,
        action: str,
    ) -> AuthzDecision:
        for role_name in ctx.roles:
            role = DEFAULT_ROLES.get(role_name)
            if role and role.has_permission(resource, action):
                return AuthzDecision(
                    allowed=True,
                    reason="role_permission",
                    matched_roles=(role_name,),
                )
        return AuthzDecision(
            allowed=False,
            reason="no_matching_role",
        )

    async def check_tenant_access(
        self,
        ctx: RequestContext,
        target_tenant_id: str,
    ) -> AuthzDecision:
        # platform_admin 允许访问所有租户
        if "platform_admin" in ctx.roles:
            return AuthzDecision(allowed=True, reason="platform_admin")

        # 无租户上下文只允许访问无租户资源
        if not ctx.tenant_id:
            if not target_tenant_id:
                return AuthzDecision(allowed=True, reason="same_tenant")
            return AuthzDecision(allowed=False, reason="tenant_boundary")

        # 同租户允许
        if ctx.tenant_id == target_tenant_id:
            return AuthzDecision(allowed=True, reason="same_tenant")

        return AuthzDecision(allowed=False, reason="tenant_boundary")
