# -*- coding: utf-8 -*-
"""Authentication API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...constant import EnvVarLoader
from ...enterprise.audit.emit import emit_audit_event
from ...enterprise.audit.models import AuditEventType, AuditOutcome
from ...enterprise.authz.deps import get_request_context
from ...enterprise.authz.models import DEFAULT_ROLES
from ..auth import (
    authenticate,
    create_user,
    has_registered_users,
    is_auth_enabled,
    list_users,
    register_user,
    revoke_all_tokens,
    revoke_token,
    update_credentials,
    update_user,
    verify_token,
    verify_token_with_claims,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=8192)
    expires_in: int | None = None


class LoginResponse(BaseModel):
    token: str
    username: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=8192)
    expires_in: int | None = None


class AuthStatusResponse(BaseModel):
    enabled: bool
    has_users: bool


@router.post("/login")
async def login(req: LoginRequest, request: Request):
    """Authenticate with username and password.

    Optional `expires_in` field:
    - Positive integer: token expires in N seconds
    - 0 or -1: permanent token (100 years)
    - None/omitted: default 7 days
    """
    if not is_auth_enabled():
        return LoginResponse(token="", username="")

    token = authenticate(req.username, req.password, req.expires_in)
    if token is None:
        await emit_audit_event(
            request,
            event_type=AuditEventType.AUTH_LOGIN_FAILED,
            action="login",
            outcome=AuditOutcome.FAILURE,
            resource_type="auth",
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    await emit_audit_event(
        request,
        event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
        action="login",
        outcome=AuditOutcome.SUCCESS,
        resource_type="auth",
    )
    return LoginResponse(token=token, username=req.username)


@router.post("/register")
async def register(req: RegisterRequest, request: Request):
    """Register the single user account (only allowed once).

    Optional `expires_in` field:
    - Positive integer: token expires in N seconds
    - 0 or -1: permanent token (100 years)
    - None/omitted: default 7 days
    """
    env_flag = EnvVarLoader.get_str("QWENPAW_AUTH_ENABLED", "").strip().lower()
    if env_flag not in ("true", "1", "yes"):
        raise HTTPException(
            status_code=403,
            detail="Authentication is not enabled",
        )

    if has_registered_users():
        raise HTTPException(
            status_code=403,
            detail="User already registered",
        )

    if not req.username.strip() or not req.password.strip():
        raise HTTPException(
            status_code=400,
            detail="Username and password are required",
        )

    token = register_user(req.username.strip(), req.password, req.expires_in)
    if token is None:
        raise HTTPException(
            status_code=409,
            detail="Registration failed",
        )

    await emit_audit_event(
        request,
        event_type=AuditEventType.AUTH_REGISTER,
        action="register",
        outcome=AuditOutcome.SUCCESS,
        resource_type="auth",
    )
    return LoginResponse(token=token, username=req.username.strip())


@router.get("/status")
async def auth_status():
    """Check if authentication is enabled and whether a user exists."""
    return AuthStatusResponse(
        enabled=is_auth_enabled(),
        has_users=has_registered_users(),
    )


@router.get("/verify")
async def verify(request: Request):
    """Verify that the caller's Bearer token is still valid."""
    if not is_auth_enabled():
        return {"valid": True, "username": ""}

    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")

    token_result = verify_token_with_claims(token)
    if token_result is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    username, roles = token_result
    return {"valid": True, "username": username, "roles": list(roles)}


class UpdateProfileRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=8192)
    new_username: str | None = Field(min_length=1, max_length=128, default=None)
    new_password: str | None = Field(min_length=1, max_length=8192, default=None)
    expires_in: int | None = None


@router.post("/update-profile")
async def update_profile(req: UpdateProfileRequest, request: Request):
    """Update username and/or password for the authenticated user."""
    if not is_auth_enabled():
        raise HTTPException(
            status_code=403,
            detail="Authentication is not enabled",
        )

    if not has_registered_users():
        raise HTTPException(
            status_code=403,
            detail="No user registered",
        )

    # Verify caller is authenticated
    auth_header = request.headers.get("Authorization", "")
    caller_token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    token_result = verify_token_with_claims(caller_token)
    if not caller_token or token_result is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    current_username, _ = token_result

    if not req.new_username and not req.new_password:
        raise HTTPException(
            status_code=400,
            detail="Nothing to update",
        )

    if req.new_username is not None and not req.new_username.strip():
        raise HTTPException(
            status_code=400,
            detail="Username cannot be empty",
        )

    if req.new_password is not None and not req.new_password.strip():
        raise HTTPException(
            status_code=400,
            detail="Password cannot be empty",
        )

    token = update_credentials(
        username=current_username,
        current_password=req.current_password,
        new_username=req.new_username,
        new_password=req.new_password,
        expiry_seconds=req.expires_in,
    )
    if token is None:
        raise HTTPException(
            status_code=401,
            detail="Current password is incorrect",
        )

    username = req.new_username.strip() if req.new_username else ""
    return LoginResponse(token=token, username=username)


