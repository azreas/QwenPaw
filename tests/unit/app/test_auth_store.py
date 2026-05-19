from __future__ import annotations

from pathlib import Path

import pytest

from qwenpaw.app.auth_store import AuthStore


def test_auth_store_registers_multiple_users(tmp_path: Path):
    store = AuthStore(tmp_path / "auth.json")

    admin = store.register_user("admin", "secret", roles=("platform_admin",))
    member = store.register_user("operator", "secret2", roles=("tenant_operator",))

    assert admin.username == "admin"
    assert member.username == "operator"
    assert store.authenticate("admin", "secret") is not None
    assert store.authenticate("operator", "secret2") is not None


def test_auth_store_preserves_tenant_id(tmp_path: Path):
    store = AuthStore(tmp_path / "auth.json")

    store.register_user(
        "tenant-admin",
        "secret",
        roles=("tenant_admin",),
        tenant_id="acme",
    )

    record = store.authenticate("tenant-admin", "secret")
    assert record is not None
    assert record.roles == ("tenant_admin",)
    assert record.tenant_id == "acme"


def test_auth_store_migrates_v1_single_user_after_login(tmp_path: Path):
    path = tmp_path / "auth.json"
    path.write_text(
        """
{
  "user": {
    "username": "admin",
    "password_hash": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",
    "password_salt": ""
  },
  "jwt_secret": "secret"
}
""".strip(),
        encoding="utf-8",
    )
    store = AuthStore(path)

    assert store.authenticate("admin", "password") is not None
    data = store.load()
    assert data["version"] == 2
    assert data["users"]["admin"]["password_hash"].startswith("bcrypt$")


def test_auth_store_rejects_wrong_password(tmp_path: Path):
    store = AuthStore(tmp_path / "auth.json")
    store.register_user("admin", "correct", roles=("platform_admin",))

    assert store.authenticate("admin", "wrong") is None


def test_auth_store_rejects_duplicate_user(tmp_path: Path):
    store = AuthStore(tmp_path / "auth.json")
    store.register_user("admin", "secret", roles=("platform_admin",))

    with pytest.raises(ValueError, match="user already exists"):
        store.register_user("admin", "another", roles=("tenant_operator",))


def test_auth_store_revoked_tokens_meta_preserved(tmp_path: Path):
    store = AuthStore(tmp_path / "auth.json")
    store.register_user("admin", "secret", roles=("platform_admin",))

    # Simulate revoked token by writing directly
    data = store.load()
    data["revoked_tokens_meta"] = {"token123": 1234567890}
    store.save(data)

    reloaded = store.load()
    assert reloaded["revoked_tokens_meta"]["token123"] == 1234567890
