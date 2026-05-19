# -*- coding: utf-8 -*-
"""WeCom tenant channel."""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Optional

from qwenpaw.constant import WORKING_DIR
from qwenpaw.tenancy.ids import tenant_agent_id
from qwenpaw.tenancy.tenant_agent_registry import TenantAgentRegistry
from qwenpaw.tenancy.workspace_provisioner import WorkspaceProvisioner
from qwenpaw.tenancy.wx_tenant_router import WxTenantRouter

from ..wecom.channel import WecomChannel
from .tenant_adapter import WeComTenantAdapter

logger = logging.getLogger(__name__)


class WecomTenantChannel(WecomChannel):
    """企业微信多租户 channel。"""

    channel = "wecom_tenant"
    uses_manager_queue = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tenant_router = None
        self._tenant_adapter = None
        self._tenant_media_save_dir: Optional[Path] = None

    def set_workspace(self, workspace, command_registry=None) -> None:
        super().set_workspace(workspace, command_registry=command_registry)
        self._ensure_tenant_router()

    def _ensure_tenant_router(self) -> None:
        if self._tenant_adapter is not None:
            return
        workspace = getattr(self, "_workspace", None)
        manager = getattr(workspace, "_manager", None)
        if manager is None:
            logger.warning(
                "wecom_tenant: workspace manager missing, tenant router not ready",
            )
            return

        working_dir = Path(WORKING_DIR)
        template_dir = working_dir / "_template"
        provisioner = WorkspaceProvisioner(
            working_dir=working_dir,
            template_dir=template_dir,
        )
        registry = TenantAgentRegistry(manager)
        router = WxTenantRouter(registry=registry, provisioner=provisioner)
        self._tenant_router = router
        self._tenant_adapter = WeComTenantAdapter(router)

    async def _on_message(self, frame: Any) -> None:
        """Parse one incoming message and route it to tenant runtime."""
        body = frame.get("body") or {}
        self._ensure_tenant_router()
        tenant_adapter = self._tenant_adapter
        if tenant_adapter is None:
            logger.warning("wecom_tenant adapter missing, drop message")
            return

        tenant_id = tenant_adapter.resolve_tenant_id(body)
        if not tenant_id:
            logger.warning("wecom_tenant tenant_id missing, drop message")
            return

        try:
            media_save_dir = tenant_adapter.get_media_dir(tenant_id)
        except Exception:
            logger.exception(
                "wecom_tenant get_media_dir failed, tenant_id=%s",
                tenant_id,
            )
            await self._send_init_degrade(tenant_id, body)
            return

        captured: list[Any] = []
        original_enqueue = self._enqueue
        self._enqueue = lambda native: captured.append(native)
        self._tenant_media_save_dir = (
            Path(media_save_dir) if media_save_dir else None
        )
        try:
            await super()._on_message(frame)
        finally:
            self._tenant_media_save_dir = None
            self._enqueue = original_enqueue

        for native in captured:
            native["channel_id"] = self.channel
            sender_id = str(native.get("sender_id") or tenant_id)
            request_id = uuid.uuid4().hex
            trace_id = uuid.uuid4().hex
            agent_id = tenant_agent_id(tenant_id)
            native["tenant_id"] = tenant_id
            native["agent_id"] = agent_id
            native["entrypoint"] = self.channel
            native["request_id"] = request_id
            native["trace_id"] = trace_id
            meta = native.setdefault("meta", {})
            meta.update(
                {
                    "entrypoint": self.channel,
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "tenant_id": tenant_id,
                    "agent_id": agent_id,
                    "employee_id": sender_id,
                    "wechat_company_id": sender_id,
                    "session_id": native.get("session_id", ""),
                },
            )
            await tenant_adapter.handle(tenant_id, native, self)

    async def _send_init_degrade(
        self,
        tenant_id: str,
        body: dict,
    ) -> None:
        """工作区初始化失败时给员工发降级提示。"""
        from agentscope_runtime.engine.schemas.agent_schemas import ContentType

        sender_id = (body.get("from") or {}).get("userid", tenant_id)
        session_id = f"wecom:{sender_id}"
        try:
            await self.send_content_parts(
                to_handle=session_id,
                parts=[
                    {
                        "type": ContentType.TEXT,
                        "text": "助手工作区初始化失败，请稍后重试或联系管理员。",
                    },
                ],
                meta={},
            )
        except Exception:
            logger.exception(
                "wecom_tenant 降级提示发送失败，tenant_id=%s",
                tenant_id,
            )

    async def _download_media(
        self,
        url: str,
        aes_key: str = "",
        filename_hint: str = "file.bin",
        save_dir: Optional[Path] = None,
    ) -> Optional[str]:
        return await super()._download_media(
            url,
            aes_key=aes_key,
            filename_hint=filename_hint,
            save_dir=save_dir or self._tenant_media_save_dir,
        )
