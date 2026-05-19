# -*- coding: utf-8 -*-
"""WxTenantRouter：企业微信多租户路由入口。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from agentscope_runtime.engine.schemas.agent_schemas import ContentType

logger = logging.getLogger(__name__)

_DEGRADE_WORKSPACE = "助手工作区初始化失败，请稍后重试或联系管理员。"
_DEGRADE_AGENT = "助手服务暂时不可用，请稍后重试。"
_DEGRADE_RUN = "助手处理消息时出错，请稍后重试或联系管理员。"
_DEGRADE_GENERIC = "服务暂时不可用，请稍后重试或联系管理员。"


class WxTenantRouter:
    """将企业微信消息按 tenant_id 路由到独立 Workspace。"""

    def __init__(self, registry: Any, provisioner: Any):
        self._registry = registry
        self._provisioner = provisioner

    def get_media_dir(self, tenant_id: str) -> Path:
        """返回租户工作区内的媒体落盘目录。"""
        workspace_dir = Path(self._provisioner.ensure(tenant_id))
        media_dir = workspace_dir / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        return media_dir

    async def handle(
        self,
        tenant_id: str,
        native: dict,
        channel: Any,
    ) -> None:
        """处理单条企业微信消息并路由到对应租户 Agent。"""
        request = None
        phase = "init"
        try:
            # 企微 Bot 用户默认为 tenant_member，显式注入到 meta
            # 以便 runner 重建 RequestContext 时正确继承角色
            native.setdefault("meta", {})
            native["meta"].setdefault("roles", ["tenant_member"])
            request = channel.build_agent_request_from_native(native)
            phase = "workspace"
            workspace_dir = self._provisioner.ensure(tenant_id)
            phase = "agent"
            workspace = await self._registry.get_or_create(
                tenant_id,
                workspace_dir,
            )
            phase = "run"
            send_meta = dict(native.get("meta") or {})
            async for event in workspace.runner.stream_query(request):
                await channel.send_event(
                    user_id=request.user_id or tenant_id,
                    session_id=request.session_id,
                    event=event,
                    meta=send_meta,
                )
        except Exception:
            logger.exception(
                "WxTenantRouter.handle 异常，tenant_id=%s phase=%s",
                tenant_id,
                phase,
            )
            try:
                request = request or channel.build_agent_request_from_native(
                    native,
                )
                await self._send_degrade_message(
                    channel=channel,
                    native=native,
                    request=request,
                    phase=phase,
                )
            except Exception:
                logger.exception(
                    "WxTenantRouter.handle 降级提示发送失败，tenant_id=%s",
                    tenant_id,
                )

    async def _send_degrade_message(
        self,
        *,
        channel: Any,
        native: dict,
        request: Any,
        phase: str = "init",
    ) -> None:
        """在 tenant 主链失败时给用户回发区分阶段的降级提示。"""
        msg = {
            "workspace": _DEGRADE_WORKSPACE,
            "agent": _DEGRADE_AGENT,
            "run": _DEGRADE_RUN,
        }.get(phase, _DEGRADE_GENERIC)
        send_meta = dict(native.get("meta") or {})
        await channel.send_content_parts(
            to_handle=channel.get_to_handle_from_request(request),
            parts=[
                {
                    "type": ContentType.TEXT,
                    "text": msg,
                },
            ],
            meta=send_meta,
        )