class RevokeTokenRequest(BaseModel):
    token: str | None = (
        None  # Optional: revoke specific token, or current if omitted
    )


@router.post("/revoke-token")
async def revoke_single_token(req: RevokeTokenRequest, request: Request):
    """Revoke a single token by adding it to the blacklist.

    If `token` is provided in the request body, revokes that token.
    If `token` is omitted, revokes the token used for authentication
    (current token).

    This allows you to:
    - Revoke a leaked token from another device
    - Logout from the current session
    """
    if not is_auth_enabled():
        raise HTTPException(
            status_code=403,
            detail="Authentication is not enabled",
        )

    # Get current token for authentication
    auth_header = request.headers.get("Authorization", "")
    caller_token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if not caller_token or verify_token(caller_token) is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Determine which token to revoke
    token_to_revoke = req.token if req.token else caller_token
    is_current_token = token_to_revoke == caller_token

    success = revoke_token(token_to_revoke)
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to revoke token",
        )

    message = (
        "Current token has been revoked. Please login again."
        if is_current_token
        else "Specified token has been revoked."
    )

    await emit_audit_event(
        request,
        event_type=AuditEventType.AUTH_TOKEN_REVOKED,
        action="revoke_token",
        outcome=AuditOutcome.SUCCESS,
        resource_type="auth",
    )
    return {
        "message": message,
        "revoked": True,
        "revoked_current_token": is_current_token,
    }


@router.post("/revoke-all-tokens")
async def revoke_all_sessions(request: Request):
    """Revoke all existing tokens by rotating the JWT secret.

    This endpoint requires authentication. After calling this endpoint,
    all previously issued tokens will be invalidated, and you will need
    to login again to get a new token.

    This is more efficient than revoking tokens individually when you
    want to invalidate all sessions (e.g., password reset, security incident).
    """
    if not is_auth_enabled():
        raise HTTPException(
            status_code=403,
            detail="Authentication is not enabled",
        )

    # Verify caller is authenticated
    auth_header = request.headers.get("Authorization", "")
    caller_token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if not caller_token or verify_token(caller_token) is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    success = revoke_all_tokens()
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to revoke tokens",
        )

    await emit_audit_event(
        request,
        event_type=AuditEventType.AUTH_TOKEN_REVOKED,
        action="revoke_all_tokens",
        outcome=AuditOutcome.SUCCESS,
        resource_type="auth",
    )
    return {
        "message": "All tokens have been revoked. Please login again.",
        "revoked": True,
    }


# ── P3-4: Console 用户管理 API ─────────────────────────────


class UserItemResponse(BaseModel):
    username: str
    roles: list[str] = Field(default_factory=list)
    tenant_id: str = ""
    disabled: bool = False


class UserListResponse(BaseModel):
    items: list[UserItemResponse] = Field(default_factory=list)


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=8192)
    roles: list[str] = Field(default_factory=lambda: ["tenant_member"])
    tenant_id: str = ""


class UpdateUserRequest(BaseModel):
    roles: list[str] | None = None
    tenant_id: str | None = None
    disabled: bool | None = None


_TENANT_ADMIN_MANAGED_ROLES = {"tenant_admin", "tenant_readonly"}


def _normalize_roles(roles: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(
        dict.fromkeys(str(role).strip() for role in roles if str(role).strip()),
    )
    if not normalized:
        raise HTTPException(status_code=400, detail="At least one role is required")
    unknown = [role for role in normalized if role not in DEFAULT_ROLES]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown role: {', '.join(unknown)}",
        )
    return normalized


def _require_user_manager(request: Request):
    ctx = get_request_context(request)
    if "platform_admin" in ctx.roles:
        return ctx
    if "tenant_admin" in ctx.roles and ctx.tenant_id:
        return ctx
    raise HTTPException(
        status_code=403,
        detail="Only platform administrators or tenant administrators can manage users",
    )


