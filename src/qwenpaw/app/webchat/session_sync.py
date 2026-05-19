# -*- coding: utf-8 -*-
from __future__ import annotations

from qwenpaw.constant import EnvVarLoader

from .session import WebchatIdentity

_SYNC_ENV = "QWENPAW_WEBCHAT_WECOM_SESSION_SYNC_ENABLED"
_WECOM_PREFIX = "wecom:"
_WECOM_GROUP_PREFIX = "wecom:group:"


def is_webchat_wecom_session_sync_enabled() -> bool:
    return EnvVarLoader.get_bool(_SYNC_ENV, True)


def canonical_session_id_for_identity(identity: WebchatIdentity) -> str:
    user_id = str(identity.wechat_company_id or "").strip()
    if not user_id:
        raise ValueError("wechat_company_id is required")
    return f"{_WECOM_PREFIX}{user_id}"


def is_wecom_group_session_id(session_id: str | None) -> bool:
    return str(session_id or "").startswith(_WECOM_GROUP_PREFIX)


def is_wecom_single_session_id(session_id: str | None) -> bool:
    value = str(session_id or "")
    return value.startswith(_WECOM_PREFIX) and not value.startswith(_WECOM_GROUP_PREFIX)


def ensure_webchat_session_access(
    identity: WebchatIdentity,
    session_id: str,
) -> str:
    value = str(session_id or "").strip()
    if not value:
        raise PermissionError("Session id is required")
    if is_wecom_group_session_id(value):
        raise PermissionError("WebChat cannot access WeCom group sessions")
    if is_wecom_single_session_id(value):
        expected = canonical_session_id_for_identity(identity)
        if value != expected:
            raise PermissionError("Cannot access another user's WeCom session")
    return value
