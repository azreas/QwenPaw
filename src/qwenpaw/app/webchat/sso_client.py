# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from typing import Any

import httpx
from pydantic import BaseModel

from qwenpaw.app.webchat.identity_errors import build_missing_identity_fields_detail
from qwenpaw.constant import EnvVarLoader

logger = logging.getLogger(__name__)


class SsoIdentity(BaseModel):
    full_name: str
    employee_id: str
    wechat_company_id: str
    department: str = ""
    station: str = ""


class WebchatSsoError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class WebchatSsoClient:
    def __init__(
        self,
        *,
        login_url: str,
        cookie: str = "",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.login_url = login_url.strip()
        self.cookie = cookie.strip()
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> "WebchatSsoClient":
        login_url = EnvVarLoader.get_str("QWENPAW_WEBCHAT_SSO_LOGIN_URL", "")
        cookie = EnvVarLoader.get_str("QWENPAW_WEBCHAT_SSO_COOKIE", "")
        timeout = EnvVarLoader.get_float(
            "QWENPAW_WEBCHAT_SSO_TIMEOUT_SECONDS",
            30.0,
            min_value=1.0,
            max_value=60.0,
        )
        logger.info(
            "SSO from_env: login_url=%s, cookie=%s, timeout=%s",
            login_url or "<未配置>",
            "<已设置>" if cookie else "<未设置>",
            timeout,
        )
        if not login_url.strip():
            raise WebchatSsoError(
                503,
                "登录服务未配置 — 请设置环境变量 QWENPAW_WEBCHAT_SSO_LOGIN_URL",
            )
        return cls(
            login_url=login_url,
            cookie=cookie,
            timeout_seconds=timeout,
        )

    async def authenticate(self, username: str, password: str) -> SsoIdentity:
        headers = {"Cookie": self.cookie} if self.cookie else {}
        payload = {
            "userName": username,
            "password": password,
            "imageVerifyCode": "",
        }
        logger.info(
            "SSO authenticate: url=%s username=%s timeout=%s",
            self.login_url,
            username,
            self.timeout_seconds,
        )
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                trust_env=False,
            ) as client:
                response = await client.post(
                    self.login_url,
                    json=payload,
                    headers=headers,
                )
                logger.info(
                    "SSO response: status=%s",
                    response.status_code,
                )
        except httpx.TimeoutException as exc:
            logger.warning("SSO timeout: %s", exc)
            raise WebchatSsoError(504, "登录服务暂时不可用") from exc
        except httpx.RequestError as exc:
            logger.warning("SSO request error: %s", exc)
            raise WebchatSsoError(503, "登录服务暂时不可用") from exc

        if response.status_code in (400, 401, 403):
            raise WebchatSsoError(401, "用户名或密码错误")
        if response.status_code >= 500:
            logger.warning("SSO upstream 5xx: status=%s", response.status_code)
            raise WebchatSsoError(503, "登录服务暂时不可用")
        if response.status_code >= 400:
            logger.warning(
                "SSO unexpected status: status=%s",
                response.status_code,
            )
            raise WebchatSsoError(502, "登录服务返回异常")

        try:
            body = response.json()
        except ValueError as exc:
            logger.warning("SSO response is not valid JSON")
            raise WebchatSsoError(502, "登录服务返回异常") from exc

        return self._parse_sso_body(body)

    @staticmethod
    def _parse_sso_body(body: Any) -> SsoIdentity:
        """解析 SSO 响应体：{ code, msg, result: { fullName, employeeId, wechatCompanyId } }。"""
        if not isinstance(body, dict):
            logger.warning("SSO response is not a dict: %s", type(body).__name__)
            raise WebchatSsoError(502, "登录服务返回异常")

        code = body.get("code")
        if code != 200:
            msg = str(body.get("msg") or "未知错误")
            logger.warning("SSO returned code=%s msg=%s", code, msg)
            if code in (400, 401, 403):
                raise WebchatSsoError(401, msg)
            raise WebchatSsoError(502, msg)

        result = body.get("result")
        if not isinstance(result, dict):
            logger.warning(
                "SSO result is missing or not a dict: %s",
                type(result).__name__,
            )
            raise WebchatSsoError(502, "登录服务返回异常")

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
                "SSO identity missing fields: %s (got keys: %s)",
                missing,
                list(result.keys()),
            )
            raise WebchatSsoError(502, build_missing_identity_fields_detail(missing))

        logger.info("SSO identity resolved: required fields present")
        department = str(
            result.get("department")
            or result.get("departmentName")
            or ""
        ).strip()
        station = str(
            result.get("station")
            or result.get("position")
            or ""
        ).strip()
        return SsoIdentity(
            full_name=full_name,
            employee_id=employee_id,
            wechat_company_id=wechat_company_id,
            department=department,
            station=station,
        )
