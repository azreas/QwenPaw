"""FastAPI route permission matrix scanner."""

from __future__ import annotations

from typing import Any

from .permissions import resolve_route_permission

_IGNORED_METHODS = {"HEAD", "OPTIONS"}


def _iter_route_methods(route: Any) -> list[str]:
    methods = getattr(route, "methods", None) or set()
    return sorted(m for m in methods if m not in _IGNORED_METHODS)


def find_uncovered_api_routes(app: Any) -> list[tuple[str, str, tuple[str, str]]]:
    """Return API routes that resolve to the fallback unknown permission."""
    issues: list[tuple[str, str, tuple[str, str]]] = []
    for route in getattr(app, "routes", []):
        path = getattr(route, "path", "")
        if not path.startswith("/api/"):
            continue
        for method in _iter_route_methods(route):
            permission = resolve_route_permission(method, path)
            if permission == ("unknown", "read"):
                issues.append((method, path, permission))
    return issues
