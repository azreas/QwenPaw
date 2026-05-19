# -*- coding: utf-8 -*-
"""Aggregated WeCom tenant management router."""
from __future__ import annotations

from fastapi import APIRouter

from .feature_config import router as feature_config_router
from .monitoring import router as monitoring_router
from .operations import router as operations_router
from .ops_insights import router as ops_insights_router

router = APIRouter(
    prefix="/config/channels/wecom_tenant",
    tags=["wecom-tenant-config"],
)

router.include_router(feature_config_router)
router.include_router(monitoring_router)
router.include_router(operations_router)
router.include_router(ops_insights_router)

__all__ = ["router"]