def _assert_tenant_admin_scope(
    *,
    ctx,
    roles: tuple[str, ...] | None = None,
    tenant_id: str | None = None,
    existing: dict | None = None,
) -> str:
    target_tenant_id = (tenant_id or ctx.tenant_id or "").strip()
    if target_tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant boundary denied")
    if existing is not None:
        if existing.get("tenant_id") != ctx.tenant_id:
            raise HTTPException(status_code=403, detail="Tenant boundary denied")
        existing_roles = set(existing.get("roles") or [])
        if "platform_admin" in existing_roles:
            raise HTTPException(
                status_code=403,
                detail="Cannot manage platform administrators",
            )
    if (
        roles is not None
        and not set(roles).issubset(_TENANT_ADMIN_MANAGED_ROLES)
    ):
        raise HTTPException(
            status_code=403,
            detail="Tenant administrators can only grant tenant_admin or tenant_readonly",
        )
    return target_tenant_id


@router.get("/users", response_model=UserListResponse)
async def get_users(request: Request):
    """列出 Console 用户。需要 auth_users:read 权限。"""
    ctx = _require_user_manager(request)
    users = list_users()
    if "platform_admin" not in ctx.roles:
        users = [
            user for user in users
            if user.get("tenant_id") == ctx.tenant_id
            and "platform_admin" not in set(user.get("roles") or [])
        ]
    return UserListResponse(
        items=[UserItemResponse(**u) for u in users],
    )


@router.post("/users", response_model=UserItemResponse, status_code=201)
async def create_new_user(req: CreateUserRequest, request: Request):
    """创建新用户。需要 auth_users:write 权限。

    权限规则：只有 platform_admin 可创建/修改 platform_admin；
    不能创建与已有用户同名的用户。
    """
    ctx = _require_user_manager(request)
    if not is_auth_enabled():
        raise HTTPException(status_code=403, detail="Authentication is not enabled")

    roles_tuple = _normalize_roles(req.roles or ["tenant_member"])
    tenant_id = req.tenant_id.strip()
    if "platform_admin" not in ctx.roles:
        tenant_id = _assert_tenant_admin_scope(
            ctx=ctx,
            roles=roles_tuple,
            tenant_id=tenant_id or ctx.tenant_id,
        )

    result = create_user(
        req.username.strip(),
        req.password,
        roles=roles_tuple,
        tenant_id=tenant_id,
    )
    if result is None:
        raise HTTPException(status_code=409, detail="User already exists")

    await emit_audit_event(
        request,
        AuditEventType.AUTH_USER_CREATED,
        action="create_user",
        outcome=AuditOutcome.SUCCESS,
        resource_type="auth",
        resource_id=req.username,
        payload={"roles": list(roles_tuple), "tenant_id": tenant_id},
    )
    return UserItemResponse(**result)


@router.patch("/users/{username}", response_model=UserItemResponse)
async def patch_user(username: str, req: UpdateUserRequest, request: Request):
    """更新用户角色、租户绑定或禁用状态。需要 auth_users:write 权限。"""
    ctx = _require_user_manager(request)
    if not is_auth_enabled():
        raise HTTPException(status_code=403, detail="Authentication is not enabled")

    existing = next((user for user in list_users() if user["username"] == username), None)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")

    updates: dict = {}
    if req.roles is not None:
        updates["roles"] = _normalize_roles(req.roles)
    if req.tenant_id is not None:
        updates["tenant_id"] = req.tenant_id.strip()
    if req.disabled is not None:
        updates["disabled"] = req.disabled

    if "platform_admin" not in ctx.roles:
        target_tenant_id = _assert_tenant_admin_scope(
            ctx=ctx,
            roles=updates.get("roles"),
            tenant_id=updates.get("tenant_id") or existing.get("tenant_id"),
            existing=existing,
        )
        updates["tenant_id"] = target_tenant_id

    result = update_user(username, **updates)
    if result is None:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")

    audit_updates = {
        key: list(value) if isinstance(value, tuple) else value
        for key, value in updates.items()
    }
    await emit_audit_event(
        request,
        AuditEventType.AUTH_USER_UPDATED,
        action="update_user",
        outcome=AuditOutcome.SUCCESS,
        resource_type="auth",
        resource_id=username,
        payload=audit_updates,
    )
    return UserItemResponse(**result)
