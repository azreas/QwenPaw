# -*- coding: utf-8 -*-
from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from qwenpaw.app.webchat.sso_client import (
    SsoIdentity,
    WebchatSsoClient,
    WebchatSsoError,
)


class FakeAsyncClient:
    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, *, json, headers):
        self.requests.append((url, json, headers))
        if self.exc:
            raise self.exc
        return self.response


@pytest.mark.asyncio
async def test_authenticate_posts_sso_payload_and_normalizes_identity(monkeypatch):
    """真实 SSO 响应：{ code, msg, result: { fullName, employeeId, wechatCompanyId } }。"""
    response = httpx.Response(
        200,
        json={
            "code": 200,
            "msg": "OK",
            "result": {
                "fullName": "测试员工",
                "employeeId": "E000001",
                "wechatCompanyId": "test_user",
            },
        },
    )
    fake_client = FakeAsyncClient(response=response)
    monkeypatch.setattr(
        "qwenpaw.app.webchat.sso_client.httpx.AsyncClient",
        lambda **kwargs: fake_client,
    )
    client = WebchatSsoClient(
        login_url="https://sso.example.com/auth/login",
        cookie="AI_PLATFORM=fake",
        timeout_seconds=3,
    )

    identity = await client.authenticate("test_user", "secret")

    assert identity == SsoIdentity(
        full_name="测试员工",
        employee_id="E000001",
        wechat_company_id="test_user",
    )
    assert fake_client.requests == [
        (
            "https://sso.example.com/auth/login",
            {
                "userName": "test_user",
                "password": "secret",
                "imageVerifyCode": "",
            },
            {"Cookie": "AI_PLATFORM=fake"},
        )
    ]


@pytest.mark.asyncio
async def test_authenticate_falls_back_to_real_name(monkeypatch):
    """result 中缺少 fullName 时回退到 realName。"""
    response = httpx.Response(
        200,
        json={
            "code": 200,
            "msg": "OK",
            "result": {
                "realName": "测试员工",
                "employeeId": "E000001",
                "wechatCompanyId": "test_user",
            },
        },
    )
    fake_client = FakeAsyncClient(response=response)
    monkeypatch.setattr(
        "qwenpaw.app.webchat.sso_client.httpx.AsyncClient",
        lambda **kwargs: fake_client,
    )

    identity = await WebchatSsoClient(
        login_url="https://sso.example.com/auth/login",
    ).authenticate("test_user", "secret")

    assert identity.full_name == "测试员工"


@pytest.mark.asyncio
async def test_authenticate_raises_401_when_code_not_200(monkeypatch):
    """SSO 返回 code=401 时，用 msg 作为错误提示。"""
    response = httpx.Response(
        200,
        json={
            "code": 401,
            "msg": "用户名或密码错误",
            "result": None,
        },
    )
    fake_client = FakeAsyncClient(response=response)
    monkeypatch.setattr(
        "qwenpaw.app.webchat.sso_client.httpx.AsyncClient",
        lambda **kwargs: fake_client,
    )

    with pytest.raises(WebchatSsoError) as exc:
        await WebchatSsoClient(
            login_url="https://sso.example.com/auth/login",
        ).authenticate("bad", "secret")

    assert exc.value.status_code == 401
    assert exc.value.detail == "用户名或密码错误"


@pytest.mark.asyncio
async def test_authenticate_reports_missing_identity_fields(monkeypatch):
    """result 缺少必填字段时返回明确字段提示。"""
    response = httpx.Response(
        200,
        json={
            "code": 200,
            "msg": "OK",
            "result": {
                "fullName": "测试员工",
            },
        },
    )
    fake_client = FakeAsyncClient(response=response)
    monkeypatch.setattr(
        "qwenpaw.app.webchat.sso_client.httpx.AsyncClient",
        lambda **kwargs: fake_client,
    )

    with pytest.raises(WebchatSsoError) as exc:
        await WebchatSsoClient(
            login_url="https://sso.example.com/auth/login",
        ).authenticate("test_user", "secret")

    assert exc.value.status_code == 502
    assert exc.value.detail == (
        "登录服务返回身份信息缺少：工号(employeeId)、企微 ID(wechatCompanyId)"
    )


@pytest.mark.asyncio
async def test_authenticate_raises_504_on_timeout(monkeypatch):
    request = httpx.Request("POST", "https://sso.example.com/auth/login")
    fake_client = FakeAsyncClient(exc=httpx.TimeoutException("slow", request=request))
    monkeypatch.setattr(
        "qwenpaw.app.webchat.sso_client.httpx.AsyncClient",
        lambda **kwargs: fake_client,
    )

    with pytest.raises(WebchatSsoError) as exc:
        await WebchatSsoClient(
            login_url="https://sso.example.com/auth/login",
        ).authenticate("test_user", "secret")

    assert exc.value.status_code == 504
    assert exc.value.detail == "登录服务暂时不可用"


def test_from_env_requires_login_url(monkeypatch):
    monkeypatch.delenv("QWENPAW_WEBCHAT_SSO_LOGIN_URL", raising=False)

    with pytest.raises(WebchatSsoError) as exc:
        WebchatSsoClient.from_env()

    assert exc.value.status_code == 503
    assert "QWENPAW_WEBCHAT_SSO_LOGIN_URL" in exc.value.detail
