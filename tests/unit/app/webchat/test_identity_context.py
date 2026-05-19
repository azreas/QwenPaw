# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import time
from types import SimpleNamespace

from qwenpaw.app.webchat.session import (
    WebchatIdentity,
    _b64encode,
    sign_webchat_token,
    verify_webchat_token,
)
from qwenpaw.app.webchat.sso_client import WebchatSsoClient


def test_webchat_identity_optional_org_fields_roundtrip():
    identity = WebchatIdentity.from_sso(
        full_name="张三",
        employee_id="E001",
        wechat_company_id="corp1",
        department="研发部",
        station="工程师",
        roles=("tenant_admin",),
    )
    token = sign_webchat_token(identity, secret="secret", ttl_seconds=300)

    loaded = verify_webchat_token(token, secret="secret")
    assert loaded.department == "研发部"
    assert loaded.station == "工程师"
    assert loaded.roles == ("tenant_admin",)


def test_sso_parser_accepts_optional_department_station():
    body = {
        "code": 200,
        "result": {
            "fullName": "张三",
            "employeeId": "E001",
            "wechatCompanyId": "corp1",
            "department": "研发部",
            "station": "工程师",
        },
    }
    identity = WebchatSsoClient._parse_sso_body(body)
    assert identity.department == "研发部"
    assert identity.station == "工程师"


def test_webchat_identity_defaults_tenant_member():
    """SSO 用户不传 roles 时默认 tenant_member。"""
    identity = WebchatIdentity.from_sso(
        full_name="李四",
        employee_id="E002",
        wechat_company_id="corp2",
    )
    assert identity.department == ""
    assert identity.station == ""
    assert identity.roles == ("tenant_member",)


def test_webchat_identity_explicit_empty_roles():
    """显式传空 tuple 可覆盖默认角色。"""
    identity = WebchatIdentity.from_sso(
        full_name="赵六",
        employee_id="E004",
        wechat_company_id="corp4",
        roles=(),
    )
    assert identity.roles == ()


def test_explicit_empty_roles_survives_roundtrip():
    """显式 roles=() 签名后验签仍是 ()，不会被提升为 tenant_member。"""
    identity = WebchatIdentity.from_sso(
        full_name="赵六",
        employee_id="E004",
        wechat_company_id="corp4",
        roles=(),
    )
    token = sign_webchat_token(identity, secret="secret", ttl_seconds=300)
    loaded = verify_webchat_token(token, secret="secret")
    assert loaded.roles == ()


def test_verify_old_token_without_new_fields():
    """旧 token 缺失 department/station/roles 时使用默认值。"""
    now = int(time.time())
    old_payload = {
        "employee_id": "E003",
        "username": "王五",
        "wechat_company_id": "corp3",
        "tenant_id": "corp3",
        "agent_id": "corp3",
        "sub": "E003",
        "iat": now,
        "exp": now + 300,
    }
    raw = json.dumps(old_payload, ensure_ascii=False, separators=(",", ":"))
    payload_b64 = _b64encode(raw.encode("utf-8"))
    sig = hmac.new(b"secret", payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    token = f"{payload_b64}.{sig}"
    loaded = verify_webchat_token(token, secret="secret")
    assert loaded.department == ""
    assert loaded.station == ""
    # 旧 token 无 roles 字段，回落到模型默认值 tenant_member
    assert loaded.roles == ("tenant_member",)


def test_get_identity_from_request_caches_identity(monkeypatch):
    from qwenpaw.app.routers import webchat

    calls = {"count": 0}

    def fake_verify(token):
        calls["count"] += 1
        return WebchatIdentity.from_sso(
            full_name="张三",
            employee_id="E001",
            wechat_company_id="corp1",
        )

    monkeypatch.setattr(webchat, "verify_webchat_session_token", fake_verify)
    request = SimpleNamespace(
        headers={"Authorization": "Bearer token"},
        state=SimpleNamespace(request_id="r", trace_id="t"),
    )

    assert webchat._get_identity_from_request(request).employee_id == "E001"
    assert webchat._get_identity_from_request(request).employee_id == "E001"
    assert calls["count"] == 1
    assert request.state.webchat_identity.employee_id == "E001"


def test_get_identity_from_request_builds_employee_entry_context(monkeypatch):
    from qwenpaw.app.routers import webchat

    identity = WebchatIdentity.from_sso(
        full_name="张三",
        employee_id="E001",
        wechat_company_id="zhangsan",
    )
    monkeypatch.setattr(
        webchat,
        "verify_webchat_session_token",
        lambda token: identity,
    )
    request = SimpleNamespace(
        headers={
            "Authorization": "Bearer token",
            "user-agent": "pytest",
        },
        state=SimpleNamespace(request_id="req-webchat", trace_id="trace-webchat"),
        client=SimpleNamespace(host="127.0.0.1"),
    )

    parsed = webchat._get_identity_from_request(request)
    ctx = request.state.request_context

    assert parsed.tenant_id == "zhangsan"
    assert parsed.agent_id == "wx_zhangsan"
    assert ctx.request_id == "req-webchat"
    assert ctx.trace_id == "trace-webchat"
    assert ctx.tenant_id == "zhangsan"
    assert ctx.agent_id == "wx_zhangsan"
    assert ctx.user_id == "E001"
    assert ctx.channel == "webchat"
    assert ctx.actor.actor_id == "E001"
    assert ctx.metadata["wechat_company_id"] == "zhangsan"
    assert not hasattr(request.state, "webchat_workspace_dir")
