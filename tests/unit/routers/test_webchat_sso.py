# -*- coding: utf-8 -*-
from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from qwenpaw.app.routers.webchat import router
from qwenpaw.config.agent_config_file import (
    load_agent_config_from_workspace,
    write_agent_config_to_workspace,
)
from qwenpaw.config.config import AgentProfileConfig, ModelSlotConfig
from qwenpaw.app.webchat.session import WebchatIdentity, sign_webchat_token

TEST_USERNAME = "test.user"
TEST_FULL_NAME = "测试员工"
TEST_EMPLOYEE_ID = "E000001"
TEST_AGENT_ID = "wx_test_user"


class FakeSsoClient:
    async def authenticate(self, username: str, password: str):
        assert username == TEST_USERNAME
        assert password == "secret"
        return SimpleNamespace(
            full_name=TEST_FULL_NAME,
            employee_id=TEST_EMPLOYEE_ID,
            wechat_company_id="test_user",
            department="",
            station="",
        )


class FakeQrcodeLoginClient:
    def __init__(self, error=None):
        self.error = error

    async def authenticate(self, code: str):
        assert code == "wecom_code"
        if self.error:
            raise self.error
        return SimpleNamespace(
            full_name=TEST_FULL_NAME,
            employee_id=TEST_EMPLOYEE_ID,
            wechat_company_id="test_user",
            department="",
            station="",
        )


class FakeChatManager:
    def __init__(self):
        self.created = []

    def seed(self, chat):
        self.created.append(chat)

    async def get_or_create_chat(self, session_id, user_id, channel, name="New Chat"):
        chat = SimpleNamespace(
            id=f"chat-{len(self.created) + 1}",
            session_id=session_id,
            user_id=user_id,
            channel=channel,
            name=name,
            created_at="2026-04-28T00:00:00+00:00",
            updated_at="2026-04-28T00:00:00+00:00",
            status="idle",
            pinned=False,
            meta={},
        )
        self.created.append(chat)
        return chat

    async def list_chats(self, user_id=None, channel=None):
        chats = self.created
        if user_id is not None:
            chats = [chat for chat in chats if chat.user_id == user_id]
        if channel is not None:
            chats = [chat for chat in chats if chat.channel == channel]
        return chats

    async def get_chat(self, chat_id):
        return next((chat for chat in self.created if chat.id == chat_id), None)

    async def delete_chats(self, chat_ids):
        chat_ids = set(chat_ids)
        self.created = [chat for chat in self.created if chat.id not in chat_ids]

    async def patch_chat(self, chat_id, chat_update):
        chat = await self.get_chat(chat_id)
        if not chat:
            return None
        data = chat_update.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(chat, key, value)
        return chat


class FakeTaskTracker:
    def __init__(self):
        self.started_payloads = []

    async def attach_or_start(self, chat_id, payload, stream_fn):
        self.started_payloads.append((chat_id, payload))
        return object(), True

    async def attach(self, chat_id):
        return object()

    async def request_stop(self, chat_id):
        return False

    async def stream_from_queue(self, queue, chat_id):
        if False:
            yield ""


class FakeRunner:
    async def stream_query(self, request):
        if False:
            yield ""


class FakeManager:
    def __init__(self):
        self.workspace = SimpleNamespace(
            agent_id=TEST_AGENT_ID,
            workspace_dir=None,
            runner=FakeRunner(),
            chat_manager=FakeChatManager(),
            task_tracker=FakeTaskTracker(),
        )

    async def get_or_create_tenant_agent(self, agent_id: str, workspace_dir):
        self.workspace.agent_id = agent_id
        self.workspace.workspace_dir = workspace_dir
        return self.workspace

    async def get_agent(self, agent_id: str):
        if agent_id != self.workspace.agent_id:
            return None
        return self.workspace


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "qwenpaw.app.routers.webchat.WebchatSsoClient.from_env",
        lambda: FakeSsoClient(),
    )
    monkeypatch.setattr(
        "qwenpaw.app.webchat.session.get_webchat_session_secret",
        lambda: "test-secret",
    )
    app = FastAPI()
    fake_manager = FakeManager()
    app.state.multi_agent_manager = fake_manager
    app.state.fake_manager = fake_manager
    app.include_router(router, prefix="/api")
    return app


@pytest.fixture
def client(app):
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def make_token() -> str:
    identity = WebchatIdentity(
        employee_id=TEST_EMPLOYEE_ID,
        username=TEST_FULL_NAME,
        wechat_company_id="test_user",
        tenant_id="test_user",
        agent_id=TEST_AGENT_ID,
    )
    return sign_webchat_token(identity, secret="test-secret", ttl_seconds=60)


