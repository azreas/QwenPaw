# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import Request
import pytest

from qwenpaw.app.auth import AuthMiddleware
from qwenpaw.app.routers import webchat_tasks
from qwenpaw.app.webchat.session import WebchatIdentity


def make_request(path: str, method: str = "GET") -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("test", 80),
            "scheme": "http",
        }
    )


def test_webchat_routes_skip_admin_auth(monkeypatch):
    monkeypatch.setattr("qwenpaw.app.auth.is_auth_enabled", lambda: True)
    monkeypatch.setattr("qwenpaw.app.auth.has_registered_users", lambda: True)

    assert AuthMiddleware._should_skip_auth(make_request("/api/webchat/login")) is True
    assert AuthMiddleware._should_skip_auth(make_request("/api/webchat/me")) is True
    assert AuthMiddleware._should_skip_auth(make_request("/api/webchat/chat")) is True


@pytest.mark.asyncio
async def test_webchat_task_entry_error_uses_standard_envelope(monkeypatch):
    identity = WebchatIdentity.from_sso(
        full_name="张三",
        employee_id="E001",
        wechat_company_id="zhangsan",
    )
    monkeypatch.setattr(
        webchat_tasks,
        "_get_identity_from_request",
        lambda request: identity,
    )
    monkeypatch.setattr(
        webchat_tasks,
        "_resolve_policy",
        lambda identity: type("Policy", (), {"allow_tasks": False})(),
    )
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/webchat/tasks",
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
            "server": ("test", 80),
            "scheme": "http",
        },
    )
    request.state.request_id = "req-webchat-task"
    request.state.trace_id = "trace-webchat-task"

    with pytest.raises(Exception) as exc_info:
        await webchat_tasks.list_tasks(request)

    detail = exc_info.value.detail
    assert detail["error_code"] == "WEBCHAT_TASKS_DISABLED"
    assert detail["message"] == "Tasks are disabled"
    assert detail["request_id"] == "req-webchat-task"
    assert detail["trace_id"] == "trace-webchat-task"
    assert detail["tenant_id"] == "zhangsan"
    assert detail["agent_id"] == "wx_zhangsan"
    assert detail["session_id"] == ""
    assert detail["recoverable"] is False
