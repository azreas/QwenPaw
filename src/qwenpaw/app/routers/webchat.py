# -*- coding: utf-8 -*-
"""Webchat API endpoints: authentication, chat, and file upload."""
from __future__ import annotations

import json
import logging
import re
import uuid
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Union

from fastapi import APIRouter, Body, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field
from starlette.responses import FileResponse, StreamingResponse

from agentscope_runtime.engine.schemas.agent_schemas import AgentRequest
from ..agent_context import get_agent_for_request
from ..utils import schedule_agent_reload
from ...agents.templates import get_workspace_md_template_id
from ...agents.utils import copy_workspace_md_files
from ...config import AgentsRunningConfig
from ...config.config import AgentProfileConfig
from ...config.agent_config_file import (
    load_agent_config_from_workspace,
    write_agent_config_to_workspace,
)
from ...constant import BUILTIN_QA_AGENT_ID, SUPPORTED_AGENT_LANGUAGES, EnvVarLoader
from ...enterprise.context import RequestContext
from ...enterprise.errors import build_error_envelope
from ..channels.webchat.user_manager import WebchatUserManager
from ..webchat.qrcode_login_client import (
    WebchatQrcodeLoginClient,
    WebchatQrcodeLoginError,
)
from ..webchat.session import (
    InvalidWebchatQrcodeState,
    InvalidWebchatToken,
    WebchatIdentity,
    sign_webchat_qrcode_state,
    sign_webchat_token,
    verify_webchat_qrcode_state,
    verify_webchat_token as verify_webchat_session_token,
)
from ..webchat.session_catalog import (
    list_webchat_visible_sessions,
    resolve_visible_chat,
)
from ..webchat.session_sync import (
    canonical_session_id_for_identity,
    ensure_webchat_session_access,
    is_webchat_wecom_session_sync_enabled,
)
from ..webchat.sso_client import WebchatSsoClient, WebchatSsoError
from ..webchat.tenant_resolver import (
    build_webchat_channel_facade,
    ensure_requested_agent_allowed,
    get_tenant_workspace_for_identity,
)
from .workspace import _validate_and_extract_zip, _zip_directory


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webchat", tags=["webchat"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

_user_manager: WebchatUserManager | None = None


def get_user_manager() -> WebchatUserManager:
    """Get or create user manager singleton."""
    global _user_manager
    if _user_manager is None:
        from qwenpaw.constant import WORKING_DIR
        user_data_dir = WORKING_DIR / "webchat" / "users"
        _user_manager = WebchatUserManager(user_data_dir)
    return _user_manager


def _safe_filename(name: str) -> str:
    """Safe basename, alphanumeric/./-/_, max 200 chars."""
    base = Path(name).name if name else "file"
    safe = re.sub(r"[^\w.\-]", "_", base)[:200] or "file"
    if safe in {".", ".."}:
        return "file"
    return safe


# ── Workspace file browser helpers ──────────────────────────────────────────

_PROTECTED_FILES = frozenset({
    "AGENTS.md", "SOUL.md", "PROFILE.md", "MEMORY.md",
    "HEARTBEAT.md", "agent.json", "skills.json",
    "jobs.json", "chats.json",
})
_PROTECTED_DIRS = frozenset({"sessions", "memory", "skills"})


def _is_file_deletable(workspace_dir: Path, file_path: Path) -> bool:
    """文件在 media/ 或根目录且非受保护文件时可删除。"""
    rel = file_path.resolve().relative_to(workspace_dir.resolve())
    parts = rel.parts
    if any(p in _PROTECTED_DIRS for p in parts):
        return False
    if file_path.name in _PROTECTED_FILES:
        return False
    return True