@pytest.mark.asyncio
async def test_login_returns_enterprise_identity(client):
    async with client:
        resp = await client.post(
            "/api/webchat/login",
            json={"username": TEST_USERNAME, "password": "secret"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["token"]
    assert body["user_id"] == "test_user"
    assert body["username"] == TEST_FULL_NAME
    assert body["agent_id"] == TEST_AGENT_ID
    assert body["employee_id"] == TEST_EMPLOYEE_ID


@pytest.mark.asyncio
async def test_qrcode_config_disabled_by_default(client, monkeypatch):
    monkeypatch.delenv("QWENPAW_WEBCHAT_QRCODE_ENABLED", raising=False)

    async with client:
        resp = await client.get("/api/webchat/qrcode/config")

    assert resp.status_code == 200
    assert resp.json() == {
        "enabled": False,
        "appid": None,
        "agentid": None,
        "redirect_uri": None,
        "state": None,
        "href": None,
    }


@pytest.mark.asyncio
async def test_qrcode_config_returns_wecom_login_config(client, monkeypatch):
    monkeypatch.setenv("QWENPAW_WEBCHAT_QRCODE_ENABLED", "true")
    monkeypatch.setenv("QWENPAW_WEBCHAT_QRCODE_APP_ID", "wx_app")
    monkeypatch.setenv("QWENPAW_WEBCHAT_QRCODE_AGENT_ID", "1000015")
    monkeypatch.setenv("QWENPAW_WEBCHAT_QRCODE_HREF", "https://wechat.example/qrcode.css")
    monkeypatch.delenv("QWENPAW_WEBCHAT_QRCODE_REDIRECT_URI", raising=False)

    async with client:
        resp = await client.get("/api/webchat/qrcode/config")

    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is True
    assert body["appid"] == "wx_app"
    assert body["agentid"] == "1000015"
    assert body["redirect_uri"] == "http://test/webchat/login"
    assert body["state"]
    assert body["href"] == "https://wechat.example/qrcode.css"


@pytest.mark.asyncio
async def test_qrcode_login_returns_enterprise_identity(client, monkeypatch):
    monkeypatch.setattr(
        "qwenpaw.app.routers.webchat.WebchatQrcodeLoginClient.from_env",
        lambda: FakeQrcodeLoginClient(),
    )
    from qwenpaw.app.webchat.session import sign_webchat_qrcode_state

    qr_state = sign_webchat_qrcode_state(secret="test-secret", ttl_seconds=60)

    async with client:
        resp = await client.post(
            "/api/webchat/login/qrcode",
            json={"code": "wecom_code", "state": qr_state},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["token"]
    assert body["user_id"] == "test_user"
    assert body["username"] == TEST_FULL_NAME
    assert body["agent_id"] == TEST_AGENT_ID
    assert body["employee_id"] == TEST_EMPLOYEE_ID


@pytest.mark.asyncio
async def test_qrcode_login_rejects_invalid_state(client, monkeypatch):
    monkeypatch.setattr(
        "qwenpaw.app.routers.webchat.WebchatQrcodeLoginClient.from_env",
        lambda: FakeQrcodeLoginClient(),
    )

    async with client:
        resp = await client.post(
            "/api/webchat/login/qrcode",
            json={"code": "wecom_code", "state": "bad-state"},
        )

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_qrcode_login_maps_upstream_error(client, monkeypatch):
    from qwenpaw.app.webchat.qrcode_login_client import WebchatQrcodeLoginError
    from qwenpaw.app.webchat.session import sign_webchat_qrcode_state

    monkeypatch.setattr(
        "qwenpaw.app.routers.webchat.WebchatQrcodeLoginClient.from_env",
        lambda: FakeQrcodeLoginClient(
            error=WebchatQrcodeLoginError(504, "登录服务响应超时"),
        ),
    )
    qr_state = sign_webchat_qrcode_state(secret="test-secret", ttl_seconds=60)

    async with client:
        resp = await client.post(
            "/api/webchat/login/qrcode",
            json={"code": "wecom_code", "state": qr_state},
        )

    assert resp.status_code == 504
    assert resp.json()["detail"] == "登录服务响应超时"


@pytest.mark.asyncio
async def test_status_reports_sso_mode(client):
    async with client:
        resp = await client.get("/api/webchat/status")

    assert resp.status_code == 200
    assert resp.json() == {"has_users": True, "auth_mode": "sso"}


@pytest.mark.asyncio
async def test_verify_and_me_return_token_identity(client):
    token = make_token()

    async with client:
        verify_resp = await client.post(
            "/api/webchat/verify",
            headers={"Authorization": f"Bearer {token}"},
        )
        me_resp = await client.get(
            "/api/webchat/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert verify_resp.status_code == 200
    assert verify_resp.json()["agent_id"] == TEST_AGENT_ID
    assert verify_resp.json()["employee_id"] == TEST_EMPLOYEE_ID
    assert me_resp.status_code == 200
    assert me_resp.json()["user_id"] == "test_user"


@pytest.mark.asyncio
async def test_register_disabled_in_sso_mode(client):
    async with client:
        resp = await client.post(
            "/api/webchat/register",
            json={"username": "x", "password": "y"},
        )

    assert resp.status_code == 410


@pytest.mark.asyncio
async def test_set_agent_forbidden_in_sso_mode(client):
    token = make_token()

    async with client:
        unauth_resp = await client.post("/api/webchat/set-agent?agent_id=wx_other")
        resp = await client.post(
            "/api/webchat/set-agent?agent_id=wx_other",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert unauth_resp.status_code == 401
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_webchat_workspace_context_sets_agent_id_without_workspace_dir(
    monkeypatch,
):
    from qwenpaw.app.routers import webchat

    request = SimpleNamespace(state=SimpleNamespace())
    identity = SimpleNamespace(
        tenant_id="alice",
        agent_id="wx_alice",
    )
    monkeypatch.setattr(
        webchat,
        "get_tenant_workspace_for_identity",
        AsyncMock(
            return_value=SimpleNamespace(
                workspace_dir="/tmp/tenants/wx_alice",
            ),
        ),
    )

    agent_id = await webchat._set_webchat_workspace_context(request, identity)

    assert agent_id == "wx_alice"
    assert request.state.agent_id == "wx_alice"
    assert not hasattr(request.state, "webchat_workspace_dir")


def test_webchat_routes_require_identity_except_public_contracts():
    public_endpoints = {
        "login",
        "login_with_qrcode",
        "qrcode_config",
        "status",
        "verify_token",
        "register",
    }
    missing = []

    for route in router.routes:
        endpoint = getattr(route, "endpoint", None)
        path = getattr(route, "path", "")
        if endpoint is None or not path.startswith("/webchat"):
            continue
        if endpoint.__name__ in public_endpoints:
            continue
        source = inspect.getsource(endpoint)
        if "_get_identity_from_request" not in source:
            missing.append(f"{sorted(route.methods)} {path} -> {endpoint.__name__}")

    assert missing == []


@pytest.mark.asyncio
async def test_early_return_session_routes_still_require_token(client):
    async with client:
        get_resp = await client.get("/api/webchat/sessions/undefined")
        put_resp = await client.put(
            "/api/webchat/sessions/undefined",
            json={"name": "Ignored"},
        )

    assert get_resp.status_code == 401
    assert put_resp.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/webchat/providers"),
        ("POST", "/api/webchat/agent/skills/install-uploaded"),
        ("GET", "/api/webchat/agent/skill-pool/skills"),
        ("POST", "/api/webchat/agent/skill-pool/refresh"),
        ("GET", "/api/webchat/agent/skill-pool/builtin-sources"),
        ("GET", "/api/webchat/agent/skill-pool/builtin-notice"),
    ],
)
async def test_public_prefix_sensitive_routes_require_token(client, method, path):
    async with client:
        resp = await client.request(method, path)

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_chat_uses_canonical_wecom_session_when_sync_enabled(
    client,
    app,
    monkeypatch,
):
    monkeypatch.setenv("QWENPAW_WEBCHAT_WECOM_SESSION_SYNC_ENABLED", "true")
    token = make_token()

    async with client:
        resp = await client.post(
            "/api/webchat/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "session_id": "default",
                "input": [
                    {
                        "content": [
                            {"type": "text", "text": "你好"},
                        ],
                    },
                ],
            },
        )

    assert resp.status_code == 200
    workspace = app.state.fake_manager.workspace
    chat = workspace.chat_manager.created[-1]
    assert chat.session_id == "wecom:test_user"
    assert chat.user_id == "test_user"
    assert chat.channel == "webchat"
    payload = workspace.task_tracker.started_payloads[-1][1]
    assert payload["meta"]["canonical_session_id"] == "wecom:test_user"


@pytest.mark.asyncio
async def test_chat_resolves_wecom_chat_id_to_canonical_session(
    client,
    app,
    monkeypatch,
):
    monkeypatch.setenv("QWENPAW_WEBCHAT_WECOM_SESSION_SYNC_ENABLED", "true")
    workspace = app.state.fake_manager.workspace
    workspace.chat_manager.seed(
        SimpleNamespace(
            id="wecom-chat",
            session_id="wecom:test_user",
            user_id="test_user",
            channel="wecom_tenant",
            name="企微历史",
            created_at="2026-04-28T00:00:00+00:00",
            updated_at="2026-04-28T00:00:02+00:00",
            status="idle",
            pinned=False,
            meta={},
        ),
    )
    token = make_token()

    async with client:
        resp = await client.post(
            "/api/webchat/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "session_id": "wecom-chat",
                "input": [
                    {
                        "content": [
                            {"type": "text", "text": "继续企微单聊"},
                        ],
                    },
                ],
            },
        )

    assert resp.status_code == 200
    chat = workspace.chat_manager.created[-1]
    assert chat.session_id == "wecom:test_user"
    assert chat.channel == "webchat"
    payload = workspace.task_tracker.started_payloads[-1][1]
    assert payload["meta"]["canonical_session_id"] == "wecom:test_user"


@pytest.mark.asyncio
async def test_chat_keeps_legacy_webchat_session_when_explicit(
    client,
    app,
    monkeypatch,
):
    monkeypatch.setenv("QWENPAW_WEBCHAT_WECOM_SESSION_SYNC_ENABLED", "true")
    token = make_token()

    async with client:
        resp = await client.post(
            "/api/webchat/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "session_id": "webchat:test_user:session_old",
                "input": [
                    {
                        "content": [
                            {"type": "text", "text": "继续旧会话"},
                        ],
                    },
                ],
            },
        )

    assert resp.status_code == 200
    chat = app.state.fake_manager.workspace.chat_manager.created[-1]
    assert chat.session_id == "webchat:test_user:session_old"


