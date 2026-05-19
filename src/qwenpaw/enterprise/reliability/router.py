"""健康检查路由。"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse


def create_reliability_router() -> APIRouter:
    """创建可靠性检查路由。

    Returns:
        包含 /health 和 /ready 端点的 APIRouter
    """
    router = APIRouter(tags=["reliability"])

    @router.get("/health")
    def health() -> dict[str, str]:
        """Liveness 探针 - 仅表示进程存活。

        部署平台使用此端点判断服务是否需要重启。
        不包含任何业务逻辑检查，始终返回 200。
        """
        return {"status": "ok"}

    @router.get("/ready")
    async def ready(request: Request) -> JSONResponse:
        """Readiness 探针 - 聚合所有服务组件的就绪状态。

        部署平台使用此端点判断是否可以将流量路由到此实例。
        返回 200 表示可以接收流量，503 表示不可用。
        """
        runtime = getattr(request.app.state, "enterprise_runtime", None)
        health_service = getattr(runtime, "health", None)

        if health_service is None:
            return JSONResponse(
                status_code=503,
                content={"ready": False, "status": "down", "components": []},
            )

        report = await health_service.readiness()
        return JSONResponse(
            status_code=200 if report.ready else 503,
            content=report.as_dict(),
        )

    return router
