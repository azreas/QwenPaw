# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from qwenpaw.constant import EnvVarLoader, SECRET_DIR
from qwenpaw.tenancy.ids import tenant_agent_id


class WebchatIdentity(BaseModel):
    """WebChat 用户身份。

    身份主键契约：wechat_company_id 必须与企微 Bot 回调的 from.userid
    是同一个值。这是企业微信的强契约——同一企业在企微和内部 SSO 系统
    中使用统一的 userid。双入口（WebChat + 企微 Bot）通过此字段
    收敛到同一个 wx_* 租户工作区。
    """

    employee_id: str
    username: str
    wechat_company_id: str
    tenant_id: str
    agent_id: str
    department: str = ""
    station: str = ""
    roles: tuple[str, ...] = ("tenant_member",)

    @classmethod
    def from_sso(
        cls,
        *,
        full_name: str,
        employee_id: str,
        wechat_company_id: str,
        department: str = "",
        station: str = "",
        roles: tuple[str, ...] | None = None,
    ) -> "WebchatIdentity":
        # wechat_company_id 即企微 userid，作为 tenant_id 收敛双入口
        tenant_id = wechat_company_id
        # SSO 用户默认 tenant_member，显式传空 tuple 可覆盖
        effective_roles = roles if roles is not None else ("tenant_member",)
        return cls(
            employee_id=employee_id,
            username=full_name,
            wechat_company_id=wechat_company_id,
            tenant_id=tenant_id,
            agent_id=tenant_agent_id(tenant_id),
            department=department,
            station=station,
            roles=effective_roles,
        )


class InvalidWebchatToken(Exception):
    pass


class InvalidWebchatQrcodeState(Exception):
    pass


def get_webchat_session_secret() -> str:
    configured = EnvVarLoader.get_str("QWENPAW_WEBCHAT_SESSION_SECRET", "")
    if configured.strip():
        return configured.strip()
    secret_file = Path(SECRET_DIR) / "webchat_session_secret"
    if secret_file.is_file():
        return secret_file.read_text(encoding="utf-8").strip()
    secret_file.parent.mkdir(parents=True, exist_ok=True)
    secret = secrets.token_hex(32)
    secret_file.write_text(secret, encoding="utf-8")
    return secret


def get_webchat_session_ttl_seconds() -> int:
    return EnvVarLoader.get_int(
        "QWENPAW_WEBCHAT_SESSION_TTL_SECONDS",
        12 * 3600,
        min_value=300,
        max_value=30 * 24 * 3600,
    )


def get_webchat_qrcode_state_ttl_seconds() -> int:
    return EnvVarLoader.get_int(
        "QWENPAW_WEBCHAT_QRCODE_STATE_TTL_SECONDS",
        300,
        min_value=60,
        max_value=3600,
    )


def sign_webchat_token(
    identity: WebchatIdentity,
    *,
    secret: str | None = None,
    ttl_seconds: int | None = None,
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = identity.model_dump(mode="json")
    payload.update(
        {
            "sub": identity.employee_id,
            "iat": now,
            "exp": now + (ttl_seconds if ttl_seconds is not None else get_webchat_session_ttl_seconds()),
        },
    )
    raw_payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    payload_b64 = _b64encode(raw_payload.encode("utf-8"))
    signature = hmac.new(
        (secret or get_webchat_session_secret()).encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_b64}.{signature}"


def sign_webchat_qrcode_state(
    *,
    secret: str | None = None,
    ttl_seconds: int | None = None,
    purpose: str = "webchat_qrcode_login",
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "purpose": purpose,
        "iat": now,
        "exp": now
        + (
            ttl_seconds
            if ttl_seconds is not None
            else get_webchat_qrcode_state_ttl_seconds()
        ),
        "nonce": secrets.token_hex(16),
    }
    raw_payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    payload_b64 = _b64encode(raw_payload.encode("utf-8"))
    signature = hmac.new(
        (secret or get_webchat_session_secret()).encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_webchat_token(
    token: str,
    *,
    secret: str | None = None,
) -> WebchatIdentity:
    try:
        payload_b64, signature = token.split(".", 1)
    except ValueError as exc:
        raise InvalidWebchatToken("Invalid token format") from exc
    expected = hmac.new(
        (secret or get_webchat_session_secret()).encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise InvalidWebchatToken("Invalid token signature")
    try:
        payload = json.loads(_b64decode(payload_b64).decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise InvalidWebchatToken("Invalid token payload") from exc
    if int(payload.get("exp", 0)) < int(time.time()):
        raise InvalidWebchatToken("Token expired")
    try:
        return WebchatIdentity(
            employee_id=str(payload["employee_id"]),
            username=str(payload["username"]),
            wechat_company_id=str(payload["wechat_company_id"]),
            tenant_id=str(payload["tenant_id"]),
            agent_id=str(payload["agent_id"]),
            department=str(payload.get("department", "")),
            station=str(payload.get("station", "")),
            # 旧 token 无 roles 字段时使用模型默认值 tenant_member
            # 显式传空 roles=[] 时保留空 tuple，不提升为 tenant_member
            **(
                {"roles": tuple(payload.get("roles") or ())}
                if "roles" in payload
                else {}
            ),
        )
    except KeyError as exc:
        raise InvalidWebchatToken("Missing identity field") from exc


def verify_webchat_qrcode_state(
    state: str,
    *,
    secret: str | None = None,
) -> None:
    try:
        payload_b64, signature = state.split(".", 1)
    except ValueError as exc:
        raise InvalidWebchatQrcodeState("Invalid state format") from exc
    expected = hmac.new(
        (secret or get_webchat_session_secret()).encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise InvalidWebchatQrcodeState("Invalid state signature")
    try:
        payload = json.loads(_b64decode(payload_b64).decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise InvalidWebchatQrcodeState("Invalid state payload") from exc
    if payload.get("purpose") != "webchat_qrcode_login":
        raise InvalidWebchatQrcodeState("Invalid state purpose")
    if int(payload.get("exp", 0)) < int(time.time()):
        raise InvalidWebchatQrcodeState("State expired")


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)
