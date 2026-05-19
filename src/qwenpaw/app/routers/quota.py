"""Quota management read APIs."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from qwenpaw.enterprise.quota.config import QuotaConfig

router = APIRouter(prefix="/quota", tags=["quota"])


class QuotaLimitSummary(BaseModel):
    dimension: str
    window: str
    max_value: int
    resource: str


class QuotaSummary(BaseModel):
    enabled: bool
    redis_url_set: bool
    default_limits: list[QuotaLimitSummary]


@router.get("/summary", response_model=QuotaSummary)
async def get_quota_summary() -> QuotaSummary:
    """Return quota runtime configuration without exposing connection strings."""
    config = QuotaConfig.from_env()
    return QuotaSummary(
        enabled=config.enabled,
        redis_url_set=bool(config.redis_url),
        default_limits=[
            QuotaLimitSummary(
                dimension=limit.dimension.value,
                window=limit.window.value,
                max_value=limit.max_value,
                resource=limit.resource,
            )
            for limit in config.default_limits
        ],
    )
