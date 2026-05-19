import zipfile

import pytest
from httpx import ASGITransport, AsyncClient

from qwenpaw.app.routers.backup import router
from qwenpaw.enterprise.audit.models import AuditEventType, AuditOutcome


class CaptureBus:
    def __init__(self):
        self.events = []

    async def emit(self, event):
        self.events.append(event)


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    """创建测试用异步客户端，挂载 backup router，BACKUP_DIR 指向临时目录。"""
    from fastapi import FastAPI

    import qwenpaw.app.routers.backup as backup_mod
    import qwenpaw.backup._utils.constants as constants_mod

    monkeypatch.setattr(backup_mod, "BACKUP_DIR", tmp_path)
    monkeypatch.setattr(constants_mod, "BACKUP_DIR", tmp_path)
    app = FastAPI()
    app.include_router(router, prefix="/api")
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def audited_api_client(tmp_path, monkeypatch):
    """创建带审计捕获的 backup router 客户端。"""
    from fastapi import FastAPI

    import qwenpaw.app.routers.backup as backup_mod
    import qwenpaw.backup._utils.constants as constants_mod

    monkeypatch.setattr(backup_mod, "BACKUP_DIR", tmp_path)
    monkeypatch.setattr(constants_mod, "BACKUP_DIR", tmp_path)

    bus = CaptureBus()
    runtime = type("Runtime", (), {"audit": bus})()
    app = FastAPI()
    app.state.enterprise_runtime = runtime
    app.include_router(router, prefix="/api")
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test"), bus, tmp_path


@pytest.mark.asyncio
async def test_backup_production_policy_endpoint(api_client):
    async with api_client:
        response = await api_client.get("/api/backups/production/policy")
    assert response.status_code == 200
    data = response.json()
    assert "schedule" in data
    assert "retention_days" in data
    assert "integrity" in data


@pytest.mark.asyncio
async def test_backup_manifest_verify_endpoint(tmp_path, api_client):
    from qwenpaw.backup.production.manifest import build_manifest

    backup = tmp_path / "test.zip"
    backup.write_bytes(b"test-data")
    manifest = build_manifest(backup)

    async with api_client:
        response = await api_client.post(
            "/api/backups/production/manifest/verify",
            json=manifest.model_dump(),
        )
    assert response.status_code == 200
    assert response.json()["valid"] is True


@pytest.mark.asyncio
async def test_backup_manifest_verify_rejects_tampered(tmp_path, api_client):
    from qwenpaw.backup.production.manifest import build_manifest

    backup = tmp_path / "test.zip"
    backup.write_bytes(b"original")
    manifest = build_manifest(backup)
    backup.write_bytes(b"tampered")

    async with api_client:
        response = await api_client.post(
            "/api/backups/production/manifest/verify",
            json=manifest.model_dump(),
        )
    assert response.status_code == 200
    assert response.json()["valid"] is False


@pytest.mark.asyncio
async def test_backup_manifest_verify_rejects_path_traversal(api_client):
    async with api_client:
        # ../ 穿越
        r1 = await api_client.post(
            "/api/backups/production/manifest/verify",
            json={
                "filename": "../outside.zip",
                "size_bytes": 0,
                "sha256": "abc",
                "created_at": "2026-01-01T00:00:00Z",
            },
        )
        # 绝对路径
        r2 = await api_client.post(
            "/api/backups/production/manifest/verify",
            json={
                "filename": "/etc/passwd",
                "size_bytes": 0,
                "sha256": "abc",
                "created_at": "2026-01-01T00:00:00Z",
            },
        )
        # 子目录路径
        r3 = await api_client.post(
            "/api/backups/production/manifest/verify",
            json={
                "filename": "sub/file.zip",
                "size_bytes": 0,
                "sha256": "abc",
                "created_at": "2026-01-01T00:00:00Z",
            },
        )
    assert r1.status_code == 400
    assert r2.status_code == 400
    assert r3.status_code == 400


@pytest.mark.asyncio
async def test_backup_drill_endpoint(tmp_path, api_client):
    backup = tmp_path / "drill-test.zip"
    with zipfile.ZipFile(backup, "w") as archive:
        archive.writestr("test.txt", "hello")

    async with api_client:
        response = await api_client.post(
            "/api/backups/production/drill",
            json={"backup_id": "drill-test"},
        )
    assert response.status_code == 200
    result = response.json()
    assert result["ok"] is True
    assert "_restore_drills" in result["sandbox_dir"]


@pytest.mark.asyncio
async def test_backup_drill_emits_audit_event(audited_api_client):
    api_client, bus, backup_dir = audited_api_client
    backup = backup_dir / "drill-audit.zip"
    with zipfile.ZipFile(backup, "w") as archive:
        archive.writestr("test.txt", "hello")

    async with api_client:
        response = await api_client.post(
            "/api/backups/production/drill",
            json={"backup_id": "drill-audit"},
        )

    assert response.status_code == 200
    assert len(bus.events) == 1
    event = bus.events[0]
    assert event.event_type == AuditEventType.BACKUP_OPERATION
    assert event.action == "drill"
    assert event.outcome == AuditOutcome.SUCCESS
    assert event.resource_id == "drill-audit"