def _safe_resolve(workspace_dir: Path, subpath: str) -> Path:
    """解析子路径，拒绝逃逸。"""
    clean = subpath.replace("\\", "/").lstrip("/")
    target = (workspace_dir / clean).resolve()
    if not target.is_relative_to(workspace_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid path")
    return target


def _extract_session_and_payload(request_data: Union[AgentRequest, dict]):
    """Extract run_key (ChatSpec.id), session_id, and native payload."""
    if isinstance(request_data, AgentRequest):
        channel_id = "webchat"
        sender_id = request_data.user_id or "default"
        session_id = request_data.session_id or "default"
        content_parts = []
        if request_data.input and len(request_data.input) > 0:
            content_parts = list(request_data.input[0].content)
    else:
        channel_id = request_data.get("channel", "webchat")
        sender_id = request_data.get("user_id", "default")
        session_id = request_data.get("session_id", "default")
        input_data = request_data.get("input", [])
        content_parts = []
        for item in input_data:
            if isinstance(item, dict) and "content" in item:
                content_list = item["content"]
                if isinstance(content_list, list):
                    for part in content_list:
                        if isinstance(part, dict) and "text" in part:
                            from ..channels.base import TextContent, ContentType
                            content_parts.append(TextContent(
                                type=ContentType.TEXT,
                                text=part["text"],
                            ))

    native_payload = {
        "channel_id": channel_id,
        "sender_id": sender_id,
        "content_parts": content_parts,
        "meta": {
            "session_id": session_id,
            "user_id": sender_id,
        },
    }
    return native_payload


def _resolve_webchat_session_for_request(
    identity: WebchatIdentity,
    requested_session_id: str | None,
    visible_chats: list[Any] | None = None,
) -> tuple[str, dict]:
    requested = str(requested_session_id or "").strip()
    meta: dict[str, str] = {"user_id": identity.wechat_company_id}
    if not is_webchat_wecom_session_sync_enabled():
        return requested or "default", meta

    canonical = canonical_session_id_for_identity(identity)
    if requested in ("", "default", canonical):
        meta["canonical_session_id"] = canonical
        return canonical, meta

    if visible_chats is not None:
        chat = resolve_visible_chat(identity, visible_chats, requested)
        if chat is None and ":" not in requested:
            legacy_session_id = f"webchat:{identity.wechat_company_id}:{requested}"
            chat = resolve_visible_chat(identity, visible_chats, legacy_session_id)
        if chat is not None:
            session_id = ensure_webchat_session_access(
                identity,
                str(getattr(chat, "session_id", "")),
            )
            if session_id == canonical:
                meta["canonical_session_id"] = canonical
            return session_id, meta

    allowed = ensure_webchat_session_access(identity, requested)
    if allowed == canonical:
        meta["canonical_session_id"] = canonical
    elif ":" not in allowed:
        return f"webchat:{identity.wechat_company_id}:{allowed}", meta
    return allowed, meta


class WebchatLoginRequest(BaseModel):
    username: str
    password: str


class WebchatLoginResponse(BaseModel):
    token: str
    user_id: str
    username: str
    agent_id: str
    employee_id: str | None = None


class WebchatRegisterRequest(BaseModel):
    username: str
    password: str


class WebchatStatusResponse(BaseModel):
    has_users: bool
    auth_mode: str = "sso"


class WebchatUserResponse(BaseModel):
    user_id: str
    username: str
    agent_id: str
    employee_id: str | None = None


class WebchatQrcodeConfigResponse(BaseModel):
    enabled: bool
    appid: str | None = None
    agentid: str | None = None
    redirect_uri: str | None = None
    state: str | None = None
    href: str | None = None


class WebchatQrcodeLoginRequest(BaseModel):
    code: str
    state: str


def _get_user_id_from_request(request: Request) -> str:
    """Extract user_id from request token."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_manager = get_user_manager()
    user_id = user_manager.verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_id


def _get_token_from_request(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return token


def _get_or_build_webchat_request_context(
    request: Request,
    identity: WebchatIdentity,
) -> RequestContext:
    ctx = getattr(request.state, "request_context", None)
    if ctx is not None:
        return ctx

    from ...enterprise.context_builders import build_context_from_webchat_identity

    ctx = build_context_from_webchat_identity(request, identity)
    request.state.request_context = ctx
    return ctx


def _get_identity_from_request(request: Request) -> WebchatIdentity:
    cached = getattr(request.state, "webchat_identity", None)
    if cached is not None:
        _get_or_build_webchat_request_context(request, cached)
        return cached
    try:
        identity = verify_webchat_session_token(
            _get_token_from_request(request),
        )
    except InvalidWebchatToken as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        ) from exc
    request.state.webchat_identity = identity

    _get_or_build_webchat_request_context(request, identity)
    return identity


def _webchat_error_detail(
    request: Request,
    identity: WebchatIdentity,
    *,
    error_code: str,
    message: str,
    session_id: str = "",
    recoverable: bool = False,
    retry_after: int | None = None,
) -> dict[str, Any]:
    ctx = _get_or_build_webchat_request_context(request, identity)
    if session_id and ctx.session_id != session_id:
        ctx = RequestContext(
            request_id=ctx.request_id,
            trace_id=ctx.trace_id,
            tenant_id=ctx.tenant_id,
            agent_id=ctx.agent_id,
            user_id=ctx.user_id,
            session_id=session_id,
            root_session_id=ctx.root_session_id or session_id,
            channel=ctx.channel,
            roles=ctx.roles,
            actor=ctx.actor,
            metadata=ctx.metadata,
        )
    return build_error_envelope(
        ctx,
        error_code=error_code,
        message=message,
        recoverable=recoverable,
        retry_after=retry_after,
    )


def _webchat_context_meta(
    request: Request,
    identity: WebchatIdentity,
    *,
    session_id: str,
    entrypoint: str = "webchat",
) -> dict[str, Any]:
    ctx = _get_or_build_webchat_request_context(request, identity)
    return {
        "entrypoint": entrypoint,
        "request_id": ctx.request_id,
        "trace_id": ctx.trace_id,
        "tenant_id": identity.tenant_id,
        "agent_id": identity.agent_id,
        "session_id": session_id,
        "employee_id": identity.employee_id,
        "wechat_company_id": identity.wechat_company_id,
    }


async def _get_tenant_workspace_config(
    request: Request,
    identity: WebchatIdentity,
):
    workspace = await get_tenant_workspace_for_identity(request, identity)
    workspace_dir_value = getattr(workspace, "workspace_dir", "")
    if not workspace_dir_value:
        raise HTTPException(status_code=404, detail="Workspace not found")

    workspace_dir = Path(workspace_dir_value).expanduser()
    from qwenpaw.tenancy.tenant_agent_config import (
        ensure_tenant_agent_config_file,
    )

    agent_config = ensure_tenant_agent_config_file(
        agent_id=identity.agent_id,
        workspace_dir=workspace_dir,
    )
    return workspace, workspace_dir, agent_config


def _save_tenant_agent_config(workspace_dir: Path, agent_config) -> None:
    from qwenpaw.config.agent_config_file import write_agent_config_to_workspace

    write_agent_config_to_workspace(workspace_dir, agent_config)


@router.post("/register")
async def register(req: WebchatRegisterRequest):
    raise HTTPException(
        status_code=410,
        detail="WebChat registration is disabled in SSO mode",
    )


@router.post("/login")
async def login(req: WebchatLoginRequest):
    """Login via enterprise SSO."""
    logger.info("WebChat login attempt")
    if not req.username.strip() or not req.password.strip():
        raise HTTPException(status_code=400, detail="Username and password are required")
    try:
        sso_identity = await WebchatSsoClient.from_env().authenticate(
            req.username.strip(),
            req.password,
        )
    except WebchatSsoError as exc:
        logger.warning(
            "WebChat login failed: status=%s detail=%s",
            exc.status_code,
            exc.detail,
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    identity = WebchatIdentity.from_sso(
        full_name=sso_identity.full_name,
        employee_id=sso_identity.employee_id,
        wechat_company_id=sso_identity.wechat_company_id,
        department=sso_identity.department,
        station=sso_identity.station,
    )
    token = sign_webchat_token(identity)
    logger.info("WebChat login success")
    return WebchatLoginResponse(
        token=token,
        user_id=identity.wechat_company_id,
        username=identity.username,
        agent_id=identity.agent_id,
        employee_id=identity.employee_id,
    )


@router.get("/qrcode/config", response_model=WebchatQrcodeConfigResponse)
async def qrcode_config(request: Request):
    """Return enterprise WeCom QR login config for the WebChat login page."""
    if not EnvVarLoader.get_bool("QWENPAW_WEBCHAT_QRCODE_ENABLED", False):
        return WebchatQrcodeConfigResponse(enabled=False)

    appid = EnvVarLoader.get_str("QWENPAW_WEBCHAT_QRCODE_APP_ID", "").strip()
    agentid = EnvVarLoader.get_str("QWENPAW_WEBCHAT_QRCODE_AGENT_ID", "").strip()
    if not appid or not agentid:
        logger.warning("WebChat QR login enabled but appid or agentid is missing")
        return WebchatQrcodeConfigResponse(enabled=False)

    redirect_uri = EnvVarLoader.get_str(
        "QWENPAW_WEBCHAT_QRCODE_REDIRECT_URI",
        "",
    ).strip()
    if not redirect_uri:
        redirect_uri = f"{str(request.base_url).rstrip('/')}/webchat/login"
    href = EnvVarLoader.get_str("QWENPAW_WEBCHAT_QRCODE_HREF", "").strip() or None

    return WebchatQrcodeConfigResponse(
        enabled=True,
        appid=appid,
        agentid=agentid,
        redirect_uri=redirect_uri,
        state=sign_webchat_qrcode_state(),
        href=href,
    )


@router.post("/login/qrcode", response_model=WebchatLoginResponse)
async def login_with_qrcode(req: WebchatQrcodeLoginRequest):
    """Login via enterprise WeCom QR code callback code."""
    logger.info("WebChat QR login attempt")
    if not req.code.strip() or not req.state.strip():
        raise HTTPException(status_code=400, detail="二维码登录参数无效，请重试")
    try:
        verify_webchat_qrcode_state(req.state.strip())
    except InvalidWebchatQrcodeState as exc:
        raise HTTPException(status_code=401, detail="二维码已过期，请重新打开扫码登录") from exc

    try:
        qrcode_identity = await WebchatQrcodeLoginClient.from_env().authenticate(
            req.code.strip(),
        )
    except WebchatQrcodeLoginError as exc:
        logger.warning(
            "WebChat QR login failed: status=%s detail=%s",
            exc.status_code,
            exc.detail,
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    identity = WebchatIdentity.from_sso(
        full_name=qrcode_identity.full_name,
        employee_id=qrcode_identity.employee_id,
        wechat_company_id=qrcode_identity.wechat_company_id,
        department=getattr(qrcode_identity, "department", ""),
        station=getattr(qrcode_identity, "station", ""),
    )
    token = sign_webchat_token(identity)
    logger.info("WebChat QR login success")
    return WebchatLoginResponse(
        token=token,
        user_id=identity.wechat_company_id,
        username=identity.username,
        agent_id=identity.agent_id,
        employee_id=identity.employee_id,
    )


@router.get("/status")
async def status():
    return WebchatStatusResponse(has_users=True, auth_mode="sso")


@router.get("/token-usage")
async def get_token_usage(
    request: Request,
    start_date: str | None = Query(None, description="Start date YYYY-MM-DD"),
    end_date: str | None = Query(None, description="End date YYYY-MM-DD"),
):
    """Get token usage summary for webchat user."""
    from ...token_usage import get_token_usage_manager
    from datetime import date as date_type

    def _parse_date(s: str | None) -> date_type | None:
        if not s:
            return None
        try:
            return date_type.fromisoformat(s)
        except (ValueError, TypeError):
            return None

    # Get user's agent_id from webchat session token
    identity = _get_identity_from_request(request)
    agent_id = identity.agent_id

    start_d = _parse_date(start_date)
    end_d = _parse_date(end_date)

    return await get_token_usage_manager().get_summary(
        start_date=start_d,
        end_date=end_d,
        agent_id=agent_id,
    )


@router.get("/me", response_model=WebchatUserResponse)
async def get_current_user(request: Request):
    """Get current user info from webchat session token."""
    identity = _get_identity_from_request(request)
    return WebchatUserResponse(
        user_id=identity.wechat_company_id,
        username=identity.username,
        agent_id=identity.agent_id,
        employee_id=identity.employee_id,
    )


@router.post("/verify")
async def verify_token(request: Request):
    """Verify webchat session token validity."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""

    if not token:
        return {
            "valid": False,
            "user_id": "",
            "username": "",
            "agent_id": "",
            "employee_id": "",
        }

    try:
        identity = verify_webchat_session_token(token)
    except InvalidWebchatToken:
        return {
            "valid": False,
            "user_id": "",
            "username": "",
            "agent_id": "",
            "employee_id": "",
        }

    return {
        "valid": True,
        "user_id": identity.wechat_company_id,
        "username": identity.username,
        "agent_id": identity.agent_id,
        "employee_id": identity.employee_id,
    }


@router.post(
    "/chat",
    status_code=200,
    summary="Chat with webchat (streaming response)",
)
async def post_webchat_chat(
    request_data: Union[AgentRequest, dict],
    request: Request,
) -> StreamingResponse:
    """Stream agent response for webchat user via wx_* tenant workspace."""
    identity = _get_identity_from_request(request)
    logger.info("Webchat chat request accepted")

    try:
        workspace = await get_tenant_workspace_for_identity(request, identity)
    except Exception as e:
        logger.error("Failed to get tenant workspace: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get agent: {str(e)}",
        )

    webchat_channel = build_webchat_channel_facade(workspace)
    logger.info("Webchat channel facade built")

    try:
        native_payload = _extract_session_and_payload(request_data)
        requested_session_id = native_payload.get("meta", {}).get("session_id")
        visible_chats = None
        if is_webchat_wecom_session_sync_enabled():
            visible_chats = await workspace.chat_manager.list_chats(
                user_id=identity.wechat_company_id,
            )
        resolved_session_id, resolved_meta = _resolve_webchat_session_for_request(
            identity,
            requested_session_id,
            visible_chats,
        )
        native_payload["sender_id"] = identity.wechat_company_id
        native_payload["channel_id"] = "webchat"
        native_payload["session_id"] = resolved_session_id
        native_payload["user_id"] = identity.wechat_company_id
        native_payload.setdefault("meta", {}).update(resolved_meta)
        native_payload["meta"]["session_id"] = resolved_session_id
        native_payload["meta"].update(
            _webchat_context_meta(
                request,
                identity,
                session_id=resolved_session_id,
            ),
        )
        native_payload["request_id"] = native_payload["meta"]["request_id"]
        native_payload["trace_id"] = native_payload["meta"]["trace_id"]
        native_payload["tenant_id"] = identity.tenant_id
        native_payload["agent_id"] = identity.agent_id
        native_payload["entrypoint"] = "webchat"
        # P3-2: 将 WebChat token 中的 roles 传入 runner，
        # 避免 runner 重建 context 时丢失角色信息
        native_payload["meta"]["roles"] = list(identity.roles)
    except Exception as e:
        logger.error("Failed to extract payload: %s", type(e).__name__, exc_info=True)
        raise HTTPException(status_code=400, detail=str(e)) from e

    session_id = webchat_channel.resolve_session_id(
        sender_id=identity.wechat_company_id,
        channel_meta=native_payload["meta"],
    )
    logger.info("Webchat session resolved")

    name = "New Chat"
    if len(native_payload["content_parts"]) > 0:
        content = native_payload["content_parts"][0]
        if content:
            if hasattr(content, "text"):
                name = content.text[:10]
            elif isinstance(content, dict) and "text" in content:
                name = content["text"][:10]
            else:
                name = "Media Message"
        else:
            name = "Media Message"

    try:
        chat = await workspace.chat_manager.get_or_create_chat(
            session_id,
            identity.wechat_company_id,
            native_payload["channel_id"],
            name=name,
        )
        logger.info("Chat created/found: %s", chat.id)
    except Exception as e:
        logger.error("Failed to create chat: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create chat: {str(e)}",
        )

    tracker = workspace.task_tracker

    is_reconnect = False
    if isinstance(request_data, dict):
        is_reconnect = request_data.get("reconnect") is True

    try:
        if is_reconnect:
            queue = await tracker.attach(chat.id)
            if queue is None:
                logger.warning("No queue to reconnect for chat %s", chat.id)
                return
        else:
            logger.info("Starting chat task for chat %s", chat.id)
            queue, _ = await tracker.attach_or_start(
                chat.id,
                native_payload,
                webchat_channel.stream_one,
            )
            logger.info("Queue started for chat %s", chat.id)
    except Exception as e:
        logger.error("Failed to start chat task: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start chat: {str(e)}",
        )

    async def event_generator() -> AsyncGenerator[str, None]:
        stream_it = tracker.stream_from_queue(queue, chat.id)
        try:
            try:
                async for event_data in stream_it:
                    yield event_data
            except Exception as e:
                logger.exception("Webchat chat stream error")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            await stream_it.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post(
    "/chat/stop",
    status_code=200,
    summary="Stop running webchat chat",
)
async def post_webchat_chat_stop(
    request: Request,
    chat_id: str = Query(..., description="Chat id to stop"),
) -> dict:
    """Stop the running chat."""
    identity = _get_identity_from_request(request)
    workspace = await get_tenant_workspace_for_identity(request, identity)
    stopped = await workspace.task_tracker.request_stop(chat_id)
    return {"stopped": stopped}


@router.post("/upload", response_model=dict, summary="Upload file for chat")
async def post_webchat_upload(
    request: Request,
    file: UploadFile = File(..., description="File to attach"),
) -> dict:
    """Upload file for webchat via wx_* tenant workspace."""
    identity = _get_identity_from_request(request)
    workspace = await get_tenant_workspace_for_identity(request, identity)
    webchat_channel = build_webchat_channel_facade(workspace)

    media_dir = webchat_channel.media_dir
    media_dir.mkdir(parents=True, exist_ok=True)
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail="File too large (max "
            f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB)",
        )
    safe_name = _safe_filename(file.filename or "file")
    stored_name = f"{uuid.uuid4().hex}_{safe_name}"

    path = (media_dir / stored_name).resolve()
    path.write_bytes(data)
    return {
        "url": str(path),
        "file_name": safe_name,
        "size": len(data),
    }


