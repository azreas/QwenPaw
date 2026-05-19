# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pytest

from qwenpaw.tenancy import product_store
from qwenpaw.tenancy.product_models import (
    TenantPolicy,
    TenantRecord,
    TenantTemplate,
)
from qwenpaw.tenancy.product_service import (
    ensure_tenant_record,
    resolve_tenant_policy,
)
from qwenpaw.tenancy.product_store import TenantProductStore


def test_new_store_bootstraps_default_product_data(tmp_path):
    store = TenantProductStore(tmp_path / "product-tenancy.json")

    data = store.load()

    assert data.version == 1
    assert data.policies[0].policy_id == "default"
    assert data.policies[0].allow_tasks is True
    assert data.templates[0].template_id == "default"
    assert data.templates[0].default_model is None
    assert data.templates[0].default_task_templates == []


def test_upsert_tenant_can_read_back_by_tenant_id(tmp_path):
    store = TenantProductStore(tmp_path / "product-tenancy.json")
    tenant = TenantRecord(
        tenant_id="test_user",
        display_name="测试员工",
        agent_id="wx_test_user",
        status="active",
        source="manual",
        policy_id="default",
        template_id="default",
    )

    store.upsert_tenant(tenant)

    saved = store.get_tenant("test_user")
    assert saved is not None
    assert saved.agent_id == "wx_test_user"
    assert saved.display_name == "测试员工"


def test_upsert_tenant_refreshes_updated_at_and_preserves_created_at(
    tmp_path,
    monkeypatch,
):
    store = TenantProductStore(tmp_path / "product-tenancy.json")
    store.upsert_tenant(
        TenantRecord(
            tenant_id="test_user",
            display_name="旧名称",
            agent_id="wx_test_user",
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        ),
    )
    monkeypatch.setattr(
        product_store,
        "utc_now_iso",
        lambda: "2026-02-01T00:00:00+00:00",
        raising=False,
    )

    store.upsert_tenant(
        TenantRecord(
            tenant_id="test_user",
            display_name="新名称",
            agent_id="wx_test_user_v2",
            created_at="2026-03-01T00:00:00+00:00",
            updated_at="2026-03-01T00:00:00+00:00",
        ),
    )

    saved = store.get_tenant("test_user")
    assert saved is not None
    assert saved.created_at == "2026-01-01T00:00:00+00:00"
    assert saved.updated_at == "2026-02-01T00:00:00+00:00"
    assert saved.display_name == "新名称"


def test_upsert_policy_round_trips_overrides(tmp_path):
    store = TenantProductStore(tmp_path / "product-tenancy.json")
    policy = TenantPolicy(
        policy_id="restricted",
        allow_skill_upload_zip=False,
        allow_tasks=False,
        max_cron_jobs=3,
    )

    store.upsert_policy(policy)

    saved = store.get_policy("restricted")
    assert saved is not None
    assert saved.policy_id == "restricted"
    assert saved.allow_skill_upload_zip is False
    assert saved.allow_tasks is False
    assert saved.max_cron_jobs == 3


def test_delete_policy_removes_existing_policy(tmp_path):
    store = TenantProductStore(tmp_path / "product-tenancy.json")
    store.upsert_policy(TenantPolicy(policy_id="restricted"))

    assert store.delete_policy("restricted") is True

    assert store.get_policy("restricted") is None
    assert store.delete_policy("missing") is False


def test_upsert_template_round_trips_defaults(tmp_path):
    store = TenantProductStore(tmp_path / "product-tenancy.json")
    template = TenantTemplate(
        template_id="member",
        display_name="成员模板",
        default_model="gpt-4o-mini",
        default_prompt_files=["persona.md"],
        default_skills=["weather"],
        default_tools=["search"],
        default_task_templates=[{"name": "日报"}],
    )

    store.upsert_template(template)

    saved = store.get_template("member")
    assert saved is not None
    assert saved.display_name == "成员模板"
    assert saved.default_model == "gpt-4o-mini"
    assert saved.default_prompt_files == ["persona.md"]
    assert saved.default_skills == ["weather"]
    assert saved.default_tools == ["search"]
    assert saved.default_task_templates == [{"name": "日报"}]


def test_delete_template_removes_existing_template(tmp_path):
    store = TenantProductStore(tmp_path / "product-tenancy.json")
    store.upsert_template(TenantTemplate(template_id="member"))

    assert store.delete_template("member") is True

    assert store.get_template("member") is None
    assert store.delete_template("missing") is False


def test_upsert_tenant_and_policy_preserve_existing_data(tmp_path):
    store = TenantProductStore(tmp_path / "product-tenancy.json")

    store.upsert_tenant(
        TenantRecord(
            tenant_id="test_user",
            display_name="测试员工",
            agent_id="wx_test_user",
        ),
    )
    store.upsert_policy(TenantPolicy(policy_id="restricted", allow_tasks=False))

    assert store.get_tenant("test_user") is not None
    saved_policy = store.get_policy("restricted")
    assert saved_policy is not None
    assert saved_policy.allow_tasks is False


def test_store_save_uses_atomic_replace(tmp_path, monkeypatch):
    store_path = tmp_path / "product-tenancy.json"
    store = TenantProductStore(store_path)
    original_replace = Path.replace
    replace_calls = []

    def track_replace(self, target):
        replace_calls.append((self, Path(target)))
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", track_replace)

    store.save(store.load())

    assert len(replace_calls) == 1
    tmp_path_used, target_path = replace_calls[0]
    assert tmp_path_used.parent == store_path.parent
    assert tmp_path_used != store_path
    assert target_path == store_path
    assert tmp_path_used.exists() is False
    assert store_path.exists()


def test_store_save_cleans_tmp_file_when_replace_fails(tmp_path, monkeypatch):
    store_path = tmp_path / "product-tenancy.json"
    store = TenantProductStore(store_path)

    def fail_replace(self, target):
        raise OSError("replace failed")

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        store.save(store.load())

    assert list(tmp_path.glob("*.tmp")) == []


def test_ensure_tenant_record_resolves_custom_tenant_policy(tmp_path):
    store = TenantProductStore(tmp_path / "product-tenancy.json")
    store.upsert_policy(TenantPolicy(policy_id="member-safe", allow_mcp=False))

    tenant = ensure_tenant_record(
        store,
        tenant_id="test_user",
        agent_id="wx_test_user",
        display_name="测试员工",
        source="wecom",
        policy_id="member-safe",
    )
    policy = resolve_tenant_policy(store, tenant)

    assert tenant.policy_id == "member-safe"
    assert policy.policy_id == "member-safe"
    assert policy.allow_mcp is False


def test_ensure_tenant_record_preserves_existing_policy_and_template(tmp_path):
    store = TenantProductStore(tmp_path / "product-tenancy.json")
    store.upsert_tenant(
        TenantRecord(
            tenant_id="test_user",
            display_name="旧名称",
            agent_id="wx_test_user",
            source="manual",
            policy_id="member-safe",
            template_id="member-template",
        ),
    )

    tenant = ensure_tenant_record(
        store,
        tenant_id="test_user",
        agent_id="wx_test_user_v2",
        display_name="",
        source="wecom",
        policy_id="default",
        template_id="default",
    )

    assert tenant.display_name == "旧名称"
    assert tenant.agent_id == "wx_test_user_v2"
    assert tenant.source == "wecom"
    assert tenant.policy_id == "member-safe"
    assert tenant.template_id == "member-template"
