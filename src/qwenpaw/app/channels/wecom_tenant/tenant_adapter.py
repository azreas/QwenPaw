# -*- coding: utf-8 -*-
"""WeCom 租户路由适配器。"""
from __future__ import annotations

from typing import Any


class WeComTenantAdapter:
    """把 WeCom 消息分发到租户运行时。

    身份主键契约：单聊的 from.userid 必须与 WebChat SSO 返回的
    wechatCompanyId 是同一个值。这是企业微信的强契约——两者使用
    统一的企业成员 userid。resolve_tenant_id 返回的 tenant_id
    经 TenantAgentRegistry 转换为 wx_* agent_id，与 WebChat
    的 WebchatIdentity.agent_id 收敛到同一个值。
    """

    def __init__(self, tenant_router: Any) -> None:
        self._tenant_router = tenant_router

    def resolve_tenant_id(self, body: dict[str, Any]) -> str:
        sender_id = (body.get("from") or {}).get("userid", "")
        chatid = body.get("chatid", "")
        chat_type = body.get("chattype", "single")
        return chatid if chat_type == "group" else sender_id

    def get_media_dir(self, tenant_id: str) -> Any:
        get_media_dir = getattr(self._tenant_router, "get_media_dir", None)
        if callable(get_media_dir):
            return get_media_dir(tenant_id)
        return None

    async def handle(
        self,
        tenant_id: str,
        native: dict[str, Any],
        channel: Any,
    ) -> None:
        await self._tenant_router.handle(tenant_id, native, channel)