@router.post("/set-agent")
async def set_user_agent(
    request: Request,
    agent_id: str = Query(..., description="Agent ID to assign"),
) -> dict:
    """Agent switching is disabled in SSO mode."""
    _get_identity_from_request(request)
    raise HTTPException(status_code=403, detail="Agent switching is disabled in SSO mode")


@router.get("/agent/config")
async def get_user_agent_config(request: Request) -> dict:
    """Get current user's agent configuration including tools, MCP, and files."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    logger.info("Getting WebChat agent config")

    try:
        workspace, workspace_dir, agent_config = await _get_tenant_workspace_config(
            request,
            identity,
        )
    except Exception as e:
        logger.error("Failed to get WebChat agent config: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get agent: {str(e)}",
        )

    tools_list = []
    if agent_config and agent_config.tools:
        for tool_name, tool_config in agent_config.tools.builtin_tools.items():
            tools_list.append({
                "name": tool_name,
                "enabled": tool_config.enabled,
                "description": tool_config.description or tool_name,
                "display_to_user": tool_config.display_to_user,
            })

    mcp_clients = []
    if agent_config and agent_config.mcp:
        for client_name, client_config in agent_config.mcp.clients.items():
            mcp_clients.append({
                "name": client_name,
                "display_name": client_config.name,
                "enabled": client_config.enabled,
                "description": client_config.description,
                "transport": client_config.transport,
            })

    files_list = []
    for md_file in ["AGENTS.md", "SOUL.md", "PROFILE.md"]:
        file_path = workspace_dir / md_file
        if file_path.exists():
            try:
                content = file_path.read_text(encoding="utf-8")
                files_list.append({
                    "name": md_file,
                    "type": "prompt",
                    "size": len(content),
                    "lines": content.count("\n") + 1,
                })
            except Exception:
                pass

    memory_dir = workspace_dir / "memory"
    if memory_dir.exists():
        for mem_file in memory_dir.glob("*.md"):
            try:
                content = mem_file.read_text(encoding="utf-8")
                files_list.append({
                    "name": mem_file.name,
                    "type": "memory",
                    "size": len(content),
                    "lines": content.count("\n") + 1,
                })
            except Exception:
                pass

    return {
        "agent_id": agent_id,
        "name": agent_config.name if agent_config else agent_id,
        "description": agent_config.description if agent_config else "",
        "model_id": f"{agent_config.active_model.provider_id}/{agent_config.active_model.model}" if agent_config and agent_config.active_model else "",
        "system_prompt": "",
        "max_turns": agent_config.running.max_iters if agent_config else 100,
        "temperature": 0.7,
        "enable_memory": True,
        "language": agent_config.language if agent_config else "zh",
        "tools": tools_list,
        "mcp_clients": mcp_clients,
        "files": files_list,
        "workspace_dir": str(workspace_dir),
    }


@router.put("/agent/config")
async def update_user_agent_config(
    request: Request,
    config_data: dict,
) -> dict:
    """Update current user's agent configuration."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id

    try:
        _, workspace_dir, agent_config = await _get_tenant_workspace_config(
            request,
            identity,
        )
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Agent config not found: {str(e)}",
        )

    if "model_id" in config_data:
        from qwenpaw.config.config import ModelSlotConfig

        provider_id, separator, model = str(config_data["model_id"]).partition("/")
        if separator and provider_id and model:
            agent_config.active_model = ModelSlotConfig(
                provider_id=provider_id,
                model=model,
            )
    if "max_turns" in config_data:
        agent_config.running.max_iters = int(config_data["max_turns"])
    if "language" in config_data:
        agent_config.language = str(config_data["language"])

    _save_tenant_agent_config(workspace_dir, agent_config)

    return {"success": True, "agent_id": agent_id}