@pytest.mark.asyncio
async def test_chat_keeps_legacy_webchat_session_when_frontend_sends_suffix(
    client,
    app,
    monkeypatch,
):
    monkeypatch.setenv("QWENPAW_WEBCHAT_WECOM_SESSION_SYNC_ENABLED", "true")
    workspace = app.state.fake_manager.workspace
    workspace.chat_manager.seed(
        SimpleNamespace(
            id="legacy-chat",
            session_id="webchat:test_user:session_old",
            user_id="test_user",
            channel="webchat",
            name="旧网页会话",
            created_at="2026-04-28T00:00:00+00:00",
            updated_at="2026-04-28T00:00:01+00:00",
            status="idle",
            pinned=False,
            meta={},
        ),
    )
    token = make_token()

    async with client:
        resp = await client.post(
            "/api/webchat/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "session_id": "session_old",
                "input": [
                    {
                        "content": [
                            {"type": "text", "text": "继续旧网页会话"},
                        ],
                    },
                ],
            },
        )

    assert resp.status_code == 200
    chat = workspace.chat_manager.created[-1]
    assert chat.session_id == "webchat:test_user:session_old"
    payload = workspace.task_tracker.started_payloads[-1][1]
    assert "canonical_session_id" not in payload["meta"]


@pytest.mark.asyncio
async def test_chat_keeps_new_frontend_local_session_separate_from_canonical(
    client,
    app,
    monkeypatch,
):
    monkeypatch.setenv("QWENPAW_WEBCHAT_WECOM_SESSION_SYNC_ENABLED", "true")
    token = make_token()

    async with client:
        resp = await client.post(
            "/api/webchat/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "session_id": "1714291200000",
                "input": [
                    {
                        "content": [
                            {"type": "text", "text": "新网页会话"},
                        ],
                    },
                ],
            },
        )

    assert resp.status_code == 200
    workspace = app.state.fake_manager.workspace
    chat = workspace.chat_manager.created[-1]
    assert chat.session_id == "webchat:test_user:1714291200000"
    payload = workspace.task_tracker.started_payloads[-1][1]
    assert payload["meta"]["session_id"] == "webchat:test_user:1714291200000"
    assert "canonical_session_id" not in payload["meta"]


