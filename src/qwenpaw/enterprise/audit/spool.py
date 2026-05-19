"""审计 fallback spool — JSONL 文件持久化。

队列满或 DB 写入失败时，事件写入按日期命名的 JSONL 文件。
后台重放任务读取并回写 DB，成功后归档到 sent/。
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qwenpaw.enterprise.audit.models import AuditEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SpoolBatch:
    """一批从 spool 读取的事件，包含来源文件路径。"""

    events: list[AuditEvent]
    source_file: Path


class AuditSpool:
    """JSONL 审计事件 spool。"""

    def __init__(self, base_dir: Path) -> None:
        self._base = base_dir
        self._sent = base_dir / "sent"
        self._corrupt = base_dir / "corrupt"

    def _date_file(self) -> Path:
        now = datetime.now(timezone.utc)
        name = f"audit-{now.strftime('%Y-%m-%d')}.jsonl"
        return self._base / name

    async def write(self, event: AuditEvent) -> None:
        """追加写入一个事件到当日 JSONL 文件。"""
        line = json.dumps(_event_to_dict(event), ensure_ascii=False) + "\n"
        path = self._date_file()
        await _write_line(path, line)

    async def write_many(self, events: list[AuditEvent]) -> None:
        """批量写入多个事件。"""
        if not events:
            return
        path = self._date_file()
        lines = [
            json.dumps(_event_to_dict(e), ensure_ascii=False) + "\n"
            for e in events
        ]
        await _write_lines(path, lines)

    async def read_batch(self, limit: int = 100) -> SpoolBatch:
        """读取最早的一批事件，按文件日期排序。"""
        files = sorted(self._base.glob("*.jsonl"))
        if not files:
            return SpoolBatch(events=[], source_file=Path())

        path = files[0]
        events: list[AuditEvent] = []
        corrupt_lines: list[str] = []

        await _ensure_read(path)
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                events.append(_event_from_dict(data))
            except (json.JSONDecodeError, KeyError, TypeError):
                corrupt_lines.append(f"{path.name}:{line_no}")
                logger.warning("spool 行解析失败: %s:%d", path.name, line_no)

        if corrupt_lines:
            await _move_to_corrupt(path, self._corrupt)
            logger.error(
                "spool 文件含损坏行，已移入 corrupt/: %s", ", ".join(corrupt_lines)
            )

        # 返回文件中全部有效事件（ack 会移动整个文件，必须完整读取）
        return SpoolBatch(events=events, source_file=path)

    async def ack(self, batch: SpoolBatch) -> None:
        """确认重放成功，将来源文件移到 sent/。"""
        if not batch.source_file.exists():
            return
        self._sent.mkdir(parents=True, exist_ok=True)
        dest = self._sent / batch.source_file.name
        await _move_file(batch.source_file, dest)


def _event_to_dict(event: AuditEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "event_type": event.event_type,
        "action": event.action,
        "outcome": event.outcome,
        "tenant_id": event.tenant_id,
        "agent_id": event.agent_id,
        "session_id": event.session_id,
        "actor_id": event.actor_id,
        "actor_type": event.actor_type,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "request_id": event.request_id,
        "trace_id": event.trace_id,
        "ip_address": event.ip_address,
        "user_agent": event.user_agent,
        "payload": event.payload,
        "created_at": event.created_at.isoformat(),
    }


def _event_from_dict(data: dict[str, Any]) -> AuditEvent:
    created = data.pop("created_at", None)
    dt = datetime.fromisoformat(created) if created else datetime.now(timezone.utc)
    return AuditEvent(**data, created_at=dt)


async def _write_line(path: Path, line: str) -> None:
    def _sync() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(line)

    import asyncio

    await asyncio.to_thread(_sync)


async def _write_lines(path: Path, lines: list[str]) -> None:
    def _sync() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.writelines(lines)

    import asyncio

    await asyncio.to_thread(_sync)


async def _ensure_read(path: Path) -> None:
    """确保文件可读（to_thread 包装）。"""
    import asyncio

    def _sync() -> None:
        if not path.exists():
            path.touch()

    await asyncio.to_thread(_sync)


async def _move_file(src: Path, dest: Path) -> None:
    import asyncio

    def _sync() -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))

    await asyncio.to_thread(_sync)


async def _move_to_corrupt(src: Path, corrupt_dir: Path) -> None:
    import asyncio

    def _sync() -> None:
        corrupt_dir.mkdir(parents=True, exist_ok=True)
        dest = corrupt_dir / src.name
        shutil.move(str(src), str(dest))

    await asyncio.to_thread(_sync)