class ChatSessionResponse(BaseModel):
    sessions: list


class ChatSessionCreateResponse(BaseModel):
    session_id: str


@router.get("/sessions", response_model=ChatSessionResponse)
async def list_chat_sessions(
    request: Request,
    agent_id: str = Query(None, description="Filter by agent ID"),
) -> ChatSessionResponse:
    """List chat sessions for user, optionally filtered by agent."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    effective_agent_id = ensure_requested_agent_allowed(identity, agent_id)

    workspace = await get_tenant_workspace_for_identity(request, identity)
    chats = await workspace.chat_manager.list_chats(user_id=user_id)
    sessions = list_webchat_visible_sessions(identity, chats)
    return ChatSessionResponse(sessions=sessions)


@router.post("/sessions", response_model=ChatSessionCreateResponse)
async def create_chat_session(
    request: Request,
) -> ChatSessionCreateResponse:
    """Create a new chat session."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id

    workspace = await get_tenant_workspace_for_identity(request, identity)
    requested_session_id = str(uuid.uuid4())
    session_id, _ = _resolve_webchat_session_for_request(
        identity,
        requested_session_id,
    )

    await workspace.chat_manager.get_or_create_chat(
        session_id,
        user_id,
        "webchat",
        name="New Chat",
    )

    return ChatSessionCreateResponse(session_id=session_id)


@router.get("/sessions/{session_id}")
async def get_chat_session(
    session_id: str,
    request: Request,
) -> dict:
    """Get a chat session with messages."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id

    # 处理 undefined/null 的情况，返回空会话
    if not session_id or session_id in ("undefined", "null"):
        return {
            "id": "",
            "session_id": "",
            "user_id": "",
            "channel": "webchat",
            "name": "New Chat",
            "messages": [],
        }
    
    from agentscope.memory import InMemoryMemory
    from ..runner.utils import agentscope_msg_to_message

    try:
        ensure_webchat_session_access(identity, session_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    workspace = await get_tenant_workspace_for_identity(request, identity)
    chats = await workspace.chat_manager.list_chats(user_id=user_id)
    chat = resolve_visible_chat(identity, chats, session_id)

    if not chat:
        raise HTTPException(status_code=404, detail="Session not found")

    # 从 session 状态中获取消息
    messages = []
    try:
        # 使用 workspace.runner.session 而不是 workspace.session
        if not workspace.runner:
            raise HTTPException(status_code=500, detail="Runner not initialized")
        
        session_state = await workspace.runner.session.get_session_state_dict(
            chat.session_id,
            chat.user_id,
            channel=chat.channel,
        )
        
        if session_state:
            memory_state = session_state.get("agent", {}).get("memory", {})
            memory = InMemoryMemory()
            memory.load_state_dict(memory_state, strict=False)
            
            memories = await memory.get_memory(prepend_summary=False)
            converted_messages = agentscope_msg_to_message(memories)
            
            for msg in converted_messages:
                # 将 Message 对象转换为可序列化的字典
                # Message.content 可能是字符串，也可能是 TextContent 等对象列表
                raw_content = msg.content
                serializable_content = raw_content
                
                # 如果 content 是列表（包含 Content 对象），需要序列化
                if isinstance(raw_content, list):
                    serializable_content = []
                    for item in raw_content:
                        if hasattr(item, 'model_dump'):
                            # Pydantic 模型
                            serializable_content.append(item.model_dump())
                        elif hasattr(item, '__dict__'):
                            # 普通对象
                            serializable_content.append({
                                k: v for k, v in item.__dict__.items() 
                                if not k.startswith('_')
                            })
                        else:
                            serializable_content.append(item)
                elif hasattr(raw_content, 'model_dump'):
                    serializable_content = raw_content.model_dump()
                elif hasattr(raw_content, '__dict__'):
                    serializable_content = {
                        k: v for k, v in raw_content.__dict__.items() 
                        if not k.startswith('_')
                    }
                
                msg_dict = {
                    "id": getattr(msg, 'id', None) or str(uuid.uuid4()),
                    "role": msg.role,
                    "content": serializable_content,
                    "type": getattr(msg, 'type', None),
                    "sequence_number": getattr(msg, 'sequence_number', None),
                }
                messages.append(msg_dict)
    except Exception as e:
        logger.warning("Failed to load messages for session %s: %s", session_id, e)

    return {
        "id": chat.id,
        "session_id": chat.session_id,
        "user_id": chat.user_id,
        "channel": chat.channel,
        "name": chat.name or "New Chat",
        "messages": messages,
    }


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    request: Request,
) -> dict:
    """Delete a chat session."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id

    workspace = await get_tenant_workspace_for_identity(request, identity)
    chats = await workspace.chat_manager.list_chats(user_id=user_id)
    chat = resolve_visible_chat(identity, chats, session_id)

    if not chat:
        raise HTTPException(status_code=404, detail="Session not found")

    await workspace.chat_manager.delete_chats([chat.id])

    return {"success": True}


class ChatUpdateRequest(BaseModel):
    """Request body for updating a chat session."""
    name: str | None = Field(default=None, description="Chat name")
    pinned: bool | None = Field(default=None, description="Whether the chat is pinned")


@router.put("/sessions/{session_id}")
async def update_chat_session(
    session_id: str,
    request: Request,
    update_data: ChatUpdateRequest,
) -> dict:
    """Update a chat session (name, pinned status, etc.)."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id

    # 处理 undefined/null 的情况，返回空会话
    if not session_id or session_id in ("undefined", "null"):
        return {
            "id": "",
            "session_id": "",
            "user_id": "",
            "channel": "webchat",
            "name": "New Chat",
        }

    workspace = await get_tenant_workspace_for_identity(request, identity)
    chats = await workspace.chat_manager.list_chats(user_id=user_id)
    chat = resolve_visible_chat(identity, chats, session_id)
    
    if not chat:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 构建更新数据
    from ..runner.models import ChatUpdate
    patch_data = {}
    if update_data.name is not None:
        patch_data["name"] = update_data.name
    if update_data.pinned is not None:
        patch_data["pinned"] = update_data.pinned
    
    # 如果有需要更新的字段，调用 patch_chat
    if patch_data:
        chat_update = ChatUpdate(**patch_data)
        updated_chat = await workspace.chat_manager.patch_chat(chat.id, chat_update)
        if updated_chat:
            chat = updated_chat
    
    return {
        "id": chat.id,
        "session_id": chat.session_id,
        "user_id": chat.user_id,
        "channel": chat.channel,
        "name": chat.name or "New Chat",
    }


@router.get("/agent/config")
async def get_agent_config(request: Request) -> dict:
    """Get agent configuration for the current user."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id

    workspace = await get_tenant_workspace_for_identity(request, identity)
    agent_spec = workspace.agent_spec

    tools = []
    if hasattr(agent_spec, "tools") and agent_spec.tools:
        for tool in agent_spec.tools:
            tools.append({
                "name": tool.name if hasattr(tool, "name") else str(tool),
                "enabled": getattr(tool, "enabled", True),
                "description": getattr(tool, "description", ""),
                "display_to_user": getattr(tool, "display_to_user", True),
            })

    mcp_clients = []
    if hasattr(agent_spec, "mcp_clients") and agent_spec.mcp_clients:
        for client in agent_spec.mcp_clients:
            mcp_clients.append({
                "name": client.name if hasattr(client, "name") else str(client),
                "display_name": getattr(client, "display_name", ""),
                "enabled": getattr(client, "enabled", True),
                "description": getattr(client, "description", ""),
                "transport": getattr(client, "transport", "stdio"),
            })

    skills = []
    if hasattr(agent_spec, "skills") and agent_spec.skills:
        for skill in agent_spec.skills:
            skills.append({
                "name": skill.name if hasattr(skill, "name") else str(skill),
                "enabled": getattr(skill, "enabled", True),
                "description": getattr(skill, "description", ""),
                "source": getattr(skill, "source", ""),
            })

    files = []
    workspace_dir = workspace.workspace_dir if hasattr(workspace, "workspace_dir") else ""
    if workspace_dir:
        workspace_path = Path(workspace_dir)
        if workspace_path.exists():
            for f in workspace_path.rglob("*"):
                if f.is_file() and not f.name.startswith("."):
                    try:
                        lines = len(f.read_text(encoding="utf-8").splitlines())
                    except Exception:
                        lines = 0
                    files.append({
                        "name": f.name,
                        "path": str(f.relative_to(workspace_path)),
                        "type": f.suffix.lstrip(".") or "txt",
                        "size": f.stat().st_size,
                        "lines": lines,
                        "enabled": True,
                    })

    return {
        "agent_id": agent_id,
        "name": agent_spec.name if hasattr(agent_spec, "name") else agent_id,
        "description": getattr(agent_spec, "description", ""),
        "model_id": getattr(agent_spec, "model_id", ""),
        "system_prompt": getattr(agent_spec, "system_prompt", ""),
        "max_turns": getattr(agent_spec, "max_turns", 10),
        "temperature": getattr(agent_spec, "temperature", 0.7),
        "enable_memory": getattr(agent_spec, "enable_memory", True),
        "language": getattr(agent_spec, "language", "zh"),
        "tools": tools,
        "mcp_clients": mcp_clients,
        "skills": skills,
        "files": files,
        "workspace_dir": str(workspace_dir),
    }


