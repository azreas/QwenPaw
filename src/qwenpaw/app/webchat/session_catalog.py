# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any

from .session import WebchatIdentity
from .session_sync import (
    canonical_session_id_for_identity,
    ensure_webchat_session_access,
    is_webchat_wecom_session_sync_enabled,
    is_wecom_group_session_id,
)

_WECOM_CHANNELS = {"wecom", "wecom_tenant"}
_VISIBLE_CHANNELS = {"webchat", *_WECOM_CHANNELS}


def _chat_value(chat: Any, name: str, default: Any = None) -> Any:
    return getattr(chat, name, default)


def _updated_sort_key(item: dict[str, Any]) -> tuple[bool, str]:
    return (bool(item.get("pinned")), str(item.get("updated_at") or ""))


def _source_channels(chats: list[Any]) -> list[str]:
    channels = sorted({str(_chat_value(chat, "channel", "")) for chat in chats})
    return [channel for channel in channels if channel]


def _source_group(channel: str) -> str:
    if channel in _WECOM_CHANNELS:
        return "wecom"
    return channel


def _pick_primary_chat(chats: list[Any]) -> Any:
    wecom_tenant = [
        chat for chat in chats if _chat_value(chat, "channel") == "wecom_tenant"
    ]
    pool = wecom_tenant or chats
    return max(pool, key=lambda chat: str(_chat_value(chat, "updated_at", "")))


def _chat_to_item(chat: Any, group: list[Any]) -> dict[str, Any]:
    channels = _source_channels(group)
    meta = dict(_chat_value(chat, "meta", {}) or {})
    return {
        "id": _chat_value(chat, "id", ""),
        "session_id": _chat_value(chat, "session_id", ""),
        "user_id": _chat_value(chat, "user_id", ""),
        "channel": _chat_value(chat, "channel", "webchat"),
        "name": _chat_value(chat, "name", None) or "New Chat",
        "created_at": _chat_value(chat, "created_at", "") or "",
        "updated_at": _chat_value(chat, "updated_at", "") or "",
        "status": _chat_value(chat, "status", None) or "idle",
        "pinned": bool(_chat_value(chat, "pinned", False)),
        "meta": meta,
        "source_channels": channels,
        "synced": any(channel in _WECOM_CHANNELS for channel in channels)
        or bool(meta.get("synced")),
    }


def list_webchat_visible_sessions(
    identity: WebchatIdentity,
    chats: list[Any],
) -> list[dict[str, Any]]:
    canonical = canonical_session_id_for_identity(identity)
    sync_enabled = is_webchat_wecom_session_sync_enabled()
    groups: dict[tuple[str, str, str], list[Any]] = {}
    for chat in chats:
        session_id = str(_chat_value(chat, "session_id", ""))
        user_id = str(_chat_value(chat, "user_id", ""))
        channel = str(_chat_value(chat, "channel", ""))
        if channel not in _VISIBLE_CHANNELS:
            continue
        if not sync_enabled and channel != "webchat":
            continue
        if is_wecom_group_session_id(session_id):
            continue
        if user_id != identity.wechat_company_id:
            continue
        if channel in _WECOM_CHANNELS and session_id != canonical:
            continue
        groups.setdefault((session_id, user_id, _source_group(channel)), []).append(chat)

    items = [_chat_to_item(_pick_primary_chat(group), group) for group in groups.values()]
    items.sort(key=_updated_sort_key, reverse=True)
    return items


def resolve_visible_chat(
    identity: WebchatIdentity,
    chats: list[Any],
    identifier: str,
) -> Any | None:
    target = ensure_webchat_session_access(identity, identifier)
    canonical = canonical_session_id_for_identity(identity)
    sync_enabled = is_webchat_wecom_session_sync_enabled()
    eligible: list[Any] = []
    for chat in chats:
        session_id = str(_chat_value(chat, "session_id", ""))
        user_id = str(_chat_value(chat, "user_id", ""))
        channel = str(_chat_value(chat, "channel", ""))
        if channel not in _VISIBLE_CHANNELS:
            continue
        if not sync_enabled and channel != "webchat":
            continue
        if user_id != identity.wechat_company_id:
            continue
        if is_wecom_group_session_id(session_id):
            continue
        if channel in _WECOM_CHANNELS and session_id != canonical:
            continue
        eligible.append(chat)
        if _chat_value(chat, "id", "") == target:
            return chat

    session_matches = [
        chat
        for chat in eligible
        if str(_chat_value(chat, "session_id", "")) == target
    ]
    if target == canonical:
        wecom_matches = [
            chat
            for chat in session_matches
            if str(_chat_value(chat, "channel", "")) in _WECOM_CHANNELS
        ]
        if wecom_matches:
            return _pick_primary_chat(wecom_matches)
    if session_matches:
        return _pick_primary_chat(session_matches)
    return None
