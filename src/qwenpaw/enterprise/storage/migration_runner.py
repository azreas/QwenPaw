"""Alembic migration runner for enterprise storage."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from alembic import command
from alembic.config import Config

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection
    from sqlalchemy.ext.asyncio import AsyncEngine


class MigrationRunner:
    """Run enterprise storage migrations using an existing async engine."""

    def __init__(self, script_location: str | None = None) -> None:
        default_location = Path(__file__).parent / "migrations"
        self._script_location = script_location or str(default_location)

    def _build_config(self) -> Config:
        cfg = Config()
        cfg.set_main_option("script_location", self._script_location)
        return cfg

    @staticmethod
    def _run_upgrade(connection: "Connection", cfg: Config) -> None:
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")

    async def upgrade(self, engine: "AsyncEngine") -> None:
        cfg = self._build_config()
        async with engine.begin() as conn:
            await conn.run_sync(self._run_upgrade, cfg)
