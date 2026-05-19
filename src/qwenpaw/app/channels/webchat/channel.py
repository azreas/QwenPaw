# -*- coding: utf-8 -*-
"""Webchat Channel.

A multi-user web chat channel that provides user isolation.
Each user gets their own agent workspace with isolated memory, workspace, and tasks.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from agentscope_runtime.engine.schemas.agent_schemas import (
    MessageType,
    Message,
    RunStatus,
)

from ....config.config import BaseChannelConfig
from ....constant import WORKING_DIR
from ..base import (
    BaseChannel,
    AudioContent,
    ContentType,
    FileContent,
    ImageContent,
    OnReplySent,
    OutgoingContentPart,
    ProcessHandler,
    VideoContent,
    TextContent,
)
from ..utils import file_url_to_local_path


logger = logging.getLogger(__name__)


class WebchatConfig(BaseChannelConfig):
    """Webchat channel configuration."""

    media_dir: Optional[str] = None
    user_data_dir: Optional[str] = None


class WebchatChannel(BaseChannel):
    """Webchat Channel: multi-user web chat with agent isolation.

    Each user is mapped to their own agent workspace.
    User authentication is handled by the webchat API endpoints.
    """

    channel = "webchat"

    def __init__(
        self,
        process: ProcessHandler,
        enabled: bool,
        bot_prefix: str,
        on_reply_sent: OnReplySent = None,
        show_tool_details: bool = True,
        filter_tool_messages: bool = False,
        filter_thinking: bool = False,
        workspace_dir: Optional[Union[str, Path]] = None,
        media_dir: Optional[str] = None,
        user_data_dir: Optional[str] = None,
    ):
        """Initialize WebchatChannel.

        Args:
            process: Handler for agent requests.
            enabled: Whether this channel is active.
            bot_prefix: Prefix string for bot messages.
            on_reply_sent: Callback when reply is sent.
            show_tool_details: Whether to show tool execution details.
            filter_tool_messages: Whether to filter out tool messages.
            filter_thinking: Whether to filter thinking/reasoning blocks.
            workspace_dir: Agent workspace directory.
            media_dir: Directory for media files.
            user_data_dir: Directory for user data storage.
        """
        super().__init__(
            process,
            on_reply_sent=on_reply_sent,
            show_tool_details=show_tool_details,
            filter_tool_messages=filter_tool_messages,
            filter_thinking=filter_thinking,
        )
        self.enabled = enabled
        self.bot_prefix = bot_prefix
        self._workspace_dir = (
            Path(workspace_dir).expanduser() if workspace_dir else None
        )

        if not media_dir and self._workspace_dir:
            self._media_dir = self._workspace_dir / "media"
        elif media_dir:
            self._media_dir = Path(media_dir).expanduser()
        else:
            self._media_dir = Path(WORKING_DIR) / "webchat" / "media"
        self._media_dir.mkdir(parents=True, exist_ok=True)

        if not user_data_dir:
            user_data_dir = Path(WORKING_DIR) / "webchat" / "users"
        self._user_data_dir = Path(user_data_dir).expanduser()
        self._user_data_dir.mkdir(parents=True, exist_ok=True)

        self._users_file = self._user_data_dir / "users.json"
        self._user_agent_map_file = self._user_data_dir / "user_agent_map.json"

    @property
    def media_dir(self) -> Path:
        """Media directory."""
        return self._media_dir

    @classmethod
    def from_env(
        cls,
        process: ProcessHandler,
        on_reply_sent: OnReplySent = None,
    ) -> "WebchatChannel":
        return cls(
            process=process,
            enabled=os.getenv("WEBCHAT_CHANNEL_ENABLED", "1") == "1",
            bot_prefix=os.getenv("WEBCHAT_BOT_PREFIX", ""),
            on_reply_sent=on_reply_sent,
            media_dir=os.getenv("WEBCHAT_MEDIA_DIR", ""),
            user_data_dir=os.getenv("WEBCHAT_USER_DATA_DIR", ""),
        )

    @classmethod
    def from_config(
        cls,
        process: ProcessHandler,
        config: WebchatConfig,
        on_reply_sent: OnReplySent = None,
        show_tool_details: bool = True,
        filter_tool_messages: bool = False,
        filter_thinking: bool = False,
        workspace_dir: Optional[Union[str, Path]] = None,
    ) -> "WebchatChannel":
        return cls(
            process=process,
            enabled=config.enabled,
            bot_prefix=config.bot_prefix or "",
            on_reply_sent=on_reply_sent,
            show_tool_details=show_tool_details,
            filter_tool_messages=filter_tool_messages,
            filter_thinking=filter_thinking,
            workspace_dir=workspace_dir,
            media_dir=config.media_dir or "",
            user_data_dir=config.user_data_dir or "",
        )

    async def start(self) -> None:
        """Start the webchat channel."""
        if not self.enabled:
            logger.debug("Webchat channel disabled")
            return
        logger.info("Webchat channel started")

    async def stop(self) -> None:
        """Stop the webchat channel."""
        if not self.enabled:
            return
        logger.info("Webchat channel stopped")

    def resolve_session_id(
        self,
        sender_id: str,
        channel_meta: Optional[dict] = None,
    ) -> str:
        """Resolve session_id for webchat.

        Format: webchat:<user_id>:<session_id>
        确保 session_id 不包含冒号，避免拼接问题。
        """
        if channel_meta and channel_meta.get("canonical_session_id"):
            return str(channel_meta["canonical_session_id"])

        if channel_meta and channel_meta.get("session_id"):
            # 清理 session_id 中可能存在的冒号
            raw_session_id = channel_meta['session_id']
            # 如果 session_id 已包含 webchat: 前缀，则直接使用
            if raw_session_id.startswith("webchat:"):
                return raw_session_id
            # 否则，确保 session_id 是安全的（替换冒号为下划线）
            clean_session_id = raw_session_id.replace(":", "_")
            return f"webchat:{sender_id}:{clean_session_id}"
        return f"webchat:{sender_id}:default"

    def _resolve_webchat_upload_refs(
        self,
        content_parts: List[Any],
    ) -> List[Any]:
        """Resolve Image/File/Audio/VideoContent."""
        if not self._media_dir:
            return content_parts

        def resolve_one(part: Any) -> Optional[OutgoingContentPart]:
            content_type = getattr(part, "type", None)
            if content_type == ContentType.IMAGE:
                url = getattr(part, "image_url", None)
                if url:
                    return ImageContent(
                        type=ContentType.IMAGE,
                        image_url=url,
                    )
            elif content_type == ContentType.VIDEO:
                url = getattr(part, "video_url", None)
                if url:
                    return VideoContent(
                        type=ContentType.VIDEO,
                        video_url=url,
                    )
            elif content_type == ContentType.AUDIO:
                url = getattr(part, "data", None)
                if url:
                    return AudioContent(
                        type=ContentType.AUDIO,
                        data=url,
                    )
            elif content_type == ContentType.FILE:
                url = getattr(part, "file_url", None)
                if url:
                    return FileContent(
                        type=ContentType.FILE,
                        filename=getattr(part, "filename", None) or url,
                        file_url=url,
                    )
            elif content_type == ContentType.TEXT:
                return TextContent(type=ContentType.TEXT, text=part.text)
            return part

        input_content_parts = []
        for content in content_parts:
            part = resolve_one(content)
            if part is not None:
                input_content_parts.append(part)
        return input_content_parts

    def build_agent_request_from_native(self, native_payload: Any) -> Any:
        """Build AgentRequest from webchat native payload."""
        payload = native_payload if isinstance(native_payload, dict) else {}
        channel_id = payload.get("channel_id") or self.channel
        sender_id = payload.get("sender_id") or ""
        content_parts = payload.get("content_parts") or []
        content_parts = self._resolve_webchat_upload_refs(content_parts)
        meta = payload.get("meta") or {}
        session_id = payload.get("session_id") or self.resolve_session_id(
            sender_id,
            meta,
        )
        request = self.build_agent_request_from_user_content(
            channel_id=channel_id,
            sender_id=sender_id,
            session_id=session_id,
            content_parts=content_parts,
            channel_meta=meta,
        )
        request.channel_meta = meta
        request.state = SimpleNamespace(
            request_id=str(meta.get("request_id") or payload.get("request_id") or ""),
            trace_id=str(meta.get("trace_id") or payload.get("trace_id") or ""),
        )
        return request

    async def _extract_media_message(self, message: Message) -> Message | None:
        """Extract media message from message."""
        parts = self._message_to_content_parts(message)
        media_message = None
        if message.type in (
            MessageType.FUNCTION_CALL_OUTPUT,
            MessageType.PLUGIN_CALL_OUTPUT,
            MessageType.MCP_TOOL_CALL_OUTPUT,
        ):
            new_parts = []
            for part in parts:
                if part.type == ContentType.IMAGE:
                    new_part = message.model_copy()
                    new_part.image_url = file_url_to_local_path(
                        new_part.image_url,
                    )
                    new_parts.append(new_part)
                elif part.type == ContentType.VIDEO:
                    new_part = message.model_copy()
                    new_part.video_url = file_url_to_local_path(
                        new_part.video_url,
                    )
                    new_parts.append(new_part)
                elif part.type == ContentType.AUDIO:
                    new_part = message.model_copy()
                    new_part.data = file_url_to_local_path(new_part.data)
                    new_parts.append(new_part)
                elif part.type == ContentType.FILE:
                    new_part = message.model_copy()
                    new_part.file_url = file_url_to_local_path(
                        new_part.file_url,
                    )
                    new_parts.append(new_part)
            if new_parts:
                media_message = Message(
                    type=MessageType.MESSAGE,
                    role="assistant",
                    content=new_parts,
                )
        return media_message

    def _extract_token_usage(
        self,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        from ....token_usage import TokenRecordingModelWrapper

        if not session_id:
            return None

        usage = TokenRecordingModelWrapper.pop_usage_for_session(session_id)
        logger.info("Usage for session %s: %s", session_id, usage)
        return usage

    async def stream_one(self, payload: Any) -> AsyncGenerator[str, None]:
        """Process one payload and yield SSE-formatted events."""
        if isinstance(payload, dict) and "content_parts" in payload:
            session_id = self.resolve_session_id(
                payload.get("sender_id") or "",
                payload.get("meta"),
            )
            content_parts = payload.get("content_parts") or []
            should_process, merged = self._apply_no_text_debounce(
                session_id,
                content_parts,
            )
            if not should_process:
                return
            payload = {**payload, "content_parts": merged}
            request = self.build_agent_request_from_native(payload)
        else:
            request = payload
            session_id = getattr(request, "session_id", "") or ""
            if getattr(request, "input", None):
                contents = list(
                    getattr(request.input[0], "content", None) or [],
                )
                should_process, merged = self._apply_no_text_debounce(
                    session_id,
                    contents,
                )
                if not should_process:
                    return
                if merged and hasattr(request.input[0], "content"):
                    request.input[0].content = merged

        try:
            send_meta = getattr(request, "channel_meta", None) or {}
            send_meta.setdefault("bot_prefix", self.bot_prefix)
            last_response = None
            has_completed_message = False
            event_count = 0

            async for event in self._process(request):
                event_count += 1
                obj = getattr(event, "object", None)
                status = getattr(event, "status", None)
                ev_type = getattr(event, "type", None)

                logger.debug(
                    "webchat event #%s: object=%s status=%s type=%s",
                    event_count,
                    obj,
                    status,
                    ev_type,
                )

                if (
                    event.object == "response"
                    and event.status == RunStatus.Completed
                ):
                    event_output = event.output
                    event.output = []
                    if event_output is not None:
                        for message in event_output:
                            event.output.append(message)
                            media_message = await self._extract_media_message(
                                message,
                            )
                            if media_message:
                                event.output.append(media_message)

                if obj == "response":
                    usage_data = self._extract_token_usage(session_id)
                    if usage_data and hasattr(event, "usage"):
                        setattr(event, "usage", usage_data)

                if (
                    obj == "response"
                    and status == RunStatus.Completed
                    and not (getattr(event, "output", None) or [])
                    and has_completed_message
                ):
                    continue

                if hasattr(event, "model_dump_json"):
                    data = event.model_dump_json()
                elif hasattr(event, "json"):
                    data = event.json()
                else:
                    data = json.dumps({"text": str(event)})
                yield f"data: {data}\n\n"

                if obj == "message" and status == RunStatus.Completed:
                    has_completed_message = True
                    media_message = await self._extract_media_message(event)
                    if media_message:
                        yield f"data: {media_message.model_dump_json()}\n\n"

                elif obj == "response":
                    last_response = event

            logger.info(
                "webchat stream done: event_count=%s has_response=%s",
                event_count,
                last_response is not None,
            )

            to_handle = request.user_id or ""
            if self._on_reply_sent:
                self._on_reply_sent(
                    self.channel,
                    to_handle,
                    request.session_id or f"{self.channel}:{to_handle}",
                )

        except Exception as e:
            logger.exception("webchat process/reply failed")
            err_msg = str(e).strip() or "An error occurred while processing."
            yield f"data: {json.dumps({'error': err_msg})}\n\n"

    async def consume_one(self, payload: Any) -> None:
        """Process one payload; drain stream_one."""
        async for _ in self.stream_one(payload):
            pass
