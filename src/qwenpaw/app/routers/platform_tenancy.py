# -*- coding: utf-8 -*-
"""Platform tenancy operation APIs."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from qwenpaw.tenancy.product_models import TenantPolicy, TenantRecord, TenantTemplate
from qwenpaw.tenancy.product_store import TenantProductStore
from ...enterprise.audit.emit import emit_audit_event
from ...enterprise.audit.models import AuditEventType, AuditOutcome

router = APIRouter(prefix="/platform/tenancy", tags=["platform-tenancy"])


class TenantListResponse(BaseModel):
    tenants: list[TenantRecord]


class PolicyListResponse(BaseModel):
    policies: list[TenantPolicy]


class TemplateListResponse(BaseModel):
    templates: list[TenantTemplate]


class DeleteResponse(BaseModel):
    deleted: bool


def _ensure_policy_can_delete(
    store: TenantProductStore,
    policy_id: str,
) -> None:
    if policy_id == "default":
        raise HTTPException(
            status_code=400,
            detail="default policy cannot be deleted",
        )
    if any(tenant.policy_id == policy_id for tenant in store.list_tenants()):
        raise HTTPException(status_code=409, detail="policy is in use")


def _ensure_template_can_delete(
    store: TenantProductStore,
    template_id: str,
) -> None:
    if template_id == "default":
        raise HTTPException(
            status_code=400,
            detail="default template cannot be deleted",
        )
    if any(tenant.template_id == template_id for tenant in store.list_tenants()):
        raise HTTPException(status_code=409, detail="template is in use")


@router.get("/tenants", response_model=TenantListResponse)
async def list_tenants() -> TenantListResponse:
    return TenantListResponse(tenants=TenantProductStore().list_tenants())


@router.get("/policies", response_model=PolicyListResponse)
async def list_policies() -> PolicyListResponse:
    return PolicyListResponse(policies=TenantProductStore().list_policies())


@router.put("/policies/{policy_id}", response_model=TenantPolicy)
async def upsert_policy(
    request: Request,
    policy_id: str,
    policy: TenantPolicy,
) -> TenantPolicy:
    if policy.policy_id != policy_id:
        await emit_audit_event(
            request,
            event_type=AuditEventType.TENANT_UPDATED,
            action="upsert_policy",
            outcome=AuditOutcome.FAILURE,
            resource_type="tenant_policy",
            resource_id=policy_id,
            payload={
                "changed_key": "tenant_policy",
                "policy_id": policy_id,
                "body_policy_id": policy.policy_id,
                "reason": "policy_id_mismatch",
            },
        )
        raise HTTPException(status_code=400, detail="policy_id mismatch")
    result = TenantProductStore().upsert_policy(policy)
    await emit_audit_event(
        request,
        event_type=AuditEventType.TENANT_UPDATED,
        action="upsert_policy",
        outcome=AuditOutcome.SUCCESS,
        resource_type="tenant_policy",
        resource_id=policy_id,
        payload={"changed_key": "tenant_policy", "policy_id": policy_id},
    )
    return result


@router.delete("/policies/{policy_id}", response_model=DeleteResponse)
async def delete_policy(
    request: Request,
    policy_id: str,
) -> DeleteResponse:
    store = TenantProductStore()
    _ensure_policy_can_delete(store, policy_id)
    if not store.delete_policy(policy_id):
        raise HTTPException(status_code=404, detail="policy not found")
    await emit_audit_event(
        request,
        event_type=AuditEventType.TENANT_UPDATED,
        action="delete_policy",
        outcome=AuditOutcome.SUCCESS,
        resource_type="tenant_policy",
        resource_id=policy_id,
        payload={"changed_key": "tenant_policy", "policy_id": policy_id},
    )
    return DeleteResponse(deleted=True)


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates() -> TemplateListResponse:
    return TemplateListResponse(templates=TenantProductStore().list_templates())


@router.put("/templates/{template_id}", response_model=TenantTemplate)
async def upsert_template(
    request: Request,
    template_id: str,
    template: TenantTemplate,
) -> TenantTemplate:
    if template.template_id != template_id:
        raise HTTPException(status_code=400, detail="template_id mismatch")
    result = TenantProductStore().upsert_template(template)
    await emit_audit_event(
        request,
        event_type=AuditEventType.TENANT_UPDATED,
        action="upsert_template",
        outcome=AuditOutcome.SUCCESS,
        resource_type="tenant_template",
        resource_id=template_id,
        payload={"changed_key": "tenant_template", "template_id": template_id},
    )
    return result


@router.delete("/templates/{template_id}", response_model=DeleteResponse)
async def delete_template(
    request: Request,
    template_id: str,
) -> DeleteResponse:
    store = TenantProductStore()
    _ensure_template_can_delete(store, template_id)
    if not store.delete_template(template_id):
        raise HTTPException(status_code=404, detail="template not found")
    await emit_audit_event(
        request,
        event_type=AuditEventType.TENANT_UPDATED,
        action="delete_template",
        outcome=AuditOutcome.SUCCESS,
        resource_type="tenant_template",
        resource_id=template_id,
        payload={"changed_key": "tenant_template", "template_id": template_id},
    )
    return DeleteResponse(deleted=True)
