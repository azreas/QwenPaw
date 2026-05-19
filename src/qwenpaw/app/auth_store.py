from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
from pathlib import Path

import bcrypt

from ..security.secret_store import (
    AUTH_SECRET_FIELDS,
    decrypt_dict_fields,
    encrypt_dict_fields,
)
from .auth_models import AuthFileV2, AuthUserRecord

logger = logging.getLogger(__name__)


def _chmod_best_effort(path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


class AuthStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> dict:
        """加载并解密 auth.json。文件损坏时返回带 _auth_load_error 标记的 dict。"""
        if not self._path.exists():
            return AuthFileV2(jwt_secret=secrets.token_hex(32)).model_dump(
                mode="json"
            )
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return decrypt_dict_fields(data, AUTH_SECRET_FIELDS)
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            logger.error("Failed to load auth file %s: %s", self._path, exc)
            return {"_auth_load_error": True}

    def save(self, data: dict) -> None:
        """加密并保存 auth.json，设置严格文件权限。"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        _chmod_best_effort(self._path.parent, 0o700)
        encrypted = encrypt_dict_fields(data, AUTH_SECRET_FIELDS)
        self._path.write_text(
            json.dumps(encrypted, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        _chmod_best_effort(self._path, 0o600)

    def register_user(
        self,
        username: str,
        password: str,
        *,
        roles: tuple[str, ...],
        tenant_id: str = "",
    ) -> AuthUserRecord:
        """注册新用户。"""
        data = self._ensure_v2(self.load())
        if username in data["users"]:
            raise ValueError("user already exists")
        record = AuthUserRecord(
            username=username,
            password_hash=self._hash_bcrypt(password),
            roles=roles,
            tenant_id=tenant_id,
        )
        data["users"][username] = record.model_dump(mode="json")
        self.save(data)
        return record

    def authenticate(self, username: str, password: str) -> AuthUserRecord | None:
        """验证用户名密码，成功时返回用户记录。

        v1 SHA-256 哈希验证成功后自动升级为 bcrypt。
        """
        data = self._ensure_v2(self.load())
        raw = data["users"].get(username)
        if raw is None:
            return None
        record = AuthUserRecord.model_validate(raw)
        if record.disabled:
            return None
        if self._verify_password(password, record.password_hash):
            if not record.password_hash.startswith("bcrypt$"):
                record = record.model_copy(
                    update={"password_hash": self._hash_bcrypt(password)}
                )
                data["users"][username] = record.model_dump(mode="json")
                self.save(data)
            return record
        return None

    def _ensure_v2(self, data: dict) -> dict:
        """将 v1 单用户结构升级为 v2 多用户结构。"""
        if data.get("version") == 2:
            return data
        user = data.get("user") or {}
        username = user.get("username", "")
        if username:
            salt = user.get("password_salt", "")
            legacy_hash = user.get("password_hash", "")
            password_hash = f"sha256${salt}${legacy_hash}"
            users = {
                username: AuthUserRecord(
                    username=username,
                    password_hash=password_hash,
                    roles=("platform_admin",),
                    tenant_id="",
                ).model_dump(mode="json")
            }
        else:
            users = {}
        return {
            "version": 2,
            "users": users,
            "jwt_secret": data.get("jwt_secret") or secrets.token_hex(32),
            "revoked_tokens_meta": data.get("revoked_tokens_meta", {}),
        }

    @staticmethod
    def _hash_bcrypt(password: str) -> str:
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
        return "bcrypt$" + hashed.decode("utf-8")

    @staticmethod
    def _verify_password(password: str, stored: str) -> bool:
        if stored.startswith("bcrypt$"):
            return bcrypt.checkpw(
                password.encode("utf-8"),
                stored.removeprefix("bcrypt$").encode("utf-8"),
            )
        if stored.startswith("sha256$"):
            _, salt, digest = stored.split("$", 2)
            candidate = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
            return hmac.compare_digest(candidate, digest)
        return False
