# -*- coding: utf-8 -*-
from types import SimpleNamespace

from qwenpaw.app.webchat.session import WebchatIdentity
from qwenpaw.enterprise.context_builders import (
    build_context_from_runner_payload,
    build_context_from_webchat_identity,
)


def test_build_context_from_webchat_identity():
    identity = WebchatIdentity.from_sso(
        full_name="张三",
        employee_id="E001",
        wechat_company_id="corp1",
        department="研发部",
        station="工程师",
        roles=("tenant_member",),
    )
    request = SimpleNamespace(
        state=SimpleNamespace(request_id="req-1", trace_id="trace-1"),
        client=SimpleNamespace(host="127.0.0.1"),
        headers={"user-agent": "pytest"},
    )

    ctx = build_context_from_webchat_identity(request, identity)
    assert ctx.tenant_id == "corp1"
    assert ctx.agent_id == "wx_corp1"
    assert ctx.actor.actor_id == "E001"
    assert ctx.roles == ("tenant_member",)


def test_build_context_from_webchat_identity_generates_uuid_when_missing():
    identity = WebchatIdentity.from_sso(
        full_name="张三",
        employee_id="E001",
        wechat_company_id="corp1",
    )
    request = SimpleNamespace(
        state=SimpleNamespace(),
        client=SimpleNamespace(host="127.0.0.1"),
        headers={},
    )

    ctx = build_context_from_webchat_identity(request, identity)
    assert ctx.request_id != ""
    assert ctx.trace_id != ""


def test_build_context_from_runner_payload():
    ctx = build_context_from_runner_payload(
        request_id="req-1",
        trace_id="trace-1",
        agent_id="default",
        session_id="s1",
        user_id="u1",
        channel="console",
    )
    assert ctx.agent_id == "default"
    assert ctx.session_id == "s1"
    assert ctx.user_id == "u1"
    assert ctx.channel == "console"
    assert ctx.request_id == "req-1"
    assert ctx.trace_id == "trace-1"


def test_build_context_from_runner_payload_with_root_session():
    ctx = build_context_from_runner_payload(
        request_id="r",
        trace_id="t",
        agent_id="default",
        session_id="child",
        root_session_id="root",
        user_id="u1",
        channel="webchat",
    )
    assert ctx.agent_id == "default"
    assert ctx.session_id == "child"
    assert ctx.root_session_id == "root"
