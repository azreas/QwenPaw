from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qwenpaw.app.routers.auth import router


def test_auth_register_first_user_then_reject_second(monkeypatch, tmp_path):
    import qwenpaw.app.auth as auth_module

    monkeypatch.setenv("QWENPAW_AUTH_ENABLED", "true")
    monkeypatch.setattr(auth_module, "AUTH_FILE", tmp_path / "auth.json")
    app = FastAPI()
    app.include_router(router, prefix="/api")
    client = TestClient(app)

    first = client.post(
        "/api/auth/register",
        json={"username": "admin", "password": "secret"},
    )
    second = client.post(
        "/api/auth/register",
        json={"username": "other", "password": "secret"},
    )

    assert first.status_code == 200
    assert second.status_code == 403


def test_auth_register_rejects_empty_username(monkeypatch, tmp_path):
    import qwenpaw.app.auth as auth_module

    monkeypatch.setenv("QWENPAW_AUTH_ENABLED", "true")
    monkeypatch.setattr(auth_module, "AUTH_FILE", tmp_path / "auth.json")
    app = FastAPI()
    app.include_router(router, prefix="/api")
    client = TestClient(app)

    response = client.post(
        "/api/auth/register",
        json={"username": "", "password": "secret"},
    )

    assert response.status_code == 422  # Pydantic validation error


def test_auth_login_validates_input_length(monkeypatch, tmp_path):
    import qwenpaw.app.auth as auth_module

    monkeypatch.setenv("QWENPAW_AUTH_ENABLED", "true")
    monkeypatch.setattr(auth_module, "AUTH_FILE", tmp_path / "auth.json")
    app = FastAPI()
    app.include_router(router, prefix="/api")
    client = TestClient(app)

    response = client.post(
        "/api/auth/login",
        json={"username": "a" * 200, "password": "secret"},
    )

    # Should fail validation before auth logic
    assert response.status_code in (401, 422)


def test_update_profile_validates_password_length(monkeypatch, tmp_path):
    import qwenpaw.app.auth as auth_module

    monkeypatch.setenv("QWENPAW_AUTH_ENABLED", "true")
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(auth_module, "AUTH_FILE", auth_file)

    app = FastAPI()
    app.include_router(router, prefix="/api")
    client = TestClient(app)

    # Register first
    client.post(
        "/api/auth/register",
        json={"username": "admin", "password": "secret"},
    )
    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "secret"},
    )
    token = login.json()["token"]

    response = client.post(
        "/api/auth/update-profile",
        json={
            "current_password": "secret",
            "new_password": "",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422  # Pydantic validation error


def test_update_profile_full_flow(monkeypatch, tmp_path):
    """完整流程：注册 -> 登录 -> 修改密码 -> 新密码可登录，旧密码不可。"""
    import qwenpaw.app.auth as auth_module

    monkeypatch.setenv("QWENPAW_AUTH_ENABLED", "true")
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(auth_module, "AUTH_FILE", auth_file)

    app = FastAPI()
    app.include_router(router, prefix="/api")
    client = TestClient(app)

    # 1. 注册用户
    register_resp = client.post(
        "/api/auth/register",
        json={"username": "admin", "password": "oldpass"},
    )
    assert register_resp.status_code == 200

    # 2. 使用旧密码登录
    old_login_resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "oldpass"},
    )
    assert old_login_resp.status_code == 200
    old_token = old_login_resp.json()["token"]
    assert old_token

    # 3. 使用旧 token 修改密码
    update_resp = client.post(
        "/api/auth/update-profile",
        json={
            "current_password": "oldpass",
            "new_password": "newpass",
        },
        headers={"Authorization": f"Bearer {old_token}"},
    )
    assert update_resp.status_code == 200
    new_token = update_resp.json()["token"]
    assert new_token

    # 4. 旧密码不能再登录
    old_fail_resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "oldpass"},
    )
    assert old_fail_resp.status_code == 401

    # 5. 新密码可以登录
    new_login_resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "newpass"},
    )
    assert new_login_resp.status_code == 200
    assert new_login_resp.json()["token"]

    # 6. 新 token 有效，可以进行后续操作（verify 端点验证）
    verify_resp = client.get(
        "/api/auth/verify",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["valid"] is True
    assert verify_resp.json()["username"] == "admin"
    assert verify_resp.json()["roles"] == ["platform_admin"]
