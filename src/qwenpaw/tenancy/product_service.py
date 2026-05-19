# -*- coding: utf-8 -*-
"""Service helpers for product-domain tenant overlay data."""
from __future__ import annotations

from .product_models import (
    TenantPolicy,
    TenantRecord,
    TenantSource,
)
from .product_store import TenantProductStore


def ensure_tenant_record(
    store: TenantProductStore,
    *,
    tenant_id: str,
    agent_id: str,
    display_name: str,
    source: TenantSource,
    policy_id: str = "default",
    template_id: str = "default",
) -> TenantRecord:
    tenant = store.get_tenant(tenant_id)
    if tenant is not None:
        updated = tenant.model_copy(
            update={
                "display_name": display_name or tenant.display_name,
                "agent_id": agent_id,
                "source": source,
            },
        )
        return store.upsert_tenant(updated)

    created = TenantRecord(
        tenant_id=tenant_id,
        display_name=display_name,
        agent_id=agent_id,
        source=source,
        policy_id=policy_id,
        template_id=template_id,
    )
    return store.upsert_tenant(created)


def resolve_tenant_policy(
    store: TenantProductStore,
    tenant: TenantRecord,
) -> TenantPolicy:
    return (
        store.get_policy(tenant.policy_id)
        or store.get_policy("default")
        or TenantPolicy()
    )
