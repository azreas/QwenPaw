# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from typing import Any

import httpx
from pydantic import BaseModel

from qwenpaw.app.webchat.identity_errors import build_missing_identity_fields_detail
from qwenpaw.constant import EnvVarLoader

logger = logging.getLogger(__name__)

DEFAULT_QRCODE_LOGIN_URL = "https://ai-dev.winxuan.com/service/qrcode/login"


class QrcodeLoginIdentity(BaseModel):
    full_name: str
    employee_id: str
    wechat_company_id: str


class WebchatQrcodeLoginError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class WebchatQrcodeLoginClient:
    def __init__(
        self,
        *,
        login_url: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.login_url = login_url.strip()
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> "WebchatQrcodeLoginClient":
        login_url = EnvVarLoader.get_str(
            "QWENPAW_WEBCHAT_QRCODE_LOGIN_URL",
            DEFAULT_QRCODE_LOGIN_URL,
        )
        timeout = EnvVarLoader.get_float(
            "QWENPAW_WEBCHAT_QRCODE_TIMEOUT_SECONDS",
            30.0,
            min_value=1.0,
            max_value=60.0,
        )
        logger.info(
            "WebChat QR login from_env: login_url=%s timeout=%s",
            login_url or "<未配置>",
            timeout,
        )
        if not login_url.strip():
            raise WebchatQrcodeLoginError(
                503,
                "扫码登录服务未配置",
            )
        return cls(login_url=login_url, timeout_seconds=timeout)

    async def authenticate(self, code: str) -> QrcodeLoginIdentity:
        payload = {"code": code}
        logger.info(
            "WebChat QR login authenticate: url=%s timeout=%s",
            self.login_url,
            self.timeout_seconds,
        )
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                trust_env=False,
            ) as client:
                response = await client.post(self.login_url, json=payload)
                logger.info(
                    "WebChat QR login response: status=%s",
                    response.status_code,
                )
        except httpx.TimeoutException as exc:
            logger.warning("WebChat QR login timeout")
            raise WebchatQrcodeLoginError(504, "登录服务响应超时") from exc
        except httpx.RequestError as exc:
            logger.warning("WebChat QR login request error: %s", exc)
            raise WebchatQrcodeLoginError(503, "登录服务暂时不可用") from exc

        if response.status_code in (400, 401, 403):
            raise WebchatQrcodeLoginError(401, "扫码登录失败，请重新扫码")
        if response.status_code >= 500:
            logger.warning("WebChat QR login upstream 5xx: status=%s", response.status_code)
            raise WebchatQrcodeLoginError(503, "登录服务暂时不可用")
        if response.status_code >= 400:
            logger.warning("WebChat QR login unexpected status: status=%s", response.status_code)
            raise WebchatQrcodeLoginError(502, "登录服务返回异常")

        try:
            body = response.json()
        except ValueError as exc:
            logger.warning("WebChat QR login response is not valid JSON")
            raise WebchatQrcodeLoginError(502, "登录服务返回异常") from exc

        return self._parse_body(body)

    @staticmethod
    def _parse_body(body: Any) -> QrcodeLoginIdentity:
        if not isinstance(body, dict):
            logger.warning(
                "WebChat QR login response is not a dict: %s",
                type(body).__name__,
            )
            raise WebchatQrcodeLoginError(502, "登录服务返回异常")

        code = body.get("code")
        if code is not None and code != 200:
            msg = str(body.get("msg") or "扫码登录失败，请重新扫码")
            logger.warning("WebChat QR login returned code=%s", code)
            if code in (400, 401, 403):
                raise WebchatQrcodeLoginError(401, msg)
            raise WebchatQrcodeLoginError(502, msg)

        result = body.get("result")
        if not isinstance(result, dict):
            result = body.get("data")
        if not isinstance(result, dict):
            result = body

        full_name = str(result.get("fullName") or result.get("realName") or "").strip()
        employee_id = str(result.get("employeeId") or "").strip()
        wechat_company_id = str(result.get("wechatCompanyId") or "").strip()

        missing = []
        if not full_name:
            missing.append("fullName/realName")
        if not employee_id:
            missing.append("employeeId")
        if not wechat_company_id:
            missing.append("wechatCompanyId")
        if missing:
            logger.warning(
                "WebChat QR login identity missing fields: %s (got keys: %s)",
                missing,
                list(result.keys()),
            )
            raise WebchatQrcodeLoginError(
                502,
                build_missing_identity_fields_detail(missing),
            )

        logger.info("WebChat QR login identity resolved: required fields present")
        return QrcodeLoginIdentity(
            full_name=full_name,
            employee_id=employee_id,
            wechat_company_id=wechat_company_id,
        )