@pytest.mark.asyncio
async def test_backup_drill_rejects_invalid_backup_id(api_client):
    async with api_client:
        response = await api_client.post(
            "/api/backups/production/drill",
            json={"backup_id": "../etc/passwd"},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_backup_drill_rejects_missing_backup(api_client):
    async with api_client:
        response = await api_client.post(
            "/api/backups/production/drill",
            json={"backup_id": "nonexistent"},
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_backup_delete_requires_confirmation_and_emits_denied_audit(
    audited_api_client,
):
    api_client, bus, _ = audited_api_client

    async with api_client:
        response = await api_client.post(
            "/api/backups/delete",
            json={"ids": ["backup-a"]},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "confirmation required for backup delete"
    assert len(bus.events) == 1
    event = bus.events[0]
    assert event.event_type == AuditEventType.BACKUP_OPERATION
    assert event.action == "delete"
    assert event.outcome == AuditOutcome.DENIED
    assert event.resource_id == "backup-a"
    assert event.payload["reason"] == "confirmation_required"


@pytest.mark.asyncio
async def test_backup_restore_requires_confirmation_and_emits_denied_audit(
    audited_api_client,
):
    api_client, bus, _ = audited_api_client

    async with api_client:
        response = await api_client.post(
            "/api/backups/backup-a/restore",
            json={"include_agents": False, "agent_ids": []},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "confirmation required for backup restore"
    assert len(bus.events) == 1
    event = bus.events[0]
    assert event.event_type == AuditEventType.BACKUP_OPERATION
    assert event.action == "restore"
    assert event.outcome == AuditOutcome.DENIED
    assert event.resource_id == "backup-a"
    assert event.payload["reason"] == "confirmation_required"


@pytest.mark.asyncio
async def test_backup_import_missing_file_emits_failure_audit(
    audited_api_client,
):
    api_client, bus, _ = audited_api_client

    async with api_client:
        response = await api_client.post("/api/backups/import")

    assert response.status_code == 400
    assert response.json()["detail"] == "file is required"
    assert len(bus.events) == 1
    event = bus.events[0]
    assert event.event_type == AuditEventType.BACKUP_OPERATION
    assert event.action == "import"
    assert event.outcome == AuditOutcome.FAILURE
    assert event.payload["reason"] == "file_required"


@pytest.mark.asyncio
async def test_backup_import_conflict_emits_denied_audit(audited_api_client):
    api_client, bus, backup_dir = audited_api_client
    existing = backup_dir / "conflict.zip"
    with zipfile.ZipFile(existing, "w") as archive:
        archive.writestr(
            "meta.json",
            '{"id":"conflict","name":"old","created_at":"2026-05-16T00:00:00+00:00","version":"1","scope":{"include_agents":false,"include_global_config":false,"include_secrets":false,"include_skill_pool":false},"agent_count":0,"qwenpaw_version":"1","system_info":{}}',
        )

    upload = backup_dir / "upload.zip"
    with zipfile.ZipFile(upload, "w") as archive:
        archive.writestr(
            "meta.json",
            '{"id":"conflict","name":"new","created_at":"2026-05-16T00:00:00+00:00","version":"1","scope":{"include_agents":false,"include_global_config":false,"include_secrets":false,"include_skill_pool":false},"agent_count":0,"qwenpaw_version":"1","system_info":{}}',
        )

    async with api_client:
        with upload.open("rb") as fp:
            response = await api_client.post(
                "/api/backups/import",
                files={"file": ("upload.zip", fp, "application/zip")},
            )

    assert response.status_code == 409
    assert response.json()["detail"] == "backup_conflict"
    assert len(bus.events) == 1
    event = bus.events[-1]
    assert event.event_type == AuditEventType.BACKUP_OPERATION
    assert event.action == "import"
    assert event.outcome == AuditOutcome.DENIED
    assert event.payload["reason"] == "backup_conflict"


@pytest.mark.asyncio
async def test_backup_import_pending_token_overwrite_emits_success_audit(
    audited_api_client,
):
    api_client, bus, backup_dir = audited_api_client
    existing = backup_dir / "conflict.zip"
    with zipfile.ZipFile(existing, "w") as archive:
        archive.writestr(
            "meta.json",
            '{"id":"conflict","name":"old","created_at":"2026-05-16T00:00:00+00:00","version":"1","scope":{"include_agents":false,"include_global_config":false,"include_secrets":false,"include_skill_pool":false},"agent_count":0,"qwenpaw_version":"1","system_info":{}}',
        )

    upload = backup_dir / "upload.zip"
    with zipfile.ZipFile(upload, "w") as archive:
        archive.writestr(
            "meta.json",
            '{"id":"conflict","name":"new","created_at":"2026-05-16T00:00:00+00:00","version":"1","scope":{"include_agents":false,"include_global_config":false,"include_secrets":false,"include_skill_pool":false},"agent_count":0,"qwenpaw_version":"1","system_info":{}}',
        )

    async with api_client:
        with upload.open("rb") as fp:
            first = await api_client.post(
                "/api/backups/import",
                files={"file": ("upload.zip", fp, "application/zip")},
            )

        assert first.status_code == 409
        assert first.json()["detail"] == "backup_conflict"
        assert first.json()["pending_token"]
        assert bus.events[-1].outcome == AuditOutcome.DENIED
        assert bus.events[-1].payload["reason"] == "backup_conflict"

        pending_token = first.json()["pending_token"]
        second = await api_client.post(
            "/api/backups/import",
            data={"pending_token": pending_token},
        )

    assert second.status_code == 200
    assert second.json()["id"] == "conflict"
    assert len(bus.events) == 2
    event = bus.events[-1]
    assert event.event_type == AuditEventType.BACKUP_OPERATION
    assert event.action == "import"
    assert event.outcome == AuditOutcome.SUCCESS
    assert event.resource_id == "conflict"
    assert event.payload["confirmed_overwrite"] is True
