"""企业存储配置 — 从环境变量解析后端类型和连接参数。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

_SUPPORTED_BACKENDS = ("json", "sqlite", "postgres")


@dataclass(frozen=True)
class StorageConfig:
    backend: str = "json"
    database_url: str | None = None
    pool_size: int = 5
    echo: bool = False

    @property
    def enabled(self) -> bool:
        """SQL 后端启用时返回 True。"""
        return self.backend != "json"

    @classmethod
    def from_env(cls) -> StorageConfig:
        """从环境变量构造配置。"""
        backend = os.environ.get("QWENPAW_STORAGE_BACKEND", "json").lower()
        if backend not in _SUPPORTED_BACKENDS:
            raise ValueError(
                f"Unsupported storage backend: {backend!r}. "
                f"Supported: {', '.join(_SUPPORTED_BACKENDS)}"
            )

        database_url = os.environ.get("QWENPAW_DATABASE_URL")
        if backend in ("sqlite", "postgres") and not database_url:
            if backend == "sqlite":
                working_dir = os.environ.get(
                    "QWENPAW_WORKING_DIR",
                    os.path.expanduser("~/.qwenpaw"),
                )
                database_url = f"sqlite+aiosqlite:///{working_dir}/qwenpaw.db"
            else:
                raise ValueError(
                    "QWENPAW_DATABASE_URL is required for postgres backend"
                )

        pool_size = int(os.environ.get("QWENPAW_DB_POOL_SIZE", "5"))
        echo = os.environ.get("QWENPAW_DB_ECHO", "").lower() in ("1", "true", "yes")

        return cls(
            backend=backend,
            database_url=database_url,
            pool_size=pool_size,
            echo=echo,
        )
