# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from qwenpaw.app.routers.webchat import router
from qwenpaw.app.webchat.session import WebchatIdentity, sign_webchat_token

TEST_AGENT_ID = "wx_test_user"


class FakeManager:
    async def get_or_create_tenant_agent(self, agent_id: str, workspace_dir):
        return SimpleNamespace(
            agent_id=agent_id,
            workspace_dir=workspace_dir,
            runner=SimpleNamespace(),
            chat_manager=SimpleNamespace(),
            task_tracker=SimpleNamespace(),
        )


def make_token() -> str:
    identity = WebchatIdentity(
        employee_id="E000001",
        username="测试员工",
        wechat_company_id="test_user",
        tenant_id="test_user",
        agent_id=TEST_AGENT_ID,
    )
    return sign_webchat_token(identity, secret="test-secret", ttl_seconds=60)


def make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / TEST_AGENT_ID
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "AGENTS.md").write_text("# Agent")
    (ws / "agent.json").write_text("{}")
    (ws / "media").mkdir(exist_ok=True)
    (ws / "media" / "test.png").write_text("fake png")
    return ws


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "qwenpaw.app.webchat.session.get_webchat_session_secret",
        lambda: "test-secret",
    )
    ws = make_workspace(tmp_path)

    async def fake_workspace(request, identity):
        return SimpleNamespace(
            agent_id=identity.agent_id,
            workspace_dir=ws,
            runner=SimpleNamespace(),
            chat_manager=SimpleNamespace(),
            task_tracker=SimpleNamespace(),
        )

    monkeypatch.setattr(
        "qwenpaw.app.routers.webchat.get_tenant_workspace_for_identity",
        fake_workspace,
    )

    app = FastAPI()
    app.state.multi_agent_manager = FakeManager()
    app.state.test_workspace_dir = ws
    app.include_router(router, prefix="/api")
    return app


@pytest.fixture
def client(app):
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_list_root_directory(client):
    token = make_token()
    async with client:
        resp = await client.get(
            "/api/webchat/agent/workspace/files",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["path"] == ""
    names = {e["name"] for e in body["entries"]}
    assert "AGENTS.md" in names
    assert "media" in names
    agents_entry = next(e for e in body["entries"] if e["name"] == "AGENTS.md")
    assert agents_entry["deletable"] is False
    media_entry = next(e for e in body["entries"] if e["name"] == "media")
    assert media_entry["type"] == "dir"


@pytest.mark.asyncio
async def test_list_media_subdirectory(client):
    token = make_token()
    async with client:
        resp = await client.get(
            "/api/webchat/agent/workspace/files?path=media",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["path"] == "media"
    names = {e["name"] for e in body["entries"]}
    assert "test.png" in names
    png_entry = next(e for e in body["entries"] if e["name"] == "test.png")
    assert png_entry["deletable"] is True
    assert png_entry["type"] == "file"


@pytest.mark.asyncio
async def test_delete_media_file_succeeds(client):
    token = make_token()
    async with client:
        resp = await client.delete(
            "/api/webchat/agent/workspace/files?path=media/test.png",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_delete_protected_file_rejected(client):
    token = make_token()
    async with client:
        resp = await client.delete(
            "/api/webchat/agent/workspace/files?path=AGENTS.md",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 400
    assert "不能删除" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_path_traversal_rejected(client):
    token = make_token()
    async with client:
        resp = await client.get(
            "/api/webchat/agent/workspace/files?path=..%2F..%2Fetc",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_file_to_media(client):
    token = make_token()
    content = b"hello world"
    async with client:
        resp = await client.post(
            "/api/webchat/agent/workspace/files/upload",
            files={"file": ("data.csv", io.BytesIO(content), "text/csv")},
            params={"path": "media"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "data.csv"
    assert body["path"] == "media/data.csv"


@pytest.mark.asyncio
async def test_download_binary_file(client):
    """二进制文件下载返回原始字节，非 JSON。"""
    token = make_token()
    async with client:
        resp = await client.get(
            "/api/webchat/agent/workspace/files/download?path=media/test.png",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/octet-stream"
    assert resp.content == b"fake png"


@pytest.mark.asyncio
async def test_download_protected_file_not_restricted(client):
    """受保护文件也可以下载（下载不等于删除）。"""
    token = make_token()
    async with client:
        resp = await client.get(
            "/api/webchat/agent/workspace/files/download?path=AGENTS.md",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    assert b"# Agent" in resp.content


@pytest.mark.asyncio
async def test_download_path_traversal_rejected(client):
    token = make_token()
    async with client:
        resp = await client.get(
            "/api/webchat/agent/workspace/files/download?path=..%2F..%2Fetc%2Fpasswd",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_download_workspace_uses_webchat_tenant_workspace(client):
    token = make_token()
    async with client:
        resp = await client.get(
            "/api/webchat/agent/workspace/download",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert f"qwenpaw_workspace_{TEST_AGENT_ID}_" in resp.headers["content-disposition"]

    with zipfile.ZipFile(io.BytesIO(resp.content)) as archive:
        names = set(archive.namelist())
        assert "AGENTS.md" in names
        assert "media/test.png" in names
        assert archive.read("AGENTS.md") == b"# Agent"


@pytest.mark.asyncio
async def test_upload_workspace_zip_merges_into_webchat_tenant_workspace(client, app):
    token = make_token()
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("media/imported.txt", "tenant data")
        archive.writestr("notes.txt", "tenant note")
    payload.seek(0)

    async with client:
        resp = await client.post(
            "/api/webchat/agent/workspace/upload",
            files={"file": ("workspace.zip", payload, "application/zip")},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    assert resp.json() == {"success": True}
    imported = app.state.test_workspace_dir / "media" / "imported.txt"
    assert imported.read_text(encoding="utf-8") == "tenant data"
    assert (app.state.test_workspace_dir / "notes.txt").read_text(
        encoding="utf-8",
    ) == "tenant note"


@pytest.mark.asyncio
async def test_requires_token(client):
    async with client:
        resp = await client.get("/api/webchat/agent/workspace/files")
    assert resp.status_code == 401
