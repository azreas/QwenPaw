from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from qwenpaw.constant import EnvVarLoader

MB = 1024 * 1024
DEFAULT_MAX_PAYLOAD_BYTES = 2 * MB
DEFAULT_CHAT_UPLOAD_MAX_BYTES = 10 * MB
DEFAULT_WORKSPACE_UPLOAD_MAX_BYTES = 100 * MB
DEFAULT_SKILL_UPLOAD_MAX_BYTES = 100 * MB

# Multipart form overhead (boundary + Content-Disposition headers)
# This buffer ensures the configured "file size" limit accounts for
# multipart encoding overhead in real-world upload scenarios.
MULTIPART_OVERHEAD_BYTES = 64 * 1024  # 64KB


@dataclass(frozen=True)
class PayloadSizeRule:
    """Route-specific payload size limit.

    Rules are matched in order:
    - Exact match: path == path_prefix
    - Prefix+Suffix match: path starts with path_prefix AND ends with path_suffix
    - Prefix match: path.startswith(path_prefix + "/")
    """

    path_prefix: str
    max_bytes: int
    add_multipart_overhead: bool = False
    path_suffix: str | None = None


def get_default_max_payload_bytes() -> int:
    return EnvVarLoader.get_int(
        "QWENPAW_MAX_PAYLOAD_BYTES",
        DEFAULT_MAX_PAYLOAD_BYTES,
        min_value=1,
    )


def build_default_payload_route_limits() -> tuple[PayloadSizeRule, ...]:
    chat_upload = EnvVarLoader.get_int(
        "QWENPAW_CHAT_UPLOAD_MAX_BYTES",
        DEFAULT_CHAT_UPLOAD_MAX_BYTES,
        min_value=1,
    )
    workspace_upload = EnvVarLoader.get_int(
        "QWENPAW_WORKSPACE_UPLOAD_MAX_BYTES",
        DEFAULT_WORKSPACE_UPLOAD_MAX_BYTES,
        min_value=1,
    )
    skill_upload = EnvVarLoader.get_int(
        "QWENPAW_SKILL_UPLOAD_MAX_BYTES",
        DEFAULT_SKILL_UPLOAD_MAX_BYTES,
        min_value=1,
    )
    return (
        PayloadSizeRule("/api/console/upload", chat_upload, add_multipart_overhead=True),
        PayloadSizeRule("/api/webchat/upload", chat_upload, add_multipart_overhead=True),
        PayloadSizeRule(
            "/api/webchat/agent/workspace/files/upload", chat_upload, add_multipart_overhead=True
        ),
        PayloadSizeRule("/api/workspace/upload", workspace_upload, add_multipart_overhead=True),
        PayloadSizeRule(
            "/api/webchat/agent/workspace/upload", workspace_upload, add_multipart_overhead=True
        ),
        PayloadSizeRule("/api/backups/import", workspace_upload, add_multipart_overhead=True),
        # WeCom tenant config import (zip upload) - only the import endpoint gets 100MB
        PayloadSizeRule(
            "/api/config/channels/wecom_tenant/tenants",
            workspace_upload,
            add_multipart_overhead=True,
            path_suffix="/import",
        ),
        PayloadSizeRule("/api/skills/upload", skill_upload, add_multipart_overhead=True),
        PayloadSizeRule("/api/skills/pool/upload-zip", skill_upload, add_multipart_overhead=True),
        PayloadSizeRule(
            "/api/webchat/agent/skills/upload-zip", skill_upload, add_multipart_overhead=True
        ),
    )


class PayloadSizeMiddleware(BaseHTTPMiddleware):
    """限制请求体大小，防止大 payload DoS。"""

    def __init__(
        self,
        app,
        max_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
        route_limits: Sequence[PayloadSizeRule] | None = None,
    ) -> None:
        super().__init__(app)
        self._max_bytes = max_bytes
        self._route_limits = tuple(route_limits or ())

    def _max_bytes_for_path(self, path: str) -> int:
        for rule in self._route_limits:
            if rule.path_suffix is not None:
                # Prefix + suffix match (e.g., /tenants/.../import)
                if path.startswith(f"{rule.path_prefix}/") and path.endswith(
                    rule.path_suffix
                ):
                    limit = rule.max_bytes
                    if rule.add_multipart_overhead:
                        limit += MULTIPART_OVERHEAD_BYTES
                    return limit
            elif path == rule.path_prefix or path.startswith(
                f"{rule.path_prefix}/"
            ):
                limit = rule.max_bytes
                if rule.add_multipart_overhead:
                    limit += MULTIPART_OVERHEAD_BYTES
                return limit
        return self._max_bytes

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        raw_length = request.headers.get("content-length", "0")
        try:
            content_length = int(raw_length)
        except ValueError:
            content_length = 0
        if content_length > self._max_bytes_for_path(request.url.path):
            return JSONResponse(status_code=413, content={"detail": "Payload too large"})
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """添加安全响应头。"""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    """对携带会话 cookie 的写操作验证 CSRF token。

    WebChat 路由豁免，使用自己的会话机制。
    """

    _SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method in self._SAFE_METHODS:
            return await call_next(request)
        if request.url.path.startswith("/api/webchat/"):
            return await call_next(request)
        cookie_token = request.cookies.get("qwenpaw_session")
        if not cookie_token:
            return await call_next(request)
        header_token = request.headers.get("x-csrf-token", "")
        if not header_token or header_token != cookie_token:
            return JSONResponse(
                status_code=403, content={"detail": "CSRF check failed"}
            )
        return await call_next(request)
