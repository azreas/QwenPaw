from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse


def create_metrics_router() -> APIRouter:
    """创建 metrics 端点 router（延迟从 app.state 获取 registry，避免重复注册）。"""
    router = APIRouter(tags=["metrics"])

    @router.get("/metrics", response_class=PlainTextResponse)
    def metrics(request: Request) -> PlainTextResponse:
        runtime = getattr(request.app.state, "enterprise_runtime", None)
        observability = getattr(runtime, "observability", None)
        registry = getattr(observability, "metrics", None)
        if registry is None:
            return PlainTextResponse(
                "# observability service not available\n",
                media_type="text/plain; version=0.0.4",
            )
        return PlainTextResponse(
            registry.to_prometheus_text(),
            media_type="text/plain; version=0.0.4",
        )

    return router
