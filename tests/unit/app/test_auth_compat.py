from __future__ import annotations

from pathlib import Path

from qwenpaw.app import auth


def test_auth_module_compat_functions_use_auth_store(monkeypatch, tmp_path: Path):
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(auth, "AUTH_FILE", auth_file)

    token = auth.register_user("admin", "secret")

    assert token
    assert auth.authenticate("admin", "secret")
    assert auth.has_registered_users() is True


def test_has_registered_users_detects_v1_user(monkeypatch, tmp_path: Path):
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(
        '{"user": {"username": "admin", "password_hash": "x", "password_salt": ""}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(auth, "AUTH_FILE", auth_file)

    assert auth.has_registered_users() is True


def test_register_user_rejects_second_user(monkeypatch, tmp_path: Path):
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(auth, "AUTH_FILE", auth_file)

    first = auth.register_user("admin", "secret")
    second = auth.register_user("other", "secret")

    assert first is not None
    assert second is None


def test_update_credentials_works(monkeypatch, tmp_path: Path):
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(auth, "AUTH_FILE", auth_file)

    auth.register_user("admin", "oldpass")
    new_token = auth.update_credentials(
        username="admin",
        current_password="oldpass",
        new_username="newadmin",
        new_password="newpass",
    )

    assert new_token is not None
    assert auth.authenticate("newadmin", "newpass") is not None


def test_update_credentials_rejects_wrong_password(monkeypatch, tmp_path: Path):
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(auth, "AUTH_FILE", auth_file)

    auth.register_user("admin", "correct")
    result = auth.update_credentials(
        username="admin",
        current_password="wrong",
        new_password="newpass",
    )

    assert result is None
