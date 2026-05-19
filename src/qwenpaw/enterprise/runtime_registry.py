"""Global runtime registry for non-request enterprise hooks."""

from __future__ import annotations

from typing import Any

_enterprise_runtime: Any | None = None


def set_enterprise_runtime(runtime: Any) -> None:
    global _enterprise_runtime
    _enterprise_runtime = runtime


def get_enterprise_runtime() -> Any | None:
    return _enterprise_runtime


def clear_enterprise_runtime(runtime: Any | None = None) -> None:
    global _enterprise_runtime
    if runtime is None or _enterprise_runtime is runtime:
        _enterprise_runtime = None