@pytest.mark.asyncio
async def test_create_session_returns_new_webchat_session_when_sync_enabled(
    client,
    app,
    monkeypatch,
):
    monkeypatch.setenv("QWENPAW_WEBCHAT_WECOM_SESSION_SYNC_ENABLED", "true")
    token = make_token()

    async with client:
        resp = await client.post(
            "/api/webchat/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    session_id = resp.json()["session_id"]
    assert session_id.startswith("webchat:test_user:")
    chat = app.state.fake_manager.workspace.chat_manager.created[-1]
    assert chat.session_id == session_id
    assert chat.user_id == "test_user"


@pytest.mark.asyncio
async def test_create_session_can_create_multiple_webchat_sessions(
    client,
    app,
    monkeypatch,
):
    monkeypatch.setenv("QWENPAW_WEBCHAT_WECOM_SESSION_SYNC_ENABLED", "true")
    token = make_token()

    async with client:
        first = await client.post(
            "/api/webchat/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )
        second = await client.post(
            "/api/webchat/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )
        list_resp = await client.get(
            "/api/webchat/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["session_id"] != second.json()["session_id"]
    sessions = [
        item
        for item in list_resp.json()["sessions"]
        if item["channel"] == "webchat"
    ]
    session_ids = {item["session_id"] for item in sessions}
    assert first.json()["session_id"] in session_ids
    assert second.json()["session_id"] in session_ids


@pytest.mark.asyncio
async def test_list_sessions_keeps_webchat_chats_and_wecom_bot_separate(
    client,
    app,
    monkeypatch,
):
    monkeypatch.setenv("QWENPAW_WEBCHAT_WECOM_SESSION_SYNC_ENABLED", "true")
    workspace = app.state.fake_manager.workspace
    workspace.chat_manager.seed(
        SimpleNamespace(
            id="wecom-chat",
            session_id="wecom:test_user",
            user_id="test_user",
            channel="wecom_tenant",
            name="企微历史",
            created_at="2026-04-28T00:00:00+00:00",
            updated_at="2026-04-28T00:00:02+00:00",
            status="idle",
            pinned=False,
            meta={},
        ),
    )
    workspace.chat_manager.seed(
        SimpleNamespace(
            id="webchat-chat",
            session_id="wecom:test_user",
            user_id="test_user",
            channel="webchat",
            name="网页历史",
            created_at="2026-04-28T00:00:01+00:00",
            updated_at="2026-04-28T00:00:03+00:00",
            status="idle",
            pinned=False,
            meta={},
        ),
    )
    workspace.chat_manager.seed(
        SimpleNamespace(
            id="group-chat",
            session_id="wecom:group:room",
            user_id="group",
            channel="wecom_tenant",
            name="群聊",
            created_at="2026-04-28T00:00:00+00:00",
            updated_at="2026-04-28T00:00:04+00:00",
            status="idle",
            pinned=False,
            meta={},
        ),
    )

    token = make_token()
    async with client:
        resp = await client.get(
            "/api/webchat/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    sessions = resp.json()["sessions"]
    matching = [item for item in sessions if item["session_id"] == "wecom:test_user"]
    assert len(matching) == 2
    by_channel = {item["channel"]: item for item in matching}
    assert by_channel["webchat"]["id"] == "webchat-chat"
    assert by_channel["webchat"]["source_channels"] == ["webchat"]
    assert by_channel["webchat"]["synced"] is False
    assert by_channel["wecom_tenant"]["id"] == "wecom-chat"
    assert by_channel["wecom_tenant"]["source_channels"] == ["wecom_tenant"]
    assert by_channel["wecom_tenant"]["synced"] is True
    assert all(item["session_id"] != "wecom:group:room" for item in sessions)


class FakeRunnerSession:
    def __init__(self):
        self.calls = []

    async def get_session_state_dict(
        self,
        session_id,
        user_id,
        channel="",
        allow_not_exist=True,
    ):
        self.calls.append(
            {
                "session_id": session_id,
                "user_id": user_id,
                "channel": channel,
                "allow_not_exist": allow_not_exist,
            },
        )
        if channel != "wecom_tenant":
            return {}
        return {
            "agent": {
                "memory": {
                    "_compressed_summary": "",
                    "content": [
                        [
                            {
                                "id": "msg-user-1",
                                "name": "user",
                                "role": "user",
                                "content": "我喜欢蓝色",
                                "metadata": {},
                                "timestamp": "2026-05-15 13:04:27.432",
                            },
                            [],
                        ],
                    ],
                },
            },
        }


@pytest.mark.asyncio
async def test_get_session_accepts_canonical_session_id(client, app, monkeypatch):
    monkeypatch.setenv("QWENPAW_WEBCHAT_WECOM_SESSION_SYNC_ENABLED", "true")
    workspace = app.state.fake_manager.workspace
    fake_session = FakeRunnerSession()
    workspace.runner = SimpleNamespace(session=fake_session)
    workspace.chat_manager.seed(
        SimpleNamespace(
            id="wecom-chat",
            session_id="wecom:test_user",
            user_id="test_user",
            channel="wecom_tenant",
            name="企微历史",
            created_at="2026-04-28T00:00:00+00:00",
            updated_at="2026-04-28T00:00:02+00:00",
            status="idle",
            pinned=False,
            meta={},
        ),
    )
    token = make_token()

    async with client:
        resp = await client.get(
            "/api/webchat/sessions/wecom%3Atest_user",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "wecom-chat"
    assert body["session_id"] == "wecom:test_user"
    assert body["channel"] == "wecom_tenant"
    assert body["messages"]
    assert body["messages"][0]["role"] == "user"
    assert body["messages"][0]["content"][0]["text"] == "我喜欢蓝色"
    assert fake_session.calls == [
        {
            "session_id": "wecom:test_user",
            "user_id": "test_user",
            "channel": "wecom_tenant",
            "allow_not_exist": True,
        },
    ]


@pytest.mark.asyncio
async def test_get_canonical_session_prefers_wecom_when_webchat_has_same_session_id(
    client,
    app,
    monkeypatch,
):
    monkeypatch.setenv("QWENPAW_WEBCHAT_WECOM_SESSION_SYNC_ENABLED", "true")
    workspace = app.state.fake_manager.workspace
    fake_session = FakeRunnerSession()
    workspace.runner = SimpleNamespace(session=fake_session)
    workspace.chat_manager.seed(
        SimpleNamespace(
            id="webchat-chat",
            session_id="wecom:test_user",
            user_id="test_user",
            channel="webchat",
            name="网页历史",
            created_at="2026-04-28T00:00:01+00:00",
            updated_at="2026-04-28T00:00:03+00:00",
            status="idle",
            pinned=False,
            meta={},
        ),
    )
    workspace.chat_manager.seed(
        SimpleNamespace(
            id="wecom-chat",
            session_id="wecom:test_user",
            user_id="test_user",
            channel="wecom_tenant",
            name="企微历史",
            created_at="2026-04-28T00:00:00+00:00",
            updated_at="2026-04-28T00:00:02+00:00",
            status="idle",
            pinned=False,
            meta={},
        ),
    )
    token = make_token()

    async with client:
        resp = await client.get(
            "/api/webchat/sessions/wecom%3Atest_user",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "wecom-chat"
    assert body["channel"] == "wecom_tenant"
    assert fake_session.calls == [
        {
            "session_id": "wecom:test_user",
            "user_id": "test_user",
            "channel": "wecom_tenant",
            "allow_not_exist": True,
        },
    ]


@pytest.mark.asyncio
async def test_list_sessions_keeps_webchat_and_wecom_sources_separate(
    client,
    app,
    monkeypatch,
):
    monkeypatch.setenv("QWENPAW_WEBCHAT_WECOM_SESSION_SYNC_ENABLED", "true")
    workspace = app.state.fake_manager.workspace
    fake_session = FakeRunnerSession()
    workspace.runner = SimpleNamespace(session=fake_session)
    workspace.chat_manager.seed(
        SimpleNamespace(
            id="wecom-chat",
            session_id="wecom:test_user",
            user_id="test_user",
            channel="wecom_tenant",
            name="企微历史",
            created_at="2026-04-28T00:00:00+00:00",
            updated_at="2026-04-28T00:00:02+00:00",
            status="idle",
            pinned=False,
            meta={},
        ),
    )
    workspace.chat_manager.seed(
        SimpleNamespace(
            id="webchat-chat",
            session_id="wecom:test_user",
            user_id="test_user",
            channel="webchat",
            name="网页历史",
            created_at="2026-04-28T00:00:01+00:00",
            updated_at="2026-04-28T00:00:03+00:00",
            status="idle",
            pinned=False,
            meta={},
        ),
    )
    token = make_token()

    async with client:
        resp = await client.get(
            "/api/webchat/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    sessions = [
        item for item in resp.json()["sessions"]
        if item["session_id"] == "wecom:test_user"
    ]
    assert [item["channel"] for item in sessions] == ["webchat", "wecom_tenant"]
    assert {item["id"] for item in sessions} == {"webchat-chat", "wecom-chat"}
    assert fake_session.calls == []


@pytest.mark.asyncio
async def test_update_session_accepts_canonical_session_id(client, app, monkeypatch):
    monkeypatch.setenv("QWENPAW_WEBCHAT_WECOM_SESSION_SYNC_ENABLED", "true")
    workspace = app.state.fake_manager.workspace
    workspace.chat_manager.seed(
        SimpleNamespace(
            id="wecom-chat",
            session_id="wecom:test_user",
            user_id="test_user",
            channel="wecom_tenant",
            name="企微历史",
            created_at="2026-04-28T00:00:00+00:00",
            updated_at="2026-04-28T00:00:02+00:00",
            status="idle",
            pinned=False,
            meta={},
        ),
    )
    token = make_token()

    async with client:
        resp = await client.put(
            "/api/webchat/sessions/wecom%3Atest_user",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "改名后的历史", "pinned": True},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "wecom-chat"
    assert body["name"] == "改名后的历史"
    assert workspace.chat_manager.created[0].pinned is True


@pytest.mark.asyncio
async def test_delete_session_accepts_visible_chat_id(client, app, monkeypatch):
    monkeypatch.setenv("QWENPAW_WEBCHAT_WECOM_SESSION_SYNC_ENABLED", "true")
    workspace = app.state.fake_manager.workspace
    workspace.chat_manager.seed(
        SimpleNamespace(
            id="wecom-chat",
            session_id="wecom:test_user",
            user_id="test_user",
            channel="wecom_tenant",
            name="企微历史",
            created_at="2026-04-28T00:00:00+00:00",
            updated_at="2026-04-28T00:00:02+00:00",
            status="idle",
            pinned=False,
            meta={},
        ),
    )
    token = make_token()

    async with client:
        resp = await client.delete(
            "/api/webchat/sessions/wecom-chat",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    assert workspace.chat_manager.created == []


@pytest.mark.asyncio
async def test_get_session_rejects_other_user_and_group(client):
    token = make_token()

    async with client:
        other_resp = await client.get(
            "/api/webchat/sessions/wecom%3Aother_user",
            headers={"Authorization": f"Bearer {token}"},
        )
        group_resp = await client.get(
            "/api/webchat/sessions/wecom%3Agroup%3Aroom",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert other_resp.status_code == 403
    assert group_resp.status_code == 403


@pytest.mark.asyncio
async def test_get_session_rejects_noncanonical_wecom_chat_by_id(
    client,
    app,
    monkeypatch,
):
    monkeypatch.setenv("QWENPAW_WEBCHAT_WECOM_SESSION_SYNC_ENABLED", "true")
    workspace = app.state.fake_manager.workspace
    workspace.runner = SimpleNamespace(session=FakeRunnerSession())
    workspace.chat_manager.seed(
        SimpleNamespace(
            id="noncanonical-wecom-chat",
            session_id="wecom:other_context",
            user_id="test_user",
            channel="wecom_tenant",
            name="非规范企微上下文",
            created_at="2026-04-28T00:00:00+00:00",
            updated_at="2026-04-28T00:00:02+00:00",
            status="idle",
            pinned=False,
            meta={},
        ),
    )
    token = make_token()

    async with client:
        resp = await client.get(
            "/api/webchat/sessions/noncanonical-wecom-chat",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_workspace_agent_json_drives_system_prompt_files(
    client,
    monkeypatch,
    tmp_path,
):
    workspace_dir = tmp_path / TEST_AGENT_ID
    agent_config = AgentProfileConfig(
        id=TEST_AGENT_ID,
        name="测试租户",
        description="workspace local config",
        workspace_dir=str(workspace_dir),
        system_prompt_files=["TENANT.md"],
    )
    write_agent_config_to_workspace(workspace_dir, agent_config)

    async def fake_workspace(request, identity):
        return SimpleNamespace(workspace_dir=workspace_dir)

    monkeypatch.setattr(
        "qwenpaw.app.routers.webchat.get_tenant_workspace_for_identity",
        fake_workspace,
    )
    token = make_token()

    async with client:
        get_resp = await client.get(
            "/api/webchat/agent/system-prompt-files",
            headers={"Authorization": f"Bearer {token}"},
        )
        put_resp = await client.put(
            "/api/webchat/agent/system-prompt-files",
            headers={"Authorization": f"Bearer {token}"},
            json=["AGENTS.md", "TENANT.md"],
        )

    assert get_resp.status_code == 200
    assert get_resp.json() == ["TENANT.md"]
    assert put_resp.status_code == 200
    saved = load_agent_config_from_workspace(workspace_dir)
    assert saved is not None
    assert saved.system_prompt_files == ["AGENTS.md", "TENANT.md"]


@pytest.mark.asyncio
async def test_active_model_updates_workspace_agent_json(
    client,
    monkeypatch,
    tmp_path,
):
    workspace_dir = tmp_path / TEST_AGENT_ID
    agent_config = AgentProfileConfig(
        id=TEST_AGENT_ID,
        name="测试租户",
        workspace_dir=str(workspace_dir),
        active_model=ModelSlotConfig(provider_id="old", model="old-model"),
    )
    write_agent_config_to_workspace(workspace_dir, agent_config)

    async def fake_workspace(request, identity):
        return SimpleNamespace(workspace_dir=workspace_dir)

    monkeypatch.setattr(
        "qwenpaw.app.routers.webchat.get_tenant_workspace_for_identity",
        fake_workspace,
    )

    class FakeProvider:
        def has_model(self, model: str) -> bool:
            return model == "new-model"

    class FakeProviderManager:
        def get_provider(self, provider_id: str):
            return FakeProvider() if provider_id == "new" else None

    monkeypatch.setattr(
        "qwenpaw.providers.provider_manager.ProviderManager.get_instance",
        lambda: FakeProviderManager(),
    )
    token = make_token()

    async with client:
        get_resp = await client.get(
            "/api/webchat/active-models",
            headers={"Authorization": f"Bearer {token}"},
        )
        put_resp = await client.put(
            "/api/webchat/active-models",
            headers={"Authorization": f"Bearer {token}"},
            json={"provider_id": "new", "model": "new-model"},
        )

    assert get_resp.status_code == 200
    assert get_resp.json() == {
        "active_llm": {"provider_id": "old", "model": "old-model"},
    }
    assert put_resp.status_code == 200
    saved = load_agent_config_from_workspace(workspace_dir)
    assert saved is not None
    assert saved.active_model == ModelSlotConfig(
        provider_id="new",
        model="new-model",
    )


@pytest.mark.asyncio
async def test_timezone_updates_workspace_agent_json(
    client,
    monkeypatch,
    tmp_path,
):
    workspace_dir = tmp_path / TEST_AGENT_ID
    agent_config = AgentProfileConfig(
        id=TEST_AGENT_ID,
        name="测试租户",
        workspace_dir=str(workspace_dir),
        user_timezone="Asia/Shanghai",
    )
    write_agent_config_to_workspace(workspace_dir, agent_config)

    async def fake_workspace(request, identity):
        return SimpleNamespace(agent_id=identity.agent_id, workspace_dir=workspace_dir)

    monkeypatch.setattr(
        "qwenpaw.app.routers.webchat.get_tenant_workspace_for_identity",
        fake_workspace,
    )
    token = make_token()

    async with client:
        get_resp = await client.get(
            "/api/webchat/agent/user-timezone",
            headers={"Authorization": f"Bearer {token}"},
        )
        put_resp = await client.put(
            "/api/webchat/agent/user-timezone",
            headers={"Authorization": f"Bearer {token}"},
            json={"timezone": "UTC"},
        )

    assert get_resp.status_code == 200
    assert get_resp.json() == {"timezone": "Asia/Shanghai"}
    assert put_resp.status_code == 200
    assert put_resp.json() == {"timezone": "UTC"}
    saved = load_agent_config_from_workspace(workspace_dir)
    assert saved is not None
    assert saved.user_timezone == "UTC"


@pytest.mark.asyncio
async def test_webchat_skills_include_and_import_uploaded_media_skill(
    client,
    app,
    monkeypatch,
    tmp_path,
):
    workspace_dir = tmp_path / TEST_AGENT_ID
    media_skill_dir = workspace_dir / "media" / "data-analysis"
    media_skill_dir.mkdir(parents=True)
    (media_skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: Data Analysis\n"
        "description: 数据分析与可视化\n"
        "---\n"
        "# Data Analysis\n",
        encoding="utf-8",
    )

    async def fake_workspace(request, identity):
        request.app.state.fake_manager.workspace.agent_id = identity.agent_id
        request.app.state.fake_manager.workspace.workspace_dir = workspace_dir
        return SimpleNamespace(agent_id=identity.agent_id, workspace_dir=workspace_dir)

    monkeypatch.setattr(
        "qwenpaw.app.routers.webchat.get_tenant_workspace_for_identity",
        fake_workspace,
    )
    monkeypatch.setattr(
        "qwenpaw.app.agent_context.AgentResolver",
        lambda: SimpleNamespace(
            resolve=lambda agent_id: SimpleNamespace(
                agent_id=agent_id,
                workspace_dir=workspace_dir,
                enabled=True,
            ),
        ),
    )
    token = make_token()

    async with client:
        list_resp = await client.get(
            "/api/webchat/agent/skills",
            headers={"Authorization": f"Bearer {token}"},
        )
        install_resp = await client.post(
            "/api/webchat/agent/skills/install-uploaded",
            headers={"Authorization": f"Bearer {token}"},
            json={"skill_name": "Data Analysis", "overwrite": False},
        )
        installed_resp = await client.get(
            "/api/webchat/agent/skills",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert list_resp.status_code == 200
    assert len(list_resp.json()["skills"]) == 1
    uploaded_skill = list_resp.json()["skills"][0]
    assert uploaded_skill["name"] == "Data Analysis"
    assert uploaded_skill["description"] == "数据分析与可视化"
    assert uploaded_skill["content"] == (
        "---\n"
        "name: Data Analysis\n"
        "description: 数据分析与可视化\n"
        "---\n"
        "# Data Analysis\n"
    )
    assert uploaded_skill["source"] == "uploaded_media"
    assert uploaded_skill["enabled"] is False
    assert uploaded_skill["installed"] is False
    assert uploaded_skill["installable"] is True
    assert uploaded_skill["channels"] == []
    assert install_resp.status_code == 200
    assert install_resp.json()["success"] is True
    installed_skill = installed_resp.json()["skills"][0]
    assert installed_skill["name"] == "Data Analysis"
    assert installed_skill["installed"] is True
    assert installed_skill["enabled"] is True
    assert (workspace_dir / "skills" / "Data Analysis" / "SKILL.md").exists()


@pytest.mark.asyncio
async def test_legacy_webchat_session_stays_visible_and_readable(client, app):
    workspace = app.state.fake_manager.workspace
    workspace.runner = SimpleNamespace(session=FakeRunnerSession())
    workspace.chat_manager.seed(
        SimpleNamespace(
            id="legacy-chat",
            session_id="webchat:test_user:session_old",
            user_id="test_user",
            channel="webchat",
            name="旧网页会话",
            created_at="2026-04-28T00:00:00+00:00",
            updated_at="2026-04-28T00:00:01+00:00",
            status="idle",
            pinned=False,
            meta={},
        ),
    )
    token = make_token()

    async with client:
        list_resp = await client.get(
            "/api/webchat/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )
        get_resp = await client.get(
            "/api/webchat/sessions/legacy-chat",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert list_resp.status_code == 200
    assert any(item["id"] == "legacy-chat" for item in list_resp.json()["sessions"])
    assert get_resp.status_code == 200
    assert get_resp.json()["session_id"] == "webchat:test_user:session_old"


@pytest.mark.asyncio
async def test_chat_uses_webchat_session_when_sync_disabled(client, app, monkeypatch):
    monkeypatch.setenv("QWENPAW_WEBCHAT_WECOM_SESSION_SYNC_ENABLED", "false")
    token = make_token()

    async with client:
        resp = await client.post(
            "/api/webchat/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "session_id": "default",
                "input": [
                    {
                        "content": [
                            {"type": "text", "text": "你好"},
                        ],
                    },
                ],
            },
        )

    assert resp.status_code == 200
    chat = app.state.fake_manager.workspace.chat_manager.created[-1]
    assert chat.session_id == "webchat:test_user:default"


@pytest.mark.asyncio
async def test_sync_disabled_hides_wecom_session_from_webchat(client, app, monkeypatch):
    monkeypatch.setenv("QWENPAW_WEBCHAT_WECOM_SESSION_SYNC_ENABLED", "false")
    workspace = app.state.fake_manager.workspace
    workspace.runner = SimpleNamespace(session=FakeRunnerSession())
    workspace.chat_manager.seed(
        SimpleNamespace(
            id="wecom-chat",
            session_id="wecom:test_user",
            user_id="test_user",
            channel="wecom_tenant",
            name="企微历史",
            created_at="2026-04-28T00:00:00+00:00",
            updated_at="2026-04-28T00:00:01+00:00",
            status="idle",
            pinned=False,
            meta={},
        ),
    )
    token = make_token()

    async with client:
        list_resp = await client.get(
            "/api/webchat/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )
        get_resp = await client.get(
            "/api/webchat/sessions/wecom%3Atest_user",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert list_resp.status_code == 200
    assert all(
        item["session_id"] != "wecom:test_user"
        for item in list_resp.json()["sessions"]
    )
    assert get_resp.status_code == 404