@router.put("/agent/tools/{tool_name}")
async def toggle_agent_tool(
    tool_name: str,
    request: Request,
    body: dict,
) -> dict:
    """Toggle tool enabled status."""
    enabled = body.get("enabled", True)
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id

    workspace = await get_tenant_workspace_for_identity(request, identity)
    agent_spec = workspace.agent_spec

    if hasattr(agent_spec, "tools") and agent_spec.tools:
        for tool in agent_spec.tools:
            if hasattr(tool, "name") and tool.name == tool_name:
                tool.enabled = enabled
                break

    return {"success": True}


@router.put("/agent/mcp/{client_name}")
async def toggle_agent_mcp(
    client_name: str,
    request: Request,
    body: dict,
) -> dict:
    """Toggle MCP client enabled status."""
    enabled = body.get("enabled", True)
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id

    workspace = await get_tenant_workspace_for_identity(request, identity)
    agent_spec = workspace.agent_spec

    if hasattr(agent_spec, "mcp_clients") and agent_spec.mcp_clients:
        for client in agent_spec.mcp_clients:
            if hasattr(client, "name") and client.name == client_name:
                client.enabled = enabled
                break

    return {"success": True}



def _set_webchat_agent_context(request: Request, agent_id: str) -> None:
    """Set agent context for webchat request to reuse skills.py APIs."""
    request.state.agent_id = agent_id


async def _set_webchat_workspace_context(
    request: Request, identity: WebchatIdentity
) -> str:
    """为 WebChat 请求 provision 租户并设置 agent-scoped 上下文。"""
    await get_tenant_workspace_for_identity(request, identity)
    request.state.agent_id = identity.agent_id
    return identity.agent_id


@router.get("/agent/skills")
async def list_agent_skills(request: Request) -> dict:
    """List all skills for user's agent."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    await _set_webchat_workspace_context(request, identity)
    
    from .skills import list_skills
    skills = await list_skills(request)
    return {"skills": [s.model_dump() if hasattr(s, 'model_dump') else s for s in skills]}


@router.post("/agent/skills/refresh")
async def refresh_agent_skills(request: Request) -> dict:
    """Refresh and list all skills for user's agent."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    await _set_webchat_workspace_context(request, identity)
    
    from .skills import refresh_skills
    skills = await refresh_skills(request)
    return {"skills": [s.model_dump() if hasattr(s, 'model_dump') else s for s in skills]}


@router.post("/agent/skills")
async def create_agent_skill(request: Request, body: dict) -> dict:
    """Create a new skill."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    await _set_webchat_workspace_context(request, identity)
    
    from .skills import CreateSkillRequest, create_skill
    skill_request = CreateSkillRequest(
        name=body.get("name"),
        content=body.get("content", ""),
        references=body.get("references"),
        scripts=body.get("scripts"),
        config=body.get("config"),
        enable=body.get("enable", True),
    )
    return await create_skill(request, skill_request)


@router.post("/agent/skills/install-uploaded")
async def install_uploaded_agent_skill(
    request: Request,
    body: dict | None = Body(default=None),
) -> dict:
    """Install a skill uploaded through bot media into the workspace skills."""
    identity = _get_identity_from_request(request)

    await _set_webchat_workspace_context(request, identity)

    from .skills import InstallUploadedSkillRequest, install_uploaded_workspace_skill

    payload = body or {}
    skill_name = str(
        payload.get("skill_name") or payload.get("skill_id") or "",
    ).strip()
    if not skill_name:
        raise HTTPException(status_code=400, detail="skill_name is required")

    install_request = InstallUploadedSkillRequest(
        skill_name=skill_name,
        overwrite=bool(payload.get("overwrite", False)),
    )
    return await install_uploaded_workspace_skill(request, install_request)


@router.put("/agent/skills/{skill_name}")
async def toggle_agent_skill(
    skill_name: str,
    request: Request,
    body: dict,
) -> dict:
    """Toggle skill enabled status or update skill content."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    await _set_webchat_workspace_context(request, identity)
    
    if "content" in body:
        from .skills import SaveSkillRequest, save_workspace_skill
        save_request = SaveSkillRequest(
            name=skill_name,
            content=body["content"],
            source_name=body.get("source_name"),
            config=body.get("config"),
            overwrite=body.get("overwrite", False),
        )
        return await save_workspace_skill(request, save_request)
    
    enabled = body.get("enabled", True)
    if enabled:
        from .skills import enable_skill
        return await enable_skill(request, skill_name)
    else:
        from .skills import disable_skill
        return await disable_skill(request, skill_name)


@router.delete("/agent/skills/{skill_name}")
async def delete_agent_skill(skill_name: str, request: Request) -> dict:
    """Delete a skill."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    await _set_webchat_workspace_context(request, identity)
    
    from .skills import delete_skill
    return await delete_skill(request, skill_name)


@router.post("/agent/skills/batch-delete")
async def batch_delete_agent_skills(request: Request, body: dict) -> dict:
    """Batch delete skills."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    await _set_webchat_workspace_context(request, identity)
    
    from .skills import batch_delete_skills
    return await batch_delete_skills(request, body.get("skills", []))


@router.get("/agent/skills/{skill_name}/config")
async def get_agent_skill_config(skill_name: str, request: Request) -> dict:
    """Get skill configuration."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    await _set_webchat_workspace_context(request, identity)
    
    from .skills import get_skill_config_endpoint
    return await get_skill_config_endpoint(request, skill_name)


@router.put("/agent/skills/{skill_name}/config")
async def update_agent_skill_config(
    skill_name: str,
    request: Request,
    body: dict,
) -> dict:
    """Update skill configuration."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    await _set_webchat_workspace_context(request, identity)
    
    from .skills import update_skill_config_endpoint, SkillConfigRequest
    config_request = SkillConfigRequest(config=body.get("config", {}))
    return await update_skill_config_endpoint(request, skill_name, config_request)


@router.put("/agent/skills/{skill_name}/channels")
async def update_agent_skill_channels(
    skill_name: str,
    request: Request,
    body: dict,
) -> dict:
    """Update skill channels."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    await _set_webchat_workspace_context(request, identity)
    
    from .skills import update_skill_channels_endpoint
    return await update_skill_channels_endpoint(request, skill_name, body.get("channels", ["all"]))


@router.put("/agent/skills/{skill_name}/tags")
async def update_agent_skill_tags(
    skill_name: str,
    request: Request,
    body: dict,
) -> dict:
    """Update skill tags."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    await _set_webchat_workspace_context(request, identity)
    
    from .skills import update_skill_tags
    return await update_skill_tags(request, skill_name, body.get("tags", []))


