# -*- coding: utf-8 -*-
from qwenpaw.tenancy.workspace_provisioner import WorkspaceProvisioner


def test_ensure_creates_wx_workspace_and_agent_json(tmp_path):
    template_dir = tmp_path / "_template"
    template_dir.mkdir()
    (template_dir / "SOUL.md").write_text(
        "hello {{USER_ID}}",
        encoding="utf-8",
    )

    provisioner = WorkspaceProvisioner(
        working_dir=tmp_path,
        template_dir=template_dir,
    )

    workspace_dir = provisioner.ensure("alice")

    assert workspace_dir == tmp_path / "tenants" / "wx_alice"
    assert (workspace_dir / "agent.json").is_file()
    assert "alice" in (workspace_dir / "SOUL.md").read_text(
        encoding="utf-8",
    )


def test_ensure_hashes_unsafe_tenant_id(tmp_path):
    provisioner = WorkspaceProvisioner(
        working_dir=tmp_path,
        template_dir=tmp_path / "_missing_template",
    )

    workspace_dir = provisioner.ensure("../alice")

    assert workspace_dir.parent == tmp_path / "tenants"
    assert workspace_dir.name.startswith("wx_")
    assert ".." not in workspace_dir.name


def test_ensure_existing_workspace_backfills_agent_json(tmp_path):
    workspace_dir = tmp_path / "tenants" / "wx_alice"
    workspace_dir.mkdir(parents=True)

    provisioner = WorkspaceProvisioner(
        working_dir=tmp_path,
        template_dir=tmp_path / "_missing_template",
    )

    assert provisioner.ensure("alice") == workspace_dir
    assert (workspace_dir / "agent.json").is_file()
