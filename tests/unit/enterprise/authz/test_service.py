# -*- coding: utf-8 -*-
import pytest

from qwenpaw.enterprise.authz.service import AuthzService
from qwenpaw.enterprise.context import RequestActor, RequestContext


@pytest.mark.asyncio
async def test_platform_admin_allows_everything():
    service = AuthzService()
    ctx = RequestContext(
        request_id="r",
        trace_id="t",
        roles=("platform_admin",),
        actor=RequestActor(actor_id="admin", actor_type="console_user"),
    )
    decision = await service.check_permission(ctx, "audit", "read")
    assert decision.allowed is True


@pytest.mark.asyncio
async def test_tenant_member_denied_platform_resource():
    service = AuthzService()
    ctx = RequestContext(
        request_id="r",
        trace_id="t",
        roles=("tenant_member",),
    )
    decision = await service.check_permission(ctx, "platform", "read")
    assert decision.allowed is False


@pytest.mark.asyncio
async def test_tenant_boundary_blocks_other_tenant():
    service = AuthzService()
    ctx = RequestContext(
        request_id="r",
        trace_id="t",
        tenant_id="wx_a",
        roles=("tenant_admin",),
    )
    decision = await service.check_tenant_access(ctx, target_tenant_id="wx_b")
    assert decision.allowed is False
    assert decision.reason == "tenant_boundary"


@pytest.mark.asyncio
async def test_tenant_boundary_allows_same_tenant():
    service = AuthzService()
    ctx = RequestContext(
        request_id="r",
        trace_id="t",
        tenant_id="wx_a",
        roles=("tenant_admin",),
    )
    decision = await service.check_tenant_access(ctx, target_tenant_id="wx_a")
    assert decision.allowed is True


@pytest.mark.asyncio
async def test_tenant_boundary_platform_admin_allows_all():
    service = AuthzService()
    ctx = RequestContext(
        request_id="r",
        trace_id="t",
        tenant_id="wx_a",
        roles=("platform_admin",),
    )
    decision = await service.check_tenant_access(ctx, target_tenant_id="wx_b")
    assert decision.allowed is True


@pytest.mark.asyncio
async def test_anonymous_denied_protected_resource():
    service = AuthzService()
    ctx = RequestContext(
        request_id="r",
        trace_id="t",
    )
    decision = await service.check_permission(ctx, "agents", "read")
    assert decision.allowed is False
