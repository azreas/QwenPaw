# -*- coding: utf-8 -*-
"""P3-4 Console 用户管理 API 测试。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from starlette.middleware.base import BaseHTTPMiddleware

from qwenpaw.app.routers.auth import router as auth_router


class _FakeAuthzMiddleware(BaseHTTPMiddleware):
    """注入 platform_admin RequestContext 以通过权限检查。"""

    async def dispatch(self, request: Request, call_next):
        from qwenpaw.enterprise.context import RequestContext, RequestActor

        ctx = RequestContext(
            request_id="test-req",
            trace_id="test-trace",
            user_id="admin",
            roles=("platform_admin",),
            actor=RequestActor(actor_id="admin", actor_type="console_user"),
        )
        request.state.request_context = ctx
        return await call_next(request)


class _FakeNonAdminMiddleware(BaseHTTPMiddleware):
    """注入 tenant_member RequestContext 以测试权限拒绝。"""

    async def dispatch(self, request: Request, call_next):
        from qwenpaw.enterprise.context import RequestContext, RequestActor

        ctx = RequestContext(
            request_id="test-req",
            trace_id="test-trace",
            user_id="member",
            roles=("tenant_member",),
            actor=RequestActor(actor_id="member", actor_type="console_user"),
        )
        request.state.request_context = ctx
        return await call_next(request)


class _FakeTenantAdminMiddleware(BaseHTTPMiddleware):
    """注入 tenant_admin RequestContext 以测试租户内用户管理。"""

    async def dispatch(self, request: Request, call_next):
        from qwenpaw.enterprise.context import RequestContext, RequestActor

        ctx = RequestContext(
            request_id="test-req",
            trace_id="test-trace",
            user_id="tenant-admin",
            tenant_id="acme",
            roles=("tenant_admin",),
            actor=RequestActor(actor_id="tenant-admin", actor_type="console_user"),
        )
        request.state.request_context = ctx
        return await call_next(request)


@pytest.fixture
def auth_dir(tmp_path, monkeypatch):
    """创建临时 auth 目录并启用认证。"""
    from qwenpaw.app import auth as auth_module
    from qwenpaw.app.auth_store import AuthStore

    secret_dir = tmp_path / "secret"
    secret_dir.mkdir()
    auth_file = secret_dir / "auth.json"
    monkeypatch.setattr(auth_module, "AUTH_FILE", auth_file)
    monkeypatch.setattr(auth_module, "_get_auth_store", lambda: AuthStore(auth_file))
    monkeypatch.setenv("QWENPAW_AUTH_ENABLED", "true")
    return secret_dir


@pytest.fixture
def admin_client(auth_dir):
    """带 platform_admin 上下文的 API client。"""
    from qwenpaw.enterprise.runtime_registry import set_enterprise_runtime
    from types import SimpleNamespace

    app = FastAPI()
    app.state.enterprise_runtime = SimpleNamespace(
        authz=SimpleNamespace(
            check_permission=lambda ctx, r, a: SimpleNamespace(allowed=True, reason="test"),
        ),
    )
    set_enterprise_runtime(app.state.enterprise_runtime)
    app.include_router(auth_router, prefix="/api")
    app.add_middleware(_FakeAuthzMiddleware)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def member_client(auth_dir):
    """带 tenant_member 上下文的 API client。"""
    from qwenpaw.enterprise.runtime_registry import set_enterprise_runtime
    from types import SimpleNamespace

    app = FastAPI()
    app.state.enterprise_runtime = SimpleNamespace(
        authz=SimpleNamespace(
            check_permission=lambda ctx, r, a: SimpleNamespace(allowed=True, reason="test"),
        ),
    )
    set_enterprise_runtime(app.state.enterprise_runtime)
    app.include_router(auth_router, prefix="/api")
    app.add_middleware(_FakeNonAdminMiddleware)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def tenant_admin_client(auth_dir):
    """带 tenant_admin 上下文的 API client。"""
    from qwenpaw.enterprise.runtime_registry import set_enterprise_runtime
    from types import SimpleNamespace

    app = FastAPI()
    app.state.enterprise_runtime = SimpleNamespace(
        authz=SimpleNamespace(
            check_permission=lambda ctx, r, a: SimpleNamespace(allowed=True, reason="test"),
        ),
    )
    set_enterprise_runtime(app.state.enterprise_runtime)
    app.include_router(auth_router, prefix="/api")
    app.add_middleware(_FakeTenantAdminMiddleware)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_list_users_empty(admin_client):
    response = await admin_client.get("/api/auth/users")
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.asyncio
async def test_create_tenant_readonly_user(admin_client):
    response = await admin_client.post(
        "/api/auth/users",
        json={
            "username": "readonly-acme",
            "password": "secret123",
            "roles": ["tenant_readonly"],
            "tenant_id": "acme",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "readonly-acme"
    assert body["tenant_id"] == "acme"
    assert "tenant_readonly" in body["roles"]


@pytest.mark.asyncio
async def test_create_duplicate_user_fails(admin_client):
    await admin_client.post(
        "/api/auth/users",
        json={
            "username": "dup-user",
            "password": "secret123",
            "roles": ["tenant_member"],
        },
    )
    response = await admin_client.post(
        "/api/auth/users",
        json={
            "username": "dup-user",
            "password": "secret123",
            "roles": ["tenant_member"],
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_list_users_after_create(admin_client):
    await admin_client.post(
        "/api/auth/users",
        json={
            "username": "admin1",
            "password": "secret123",
            "roles": ["platform_admin"],
        },
    )
    response = await admin_client.get("/api/auth/users")
    assert response.status_code == 200
    usernames = [u["username"] for u in response.json()["items"]]
    assert "admin1" in usernames


@pytest.mark.asyncio
async def test_update_user_disable(admin_client):
    await admin_client.post(
        "/api/auth/users",
        json={
            "username": "to-disable",
            "password": "secret123",
            "roles": ["tenant_member"],
        },
    )
    response = await admin_client.patch(
        "/api/auth/users/to-disable",
        json={"disabled": True},
    )
    assert response.status_code == 200
    assert response.json()["disabled"] is True


@pytest.mark.asyncio
async def test_update_user_roles(admin_client):
    await admin_client.post(
        "/api/auth/users",
        json={
            "username": "role-change",
            "password": "secret123",
            "roles": ["tenant_member"],
        },
    )
    response = await admin_client.patch(
        "/api/auth/users/role-change",
        json={"roles": ["tenant_admin"], "tenant_id": "acme"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "tenant_admin" in body["roles"]
    assert body["tenant_id"] == "acme"


@pytest.mark.asyncio
async def test_update_nonexistent_user_fails(admin_client):
    response = await admin_client.patch(
        "/api/auth/users/nonexistent",
        json={"disabled": True},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_non_admin_cannot_create_user(member_client):
    """tenant_member 不能创建用户。"""
    response = await member_client.post(
        "/api/auth/users",
        json={
            "username": "unauthorized",
            "password": "secret123",
            "roles": ["tenant_member"],
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_non_admin_cannot_list_users(member_client):
    """tenant_member 不能列出用户。"""
    response = await member_client.get("/api/auth/users")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_admin_lists_only_own_tenant_users(admin_client, tenant_admin_client):
    await admin_client.post(
        "/api/auth/users",
        json={
            "username": "acme-admin",
            "password": "secret123",
            "roles": ["tenant_admin"],
            "tenant_id": "acme",
        },
    )
    await admin_client.post(
        "/api/auth/users",
        json={
            "username": "beta-admin",
            "password": "secret123",
            "roles": ["tenant_admin"],
            "tenant_id": "beta",
        },
    )
    await admin_client.post(
        "/api/auth/users",
        json={
            "username": "platform-root",
            "password": "secret123",
            "roles": ["platform_admin"],
        },
    )

    response = await tenant_admin_client.get("/api/auth/users")

    assert response.status_code == 200
    usernames = {u["username"] for u in response.json()["items"]}
    assert usernames == {"acme-admin"}


@pytest.mark.asyncio
async def test_tenant_admin_can_create_user_in_own_tenant(tenant_admin_client):
    response = await tenant_admin_client.post(
        "/api/auth/users",
        json={
            "username": "acme-readonly",
            "password": "secret123",
            "roles": ["tenant_readonly"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "acme-readonly"
    assert body["tenant_id"] == "acme"
    assert body["roles"] == ["tenant_readonly"]


@pytest.mark.asyncio
async def test_tenant_admin_cannot_create_platform_admin(tenant_admin_client):
    response = await tenant_admin_client.post(
        "/api/auth/users",
        json={
            "username": "tenant-created-platform",
            "password": "secret123",
            "roles": ["platform_admin"],
            "tenant_id": "acme",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_admin_cannot_create_user_in_other_tenant(tenant_admin_client):
    response = await tenant_admin_client.post(
        "/api/auth/users",
        json={
            "username": "beta-readonly",
            "password": "secret123",
            "roles": ["tenant_readonly"],
            "tenant_id": "beta",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_admin_can_patch_own_tenant_user(admin_client, tenant_admin_client):
    await admin_client.post(
        "/api/auth/users",
        json={
            "username": "acme-operator",
            "password": "secret123",
            "roles": ["tenant_readonly"],
            "tenant_id": "acme",
        },
    )

    response = await tenant_admin_client.patch(
        "/api/auth/users/acme-operator",
        json={"roles": ["tenant_admin"], "disabled": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == "acme"
    assert body["roles"] == ["tenant_admin"]
    assert body["disabled"] is True


@pytest.mark.asyncio
async def test_tenant_admin_cannot_patch_other_tenant_user(admin_client, tenant_admin_client):
    await admin_client.post(
        "/api/auth/users",
        json={
            "username": "beta-operator",
            "password": "secret123",
            "roles": ["tenant_readonly"],
            "tenant_id": "beta",
        },
    )

    response = await tenant_admin_client.patch(
        "/api/auth/users/beta-operator",
        json={"disabled": True},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_admin_cannot_patch_platform_admin(admin_client, tenant_admin_client):
    await admin_client.post(
        "/api/auth/users",
        json={
            "username": "root-admin",
            "password": "secret123",
            "roles": ["platform_admin"],
        },
    )

    response = await tenant_admin_client.patch(
        "/api/auth/users/root-admin",
        json={"disabled": True},
    )

    assert response.status_code == 403
