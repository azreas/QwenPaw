from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000

        runtime = getattr(request.app.state, "enterprise_runtime", None)
        observability = getattr(runtime, "observability", None)
        metrics = getattr(observability, "metrics", None)
        if metrics is not None and request.url.path.startswith("/api/"):
            # 使用路由模板而非 raw path，避免高基数指标
            route = request.scope.get("route")
            if route is not None and hasattr(route, "path"):
                route_path = route.path
            else:
                route_path = "/api/unmatched"

            labels = {
                "method": request.method,
                "route": route_path,
                "status": str(response.status_code),
            }
            metrics.inc("http_requests_total", labels=labels)
            metrics.set_gauge("http_request_duration_ms", elapsed_ms, labels=labels)
        return response
