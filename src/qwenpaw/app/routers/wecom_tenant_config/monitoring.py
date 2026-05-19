# -*- coding: utf-8 -*-
"""Monitoring endpoints for WeCom tenant workspaces."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from ....agent_stats import AgentStatsSummary, get_agent_stats_service
from ....token_usage import TokenUsageStats, TokenUsageSummary, get_token_usage_manager
from ...runner.repo.json_repo import JsonChatRepository
from ...runner.session import sanitize_filename
from .common import (
    date_range,
    get_manager,
    require_workspace,
    tenants_root,
    validate_agent_id,
)

router = APIRouter()


class ChatListResponse(BaseModel):
    items: list[dict[str, Any]]
    page: int
    page_size: int
    total: int


class DashboardTrendItem(BaseModel):
    date: str
    tokens: int = 0
    messages: int = 0
    active_tenants: int = 0


class DashboardResponse(BaseModel):
    total_tenants: int
    running_tenants: int
    stopped_tenants: int
    broken_tenants: int
    total_tokens: int
    total_chats: int
    total_messages: int
    daily_trend: list[DashboardTrendItem]


def _list_workspace_agent_ids() -> list[str]:
    root = tenants_root()
    if not root.is_dir():
        return []
    return sorted(
        item.name
        for item in root.iterdir()
        if item.is_dir() and item.name.startswith("wx_")
    )


def _selected_agent_ids(agent_ids: str | None) -> list[str]:
    all_ids = set(_list_workspace_agent_ids())
    if not agent_ids:
        return sorted(all_ids)
    requested = {
        validate_agent_id(item.strip())
        for item in agent_ids.split(",")
        if item.strip()
    }
    return sorted(all_ids.intersection(requested))


def _copy_token_stats(item: TokenUsageStats) -> TokenUsageStats:
    return item.model_copy()


def _merge_stat_bucket(
    target: dict[str, TokenUsageStats],
    key: str,
    value: TokenUsageStats,
) -> None:
    if key not in target:
        target[key] = _copy_token_stats(value)
        return
    existing = target[key]
    existing.prompt_tokens += value.prompt_tokens
    existing.completion_tokens += value.completion_tokens
    existing.call_count += value.call_count


def _merge_token_summaries(items: list[TokenUsageSummary]) -> TokenUsageSummary:
    merged = TokenUsageSummary()
    for item in items:
        merged.total_prompt_tokens += item.total_prompt_tokens
        merged.total_completion_tokens += item.total_completion_tokens
        merged.total_calls += item.total_calls
        for key, value in item.by_date.items():
            _merge_stat_bucket(merged.by_date, key, value)
    return merged


async def _token_summary_for_agent(
    agent_id: str,
    start_d: date,
    end_d: date,
    model: str | None,
    provider: str | None,
) -> TokenUsageSummary:
    return await get_token_usage_manager().get_summary(
        start_date=start_d,
        end_date=end_d,
        model_name=model,
        provider_id=provider,
        agent_id=agent_id,
    )


async def _agent_stats_for_agent(
    agent_id: str,
    start_d: date,
    end_d: date,
) -> AgentStatsSummary:
    return await get_agent_stats_service().get_summary(
        workspace_dir=require_workspace(agent_id),
        start_date=start_d,
        end_date=end_d,
    )


def _merge_agent_stats(
    items: list[AgentStatsSummary],
    start_d: date,
    end_d: date,
) -> AgentStatsSummary:
    return AgentStatsSummary(
        total_active_sessions=sum(item.total_active_sessions for item in items),
        total_messages=sum(item.total_messages for item in items),
        total_user_messages=sum(item.total_user_messages for item in items),
        total_assistant_messages=sum(item.total_assistant_messages for item in items),
        total_prompt_tokens=sum(item.total_prompt_tokens for item in items),
        total_completion_tokens=sum(item.total_completion_tokens for item in items),
        total_llm_calls=sum(item.total_llm_calls for item in items),
        total_tool_calls=sum(item.total_tool_calls for item in items),
        by_date=[entry for item in items for entry in item.by_date],
        channel_stats=[entry for item in items for entry in item.channel_stats],
        start_date=start_d.isoformat(),
        end_date=end_d.isoformat(),
    )


def _paginate(
    items: list[dict[str, Any]],
    page: int,
    page_size: int,
) -> ChatListResponse:
    safe_page = max(page, 1)
    safe_size = min(max(page_size, 1), 100)
    start = (safe_page - 1) * safe_size
    return ChatListResponse(
        items=items[start : start + safe_size],
        page=safe_page,
        page_size=safe_size,
        total=len(items),
    )


async def _chat_items_for_agent(agent_id: str, channel: str | None) -> list[dict[str, Any]]:
    workspace_dir = require_workspace(agent_id)
    chats = await JsonChatRepository(workspace_dir / "chats.json").list_chats()
    items = []
    for chat in chats:
        if channel and chat.channel != channel:
            continue
        payload = chat.model_dump(mode="json")
        payload["agent_id"] = agent_id
        items.append(payload)
    return items


async def _load_session_file(workspace_dir: Path, session_id: str) -> dict[str, Any]:
    sessions_dir = workspace_dir / "sessions"
    chats = await JsonChatRepository(workspace_dir / "chats.json").list_chats()
    matched_chats = [
        chat
        for chat in chats
        if chat.id == session_id or chat.session_id == session_id
    ]
    candidates = []

    def add_candidate(path: Path) -> None:
        if path not in candidates:
            candidates.append(path)

    add_candidate(sessions_dir / f"{session_id}.json")
    add_candidate(sessions_dir / f"{sanitize_filename(session_id)}.json")
    for chat in matched_chats:
        add_candidate(sessions_dir / f"{sanitize_filename(chat.session_id)}.json")
        if chat.user_id:
            add_candidate(
                sessions_dir
                / (
                    f"{sanitize_filename(chat.user_id)}_"
                    f"{sanitize_filename(chat.session_id)}.json"
                ),
            )

    for path in candidates:
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise HTTPException(
                    status_code=422,
                    detail=f"Session '{session_id}' is invalid",
                ) from exc
            if not isinstance(data, dict):
                raise HTTPException(
                    status_code=422,
                    detail=f"Session '{session_id}' is invalid",
                )
            if matched_chats:
                data.setdefault("chat_id", matched_chats[0].id)
                data.setdefault("session_id", matched_chats[0].session_id)
                data.setdefault("user_id", matched_chats[0].user_id)
                data.setdefault("channel", matched_chats[0].channel)
            else:
                data.setdefault("session_id", session_id)
            return data
    raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")


def _count_chats(agent_id: str) -> int:
    path = tenants_root() / agent_id / "chats.json"
    if not path.is_file():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0
    return len(data.get("chats", [])) if isinstance(data, dict) else 0


def _is_broken_workspace(agent_id: str) -> bool:
    workspace_dir = tenants_root() / agent_id
    agent_json = workspace_dir / "agent.json"
    if not agent_json.is_file():
        return True
    try:
        json.loads(agent_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return True
    return False


def _dashboard_trend(
    token_summary: TokenUsageSummary,
    stats_summary: AgentStatsSummary,
) -> list[DashboardTrendItem]:
    by_date: dict[str, DashboardTrendItem] = {}
    for date_key, stat in token_summary.by_date.items():
        by_date[date_key] = DashboardTrendItem(
            date=date_key,
            tokens=stat.prompt_tokens + stat.completion_tokens,
        )
    for daily in stats_summary.by_date:
        item = by_date.setdefault(daily.date, DashboardTrendItem(date=daily.date))
        item.messages += daily.total_messages
        if daily.active_sessions:
            item.active_tenants += 1
    return [by_date[key] for key in sorted(by_date)]


@router.get("/tenants/{agent_id}/stats/token-usage", response_model=TokenUsageSummary)
async def get_tenant_token_usage(
    agent_id: str,
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    model: str | None = Query(None),
    provider: str | None = Query(None),
) -> TokenUsageSummary:
    require_workspace(agent_id)
    start_d, end_d = date_range(start_date, end_date)
    return await _token_summary_for_agent(agent_id, start_d, end_d, model, provider)


@router.get("/stats/token-usage", response_model=TokenUsageSummary)
async def get_global_token_usage(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    agent_ids: str | None = Query(None),
    model: str | None = Query(None),
    provider: str | None = Query(None),
) -> TokenUsageSummary:
    start_d, end_d = date_range(start_date, end_date)
    summaries = [
        await _token_summary_for_agent(agent_id, start_d, end_d, model, provider)
        for agent_id in _selected_agent_ids(agent_ids)
    ]
    return _merge_token_summaries(summaries)


@router.get("/tenants/{agent_id}/stats/agent", response_model=AgentStatsSummary)
async def get_tenant_agent_stats(
    agent_id: str,
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
) -> AgentStatsSummary:
    start_d, end_d = date_range(start_date, end_date)
    return await _agent_stats_for_agent(agent_id, start_d, end_d)


@router.get("/stats/agent", response_model=AgentStatsSummary)
async def get_global_agent_stats(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    agent_ids: str | None = Query(None),
) -> AgentStatsSummary:
    start_d, end_d = date_range(start_date, end_date)
    summaries = [
        await _agent_stats_for_agent(agent_id, start_d, end_d)
        for agent_id in _selected_agent_ids(agent_ids)
    ]
    return _merge_agent_stats(summaries, start_d, end_d)


@router.get("/tenants/{agent_id}/stats/chats", response_model=ChatListResponse)
async def list_tenant_chats(
    agent_id: str,
    page: int = Query(1),
    page_size: int = Query(20),
    channel: str | None = Query(None),
) -> ChatListResponse:
    return _paginate(await _chat_items_for_agent(agent_id, channel), page, page_size)


@router.get("/tenants/{agent_id}/stats/chats/{session_id}")
async def get_tenant_chat_session(agent_id: str, session_id: str) -> dict[str, Any]:
    return await _load_session_file(require_workspace(agent_id), session_id)


@router.get("/stats/chats", response_model=ChatListResponse)
async def list_global_chats(
    agent_ids: str | None = Query(None),
    page: int = Query(1),
    page_size: int = Query(20),
    channel: str | None = Query(None),
) -> ChatListResponse:
    items = []
    for agent_id in _selected_agent_ids(agent_ids):
        items.extend(await _chat_items_for_agent(agent_id, channel))
    return _paginate(items, page, page_size)


@router.get("/stats/dashboard", response_model=DashboardResponse)
async def get_dashboard(request: Request) -> DashboardResponse:
    agent_ids = _list_workspace_agent_ids()
    manager = get_manager(request)
    running = [agent_id for agent_id in agent_ids if manager.is_agent_loaded(agent_id)]
    broken = [agent_id for agent_id in agent_ids if _is_broken_workspace(agent_id)]
    start_d, end_d = date_range(None, None)
    token_summary = await get_global_token_usage(
        start_date=start_d.isoformat(),
        end_date=end_d.isoformat(),
        agent_ids=None,
        model=None,
        provider=None,
    )
    stat_summary = await get_global_agent_stats(
        start_date=start_d.isoformat(),
        end_date=end_d.isoformat(),
        agent_ids=None,
    )
    return DashboardResponse(
        total_tenants=len(agent_ids),
        running_tenants=len(running),
        stopped_tenants=len(agent_ids) - len(running),
        broken_tenants=len(broken),
        total_tokens=(
            token_summary.total_prompt_tokens
            + token_summary.total_completion_tokens
        ),
        total_chats=sum(_count_chats(agent_id) for agent_id in agent_ids),
        total_messages=stat_summary.total_messages,
        daily_trend=_dashboard_trend(token_summary, stat_summary),
    )
