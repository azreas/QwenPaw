from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from qwenpaw.app import auth


def test_corrupted_auth_file_fail_closed(monkeypatch, tmp_path: Path):
    """损坏的 auth.json 不能绕过鉴权。"""
    auth_file = tmp_path / "auth.json"
    auth_file.write_text("{this is invalid json}", encoding="utf-8")
    monkeypatch.setattr(auth, "AUTH_FILE", auth_file)

    # has_registered_users 应该返回 True，不跳过 AuthMiddleware
    assert auth.has_registered_users() is True


def test_update_credentials_rejects_rename_to_existing_user(monkeypatch, tmp_path: Path):
    """重命名时不能覆盖已存在的用户。"""
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(auth, "AUTH_FILE", auth_file)

    # 创建两个用户（通过 store 直接创建，因为 register_user 是单用户模式）
    store = auth._get_auth_store()
    store.register_user("admin", "secret1", roles=("platform_admin",))
    store.register_user("operator", "secret2", roles=("tenant_operator",))

    # operator 尝试改名为 admin，应该被拒绝
    result = auth.update_credentials(
        current_password="secret2",
        new_username="admin",
        username="operator",
    )

    assert result is None

    # admin 用户仍然存在
    assert store.authenticate("admin", "secret1") is not None
    # operator 用户也还在
    assert store.authenticate("operator", "secret2") is not None


def test_verify_token_returns_string_for_compatibility(monkeypatch, tmp_path: Path):
    """verify_token 必须返回字符串而非 tuple，保持公开契约。"""
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(auth, "AUTH_FILE", auth_file)

    auth.register_user("admin", "secret")
    token = auth.authenticate("admin", "secret")

    # verify_token 应该返回字符串，而非 tuple
    result = auth.verify_token(token)
    assert result == "admin"
    assert isinstance(result, str)
    assert not isinstance(result, tuple)


def test_create_token_accepts_positional_expiry_seconds(monkeypatch, tmp_path: Path):
    """create_token 第二个参数仍然是 expiry_seconds，保持兼容。

    验证调用不会报错，签名保持向后兼容。
    """
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(auth, "AUTH_FILE", auth_file)

    # 确保 jwt_secret 已初始化
    auth.register_user("admin", "secret")

    # 旧的调用方式仍然有效
    token = auth.create_token("admin", 60)
    assert token
    assert auth.verify_token(token) == "admin"


def test_token_claims_include_tenant_id(monkeypatch, tmp_path: Path):
    """Console token 可携带租户上下文，用于租户管理员治理查询。"""
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(auth, "AUTH_FILE", auth_file)

    auth.register_user(
        "tenant-admin",
        "secret",
        roles=("tenant_admin",),
        tenant_id="acme",
    )
    token = auth.authenticate("tenant-admin", "secret")

    claims = auth.verify_token_claims(token)
    assert claims is not None
    assert claims.username == "tenant-admin"
    assert claims.roles == ("tenant_admin",)
    assert claims.tenant_id == "acme"


def test_auth_middleware_sets_tenant_id_from_token(monkeypatch, tmp_path: Path):
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(auth, "AUTH_FILE", auth_file)
    monkeypatch.setattr(auth, "is_auth_enabled", lambda: True)

    auth.register_user(
        "tenant-admin",
        "secret",
        roles=("tenant_admin",),
        tenant_id="acme",
    )
    token = auth.authenticate("tenant-admin", "secret")

    app = FastAPI()
    app.add_middleware(auth.AuthMiddleware)

    @app.get("/api/protected")
    async def protected(request: Request):
        return {
            "user": request.state.user,
            "roles": list(request.state.roles),
            "tenant_id": request.state.tenant_id,
        }

    response = TestClient(app).get(
        "/api/protected",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "user": "tenant-admin",
        "roles": ["tenant_admin"],
        "tenant_id": "acme",
    }


def test_update_credentials_backwards_compatible_no_username(monkeypatch, tmp_path: Path):
    """不传入 username 时自动用第一个用户，保持单用户兼容。"""
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(auth, "AUTH_FILE", auth_file)

    auth.register_user("admin", "oldpass")

    # 旧的调用方式（不传入 username）仍然有效
    result = auth.update_credentials(
        current_password="oldpass",
        new_password="newpass",
    )

    assert result is not None
    assert auth.authenticate("admin", "newpass") is not None
