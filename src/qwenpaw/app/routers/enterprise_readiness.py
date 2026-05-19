from fastapi import APIRouter, Request
from pydantic import BaseModel

from qwenpaw.enterprise.readiness.checks import collect_enterprise_readiness
from qwenpaw.enterprise.readiness.models import ReadinessSummary

router = APIRouter(prefix="/enterprise", tags=["enterprise-readiness"])


class ReadinessStatus(BaseModel):
    """粗粒度就绪状态，公开访问无权限要求"""
    status: str


@router.get("/readiness", response_model=ReadinessStatus | ReadinessSummary)
async def get_enterprise_readiness(request: Request) -> ReadinessStatus | ReadinessSummary:
    """企业化就绪状态检查。

    - 未认证/普通用户：只返回粗粒度 status 字段
    - platform_admin：返回完整 checks 和 blockers 详情
    """
    summary = collect_enterprise_readiness()

    # 检查是否有 platform_admin 权限
    request_context = getattr(request.state, "request_context", None)
    if request_context is not None and "platform_admin" in request_context.roles:
        return summary

    # 公开访问只返回粗粒度状态
    return ReadinessStatus(status=summary.status)
