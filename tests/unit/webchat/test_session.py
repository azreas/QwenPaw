# -*- coding: utf-8 -*-
from __future__ import annotations

import time

import pytest

from qwenpaw.app.channels.webchat.channel import WebchatChannel
from qwenpaw.app.webchat.session import (
    InvalidWebchatQrcodeState,
    InvalidWebchatToken,
    WebchatIdentity,
    sign_webchat_qrcode_state,
    sign_webchat_token,
    verify_webchat_qrcode_state,
    verify_webchat_token,
)
from qwenpaw.app.webchat.session_sync import (
    canonical_session_id_for_identity,
    ensure_webchat_session_access,
    is_webchat_wecom_session_sync_enabled,
    is_wecom_group_session_id,
    is_wecom_single_session_id,
)


def test_sign_and_verify_webchat_token_round_trip():
    identity = WebchatIdentity(
        employee_id="E000001",
        username="测试员工",
        wechat_company_id="test_user",
        tenant_id="test_user",
        agent_id="wx_test_user",
    )

    token = sign_webchat_token(identity, secret="test-secret", ttl_seconds=60)
    decoded = verify_webchat_token(token, secret="test-secret")

    assert decoded == identity


def test_verify_rejects_tampered_token():
    identity = WebchatIdentity(
        employee_id="E000001",
        username="测试员工",
        wechat_company_id="test_user",
        tenant_id="test_user",
        agent_id="wx_test_user",
    )
    token = sign_webchat_token(identity, secret="test-secret", ttl_seconds=60)
    tampered = token[:-1] + ("0" if token[-1] != "0" else "1")

    with pytest.raises(InvalidWebchatToken):
        verify_webchat_token(tampered, secret="test-secret")


def test_verify_rejects_expired_token():
    identity = WebchatIdentity(
        employee_id="E000001",
        username="测试员工",
        wechat_company_id="test_user",
        tenant_id="test_user",
        agent_id="wx_test_user",
    )

    token = sign_webchat_token(identity, secret="test-secret", ttl_seconds=-1)
    time.sleep(0.01)

    with pytest.raises(InvalidWebchatToken):
        verify_webchat_token(token, secret="test-secret")


def test_sign_and_verify_qrcode_state_round_trip():
    state = sign_webchat_qrcode_state(secret="test-secret", ttl_seconds=60)

    verify_webchat_qrcode_state(state, secret="test-secret")


def test_verify_rejects_tampered_qrcode_state():
    state = sign_webchat_qrcode_state(secret="test-secret", ttl_seconds=60)
    tampered = state[:-1] + ("0" if state[-1] != "0" else "1")

    with pytest.raises(InvalidWebchatQrcodeState):
        verify_webchat_qrcode_state(tampered, secret="test-secret")


def test_verify_rejects_expired_qrcode_state():
    state = sign_webchat_qrcode_state(secret="test-secret", ttl_seconds=-1)
    time.sleep(0.01)

    with pytest.raises(InvalidWebchatQrcodeState):
        verify_webchat_qrcode_state(state, secret="test-secret")


def test_verify_rejects_wrong_qrcode_state_purpose():
    state = sign_webchat_qrcode_state(
        secret="test-secret",
        ttl_seconds=60,
        purpose="other",
    )

    with pytest.raises(InvalidWebchatQrcodeState):
        verify_webchat_qrcode_state(state, secret="test-secret")


def test_identity_from_sso_maps_wechat_id_to_wx_agent():
    identity = WebchatIdentity.from_sso(
        full_name="测试员工",
        employee_id="E000001",
        wechat_company_id="test_user",
    )

    assert identity.username == "测试员工"
    assert identity.employee_id == "E000001"
    assert identity.wechat_company_id == "test_user"
    assert identity.tenant_id == "test_user"
    assert identity.agent_id == "wx_test_user"


def test_canonical_session_id_for_identity_uses_wecom_single_chat_key():
    identity = WebchatIdentity(
        employee_id="E000001",
        username="测试员工",
        wechat_company_id="test_user",
        tenant_id="test_user",
        agent_id="wx_test_user",
    )

    assert canonical_session_id_for_identity(identity) == "wecom:test_user"


def test_wecom_session_kind_helpers():
    assert is_wecom_single_session_id("wecom:test_user") is True
    assert is_wecom_single_session_id("wecom:group:room") is False
    assert is_wecom_group_session_id("wecom:group:room") is True
    assert is_wecom_group_session_id("webchat:test_user:old") is False


def test_ensure_webchat_session_access_rejects_other_user_and_group():
    identity = WebchatIdentity(
        employee_id="E000001",
        username="测试员工",
        wechat_company_id="test_user",
        tenant_id="test_user",
        agent_id="wx_test_user",
    )

    assert ensure_webchat_session_access(identity, "wecom:test_user") == "wecom:test_user"

    with pytest.raises(PermissionError):
        ensure_webchat_session_access(identity, "wecom:other_user")

    with pytest.raises(PermissionError):
        ensure_webchat_session_access(identity, "wecom:group:room")


def test_sync_enabled_defaults_to_true(monkeypatch):
    monkeypatch.delenv("QWENPAW_WEBCHAT_WECOM_SESSION_SYNC_ENABLED", raising=False)
    assert is_webchat_wecom_session_sync_enabled() is True

    monkeypatch.setenv("QWENPAW_WEBCHAT_WECOM_SESSION_SYNC_ENABLED", "false")
    assert is_webchat_wecom_session_sync_enabled() is False


def test_webchat_channel_resolve_session_prefers_canonical_meta(tmp_path):
    channel = WebchatChannel(
        process=lambda request: None,
        enabled=True,
        bot_prefix="",
        workspace_dir=tmp_path,
    )

    assert (
        channel.resolve_session_id(
            "test_user",
            {"session_id": "default", "canonical_session_id": "wecom:test_user"},
        )
        == "wecom:test_user"
    )