@router.get("/agent/skills/{skill_name}/files/{file_path:path}")
async def get_agent_skill_file(
    skill_name: str,
    file_path: str,
    request: Request,
) -> dict:
    """Get skill file content."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    await _set_webchat_workspace_context(request, identity)
    
    from .skills import load_skill_file
    return await load_skill_file(request, skill_name, file_path)


@router.put("/agent/skills/save")
async def save_agent_skill(request: Request, body: dict) -> dict:
    """Save skill content."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    await _set_webchat_workspace_context(request, identity)
    
    from .skills import SaveSkillRequest, save_workspace_skill
    save_request = SaveSkillRequest(
        name=body.get("name"),
        content=body.get("content", ""),
        source_name=body.get("source_name"),
        config=body.get("config"),
        overwrite=body.get("overwrite", False),
    )
    return await save_workspace_skill(request, save_request)





@router.get("/agent/files/{filename:path}")
async def get_agent_file_content(filename: str, request: Request) -> dict:
    """Get content of a specific file."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id

    workspace = await get_tenant_workspace_for_identity(request, identity)
    workspace_dir = workspace.workspace_dir if hasattr(workspace, "workspace_dir") else ""

    if not workspace_dir:
        raise HTTPException(status_code=404, detail="Workspace not found")

    file_path = Path(workspace_dir) / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")

    return {"content": content}


@router.put("/agent/files/{filename:path}/enabled")
async def toggle_agent_file_enabled(
    filename: str,
    request: Request,
    body: dict,
) -> dict:
    """Toggle file enabled status (placeholder for future implementation)."""
    _get_identity_from_request(request)
    enabled = body.get("enabled", True)
    return {"success": True, "filename": filename, "enabled": enabled}


@router.get("/providers")
async def list_providers(request: Request) -> list:
    """List all configured providers with their models."""
    from ...providers.provider_manager import ProviderManager

    _get_identity_from_request(request)
    
    manager = ProviderManager.get_instance()
    providers = await manager.list_provider_info()
    
    result = []
    for p in providers:
        models = []
        if p.models:
            models.extend([{"id": m.id, "name": m.name or m.id} for m in p.models])
        if p.extra_models:
            models.extend([{"id": m.id, "name": m.name or m.id} for m in p.extra_models])
        
        # Return full provider info for frontend filtering
        result.append({
            "id": p.id,
            "name": p.name,
            "models": models,
            "extra_models": [],
            "base_url": p.base_url or "",
            "api_key": p.api_key or "",
            "require_api_key": p.require_api_key,
            "is_custom": p.is_custom,
        })
    
    return result


@router.get("/active-models")
async def get_active_models(request: Request) -> dict:
    """Get the active model for the current user's agent."""
    from ...providers.provider_manager import ProviderManager
    
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    manager = ProviderManager.get_instance()
    
    try:
        _, _, agent_config = await _get_tenant_workspace_config(request, identity)
        if agent_config and agent_config.active_model:
            return {
                "active_llm": {
                    "provider_id": agent_config.active_model.provider_id,
                    "model": agent_config.active_model.model,
                }
            }
    except Exception as e:
        logger.warning("Failed to load agent config for %s: %s", agent_id, e)
    
    global_model = manager.get_active_model()
    if global_model:
        return {
            "active_llm": {
                "provider_id": global_model.provider_id,
                "model": global_model.model,
            }
        }
    
    return {"active_llm": None}


