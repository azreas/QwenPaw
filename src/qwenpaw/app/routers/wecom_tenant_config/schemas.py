# -*- coding: utf-8 -*-
"""Shared schemas for WeCom tenant configuration routers."""
from __future__ import annotations

from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str


class OperationResult(BaseModel):
    agent_id: str
    success: bool
    error: str | None = None


class BatchOperationResponse(BaseModel):
    results: list[OperationResult]
