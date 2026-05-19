# -*- coding: utf-8 -*-
"""Feature configuration endpoints for WeCom tenant workspaces."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ....agents.skill_system import (
    SkillPoolService,
    SkillService,
    get_workspace_skills_dir,
    read_skill_manifest,
    reconcile_workspace_manifest,
)
from ....agents.skill_system.store import (
    _copy_skill_dir,
    _normalize_skill_dir_name,
    _read_skill_from_dir,
    _resolve_skill_name,
)
from ....config.config import (
    AgentProfileConfig,
    AgentsLLMRoutingConfig,
    ChannelConfig,
    MCPClientConfig,
    MCPConfig,
    ModelSlotConfig,
    SecurityConfig,
    ToolGuardRuleConfig,
    ToolsConfig,
    WebchatConfig,
    WecomTenantConfig,
)
from ....enterprise.audit.emit import emit_audit_event
from ....enterprise.audit.models import AuditEventType, AuditOutcome
from ....enterprise.authz.deps import require_permission
from .common import (
    audit_repository_from_request,
    emit_tenant_audit_event,
    load_tenant_config,
    maybe_reload,
    require_tenant_boundary,
    require_workspace,
    save_tenant_config,
)
from .schemas import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOADED_MEDIA_SKILL_SOURCE = "uploaded_media"


class ToolInfo(BaseModel):
    name: str
    enabled: bool
    description: str = ""
    async_execution: bool = False
    icon: str = ""


class ToolAsyncExecutionRequest(BaseModel):
    async_execution: bool


class SkillInfoResponse(BaseModel):
    name: str
    description: str = ""
    source: str = ""
    enabled: bool = False
    installed: bool = True
    installable: bool = False
    channels: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    updated_at: str | None = None
    last_call_at: str | None = None
    last_call_status: str | None = None
    last_error_reason: str | None = None
    last_duration_ms: float | None = None


class SkillInstallRequest(BaseModel):
    skill_id: str = Field(min_length=1)
    overwrite: bool = False


class SkillOperationResponse(BaseModel):
    success: bool
    name: str
    enabled: bool | None = None
    reason: str | None = None


class EntryWecomConfigRequest(BaseModel):
    enabled: bool = False
    bot_id: str = ""
    secret: str | None = None
    media_dir: str | None = None
    welcome_text: str = ""
    share_session_in_group: bool = True
    max_reconnect_attempts: int = -1
    streaming_enabled: bool = False
    require_mention: bool = False
    dm_policy: str = "open"
    group_policy: str = "open"
    allow_from: list[str] = Field(default_factory=list)
    deny_message: str = ""


class EntryWecomConfigResponse(BaseModel):
    enabled: bool = False
    bot_id: str = ""
    secret_set: bool = False
    media_dir: str | None = None
    welcome_text: str = ""
    share_session_in_group: bool = True
    max_reconnect_attempts: int = -1
    streaming_enabled: bool = False
    require_mention: bool = False
    dm_policy: str = "open"
    group_policy: str = "open"
    allow_from: list[str] = Field(default_factory=list)
    deny_message: str = ""


class EntryWebchatConfigRequest(BaseModel):
    enabled: bool = False
    media_dir: str | None = None
    user_data_dir: str | None = None
    require_mention: bool = False
    dm_policy: str = "open"
    group_policy: str = "open"
    allow_from: list[str] = Field(default_factory=list)
    deny_message: str = ""


class EntryWebchatConfigResponse(EntryWebchatConfigRequest):
    session_secret_source: str = "env"
    qrcode_config_source: str = "env"


class TenantEntryConfigRequest(BaseModel):
    wecom: EntryWecomConfigRequest = Field(default_factory=EntryWecomConfigRequest)
    webchat: EntryWebchatConfigRequest = Field(
        default_factory=EntryWebchatConfigRequest
    )


class TenantEntryConfigResponse(BaseModel):
    wecom: EntryWecomConfigResponse
    webchat: EntryWebchatConfigResponse


class TenantEntryDiagnosticsResponse(BaseModel):
    agent_id: str
    status: str
    checks: dict[str, bool]
    messages: list[str] = Field(default_factory=list)


def _ensure_channel_config(config: AgentProfileConfig) -> ChannelConfig:
    if config.channels is None:
        config.channels = ChannelConfig()
    return config.channels


def _entry_wecom_response(value: WecomTenantConfig) -> EntryWecomConfigResponse:
    return EntryWecomConfigResponse(
        enabled=value.enabled,
        bot_id=value.bot_id,
        secret_set=bool(value.secret),
        media_dir=value.media_dir,
        welcome_text=value.welcome_text,
        share_session_in_group=value.share_session_in_group,
        max_reconnect_attempts=value.max_reconnect_attempts,
        streaming_enabled=value.streaming_enabled,
        require_mention=value.require_mention,
        dm_policy=value.dm_policy,
        group_policy=value.group_policy,
        allow_from=list(value.allow_from),
        deny_message=value.deny_message,
    )


def _entry_webchat_response(value: WebchatConfig) -> EntryWebchatConfigResponse:
    return EntryWebchatConfigResponse(
        enabled=value.enabled,
        media_dir=value.media_dir,
        user_data_dir=value.user_data_dir,
        require_mention=value.require_mention,
        dm_policy=value.dm_policy,
        group_policy=value.group_policy,
        allow_from=list(value.allow_from),
        deny_message=value.deny_message,
    )


def _entry_config_response(config: AgentProfileConfig) -> TenantEntryConfigResponse:
    channels = _ensure_channel_config(config)
    return TenantEntryConfigResponse(
        wecom=_entry_wecom_response(channels.wecom_tenant),
        webchat=_entry_webchat_response(channels.webchat),
    )


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    if isinstance(value, dict):
        items: list[str] = []
        for key in ("require_bins", "require_envs"):
            items.extend(_string_list(value.get(key)))
        return items
    return []


def _skill_info_response(
    item: Any,
    entry: dict[str, Any],
    *,
    name: str | None = None,
    source: str | None = None,
    installed: bool = True,
    installable: bool = False,
    last_call_at: str | None = None,
    last_call_status: str | None = None,
    last_error_reason: str | None = None,
    last_duration_ms: float | None = None,
) -> SkillInfoResponse:
    return SkillInfoResponse(
        name=name or item.name,
        description=item.description,
        source=source or item.source,
        enabled=bool(entry.get("enabled", False)),
        installed=installed,
        installable=installable,
        channels=_string_list(entry.get("channels")),
        tags=_string_list(entry.get("tags")),
        requirements=_string_list(entry.get("requirements")),
        updated_at=entry.get("updated_at"),
        last_call_at=last_call_at,
        last_call_status=last_call_status,
        last_error_reason=last_error_reason,
        last_duration_ms=last_duration_ms,
    )


def _get_audit_repo(request: Request) -> Any | None:
    """从 enterprise_runtime 获取 AuditRepository，无则返回 None。"""
    return audit_repository_from_request(request)


@router.get(
    "/tenants/{agent_id}/entry-config",
    response_model=TenantEntryConfigResponse,
)
async def get_tenant_entry_config(
    agent_id: str,
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> TenantEntryConfigResponse:
    config = load_tenant_config(agent_id)
    return _entry_config_response(config)


@router.put(
    "/tenants/{agent_id}/entry-config",
    response_model=TenantEntryConfigResponse,
)
async def put_tenant_entry_config(
    request: Request,
    agent_id: str,
    body: TenantEntryConfigRequest,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> TenantEntryConfigResponse:
    config = load_tenant_config(agent_id)
    channels = _ensure_channel_config(config)

    existing_secret = channels.wecom_tenant.secret
    channels.wecom_tenant.enabled = body.wecom.enabled
    channels.wecom_tenant.bot_id = body.wecom.bot_id
    channels.wecom_tenant.secret = body.wecom.secret or existing_secret
    channels.wecom_tenant.media_dir = body.wecom.media_dir
    channels.wecom_tenant.welcome_text = body.wecom.welcome_text
    channels.wecom_tenant.share_session_in_group = body.wecom.share_session_in_group
    channels.wecom_tenant.max_reconnect_attempts = body.wecom.max_reconnect_attempts
    channels.wecom_tenant.streaming_enabled = body.wecom.streaming_enabled
    channels.wecom_tenant.require_mention = body.wecom.require_mention
    channels.wecom_tenant.dm_policy = body.wecom.dm_policy
    channels.wecom_tenant.group_policy = body.wecom.group_policy
    channels.wecom_tenant.allow_from = body.wecom.allow_from
    channels.wecom_tenant.deny_message = body.wecom.deny_message

    channels.webchat.enabled = body.webchat.enabled
    channels.webchat.media_dir = body.webchat.media_dir
    channels.webchat.user_data_dir = body.webchat.user_data_dir
    channels.webchat.require_mention = body.webchat.require_mention
    channels.webchat.dm_policy = body.webchat.dm_policy
    channels.webchat.group_policy = body.webchat.group_policy
    channels.webchat.allow_from = body.webchat.allow_from
    channels.webchat.deny_message = body.webchat.deny_message

    save_tenant_config(agent_id, config)
    maybe_reload(request, agent_id)
    await emit_tenant_audit_event(
        request,
        agent_id,
        AuditEventType.TENANT_UPDATED,
        "update_entry_config",
        AuditOutcome.SUCCESS,
        resource_type="tenant_config",
        resource_id=f"{agent_id}:entry-config",
        payload={
            "agent_id": agent_id,
            "changed_key": "channels",
            "channels": ["wecom_tenant", "webchat"],
        },
    )
    return _entry_config_response(config)


@router.post(
    "/tenants/{agent_id}/entry-config/diagnose",
    response_model=TenantEntryDiagnosticsResponse,
)
async def diagnose_tenant_entry_config(
    request: Request,
    agent_id: str,
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> TenantEntryDiagnosticsResponse:
    config = load_tenant_config(agent_id)
    workspace_dir = require_workspace(agent_id)
    channels = _ensure_channel_config(config)
    checks = {
        "workspace_exists": workspace_dir.is_dir(),
        "agent_json_loaded": True,
        "wecom_enabled": channels.wecom_tenant.enabled,
        "wecom_bot_id_configured": bool(channels.wecom_tenant.bot_id),
        "wecom_secret_configured": bool(channels.wecom_tenant.secret),
        "webchat_enabled": channels.webchat.enabled,
        "webchat_user_data_dir_configured": bool(channels.webchat.user_data_dir),
    }
    messages: list[str] = []
    if channels.wecom_tenant.enabled and not channels.wecom_tenant.bot_id:
        messages.append("WeCom Bot ID is required when WeCom entry is enabled.")
    if channels.wecom_tenant.enabled and not channels.wecom_tenant.secret:
        messages.append("WeCom secret is required when WeCom entry is enabled.")
    status = "ok" if not messages else "warning"
    await emit_tenant_audit_event(
        request,
        agent_id,
        AuditEventType.TENANT_UPDATED,
        "diagnose_entry_config",
        AuditOutcome.SUCCESS,
        resource_type="tenant_config",
        resource_id=f"{agent_id}:entry-config:diagnostics",
        payload={"agent_id": agent_id, "status": status, "checks": checks},
    )
    return TenantEntryDiagnosticsResponse(
        agent_id=agent_id,
        status=status,
        checks=checks,
        messages=messages,
    )


async def _query_recent_call_status(
    audit_repo: Any,
    agent_id: str,
    event_type: str,
    resource_id: str,
) -> dict[str, Any]:
    """查询指定能力最近一次调用状态。"""
    try:
        query_kwargs: dict[str, Any] = {
            "event_types": (event_type,),
            "agent_id": agent_id,
            "limit": 50 if event_type == "mcp.called" else 1,
        }
        if event_type != "mcp.called":
            query_kwargs["resource_id"] = resource_id
        rows = await audit_repo.query(**query_kwargs)
    except Exception:
        logger.debug("查询最近调用状态失败", exc_info=True)
        return {}
    if event_type == "mcp.called":
        rows = [
            row for row in rows
            if (
                (getattr(row, "payload", {}) or {}).get("mcp_name") == resource_id
                or getattr(row, "resource_id", "") == resource_id
                or str(getattr(row, "resource_id", "")).startswith(f"{resource_id}/")
            )
        ]
    if not rows:
        return {}
    row = rows[0]
    payload = getattr(row, "payload", {}) or {}
    created_at = getattr(row, "created_at", None)
    created_at_str = None
    if created_at is not None and hasattr(created_at, "isoformat"):
        created_at_str = created_at.isoformat()
    return {
        "last_call_at": created_at_str,
        "last_call_status": payload.get("status"),
        "last_error_reason": payload.get("error_reason") or None,
        "last_duration_ms": payload.get("duration_ms"),
    }


async def _query_mcp_test_status(
    audit_repo: Any,
    agent_id: str,
    client_key: str,
) -> dict[str, Any]:
    """查询 MCP 最近一次连接测试状态。"""
    try:
        rows = await audit_repo.query(
            event_types=("mcp.connection_test",),
            agent_id=agent_id,
            resource_id=client_key,
            limit=1,
        )
    except Exception:
        logger.debug("查询 MCP 测试状态失败", exc_info=True)
        return {}
    if not rows:
        return {}
    row = rows[0]
    payload = getattr(row, "payload", {}) or {}
    created_at = getattr(row, "created_at", None)
    created_at_str = None
    if created_at is not None and hasattr(created_at, "isoformat"):
        created_at_str = created_at.isoformat()
    return {
        "last_test_at": created_at_str,
        "last_test_status": payload.get("status"),
        "last_test_detail": payload.get("detail") or None,
    }


def _uploaded_skill_candidates(workspace_dir: Path) -> list[tuple[str, Path, Any]]:
    media_dir = workspace_dir / "media"
    if not media_dir.is_dir():
        return []
    media_root = media_dir.resolve()
    candidates: list[tuple[str, Path, Any]] = []
    for skill_md in sorted(media_dir.rglob("SKILL.md")):
        skill_dir = skill_md.parent
        if not skill_dir.resolve().is_relative_to(media_root):
            continue
        item = _read_skill_from_dir(skill_dir, UPLOADED_MEDIA_SKILL_SOURCE)
        if item is None:
            continue
        name = _normalize_skill_dir_name(_resolve_skill_name(skill_dir))
        candidates.append((name, skill_dir, item))
    return candidates


def _find_uploaded_skill(
    workspace_dir: Path,
    skill_id: str,
) -> tuple[str, Path] | None:
    target = _normalize_skill_dir_name(skill_id)
    for name, skill_dir, _item in _uploaded_skill_candidates(workspace_dir):
        if name == target or skill_dir.name == target:
            return name, skill_dir
    return None


def _install_uploaded_skill(
    workspace_dir: Path,
    skill_id: str,
    *,
    overwrite: bool,
) -> dict[str, Any] | None:
    candidate = _find_uploaded_skill(workspace_dir, skill_id)
    if candidate is None:
        return None
    skill_name, source_dir = candidate
    target_dir = get_workspace_skills_dir(workspace_dir) / skill_name
    if target_dir.exists() and not overwrite:
        return {"success": False, "name": skill_name, "reason": "conflict"}

    _copy_skill_dir(source_dir, target_dir)
    reconcile_workspace_manifest(workspace_dir)
    result = SkillService(workspace_dir).enable_skill(skill_name)
    if not result.get("success", False):
        return {
            "success": False,
            "name": skill_name,
            "reason": result.get("reason") or "enable_failed",
        }
    return {"success": True, "name": skill_name, "enabled": True}


class MCPClientInfo(BaseModel):
    client_key: str
    name: str
    description: str = ""
    enabled: bool = True
    transport: str = "stdio"
    url: str = ""
    command: str = ""
    args: list[str] = Field(default_factory=list)
    cwd: str = ""
    headers: dict[str, str] = Field(default_factory=dict)
    env: dict[str, str] = Field(default_factory=dict)
    last_call_at: str | None = None
    last_call_status: str | None = None
    last_error_reason: str | None = None
    last_duration_ms: float | None = None
    last_test_at: str | None = None
    last_test_status: str | None = None
    last_test_detail: str | None = None


class MCPCreateRequest(BaseModel):
    client_key: str = Field(min_length=1)
    client: MCPClientConfig


class MCPConnectionTestResponse(BaseModel):
    client_key: str
    status: str = "ok"
    detail: str = ""
    duration_ms: float = 0.0

    @classmethod
    def ok(cls, client_key: str, duration_ms: float) -> "MCPConnectionTestResponse":
        return cls(client_key=client_key, status="ok", duration_ms=duration_ms)

    @classmethod
    def auth_failed(
        cls,
        client_key: str,
        detail: str,
        duration_ms: float = 0,
    ) -> "MCPConnectionTestResponse":
        return cls(
            client_key=client_key,
            status="auth_failed",
            detail=detail,
            duration_ms=duration_ms,
        )

    @classmethod
    def timeout(cls, client_key: str, duration_ms: float) -> "MCPConnectionTestResponse":
        return cls(
            client_key=client_key,
            status="timeout",
            detail="Connection timed out",
            duration_ms=duration_ms,
        )

    @classmethod
    def unreachable(
        cls,
        client_key: str,
        detail: str,
        duration_ms: float = 0,
    ) -> "MCPConnectionTestResponse":
        return cls(
            client_key=client_key,
            status="unreachable",
            detail=detail,
            duration_ms=duration_ms,
        )

    @classmethod
    def invalid_config(cls, client_key: str, detail: str) -> "MCPConnectionTestResponse":
        return cls(client_key=client_key, status="invalid_config", detail=detail, duration_ms=0)


class SecuritySettingsRequest(BaseModel):
    approval_level: str = "AUTO"
    tool_guard_rules: list[dict[str, Any]] = Field(default_factory=list)


class SecuritySettingsResponse(BaseModel):
    approval_level: str
    tool_guard_rules: list[dict[str, Any]]


class SystemPromptFilesRequest(BaseModel):
    files: list[str]


class SystemPromptFilesResponse(BaseModel):
    files: list[str]


def _ensure_tools_config(config: AgentProfileConfig) -> ToolsConfig:
    if config.tools is None:
        config.tools = ToolsConfig()
    return config.tools


def _tool_info(tool_config) -> ToolInfo:
    return ToolInfo(
        name=tool_config.name,
        enabled=tool_config.enabled,
        description=tool_config.description,
        async_execution=tool_config.async_execution,
        icon=tool_config.icon or "",
    )


def _ensure_mcp_config(config: AgentProfileConfig) -> MCPConfig:
    if config.mcp is None:
        config.mcp = MCPConfig(clients={})
    return config.mcp


def _mcp_info(
    client_key: str,
    client: MCPClientConfig,
    *,
    last_call_at: str | None = None,
    last_call_status: str | None = None,
    last_error_reason: str | None = None,
    last_duration_ms: float | None = None,
    last_test_at: str | None = None,
    last_test_status: str | None = None,
    last_test_detail: str | None = None,
) -> MCPClientInfo:
    return MCPClientInfo(
        client_key=client_key,
        name=client.name,
        description=client.description,
        enabled=client.enabled,
        transport=client.transport,
        url=client.url,
        command=client.command,
        args=client.args,
        cwd=client.cwd,
        headers=dict(client.headers),
        env=dict(client.env),
        last_call_at=last_call_at,
        last_call_status=last_call_status,
        last_error_reason=last_error_reason,
        last_duration_ms=last_duration_ms,
        last_test_at=last_test_at,
        last_test_status=last_test_status,
        last_test_detail=last_test_detail,
    )


def _security_response(config: AgentProfileConfig) -> SecuritySettingsResponse:
    rules = []
    if config.security is not None:
        rules = [
            rule.model_dump(mode="json")
            for rule in config.security.tool_guard.custom_rules
        ]
    return SecuritySettingsResponse(
        approval_level=config.approval_level,
        tool_guard_rules=rules,
    )


def _coerce_tool_guard_rule(raw: dict[str, Any], index: int) -> ToolGuardRuleConfig:
    patterns = raw.get("patterns")
    if not patterns and raw.get("pattern"):
        patterns = [str(raw["pattern"])]
    return ToolGuardRuleConfig(
        id=str(raw.get("id") or raw.get("pattern") or f"custom_{index}"),
        tools=list(raw.get("tools") or []),
        params=list(raw.get("params") or []),
        category=str(raw.get("category") or "custom"),
        severity=str(raw.get("severity") or "HIGH"),
        patterns=list(patterns or []),
        exclude_patterns=list(raw.get("exclude_patterns") or []),
        description=str(raw.get("description") or ""),
        remediation=str(raw.get("remediation") or ""),
    )


def _validate_prompt_file(filename: str) -> str:
    value = str(filename or "").strip()
    if not value or "/" in value or "\\" in value or ".." in value:
        raise HTTPException(status_code=400, detail="Invalid prompt filename")
    return value


@router.get("/tenants/{agent_id}/model")
async def get_tenant_model(
    agent_id: str,
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> dict[str, Any] | None:
    config = load_tenant_config(agent_id)
    if config.active_model is None:
        return None
    return config.active_model.model_dump(mode="json")


@router.put("/tenants/{agent_id}/model", response_model=ModelSlotConfig)
async def put_tenant_model(
    request: Request,
    agent_id: str,
    body: ModelSlotConfig,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> ModelSlotConfig:
    config = load_tenant_config(agent_id)
    config.active_model = body
    save_tenant_config(agent_id, config)
    maybe_reload(request, agent_id)
    await emit_tenant_audit_event(
        request,
        agent_id,
        AuditEventType.TENANT_UPDATED,
        "update_model",
        AuditOutcome.SUCCESS,
        resource_type="tenant_config",
        resource_id=f"{agent_id}:model",
        payload={"agent_id": agent_id, "changed_key": "active_model"},
    )
    return body


@router.get("/tenants/{agent_id}/llm-routing", response_model=AgentsLLMRoutingConfig)
async def get_tenant_llm_routing(
    agent_id: str,
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> AgentsLLMRoutingConfig:
    return load_tenant_config(agent_id).llm_routing


@router.put("/tenants/{agent_id}/llm-routing", response_model=AgentsLLMRoutingConfig)
async def put_tenant_llm_routing(
    request: Request,
    agent_id: str,
    body: AgentsLLMRoutingConfig,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> AgentsLLMRoutingConfig:
    config = load_tenant_config(agent_id)
    config.llm_routing = body
    save_tenant_config(agent_id, config)
    maybe_reload(request, agent_id)
    await emit_tenant_audit_event(
        request,
        agent_id,
        AuditEventType.TENANT_UPDATED,
        "update_llm_routing",
        AuditOutcome.SUCCESS,
        resource_type="tenant_config",
        resource_id=f"{agent_id}:llm-routing",
        payload={"agent_id": agent_id, "changed_key": "llm_routing"},
    )
    return body


@router.get("/tenants/{agent_id}/tools", response_model=list[ToolInfo])
async def list_tenant_tools(
    agent_id: str,
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> list[ToolInfo]:
    tools = _ensure_tools_config(load_tenant_config(agent_id))
    return [_tool_info(item) for item in tools.builtin_tools.values()]


@router.patch("/tenants/{agent_id}/tools/{tool_name}/toggle", response_model=ToolInfo)
async def toggle_tenant_tool(
    request: Request,
    agent_id: str,
    tool_name: str,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> ToolInfo:
    config = load_tenant_config(agent_id)
    tools = _ensure_tools_config(config)
    if tool_name not in tools.builtin_tools:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    tool_config = tools.builtin_tools[tool_name]
    tool_config.enabled = not tool_config.enabled
    save_tenant_config(agent_id, config)
    maybe_reload(request, agent_id)
    await emit_tenant_audit_event(
        request,
        agent_id,
        AuditEventType.TENANT_UPDATED,
        "toggle_tool",
        AuditOutcome.SUCCESS,
        resource_type="tenant_tool",
        resource_id=f"{agent_id}:tool:{tool_name}",
        payload={
            "agent_id": agent_id,
            "tool_name": tool_name,
            "enabled": tool_config.enabled,
        },
    )
    return _tool_info(tool_config)


@router.patch(
    "/tenants/{agent_id}/tools/{tool_name}/async-execution",
    response_model=ToolInfo,
)
async def update_tenant_tool_async_execution(
    request: Request,
    agent_id: str,
    tool_name: str,
    body: ToolAsyncExecutionRequest,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> ToolInfo:
    config = load_tenant_config(agent_id)
    tools = _ensure_tools_config(config)
    if tool_name not in tools.builtin_tools:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    tool_config = tools.builtin_tools[tool_name]
    tool_config.async_execution = body.async_execution
    save_tenant_config(agent_id, config)
    maybe_reload(request, agent_id)
    await emit_tenant_audit_event(
        request,
        agent_id,
        AuditEventType.TENANT_UPDATED,
        "update_tool_async_execution",
        AuditOutcome.SUCCESS,
        resource_type="tenant_tool",
        resource_id=f"{agent_id}:tool:{tool_name}",
        payload={
            "agent_id": agent_id,
            "tool_name": tool_name,
            "async_execution": body.async_execution,
        },
    )
    return _tool_info(tool_config)


@router.get("/tenants/{agent_id}/skills", response_model=list[SkillInfoResponse])
async def list_tenant_skills(
    request: Request,
    agent_id: str,
    _ctx=Depends(require_permission("skills", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> list[SkillInfoResponse]:
    workspace_dir = require_workspace(agent_id)
    previous_manifest = read_skill_manifest(workspace_dir)
    manifest = reconcile_workspace_manifest(workspace_dir)
    previous_entries = previous_manifest.get("skills", {})
    entries = manifest.get("skills", {})

    # 获取审计仓储（可选，不阻断页面）
    audit_repo = _get_audit_repo(request)

    skills: list[SkillInfoResponse] = []
    installed_names: set[str] = set()
    for item in SkillService(workspace_dir).list_all_skills():
        entry = dict(entries.get(item.name, {}))
        previous_entry = previous_entries.get(item.name, {})
        if (
            not _string_list(entry.get("requirements"))
            and _string_list(previous_entry.get("requirements"))
        ):
            entry["requirements"] = previous_entry["requirements"]
        installed_names.add(item.name)

        # 查询最近调用状态
        call_kwargs: dict[str, Any] = {}
        if audit_repo is not None:
            call_kwargs = await _query_recent_call_status(
                audit_repo, agent_id, "skill.called", item.name,
            )

        skills.append(_skill_info_response(item, entry, **call_kwargs))

    for name, _skill_dir, item in _uploaded_skill_candidates(workspace_dir):
        if name in installed_names:
            continue
        call_kwargs: dict[str, Any] = {}
        if audit_repo is not None:
            call_kwargs = await _query_recent_call_status(
                audit_repo, agent_id, "skill.called", name,
            )
        skills.append(
            _skill_info_response(
                item,
                {},
                name=name,
                source=UPLOADED_MEDIA_SKILL_SOURCE,
                installed=False,
                installable=True,
                **call_kwargs,
            )
        )
    return skills


@router.patch(
    "/tenants/{agent_id}/skills/{skill_id}/toggle",
    response_model=SkillOperationResponse,
)
async def toggle_tenant_skill(
    request: Request,
    agent_id: str,
    skill_id: str,
    _ctx=Depends(require_permission("skills", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> SkillOperationResponse:
    workspace_dir = require_workspace(agent_id)
    entry = read_skill_manifest(workspace_dir).get("skills", {}).get(skill_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")
    service = SkillService(workspace_dir)
    enabling = not bool(entry.get("enabled", False))
    if enabling:
        result = service.enable_skill(skill_id)
        event_type = AuditEventType.SKILL_ENABLED
    else:
        result = service.disable_skill(skill_id)
        event_type = AuditEventType.SKILL_DISABLED
    if not result.get("success", False):
        reason = str(result.get("reason") or "skill toggle failed")
        await emit_audit_event(
            request, event_type, "toggle", AuditOutcome.FAILURE,
            resource_type="skills", resource_id=skill_id,
            payload={"agent_id": agent_id, "reason": reason},
        )
        raise HTTPException(status_code=400, detail=reason)
    maybe_reload(request, agent_id)
    await emit_audit_event(
        request, event_type, "toggle", AuditOutcome.SUCCESS,
        resource_type="skills", resource_id=skill_id,
        payload={"agent_id": agent_id, "enabled": enabling},
    )
    return SkillOperationResponse(success=True, name=skill_id, enabled=enabling)


@router.post(
    "/tenants/{agent_id}/skills/install",
    response_model=SkillOperationResponse,
)
async def install_tenant_skill(
    request: Request,
    agent_id: str,
    body: SkillInstallRequest,
    _ctx=Depends(require_permission("skills", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> SkillOperationResponse:
    workspace_dir = require_workspace(agent_id)
    result = SkillPoolService().download_to_workspace(
        body.skill_id,
        workspace_dir,
        overwrite=body.overwrite,
    )
    if not result.get("success", False):
        uploaded_result = _install_uploaded_skill(
            workspace_dir,
            body.skill_id,
            overwrite=body.overwrite,
        )
        if uploaded_result is None:
            await emit_audit_event(
                request, AuditEventType.SKILL_INSTALLED, "install",
                AuditOutcome.FAILURE,
                resource_type="skills", resource_id=body.skill_id,
                payload={"agent_id": agent_id, "reason": str(result)},
            )
            raise HTTPException(status_code=400, detail=result)
        result = uploaded_result
    if not result.get("success", False):
        await emit_audit_event(
            request, AuditEventType.SKILL_INSTALLED, "install",
            AuditOutcome.FAILURE,
            resource_type="skills", resource_id=body.skill_id,
            payload={"agent_id": agent_id, "reason": str(result)},
        )
        raise HTTPException(status_code=400, detail=result)
    maybe_reload(request, agent_id)
    name = str(result.get("name") or body.skill_id)
    await emit_audit_event(
        request, AuditEventType.SKILL_INSTALLED, "install",
        AuditOutcome.SUCCESS,
        resource_type="skills", resource_id=name,
        payload={"agent_id": agent_id},
    )
    return SkillOperationResponse(success=True, name=name, enabled=True)


@router.delete(
    "/tenants/{agent_id}/skills/{skill_id}",
    response_model=SkillOperationResponse,
)
async def delete_tenant_skill(
    request: Request,
    agent_id: str,
    skill_id: str,
    _ctx=Depends(require_permission("skills", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> SkillOperationResponse:
    workspace_dir = require_workspace(agent_id)
    manifest = read_skill_manifest(workspace_dir)
    if skill_id not in manifest.get("skills", {}):
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")
    service = SkillService(workspace_dir)
    service.disable_skill(skill_id)
    if not service.delete_skill(skill_id):
        await emit_audit_event(
            request, AuditEventType.SKILL_DELETED, "delete",
            AuditOutcome.FAILURE,
            resource_type="skills", resource_id=skill_id,
            payload={"agent_id": agent_id, "reason": "delete_failed"},
        )
        raise HTTPException(status_code=400, detail=f"Skill '{skill_id}' cannot be deleted")
    maybe_reload(request, agent_id)
    await emit_audit_event(
        request, AuditEventType.SKILL_DELETED, "delete",
        AuditOutcome.SUCCESS,
        resource_type="skills", resource_id=skill_id,
        payload={"agent_id": agent_id},
    )
    return SkillOperationResponse(success=True, name=skill_id)


@router.get("/tenants/{agent_id}/mcp", response_model=list[MCPClientInfo])
async def list_tenant_mcp(
    request: Request,
    agent_id: str,
    _ctx=Depends(require_permission("mcp", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> list[MCPClientInfo]:
    config = load_tenant_config(agent_id)
    if config.mcp is None:
        return []

    # 获取审计仓储（可选，不阻断页面）
    audit_repo = _get_audit_repo(request)

    result: list[MCPClientInfo] = []
    for key, client in config.mcp.clients.items():
        call_kwargs: dict[str, Any] = {}
        test_kwargs: dict[str, Any] = {}
        if audit_repo is not None:
            call_kwargs = await _query_recent_call_status(
                audit_repo, agent_id, "mcp.called", key,
            )
            test_kwargs = await _query_mcp_test_status(
                audit_repo, agent_id, key,
            )
        result.append(_mcp_info(key, client, **call_kwargs, **test_kwargs))
    return result


@router.post(
    "/tenants/{agent_id}/mcp",
    response_model=MCPClientInfo,
    status_code=201,
)
async def create_tenant_mcp(
    request: Request,
    agent_id: str,
    body: MCPCreateRequest,
    _ctx=Depends(require_permission("mcp", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> MCPClientInfo:
    config = load_tenant_config(agent_id)
    mcp = _ensure_mcp_config(config)
    if body.client_key in mcp.clients:
        raise HTTPException(status_code=400, detail="MCP client already exists")
    mcp.clients[body.client_key] = body.client
    save_tenant_config(agent_id, config)
    maybe_reload(request, agent_id)
    await emit_audit_event(
        request, AuditEventType.MCP_CREATED, "create",
        AuditOutcome.SUCCESS,
        resource_type="mcp", resource_id=body.client_key,
        payload={"agent_id": agent_id},
    )
    return _mcp_info(body.client_key, body.client)


@router.put("/tenants/{agent_id}/mcp/{client_key}", response_model=MCPClientInfo)
async def update_tenant_mcp(
    request: Request,
    agent_id: str,
    client_key: str,
    body: MCPClientConfig,
    _ctx=Depends(require_permission("mcp", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> MCPClientInfo:
    config = load_tenant_config(agent_id)
    if config.mcp is None or client_key not in config.mcp.clients:
        raise HTTPException(status_code=404, detail=f"MCP client '{client_key}' not found")
    config.mcp.clients[client_key] = body
    save_tenant_config(agent_id, config)
    maybe_reload(request, agent_id)
    await emit_audit_event(
        request, AuditEventType.MCP_UPDATED, "update",
        AuditOutcome.SUCCESS,
        resource_type="mcp", resource_id=client_key,
        payload={"agent_id": agent_id},
    )
    return _mcp_info(client_key, body)


@router.patch("/tenants/{agent_id}/mcp/{client_key}/toggle", response_model=MCPClientInfo)
async def toggle_tenant_mcp(
    request: Request,
    agent_id: str,
    client_key: str,
    _ctx=Depends(require_permission("mcp", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> MCPClientInfo:
    config = load_tenant_config(agent_id)
    if config.mcp is None or client_key not in config.mcp.clients:
        raise HTTPException(status_code=404, detail=f"MCP client '{client_key}' not found")
    client = config.mcp.clients[client_key]
    enabling = not client.enabled
    client.enabled = enabling
    save_tenant_config(agent_id, config)
    maybe_reload(request, agent_id)
    event_type = AuditEventType.MCP_ENABLED if enabling else AuditEventType.MCP_DISABLED
    await emit_audit_event(
        request, event_type, "toggle",
        AuditOutcome.SUCCESS,
        resource_type="mcp", resource_id=client_key,
        payload={"agent_id": agent_id, "enabled": enabling},
    )
    return _mcp_info(client_key, client)


@router.delete("/tenants/{agent_id}/mcp/{client_key}", response_model=MessageResponse)
async def delete_tenant_mcp(
    request: Request,
    agent_id: str,
    client_key: str,
    _ctx=Depends(require_permission("mcp", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> MessageResponse:
    config = load_tenant_config(agent_id)
    if config.mcp is None or client_key not in config.mcp.clients:
        raise HTTPException(status_code=404, detail=f"MCP client '{client_key}' not found")
    del config.mcp.clients[client_key]
    save_tenant_config(agent_id, config)
    maybe_reload(request, agent_id)
    await emit_audit_event(
        request, AuditEventType.MCP_DELETED, "delete",
        AuditOutcome.SUCCESS,
        resource_type="mcp", resource_id=client_key,
        payload={"agent_id": agent_id},
    )
    return MessageResponse(message=f"MCP client '{client_key}' deleted successfully")


@router.post(
    "/tenants/{agent_id}/mcp/{client_key}/test",
    response_model=MCPConnectionTestResponse,
)
async def test_tenant_mcp_connection(
    request: Request,
    agent_id: str,
    client_key: str,
    _ctx=Depends(require_permission("mcp", "test")),
    _tb=Depends(require_tenant_boundary()),
) -> MCPConnectionTestResponse:
    """测试租户 MCP 客户端连接，返回产品可理解状态。"""
    import time

    config = load_tenant_config(agent_id)
    if config.mcp is None or client_key not in config.mcp.clients:
        raise HTTPException(status_code=404, detail=f"MCP client '{client_key}' not found")

    client_config = config.mcp.clients[client_key]

    # 配置校验
    if not client_config.transport:
        status = MCPConnectionTestResponse.invalid_config(client_key, "transport is required")
        await emit_tenant_audit_event(
            request, agent_id, AuditEventType.MCP_CONNECTION_TEST, "test",
            AuditOutcome.FAILURE,
            resource_type="mcp", resource_id=client_key,
            payload={"agent_id": agent_id, "status": "invalid_config", "detail": status.detail},
        )
        return status

    if client_config.transport not in ("stdio", "streamable_http", "sse"):
        status = MCPConnectionTestResponse.invalid_config(
            client_key,
            f"unsupported transport: {client_config.transport}",
        )
        await emit_tenant_audit_event(
            request, agent_id, AuditEventType.MCP_CONNECTION_TEST, "test",
            AuditOutcome.FAILURE,
            resource_type="mcp", resource_id=client_key,
            payload={"agent_id": agent_id, "status": "invalid_config", "detail": status.detail},
        )
        return status

    if client_config.transport == "stdio" and not client_config.command:
        status = MCPConnectionTestResponse.invalid_config(
            client_key,
            "stdio transport requires command",
        )
        await emit_tenant_audit_event(
            request, agent_id, AuditEventType.MCP_CONNECTION_TEST, "test",
            AuditOutcome.FAILURE,
            resource_type="mcp", resource_id=client_key,
            payload={"agent_id": agent_id, "status": "invalid_config", "detail": status.detail},
        )
        return status

    if client_config.transport != "stdio" and not client_config.url:
        status = MCPConnectionTestResponse.invalid_config(
            client_key,
            "url is required for HTTP transport",
        )
        await emit_tenant_audit_event(
            request, agent_id, AuditEventType.MCP_CONNECTION_TEST, "test",
            AuditOutcome.FAILURE,
            resource_type="mcp", resource_id=client_key,
            payload={"agent_id": agent_id, "status": "invalid_config", "detail": status.detail},
        )
        return status

    # 尝试连接
    from ....app.mcp.manager import MCPClientManager

    start = time.monotonic()
    manager = None
    try:
        manager = MCPClientManager()
        # 连接测试使用短超时（10 秒）
        await asyncio.wait_for(
            manager.replace_client(client_key, client_config, timeout=5.0),
            timeout=10.0,
        )
    except asyncio.TimeoutError:
        duration_ms = (time.monotonic() - start) * 1000
        resp = MCPConnectionTestResponse.timeout(client_key, duration_ms)
        await emit_tenant_audit_event(
            request, agent_id, AuditEventType.MCP_CONNECTION_TEST, "test",
            AuditOutcome.FAILURE,
            resource_type="mcp", resource_id=client_key,
            payload={"agent_id": agent_id, "status": "timeout", "duration_ms": duration_ms},
        )
        return resp
    except Exception as exc:
        duration_ms = (time.monotonic() - start) * 1000
        error_str = str(exc)
        # 分类错误
        lower_err = error_str.lower()
        if (
            "401" in lower_err
            or "403" in lower_err
            or "unauthorized" in lower_err
            or "auth" in lower_err
        ):
            resp = MCPConnectionTestResponse.auth_failed(client_key, error_str, duration_ms)
        else:
            resp = MCPConnectionTestResponse.unreachable(client_key, error_str, duration_ms)
        await emit_tenant_audit_event(
            request, agent_id, AuditEventType.MCP_CONNECTION_TEST, "test",
            AuditOutcome.FAILURE,
            resource_type="mcp", resource_id=client_key,
            payload={
                "agent_id": agent_id,
                "status": resp.status,
                "detail": error_str,
                "duration_ms": duration_ms,
            },
        )
        return resp
    finally:
        # 清理临时连接
        try:
            if manager is not None:
                await manager.remove_client(client_key)
        except Exception:
            logger.debug("MCP connection test: cleanup failed for %s", client_key, exc_info=True)

    duration_ms = (time.monotonic() - start) * 1000
    await emit_tenant_audit_event(
        request, agent_id, AuditEventType.MCP_CONNECTION_TEST, "test",
        AuditOutcome.SUCCESS,
        resource_type="mcp", resource_id=client_key,
        payload={"agent_id": agent_id, "status": "ok", "duration_ms": duration_ms},
    )
    return MCPConnectionTestResponse.ok(client_key, duration_ms)


@router.get("/tenants/{agent_id}/security", response_model=SecuritySettingsResponse)
async def get_tenant_security(
    agent_id: str,
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> SecuritySettingsResponse:
    return _security_response(load_tenant_config(agent_id))


@router.put("/tenants/{agent_id}/security", response_model=SecuritySettingsResponse)
async def put_tenant_security(
    request: Request,
    agent_id: str,
    body: SecuritySettingsRequest,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> SecuritySettingsResponse:
    config = load_tenant_config(agent_id)
    config.approval_level = body.approval_level
    if config.security is None:
        config.security = SecurityConfig()
    config.security.tool_guard.custom_rules = [
        _coerce_tool_guard_rule(rule, index)
        for index, rule in enumerate(body.tool_guard_rules, start=1)
    ]
    save_tenant_config(agent_id, config)
    maybe_reload(request, agent_id)
    await emit_tenant_audit_event(
        request,
        agent_id,
        AuditEventType.TENANT_UPDATED,
        "update_security",
        AuditOutcome.SUCCESS,
        resource_type="tenant_config",
        resource_id=f"{agent_id}:security",
        payload={
            "agent_id": agent_id,
            "changed_key": "security",
            "approval_level": body.approval_level,
            "rule_count": len(body.tool_guard_rules),
        },
    )
    return _security_response(config)


@router.get(
    "/tenants/{agent_id}/system-prompts",
    response_model=SystemPromptFilesResponse,
)
async def get_tenant_system_prompts(
    agent_id: str,
    _ctx=Depends(require_permission("tenant", "read")),
    _tb=Depends(require_tenant_boundary()),
) -> SystemPromptFilesResponse:
    return SystemPromptFilesResponse(files=load_tenant_config(agent_id).system_prompt_files)


@router.put(
    "/tenants/{agent_id}/system-prompts",
    response_model=SystemPromptFilesResponse,
)
async def put_tenant_system_prompts(
    request: Request,
    agent_id: str,
    body: SystemPromptFilesRequest,
    _ctx=Depends(require_permission("tenant", "write")),
    _tb=Depends(require_tenant_boundary()),
) -> SystemPromptFilesResponse:
    config = load_tenant_config(agent_id)
    config.system_prompt_files = [
        _validate_prompt_file(filename) for filename in body.files
    ]
    save_tenant_config(agent_id, config)
    maybe_reload(request, agent_id)
    await emit_tenant_audit_event(
        request,
        agent_id,
        AuditEventType.TENANT_UPDATED,
        "update_system_prompts",
        AuditOutcome.SUCCESS,
        resource_type="tenant_config",
        resource_id=f"{agent_id}:system-prompts",
        payload={
            "agent_id": agent_id,
            "changed_key": "system_prompt_files",
            "file_count": len(config.system_prompt_files),
        },
    )
    return SystemPromptFilesResponse(files=config.system_prompt_files)