@router.put("/active-models")
async def set_active_model(request: Request, body: dict) -> dict:
    """Set the active model for the current user's agent."""
    from ...providers.provider_manager import ProviderManager
    from ...config.config import ModelSlotConfig
    
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    provider_id = body.get("provider_id")
    model = body.get("model")
    
    if not provider_id or not model:
        raise HTTPException(status_code=400, detail="provider_id and model are required")
    
    manager = ProviderManager.get_instance()
    provider = manager.get_provider(provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found")
    if not provider.has_model(model):
        raise HTTPException(status_code=400, detail=f"Model '{model}' not found in provider '{provider_id}'")
    
    try:
        _, workspace_dir, agent_config = await _get_tenant_workspace_config(
            request,
            identity,
        )
        agent_config.active_model = ModelSlotConfig(
            provider_id=provider_id,
            model=model,
        )
        _save_tenant_agent_config(workspace_dir, agent_config)
    except Exception as e:
        logger.error("Failed to save agent config for %s: %s", agent_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to save model configuration: {e}")
    
    return {
        "active_llm": {
            "provider_id": provider_id,
            "model": model,
        }
    }


# ── Workspace file endpoints ───────────────────────────────────────────────

from pydantic import BaseModel as PydanticBaseModel

class MdFileInfo(PydanticBaseModel):
    """Markdown file metadata."""
    filename: str
    path: str
    size: int
    created_time: str
    modified_time: str


class MdFileContent(PydanticBaseModel):
    """Markdown file content."""
    content: str


@router.get("/agent/files")
async def list_agent_files(request: Request) -> list[MdFileInfo]:
    """List all markdown files in user's agent workspace."""
    from ...agents.memory.agent_md_manager import AgentMdManager

    identity = _get_identity_from_request(request)
    workspace = await get_tenant_workspace_for_identity(request, identity)
    workspace_dir = Path(workspace.workspace_dir)
    if not workspace_dir.exists():
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_dir}' not found")

    workspace_manager = AgentMdManager(str(workspace_dir))
    
    try:
        files = workspace_manager.list_working_mds()
        return [
            MdFileInfo(
                filename=f["filename"],
                path=f["path"],
                size=f["size"],
                created_time=f["created_time"],
                modified_time=f["modified_time"],
            )
            for f in files
        ]
    except Exception as e:
        logger.error("Failed to list files: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/files/{filename}")
async def read_agent_file(request: Request, filename: str) -> MdFileContent:
    """Read a markdown file from user's agent workspace."""
    # 处理 undefined/null 的情况
    if not filename or filename in ("undefined", "null"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    from ...agents.memory.agent_md_manager import AgentMdManager

    identity = _get_identity_from_request(request)
    workspace = await get_tenant_workspace_for_identity(request, identity)
    workspace_dir = Path(workspace.workspace_dir)
    workspace_manager = AgentMdManager(str(workspace_dir))

    try:
        content = workspace_manager.read_working_md(filename)
        return MdFileContent(content=content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
    except Exception as e:
        logger.error("Failed to read file %s: %s", filename, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agent/files/{filename}")
async def save_agent_file(request: Request, filename: str, body: dict) -> dict:
    """Save a markdown file to user's agent workspace."""
    from ...agents.memory.agent_md_manager import AgentMdManager

    identity = _get_identity_from_request(request)
    workspace = await get_tenant_workspace_for_identity(request, identity)
    workspace_dir = Path(workspace.workspace_dir)
    workspace_manager = AgentMdManager(str(workspace_dir))
    
    content = body.get("content", "")
    
    try:
        workspace_manager.write_working_md(filename, content)
        return {"success": True, "message": f"File '{filename}' saved successfully"}
    except Exception as e:
        logger.error("Failed to save file %s: %s", filename, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/system-prompt-files")
async def get_system_prompt_files(request: Request) -> list[str]:
    """Get system prompt files for user's agent."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    try:
        _, _, agent_config = await _get_tenant_workspace_config(request, identity)
        return agent_config.system_prompt_files or ["AGENTS.md", "SOUL.md", "PROFILE.md"]
    except Exception as e:
        logger.warning("Failed to load agent config for %s: %s", agent_id, e)
        return ["AGENTS.md", "SOUL.md", "PROFILE.md"]


@router.put("/agent/system-prompt-files")
async def set_system_prompt_files(request: Request, files: list[str]) -> dict:
    """Update system prompt files for user's agent."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    try:
        _, workspace_dir, agent_config = await _get_tenant_workspace_config(
            request,
            identity,
        )
        agent_config.system_prompt_files = files
        _save_tenant_agent_config(workspace_dir, agent_config)
        return {"success": True, "files": files}
    except Exception as e:
        logger.error("Failed to save system prompt files for %s: %s", agent_id, e)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Tool Management APIs
# ============================================================================

class ToolInfo(PydanticBaseModel):
    """Tool information for API responses."""
    name: str
    enabled: bool
    description: str
    async_execution: bool
    icon: str


@router.get("/agent/tools")
async def list_agent_tools(request: Request) -> list[ToolInfo]:
    """List all built-in tools and enabled status for user's agent."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    try:
        _, _, agent_config = await _get_tenant_workspace_config(request, identity)
        
        # Ensure tools config exists with defaults
        if not agent_config.tools or not agent_config.tools.builtin_tools:
            from ...config.utils import load_config
            config = load_config()
            tools_config = config.tools if hasattr(config, "tools") else None
            if not tools_config:
                return []
            builtin_tools = tools_config.builtin_tools
        else:
            builtin_tools = agent_config.tools.builtin_tools
        
        tools_list = []
        for tool_config in builtin_tools.values():
            tools_list.append(ToolInfo(
                name=tool_config.name,
                enabled=tool_config.enabled,
                description=tool_config.description,
                async_execution=tool_config.async_execution,
                icon=tool_config.icon,
            ))
        
        return tools_list
    except Exception as e:
        logger.error("Failed to list tools: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/agent/tools/{tool_name}/toggle")
async def toggle_agent_tool(tool_name: str, request: Request) -> ToolInfo:
    """Toggle tool enabled status for user's agent."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    try:
        _, workspace_dir, agent_config = await _get_tenant_workspace_config(
            request,
            identity,
        )
        
        if not agent_config.tools or tool_name not in agent_config.tools.builtin_tools:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found",
            )
        
        # Toggle enabled status
        tool_config = agent_config.tools.builtin_tools[tool_name]
        tool_config.enabled = not tool_config.enabled
        
        # Save agent config
        _save_tenant_agent_config(workspace_dir, agent_config)
        
        return ToolInfo(
            name=tool_config.name,
            enabled=tool_config.enabled,
            description=tool_config.description,
            async_execution=tool_config.async_execution,
            icon=tool_config.icon,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to toggle tool %s: %s", tool_name, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/agent/tools/{tool_name}/async-execution")
async def update_agent_tool_async_execution(
    tool_name: str,
    request: Request,
    body: dict,
) -> ToolInfo:
    """Update tool async_execution setting for user's agent."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    try:
        _, workspace_dir, agent_config = await _get_tenant_workspace_config(
            request,
            identity,
        )
        
        if not agent_config.tools or tool_name not in agent_config.tools.builtin_tools:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found",
            )
        
        # Update async_execution setting
        async_execution = body.get("async_execution", False)
        tool_config = agent_config.tools.builtin_tools[tool_name]
        tool_config.async_execution = async_execution
        
        # Save agent config
        _save_tenant_agent_config(workspace_dir, agent_config)
        
        return ToolInfo(
            name=tool_config.name,
            enabled=tool_config.enabled,
            description=tool_config.description,
            async_execution=tool_config.async_execution,
            icon=tool_config.icon,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update async_execution for tool %s: %s", tool_name, e)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Skill Pool & Hub Management APIs
# ============================================================================

@router.get("/agent/skill-pool/skills")
async def list_skill_pool_skills(request: Request) -> dict:
    """List all skills in the skill pool."""
    _get_identity_from_request(request)
    from .skills import list_pool_skills
    skills = await list_pool_skills()
    return {"skills": [s.model_dump() if hasattr(s, 'model_dump') else s for s in skills]}


@router.post("/agent/skill-pool/refresh")
async def refresh_skill_pool(request: Request) -> dict:
    """Refresh skill pool."""
    _get_identity_from_request(request)
    from .skills import refresh_pool_skills
    skills = await refresh_pool_skills()
    return {"skills": [s.model_dump() if hasattr(s, 'model_dump') else s for s in skills]}


@router.get("/agent/skill-pool/builtin-sources")
async def list_skill_pool_builtin_sources(request: Request) -> dict:
    """List builtin skill sources."""
    _get_identity_from_request(request)
    from .skills import list_pool_builtin_sources
    sources = await list_pool_builtin_sources()
    return {"sources": [s.model_dump() if hasattr(s, 'model_dump') else s for s in sources]}


@router.get("/agent/skill-pool/builtin-notice")
async def get_skill_pool_builtin_notice(request: Request) -> dict:
    """Get builtin skill update notice."""
    _get_identity_from_request(request)
    from .skills import get_pool_builtin_notice
    return await get_pool_builtin_notice()


@router.post("/agent/skill-pool/upload")
async def upload_skill_to_pool(
    request: Request,
    body: dict,
) -> dict:
    """Upload a workspace skill to the skill pool."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    await _set_webchat_workspace_context(request, identity)
    
    from .skills import UploadToPoolRequest, upload_workspace_skill_to_pool
    upload_request = UploadToPoolRequest(
        workspace_id=agent_id,
        skill_name=body.get("skill_name", ""),
        overwrite=body.get("overwrite", False),
        preview_only=body.get("preview_only", False),
    )
    return await upload_workspace_skill_to_pool(upload_request)


@router.post("/agent/skill-pool/download")
async def download_skill_from_pool(
    request: Request,
    body: dict,
) -> dict:
    """Download a skill from the skill pool to workspace."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    await _set_webchat_workspace_context(request, identity)
    
    from .skills import DownloadFromPoolRequest, PoolDownloadTarget, download_pool_skill_to_workspaces
    download_request = DownloadFromPoolRequest(
        skill_name=body.get("skill_name", ""),
        targets=[PoolDownloadTarget(workspace_id=agent_id)],
        overwrite=body.get("overwrite", False),
        preview_only=body.get("preview_only", False),
    )
    return await download_pool_skill_to_workspaces(download_request)


@router.post("/agent/skills/upload-zip")
async def upload_skill_zip(
    request: Request,
    file: UploadFile = File(...),
    enable: bool = True,
    overwrite: bool = False,
    target_name: str = "",
    rename_map: str = "",
) -> dict:
    """Upload skills from a zip file."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    await _set_webchat_workspace_context(request, identity)
    
    from .skills import upload_skill_zip as _upload_skill_zip
    return await _upload_skill_zip(
        request,
        file=file,
        enable=enable,
        target_name=target_name,
        rename_map=rename_map,
    )


@router.post("/agent/skills/import-hub")
async def import_skill_from_hub(
    request: Request,
    body: dict,
) -> dict:
    """Import a skill from Skills Hub."""
    identity = _get_identity_from_request(request)
    user_id = identity.wechat_company_id
    agent_id = identity.agent_id
    
    await _set_webchat_workspace_context(request, identity)
    
    from .skills import HubInstallRequest, start_install_from_hub
    install_request = HubInstallRequest(
        bundle_url=body.get("bundle_url", ""),
        version=body.get("version", ""),
        enable=body.get("enable", True),
        target_name=body.get("target_name", ""),
    )
    return await start_install_from_hub(install_request, request)


# ── Workspace file browser endpoints ────────────────────────────────────────


@router.get("/agent/workspace/files")
async def list_workspace_files(
    request: Request,
    path: str = Query("", description="相对工作区根目录的子路径"),
):
    """列出工作区目录内容。"""
    identity = _get_identity_from_request(request)
    workspace = await get_tenant_workspace_for_identity(request, identity)
    workspace_dir = Path(workspace.workspace_dir).resolve()
    target_dir = _safe_resolve(workspace_dir, path) if path else workspace_dir

    if not target_dir.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")

    entries = []
    for entry in sorted(target_dir.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
        if entry.name.startswith("."):
            continue
        try:
            deletable = entry.is_file() and _is_file_deletable(workspace_dir, entry)
        except (ValueError, OSError):
            deletable = False
        entries.append({
            "name": entry.name,
            "type": "dir" if entry.is_dir() else "file",
            "size": entry.stat().st_size if entry.is_file() else 0,
            "deletable": deletable,
        })

    return {
        "path": str(target_dir.relative_to(workspace_dir)).replace("\\", "/").rstrip(".").lstrip("/"),
        "entries": entries,
    }


@router.delete("/agent/workspace/files")
async def delete_workspace_file(
    request: Request,
    path: str = Query(..., description="相对工作区根目录的文件路径"),
):
    """删除工作区文件（仅允许可删除文件）。"""
    if not path or not path.strip():
        raise HTTPException(status_code=400, detail="Path is required")

    identity = _get_identity_from_request(request)
    workspace = await get_tenant_workspace_for_identity(request, identity)
    workspace_dir = Path(workspace.workspace_dir).resolve()
    target = _safe_resolve(workspace_dir, path.strip())

    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if target.is_dir():
        raise HTTPException(status_code=400, detail="Cannot delete a directory")
    if not _is_file_deletable(workspace_dir, target):
        raise HTTPException(status_code=400, detail="不能删除系统文件")

    target.unlink()
    return {"success": True}


@router.post("/agent/workspace/files/upload")
async def upload_workspace_file(
    request: Request,
    file: UploadFile = File(..., description="文件"),
    path: str = Query("", description="目标子路径"),
):
    """上传文件到工作区指定路径。"""
    identity = _get_identity_from_request(request)
    workspace = await get_tenant_workspace_for_identity(request, identity)
    workspace_dir = Path(workspace.workspace_dir).resolve()
    target_dir = _safe_resolve(workspace_dir, path) if path else workspace_dir

    if not target_dir.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")
    # 不能上传到受保护目录
    rel_dir = target_dir.relative_to(workspace_dir)
    if any(p in _PROTECTED_DIRS for p in rel_dir.parts):
        raise HTTPException(status_code=400, detail="不能上传到系统目录")

    safe_name = _safe_filename(file.filename or "file")
    # 不能覆盖受保护文件
    if safe_name in _PROTECTED_FILES:
        raise HTTPException(status_code=400, detail="不能上传系统文件")
    dest = target_dir / safe_name
    # 预检查文件大小
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)",
        )
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)",
        )
    dest.write_bytes(data)
    return {
        "name": safe_name,
        "path": str(dest.relative_to(workspace_dir)).replace("\\", "/"),
        "size": len(data),
    }


@router.get("/agent/workspace/files/download")
async def download_workspace_file(
    request: Request,
    path: str = Query(..., description="相对工作区根目录的文件路径"),
):
    """下载工作区文件（支持二进制文件）。"""
    if not path or not path.strip():
        raise HTTPException(status_code=400, detail="Path is required")

    identity = _get_identity_from_request(request)
    workspace = await get_tenant_workspace_for_identity(request, identity)
    workspace_dir = Path(workspace.workspace_dir).resolve()
    target = _safe_resolve(workspace_dir, path.strip())

    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(target),
        filename=target.name,
        media_type="application/octet-stream",
    )


