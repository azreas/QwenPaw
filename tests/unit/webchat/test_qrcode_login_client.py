# -*- coding: utf-8 -*-
from __future__ import annotations

import httpx
import pytest

from qwenpaw.app.webchat.qrcode_login_client import (
    QrcodeLoginIdentity,
    WebchatQrcodeLoginClient,
    WebchatQrcodeLoginError,
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

    async def post(self, url, *, json):
        self.requests.append((url, json))
        if self.exc:
            raise self.exc
        return self.response


@pytest.mark.asyncio
async def test_authenticate_posts_code_and_normalizes_identity(monkeypatch):
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
        "qwenpaw.app.webchat.qrcode_login_client.httpx.AsyncClient",
        lambda **kwargs: fake_client,
    )

    identity = await WebchatQrcodeLoginClient(
        login_url="https://ai-dev.winxuan.com/service/qrcode/login",
        timeout_seconds=3,
    ).authenticate("wecom_code")

    assert identity == QrcodeLoginIdentity(
        full_name="测试员工",
        employee_id="E000001",
        wechat_company_id="test_user",
    )
    assert fake_client.requests == [
        (
            "https://ai-dev.winxuan.com/service/qrcode/login",
            {"code": "wecom_code"},
        )
    ]


@pytest.mark.asyncio
async def test_authenticate_supports_real_name_and_data_wrapper(monkeypatch):
    response = httpx.Response(
        200,
        json={
            "success": True,
            "data": {
                "realName": "测试员工",
                "employeeId": "E000001",
                "wechatCompanyId": "test_user",
            },
        },
    )
    fake_client = FakeAsyncClient(response=response)
    monkeypatch.setattr(
        "qwenpaw.app.webchat.qrcode_login_client.httpx.AsyncClient",
        lambda **kwargs: fake_client,
    )

    identity = await WebchatQrcodeLoginClient(
        login_url="https://ai-dev.winxuan.com/service/qrcode/login",
    ).authenticate("wecom_code")

    assert identity.full_name == "测试员工"
    assert identity.wechat_company_id == "test_user"


@pytest.mark.asyncio
async def test_authenticate_reports_missing_identity_fields(monkeypatch):
    response = httpx.Response(
        200,
        json={
            "code": 200,
            "msg": "OK",
            "result": {"fullName": "测试员工"},
        },
    )
    fake_client = FakeAsyncClient(response=response)
    monkeypatch.setattr(
        "qwenpaw.app.webchat.qrcode_login_client.httpx.AsyncClient",
        lambda **kwargs: fake_client,
    )

    with pytest.raises(WebchatQrcodeLoginError) as exc:
        await WebchatQrcodeLoginClient(
            login_url="https://ai-dev.winxuan.com/service/qrcode/login",
        ).authenticate("wecom_code")

    assert exc.value.status_code == 502
    assert exc.value.detail == (
        "登录服务返回身份信息缺少：工号(employeeId)、企微 ID(wechatCompanyId)"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [400, 401, 403])
async def test_authenticate_maps_auth_failures_to_401(monkeypatch, status_code):
    response = httpx.Response(status_code, json={"msg": "invalid code"})
    fake_client = FakeAsyncClient(response=response)
    monkeypatch.setattr(
        "qwenpaw.app.webchat.qrcode_login_client.httpx.AsyncClient",
        lambda **kwargs: fake_client,
    )

    with pytest.raises(WebchatQrcodeLoginError) as exc:
        await WebchatQrcodeLoginClient(
            login_url="https://ai-dev.winxuan.com/service/qrcode/login",
        ).authenticate("wecom_code")

    assert exc.value.status_code == 401
    assert exc.value.detail == "扫码登录失败，请重新扫码"


@pytest.mark.asyncio
async def test_authenticate_maps_upstream_5xx_to_503(monkeypatch):
    response = httpx.Response(502, json={"msg": "bad gateway"})
    fake_client = FakeAsyncClient(response=response)
    monkeypatch.setattr(
        "qwenpaw.app.webchat.qrcode_login_client.httpx.AsyncClient",
        lambda **kwargs: fake_client,
    )

    with pytest.raises(WebchatQrcodeLoginError) as exc:
        await WebchatQrcodeLoginClient(
            login_url="https://ai-dev.winxuan.com/service/qrcode/login",
        ).authenticate("wecom_code")

    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_authenticate_raises_504_on_timeout(monkeypatch):
    request = httpx.Request(
        "POST",
        "https://ai-dev.winxuan.com/service/qrcode/login",
    )
    fake_client = FakeAsyncClient(exc=httpx.TimeoutException("slow", request=request))
    monkeypatch.setattr(
        "qwenpaw.app.webchat.qrcode_login_client.httpx.AsyncClient",
        lambda **kwargs: fake_client,
    )

    with pytest.raises(WebchatQrcodeLoginError) as exc:
        await WebchatQrcodeLoginClient(
            login_url="https://ai-dev.winxuan.com/service/qrcode/login",
        ).authenticate("wecom_code")

    assert exc.value.status_code == 504


def test_from_env_uses_default_login_url(monkeypatch):
    monkeypatch.delenv("QWENPAW_WEBCHAT_QRCODE_LOGIN_URL", raising=False)
    monkeypatch.setenv("QWENPAW_WEBCHAT_QRCODE_TIMEOUT_SECONDS", "5")

    client = WebchatQrcodeLoginClient.from_env()

    assert client.login_url == "https://ai-dev.winxuan.com/service/qrcode/login"
    assert client.timeout_seconds == 5


def test_from_env_rejects_explicit_empty_login_url(monkeypatch):
    monkeypatch.setenv("QWENPAW_WEBCHAT_QRCODE_LOGIN_URL", "")

    with pytest.raises(WebchatQrcodeLoginError) as exc:
        WebchatQrcodeLoginClient.from_env()

    assert exc.value.status_code == 503
