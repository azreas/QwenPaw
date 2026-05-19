# -*- coding: utf-8 -*-
"""File-backed JSON store for product-domain tenant overlay data."""
from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock, RLock

from qwenpaw.constant import WORKING_DIR

from .product_models import (
    TenantPolicy,
    TenantProductData,
    TenantRecord,
    TenantTemplate,
    utc_now_iso,
)


_STORE_LOCKS: dict[Path, RLock] = {}
_STORE_LOCKS_GUARD = Lock()


def _normalized_store_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _lock_for_path(path: str | Path) -> RLock:
    normalized_path = _normalized_store_path(path)
    with _STORE_LOCKS_GUARD:
        lock = _STORE_LOCKS.get(normalized_path)
        if lock is None:
            lock = RLock()
            _STORE_LOCKS[normalized_path] = lock
        return lock


def default_product_store_path() -> Path:
    configured = os.environ.get("QWENPAW_TENANT_PRODUCT_STORE")
    if configured:
        return Path(configured).expanduser()

    return Path(WORKING_DIR).expanduser() / "tenants" / "product-tenancy.json"


class TenantProductStore:
    def __init__(self, path: str | Path | None = None):
        self.path = (
            Path(path).expanduser()
            if path is not None
            else default_product_store_path()
        )

    def load(self) -> TenantProductData:
        if not self.path.exists():
            return TenantProductData()

        with self.path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        return TenantProductData.model_validate(payload)

    def save(self, data: TenantProductData) -> None:
        with _lock_for_path(self.path):
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.path.with_name(
                f"{self.path.name}.{os.getpid()}.tmp",
            )
            try:
                payload = data.model_dump(mode="json")
                content = json.dumps(payload, ensure_ascii=False, indent=2)
                with tmp_path.open("w", encoding="utf-8") as file:
                    file.write(content)
                    file.flush()
                    os.fsync(file.fileno())
                tmp_path.replace(self.path)
            except Exception:
                try:
                    tmp_path.unlink()
                except FileNotFoundError:
                    pass
                raise

    def get_tenant(self, tenant_id: str) -> TenantRecord | None:
        return next(
            (
                tenant
                for tenant in self.load().tenants
                if tenant.tenant_id == tenant_id
            ),
            None,
        )

    def upsert_tenant(self, tenant: TenantRecord) -> TenantRecord:
        with _lock_for_path(self.path):
            data = self.load()
            now = utc_now_iso()
            stored_tenant = tenant.model_copy(update={"updated_at": now})
            for index, existing in enumerate(data.tenants):
                if existing.tenant_id == tenant.tenant_id:
                    stored_tenant = tenant.model_copy(
                        update={
                            "created_at": existing.created_at,
                            "updated_at": now,
                        },
                    )
                    data.tenants[index] = stored_tenant
                    break
            else:
                data.tenants.append(stored_tenant)
            self.save(data)
            return stored_tenant

    def list_tenants(self) -> list[TenantRecord]:
        return list(self.load().tenants)

    def get_policy(self, policy_id: str) -> TenantPolicy | None:
        return next(
            (
                policy
                for policy in self.load().policies
                if policy.policy_id == policy_id
            ),
            None,
        )

    def upsert_policy(self, policy: TenantPolicy) -> TenantPolicy:
        with _lock_for_path(self.path):
            data = self.load()
            for index, existing in enumerate(data.policies):
                if existing.policy_id == policy.policy_id:
                    data.policies[index] = policy
                    break
            else:
                data.policies.append(policy)
            self.save(data)
            return policy

    def list_policies(self) -> list[TenantPolicy]:
        return list(self.load().policies)

    def delete_policy(self, policy_id: str) -> bool:
        with _lock_for_path(self.path):
            data = self.load()
            next_policies = [
                policy
                for policy in data.policies
                if policy.policy_id != policy_id
            ]
            if len(next_policies) == len(data.policies):
                return False
            data.policies = next_policies
            self.save(data)
            return True

    def get_template(self, template_id: str) -> TenantTemplate | None:
        return next(
            (
                template
                for template in self.load().templates
                if template.template_id == template_id
            ),
            None,
        )

    def upsert_template(self, template: TenantTemplate) -> TenantTemplate:
        with _lock_for_path(self.path):
            data = self.load()
            for index, existing in enumerate(data.templates):
                if existing.template_id == template.template_id:
                    data.templates[index] = template
                    break
            else:
                data.templates.append(template)
            self.save(data)
            return template

    def list_templates(self) -> list[TenantTemplate]:
        return list(self.load().templates)

    def delete_template(self, template_id: str) -> bool:
        with _lock_for_path(self.path):
            data = self.load()
            next_templates = [
                template
                for template in data.templates
                if template.template_id != template_id
            ]
            if len(next_templates) == len(data.templates):
                return False
            data.templates = next_templates
            self.save(data)
            return True