@router.get("/agent/workspace/download")
async def download_tenant_workspace(request: Request):
    """Download the current WebChat tenant workspace as a zip archive."""
    identity = _get_identity_from_request(request)
    workspace = await get_tenant_workspace_for_identity(request, identity)
    workspace_dir = Path(workspace.workspace_dir)
    if not workspace_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"Workspace does not exist: {workspace_dir}",
        )

    buf = await asyncio.to_thread(_zip_directory, workspace_dir)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"qwenpaw_workspace_{workspace.agent_id}_{timestamp}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post("/agent/workspace/upload")
async def upload_tenant_workspace(
    request: Request,
    file: UploadFile = File(..., description="Zip archive to merge"),
) -> dict:
    """Merge a zip archive into the current WebChat tenant workspace."""
    if file.content_type and file.content_type not in (
        "application/zip",
        "application/x-zip-compressed",
        "application/octet-stream",
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Expected a zip file, got content-type: {file.content_type}",
        )

    identity = _get_identity_from_request(request)
    workspace = await get_tenant_workspace_for_identity(request, identity)
    workspace_dir = Path(workspace.workspace_dir)
    data = await file.read()
    try:
        await asyncio.to_thread(_validate_and_extract_zip, data, workspace_dir)
        return {"success": True}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to merge workspace: {exc}",
        ) from exc


# ── Agent config (running-config / language) ────────────────────────────────


@router.get("/agent/running-config")
async def webchat_get_running_config(request: Request):
    """获取当前租户 agent 的运行配置。"""
    identity = _get_identity_from_request(request)
    workspace = await get_tenant_workspace_for_identity(request, identity)
    ws_dir = Path(workspace.workspace_dir)
    agent_config = load_agent_config_from_workspace(ws_dir)
    if agent_config is None:
        return AgentsRunningConfig()
    return agent_config.running or AgentsRunningConfig()


@router.put("/agent/running-config")
async def webchat_put_running_config(
    request: Request,
    running_config: AgentsRunningConfig = Body(...),
):
    """更新当前租户 agent 的运行配置。"""
    identity = _get_identity_from_request(request)
    workspace = await get_tenant_workspace_for_identity(request, identity)
    ws_dir = Path(workspace.workspace_dir)
    agent_config = load_agent_config_from_workspace(ws_dir)
    if agent_config is None:
        agent_config = AgentProfileConfig(
            id=workspace.agent_id, name=workspace.agent_id,
        )
    agent_config.running = running_config
    write_agent_config_to_workspace(ws_dir, agent_config)
    schedule_agent_reload(request, workspace.agent_id)
    return running_config


@router.get("/agent/language")
async def webchat_get_language(request: Request):
    """获取当前租户 agent 的语言设置。"""
    identity = _get_identity_from_request(request)
    workspace = await get_tenant_workspace_for_identity(request, identity)
    ws_dir = Path(workspace.workspace_dir)
    agent_config = load_agent_config_from_workspace(ws_dir)
    lang = agent_config.language if agent_config else "zh"
    return {"language": lang, "agent_id": workspace.agent_id}


@router.put("/agent/language")
async def webchat_put_language(
    request: Request,
    body: dict = Body(...),
):
    """更新当前租户 agent 的语言设置。"""
    language = (body.get("language") or "").strip().lower()
    if language not in SUPPORTED_AGENT_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid language '{language}'. Must be one of: {', '.join(sorted(SUPPORTED_AGENT_LANGUAGES))}",
        )
    identity = _get_identity_from_request(request)
    workspace = await get_tenant_workspace_for_identity(request, identity)
    ws_dir = Path(workspace.workspace_dir)
    agent_config = load_agent_config_from_workspace(ws_dir)
    if agent_config is None:
        agent_config = AgentProfileConfig(
            id=workspace.agent_id, name=workspace.agent_id,
        )
    old_language = agent_config.language
    agent_config.language = language
    write_agent_config_to_workspace(ws_dir, agent_config)

    copied_files: list[str] = []
    if old_language != language:
        copied_files = copy_workspace_md_files(
            language,
            ws_dir,
            md_template_id=get_workspace_md_template_id(
                agent_config.template_id
                or ("qa" if workspace.agent_id == BUILTIN_QA_AGENT_ID else None),
            ),
            only_if_missing=False,
        )

    schedule_agent_reload(request, workspace.agent_id)
    return {"language": language, "copied_files": copied_files}


@router.get("/agent/user-timezone")
async def webchat_get_user_timezone(request: Request) -> dict:
    """Get the current WebChat tenant agent timezone."""
    identity = _get_identity_from_request(request)
    workspace = await get_tenant_workspace_for_identity(request, identity)
    ws_dir = Path(workspace.workspace_dir)
    agent_config = load_agent_config_from_workspace(ws_dir)
    if agent_config is None:
        agent_config = AgentProfileConfig(
            id=workspace.agent_id,
            name=workspace.agent_id,
        )
    return {"timezone": agent_config.user_timezone}


@router.put("/agent/user-timezone")
async def webchat_put_user_timezone(
    request: Request,
    body: dict = Body(...),
) -> dict:
    """Update the current WebChat tenant agent timezone."""
    tz = (body.get("timezone") or "").strip()
    if not tz:
        raise HTTPException(status_code=400, detail="timezone is required")

    identity = _get_identity_from_request(request)
    workspace = await get_tenant_workspace_for_identity(request, identity)
    ws_dir = Path(workspace.workspace_dir)
    agent_config = load_agent_config_from_workspace(ws_dir)
    if agent_config is None:
        agent_config = AgentProfileConfig(
            id=workspace.agent_id,
            name=workspace.agent_id,
        )
    agent_config.user_timezone = tz
    write_agent_config_to_workspace(ws_dir, agent_config)
    schedule_agent_reload(request, workspace.agent_id)
    return {"timezone": tz}
