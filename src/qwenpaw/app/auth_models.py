from __future__ import annotations

from pydantic import BaseModel, Field


class AuthUserRecord(BaseModel):
    username: str
    password_hash: str
    roles: tuple[str, ...] = ("tenant_operator",)
    tenant_id: str = ""
    disabled: bool = False


class AuthFileV2(BaseModel):
    version: int = 2
    users: dict[str, AuthUserRecord] = Field(default_factory=dict)
    jwt_secret: str = ""
    revoked_tokens_meta: dict[str, int] = Field(default_factory=dict)
