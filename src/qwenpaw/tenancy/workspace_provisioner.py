# -*- coding: utf-8 -*-
"""WorkspaceProvisioner：租户工作区模板复制与初始化。"""
from __future__ import annotations

import logging
import shutil
import threading
from contextlib import contextmanager
from pathlib import Path

from qwenpaw.app.routers.agents import _initialize_agent_workspace

from .ids import tenant_agent_id
from .paths import tenants_root
from .tenant_agent_config import ensure_tenant_agent_config_file

logger = logging.getLogger(__name__)

_LOCK_MAP: dict[str, threading.Lock] = {}
_LOCK_MAP_LOCK = threading.Lock()

_WORKSPACE_DEFAULT_FILES = frozenset(
    {
        "AGENTS.md",
        "PROFILE.md",
        "MEMORY.md",
        "SOUL.md",
        "HEARTBEAT.md",
        "jobs.json",
        "chats.json",
    },
)
_WORKSPACE_DEFAULT_DIRS = frozenset({"sessions", "memory", "skills"})


@contextmanager
def _tenant_init_lock(ws: Path):
    """同进程内针对特定工作区路径的互斥锁。"""
    key = str(ws)
    with _LOCK_MAP_LOCK:
        if key not in _LOCK_MAP:
            _LOCK_MAP[key] = threading.Lock()
        lock = _LOCK_MAP[key]
    with lock:
        yield


class WorkspaceProvisioner:
    """负责租户工作区的首次初始化与热路径默认项回填。"""

    def __init__(self, working_dir: Path, template_dir: Path):
        self.tenants_root = tenants_root(working_dir)
        self.template_dir = Path(template_dir)

    def ensure(self, tenant_id: str) -> Path:
        """确保租户工作区存在，首次使用时从模板或内置默认文件创建。"""
        agent_id = tenant_agent_id(tenant_id)
        ws = self.tenants_root / agent_id

        if ws.exists():
            self._backfill_workspace_defaults(ws, agent_id)
            return ws

        with _tenant_init_lock(ws):
            if not ws.exists():
                self._init_workspace(ws, tenant_id, agent_id)

        return ws

    def _init_workspace(
        self,
        ws: Path,
        tenant_id: str,
        agent_id: str,
    ) -> None:
        """从模板复制工作区并完成个性化写入。"""
        self.tenants_root.mkdir(parents=True, exist_ok=True)
        if self.template_dir.exists():
            shutil.copytree(self.template_dir, ws)
            _initialize_agent_workspace(ws, language="zh")
            logger.info("创建租户工作区: %s", ws)
        else:
            ws.mkdir(parents=True, exist_ok=True)
            _initialize_agent_workspace(ws, language="zh")
            logger.info("从内置模板创建租户工作区: %s", ws)
        self._patch_soul(ws, tenant_id)
        ensure_tenant_agent_config_file(agent_id=agent_id, workspace_dir=ws)

    def _patch_soul(self, ws: Path, tenant_id: str) -> None:
        """将 SOUL.md 中的 {{USER_ID}} 替换为真实租户 ID。"""
        soul = ws / "SOUL.md"
        if soul.exists():
            content = soul.read_text(encoding="utf-8")
            soul.write_text(
                content.replace("{{USER_ID}}", tenant_id),
                encoding="utf-8",
            )

    @staticmethod
    def _backfill_workspace_defaults(ws: Path, agent_id: str) -> None:
        """确保租户工作区具备原生 agent 的默认运行契约。"""
        missing_files = [
            name for name in _WORKSPACE_DEFAULT_FILES if not (ws / name).is_file()
        ]
        missing_dirs = [
            name for name in _WORKSPACE_DEFAULT_DIRS if not (ws / name).is_dir()
        ]
        if missing_files or missing_dirs:
            _initialize_agent_workspace(ws, language="zh")
            logger.info(
                "回填缺失的租户工作区默认项: files=%s dirs=%s",
                missing_files,
                missing_dirs,
            )
        ensure_tenant_agent_config_file(agent_id=agent_id, workspace_dir=ws)
