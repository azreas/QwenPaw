# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import logging
import os
import secrets
import time
from dataclasses import dataclass
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..constant import SECRET_DIR, EnvVarLoader
from .auth_store import AuthStore

logger = logging.getLogger(__name__)

AUTH_FILE = SECRET_DIR / "auth.json"

TOKEN_EXPIRY_SECONDS = 7 * 24 * 3600
TOKEN_EXPIRY_MAX = 100 * 365 * 24 * 3600


@dataclass(frozen=True, slots=True)
class TokenClaims:
    username: str
    roles: tuple[str, ...]
    tenant_id: str = ""

_PUBLIC_PATHS: frozenset[str] = frozenset(
    {
        "/api/auth/login",
        "/api/auth/status",
        "/api/auth/register",
        "/api/auth/verify",
        "/api/version",
        "/api/settings/language",
        "/api/enterprise/readiness",
        "/api/mcp/oauth/callback",
    },
)

_PUBLIC_PREFIXES: tuple[str, ...] = (
    "/assets/",
    "/logo.png",
    "/qwenpaw-symbol.svg",
    "/api/webchat/",
)


def _chmod_best_effort(path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def _get_auth_store() -> AuthStore:
    return AuthStore(AUTH_FILE)


def _get_jwt_secret() -> str:
    data = _get_auth_store().load()
    secret = data.get("jwt_secret", "")
    if not secret:
        secret = secrets.token_hex(32)
        data["jwt_secret"] = secret
        _get_auth_store().save(data)
    return secret


def create_token(
    username: str,
    expiry_seconds: Optional[int] = None,
    *,
    roles: tuple[str, ...] = ("platform_admin",),
    tenant_id: str = "",
) -> str:
    """Create signed token.

    Args:
        username: The username to encode.
        expiry_seconds: Optional custom expiry.
        roles: Optional custom roles (keyword-only).
    """
    import base64
    import hashlib
    import hmac

    if expiry_seconds is None:
        expiry_seconds = TOKEN_EXPIRY_SECONDS
    elif expiry_seconds <= 0:
        expiry_seconds = TOKEN_EXPIRY_MAX
    else:
        expiry_seconds = min(expiry_seconds, TOKEN_EXPIRY_MAX)

    secret = _get_jwt_secret()
    token_id = secrets.token_hex(16)
    payload = json.dumps(
        {
            "sub": username,
            "roles": list(roles),
            "tenant_id": tenant_id,
            "exp": int(time.time()) + expiry_seconds,
            "iat": int(time.time()),
            "jti": token_id,
        },
    )
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode()
    sig = hmac.new(
        secret.encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_token_claims(token: str | None) -> Optional[TokenClaims]:
    """Verify token, return normalized claims or None if invalid."""
    import base64
    import hashlib
    import hmac

    try:
        if not token:
            return None
        parts = token.split(".", 1)
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        secret = _get_jwt_secret()
        expected_sig = hmac.new(
            secret.encode(),
            payload_b64.encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        if payload.get("exp", 0) < time.time():
            return None

        jti = payload.get("jti")
        if jti and _is_token_revoked(jti):
            return None

        username = payload.get("sub")
        if not username:
            return None
        roles = tuple(payload.get("roles", ["platform_admin"]))
        tenant_id = str(payload.get("tenant_id") or "")
        return TokenClaims(
            username=username,
            roles=roles,
            tenant_id=tenant_id,
        )
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        logger.debug("Token verification failed: %s", exc)
        return None


def verify_token_with_claims(token: str) -> Optional[tuple[str, tuple[str, ...]]]:
    """Verify token, return (username, roles) tuple or None if invalid."""
    claims = verify_token_claims(token)
    if claims is None:
        return None
    return (claims.username, claims.roles)


def verify_token(token: str) -> Optional[str]:
    """Verify token, return username if valid (backwards-compatible)."""
    claims = verify_token_claims(token)
    if claims is None:
        return None
    return claims.username


def _is_token_revoked(jti: str) -> bool:
    data = _get_auth_store().load()
    meta = data.get("revoked_tokens_meta", {})
    return jti in meta


def _add_to_revocation_list(jti: str, exp: int) -> None:
    store = _get_auth_store()
    data = store.load()
    if data.get("_auth_load_error"):
        return

    if "revoked_tokens_meta" not in data:
        data["revoked_tokens_meta"] = {}

    if jti not in data["revoked_tokens_meta"]:
        data["revoked_tokens_meta"][jti] = exp
        if "revoked_tokens" not in data:
            data["revoked_tokens"] = []
        data["revoked_tokens"].append(jti)

    store.save(data)


def _clean_expired_revocations() -> None:
    store = _get_auth_store()
    data = store.load()
    if data.get("_auth_load_error"):
        return

    revoked = data.get("revoked_tokens", [])
    meta = data.get("revoked_tokens_meta", {})
    current_time = int(time.time())

    cleaned_revoked = []
    cleaned_meta = {}

    for jti in revoked:
        exp = meta.get(jti, 0)
        if exp > current_time:
            cleaned_revoked.append(jti)
            cleaned_meta[jti] = exp

    if len(cleaned_revoked) < len(revoked):
        data["revoked_tokens"] = cleaned_revoked
        data["revoked_tokens_meta"] = cleaned_meta
        store.save(data)
        logger.info(
            "Cleaned %d expired tokens from revocation list",
            len(revoked) - len(cleaned_revoked),
        )


def is_auth_enabled() -> bool:
    env_flag = EnvVarLoader.get_str("QWENPAW_AUTH_ENABLED", "").strip().lower()
    return env_flag in ("true", "1", "yes")


def has_registered_users() -> bool:
    """Return True if users exist. File corruption fail-closed: treat as registered."""
    data = _get_auth_store().load()
    if data.get("_auth_load_error"):
        # Fail-closed: treat as having users to prevent auth bypass
        return True
    if data.get("version") == 2:
        return bool(data.get("users"))
    return bool(data.get("user"))


def register_user(
    username: str,
    password: str,
    expiry_seconds: Optional[int] = None,
    *,
    roles: tuple[str, ...] = ("platform_admin",),
    tenant_id: str = "",
) -> Optional[str]:
    store = _get_auth_store()
    data = store.load()
    if data.get("version") == 2 and data.get("users"):
        return None
    if data.get("user"):
        return None
    try:
        store.register_user(
            username,
            password,
            roles=roles,
            tenant_id=tenant_id,
        )
    except ValueError:
        return None
    logger.info("User '%s' registered", username)
    return create_token(
        username,
        expiry_seconds,
        roles=roles,
        tenant_id=tenant_id,
    )


def auto_register_from_env() -> None:
    if not is_auth_enabled():
        return
    if has_registered_users():
        return

    username = EnvVarLoader.get_str("QWENPAW_AUTH_USERNAME", "").strip()
    password = EnvVarLoader.get_str("QWENPAW_AUTH_PASSWORD", "").strip()
    if not username or not password:
        return

    token = register_user(username, password)
    if token:
        logger.info(
            "Auto-registered user '%s' from environment variables",
            username,
        )


def update_credentials(
    current_password: str,
    new_username: Optional[str] = None,
    new_password: Optional[str] = None,
    expiry_seconds: Optional[int] = None,
    *,
    username: Optional[str] = None,
) -> Optional[str]:
    """Update credentials.

    For backwards compatibility: if username is not passed, uses the first
    registered user (single-user mode).
    """
    store = _get_auth_store()
    data = store.load()
    data = store._ensure_v2(data)

    if not data.get("users"):
        return None

    # Single-user mode: auto-detect first user
    if username is None:
        username = next(iter(data["users"].keys()))

    if username not in data["users"]:
        return None

    user_record = store.authenticate(username, current_password)
    if user_record is None:
        return None

    final_username = username
    if new_username and new_username.strip() and new_username.strip() != username:
        # Reject if target username already exists
        if new_username.strip() in data["users"]:
            logger.warning("Username '%s' already exists, cannot rename", new_username.strip())
            return None
        del data["users"][username]
        final_username = new_username.strip()
        data["users"][final_username] = {
            "username": final_username,
            "password_hash": user_record.password_hash,
            "roles": user_record.roles,
            "disabled": False,
        }

    if new_password:
        new_hash = store._hash_bcrypt(new_password)
        data["users"][final_username]["password_hash"] = new_hash
        data["jwt_secret"] = secrets.token_hex(32)

    store.save(data)
    logger.info("Credentials updated for user '%s'", final_username)
    return create_token(
        final_username,
        expiry_seconds,
        roles=user_record.roles,
        tenant_id=user_record.tenant_id,
    )


def authenticate(
    username: str,
    password: str,
    expiry_seconds: Optional[int] = None,
) -> Optional[str]:
    record = _get_auth_store().authenticate(username, password)
    if record is None:
        return None
    return create_token(
        username,
        expiry_seconds,
        roles=record.roles,
        tenant_id=record.tenant_id,
    )


# ── P3-4: 用户管理 API 所需函数 ──────────────────────────


def list_users() -> list[dict]:
    """列出所有用户（不含密码哈希）。"""
    from .auth_models import AuthUserRecord

    store = _get_auth_store()
    data = store._ensure_v2(store.load())
    result = []
    for _uname, raw in data.get("users", {}).items():
        record = AuthUserRecord.model_validate(raw)
        result.append({
            "username": record.username,
            "roles": list(record.roles),
            "tenant_id": record.tenant_id,
            "disabled": record.disabled,
        })
    return result


def create_user(
    username: str,
    password: str,
    *,
    roles: tuple[str, ...] = ("tenant_member",),
    tenant_id: str = "",
) -> Optional[dict]:
    """创建新用户，返回用户信息 dict 或 None。"""
    store = _get_auth_store()
    try:
        record = store.register_user(username, password, roles=roles, tenant_id=tenant_id)
    except ValueError:
        return None
    logger.info("User '%s' created with roles=%s tenant_id=%s", username, roles, tenant_id)
    return {
        "username": record.username,
        "roles": list(record.roles),
        "tenant_id": record.tenant_id,
        "disabled": record.disabled,
    }


def update_user(
    username: str,
    *,
    roles: Optional[tuple[str, ...]] = None,
    tenant_id: Optional[str] = None,
    disabled: Optional[bool] = None,
) -> Optional[dict]:
    """更新用户角色、租户绑定或禁用状态。返回更新后的用户信息或 None。"""
    store = _get_auth_store()
    data = store._ensure_v2(store.load())
    raw = data.get("users", {}).get(username)
    if raw is None:
        return None
    from .auth_models import AuthUserRecord

    record = AuthUserRecord.model_validate(raw)
    updates: dict = {}
    if roles is not None:
        updates["roles"] = roles
    if tenant_id is not None:
        updates["tenant_id"] = tenant_id
    if disabled is not None:
        updates["disabled"] = disabled
    if updates:
        record = record.model_copy(update=updates)
        data["users"][username] = record.model_dump(mode="json")
        store.save(data)
        logger.info("User '%s' updated: %s", username, updates)
    return {
        "username": record.username,
        "roles": list(record.roles),
        "tenant_id": record.tenant_id,
        "disabled": record.disabled,
    }


def revoke_token(token: str) -> bool:
    import base64

    try:
        parts = token.split(".", 1)
        if len(parts) != 2:
            return False

        payload_b64 = parts[0]
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        jti = payload.get("jti")
        exp = payload.get("exp", 0)

        if not jti:
            logger.warning("Token has no jti, cannot revoke individually")
            return False

        _add_to_revocation_list(jti, exp)
        logger.info("Token %s revoked", jti[:8])

        _clean_expired_revocations()

        return True
    except Exception as exc:
        logger.error("Failed to revoke token: %s", exc)
        return False


def revoke_all_tokens() -> bool:
    try:
        store = _get_auth_store()
        data = store.load()
        if data.get("_auth_load_error"):
            return False

        data["jwt_secret"] = secrets.token_hex(32)
        data["revoked_tokens"] = []
        data["revoked_tokens_meta"] = {}

        store.save(data)
        logger.info("All tokens revoked (JWT secret rotated)")
        return True
    except Exception as exc:
        logger.error("Failed to revoke tokens: %s", exc)
        return False


class AuthMiddleware(BaseHTTPMiddleware):

    async def dispatch(
        self,
        request: Request,
        call_next,
    ) -> Response:
        if self._should_skip_auth(request):
            return await call_next(request)

        token = self._extract_token(request)
        if not token:
            return Response(
                content=json.dumps({"detail": "Not authenticated"}),
                status_code=401,
                media_type="application/json",
            )

        claims = verify_token_claims(token)
        if claims is None:
            return Response(
                content=json.dumps(
                    {"detail": "Invalid or expired token"},
                ),
                status_code=401,
                media_type="application/json",
            )

        request.state.user = claims.username
        request.state.roles = claims.roles
        request.state.tenant_id = claims.tenant_id
        return await call_next(request)

    @staticmethod
    def _should_skip_auth(request: Request) -> bool:
        if not is_auth_enabled() or not has_registered_users():
            return True

        path = request.url.path

        if request.method == "OPTIONS":
            return True

        if path in _PUBLIC_PATHS or any(
            path.startswith(p) for p in _PUBLIC_PREFIXES
        ):
            return True

        if not path.startswith("/api/"):
            return True

        from ..config import load_config

        client_host = request.client.host if request.client else ""
        config = load_config()
        allowed_hosts = config.security.allow_no_auth_hosts
        return client_host in allowed_hosts

    @staticmethod
    def _extract_token(request: Request) -> Optional[str]:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        if "upgrade" in request.headers.get("connection", "").lower():
            return request.query_params.get("token")

        token = request.query_params.get("token")
        if token:
            return token
        return None
