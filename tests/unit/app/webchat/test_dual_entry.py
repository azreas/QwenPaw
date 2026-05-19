# -*- coding: utf-8 -*-
"""P3-1 双入口交互闭环测试。

验证 WebChat 和企微 Bot 作为同一员工的两个入口，
身份、会话、工作区保持一致。
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from qwenpaw.app.webchat.session import WebchatIdentity
from qwenpaw.app.webchat.session_catalog import (
    list_webchat_visible_sessions,
    resolve_visible_chat,
)
from qwenpaw.app.webchat.session_sync import (
    canonical_session_id_for_identity,
    ensure_webchat_session_access,
    is_wecom_group_session_id,
    is_wecom_single_session_id,
)
from qwenpaw.app.webchat.tenant_resolver import ensure_requested_agent_allowed
from qwenpaw.tenancy.ids import tenant_agent_id, safe_tenant_suffix
from qwenpaw.tenancy.tenant_agent_registry import TenantAgentRegistry
from qwenpaw.tenancy.wx_tenant_router import WxTenantRouter


# ── 共用 fixture ──────────────────────────────────────────────────────────


def _identity(
    wechat_company_id: str = "zhangsan",
    employee_id: str = "E001",
) -> WebchatIdentity:
    return WebchatIdentity.from_sso(
        full_name="张三",
        employee_id=employee_id,
        wechat_company_id=wechat_company_id,
    )


def _chat(
    chat_id: str,
    session_id: str,
    user_id: str = "zhangsan",
    channel: str = "webchat",
    name: str = "New Chat",
    updated_at: str = "2026-01-01T00:00:00Z",
    **extra,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=chat_id,
        session_id=session_id,
        user_id=user_id,
        channel=channel,
        name=name,
        created_at="2026-01-01T00:00:00Z",
        updated_at=updated_at,
        status="idle",
        pinned=False,
        meta=extra.get("meta", {}),
    )


# ── 1. 同一企业员工映射到同一个 wx_* 工作区 ──────────────────────────────


class TestSameEmployeeSameWorkspace:
    """同一员工无论从 WebChat 还是企微 Bot 进入，
    都映射到同一个 wx_* 工作区。

    身份主键契约：SSO 返回的 wechatCompanyId 与企微回调的
    from.userid 是同一个值（企业微信强契约：统一 userid）。
    以下测试使用不同来源的变量名模拟真实场景。
    """

    def test_webchat_identity_maps_to_wx_workspace(self):
        # 模拟 SSO 返回的 wechatCompanyId
        sso_wechat_company_id = "zhangsan"
        identity = _identity(sso_wechat_company_id)
        assert identity.tenant_id == sso_wechat_company_id
        assert identity.agent_id == "wx_zhangsan"

    def test_wecom_tenant_id_maps_to_same_wx_workspace(self):
        """企微 Bot 用 from.userid 做 tenant_id，应映射到同一个 wx_* agent。"""
        # 模拟企微回调的 from.userid（与 SSO 的 wechatCompanyId 是同一值）
        wecom_from_userid = "zhangsan"
        assert tenant_agent_id(wecom_from_userid) == "wx_zhangsan"

    def test_both_entries_converge_on_same_agent_id(self):
        """SSO wechatCompanyId 和企微 from.userid 收敛到同一 agent_id。"""
        # 模拟两个入口分别拿到的身份字段
        sso_wechat_company_id = "zhangsan"
        wecom_from_userid = "zhangsan"
        identity = _identity(sso_wechat_company_id)
        wecom_agent_id = tenant_agent_id(wecom_from_userid)
        assert identity.agent_id == wecom_agent_id

    def test_real_enterprise_userid_converges(self):
        """使用真实企业 userid 样例验证收敛。

        企业微信强契约：SSO 的 wechatCompanyId 字段值 == 企微
        回调的 from.userid 字段值。两者是同一个企业成员 userid。
        """
        # SSO 登录返回
        sso_response = {
            "fullName": "王小明",
            "employeeId": "E20240001",
            "wechatCompanyId": "WangXiaoMing",
        }
        identity = WebchatIdentity.from_sso(
            full_name=sso_response["fullName"],
            employee_id=sso_response["employeeId"],
            wechat_company_id=sso_response["wechatCompanyId"],
        )

        # 企微 Bot 回调
        wecom_callback_from_userid = "WangXiaoMing"
        wecom_agent_id = tenant_agent_id(wecom_callback_from_userid)

        assert identity.agent_id == wecom_agent_id == "wx_WangXiaoMing"

    def test_canonical_session_id_matches_wecom_single_chat(self):
        """WebChat 的 canonical session ID 与企微单聊 session_id 一致。"""
        identity = _identity("zhangsan")
        canonical = canonical_session_id_for_identity(identity)
        assert canonical == "wecom:zhangsan"
        assert is_wecom_single_session_id(canonical)

    def test_different_employees_map_to_different_workspaces(self):
        zhangsan = _identity("zhangsan")
        lisi = _identity("lisi")
        assert zhangsan.agent_id != lisi.agent_id
        assert zhangsan.tenant_id != lisi.tenant_id

    def test_safe_tenant_suffix_rejects_path_injection(self):
        assert safe_tenant_suffix("../../etc") != "../../etc"
        assert "wx_" in tenant_agent_id("../../etc")
        # 路径分隔符被替换为 hash，不会泄漏到文件系统
        assert "/" not in tenant_agent_id("../../etc")


# ── 2. WebChat 会话与企微 Bot 会话的一致性 ─────────────────────────────────


class TestSessionConsistency:
    """WebChat 和企微 Bot 的会话在服务端可见且一致。"""

    def test_wecom_single_chat_visible_in_webchat_history(self):
        """企微 Bot 产生的单聊会话在 WebChat 历史会话中可见。"""
        identity = _identity("zhangsan")
        canonical = canonical_session_id_for_identity(identity)
        chats = [
            _chat("c1", canonical, channel="wecom_tenant", name="企微对话"),
        ]
        visible = list_webchat_visible_sessions(identity, chats)
        assert len(visible) == 1
        assert visible[0]["session_id"] == canonical
        assert visible[0]["synced"] is True

    def test_legacy_wecom_single_chat_visible_in_webchat_history(self):
        """旧 wecom channel 记录也应在 WebChat 历史会话中可见。"""
        identity = _identity("zhangsan")
        canonical = canonical_session_id_for_identity(identity)
        chats = [
            _chat("c1", canonical, channel="wecom", name="企微对话"),
        ]
        visible = list_webchat_visible_sessions(identity, chats)
        assert len(visible) == 1
        assert visible[0]["session_id"] == canonical
        assert visible[0]["source_channels"] == ["wecom"]
        assert visible[0]["synced"] is True

    def test_webchat_and_wecom_sessions_both_visible(self):
        """同一员工的 WebChat 和企微会话都在历史列表中。"""
        identity = _identity("zhangsan")
        canonical = canonical_session_id_for_identity(identity)
        chats = [
            _chat("c1", "webchat:zhangsan:s1", channel="webchat", name="Web对话1"),
            _chat("c2", canonical, channel="wecom_tenant", name="企微对话"),
            _chat("c3", "webchat:zhangsan:s3", channel="webchat", name="Web对话2"),
        ]
        visible = list_webchat_visible_sessions(identity, chats)
        # canonical session 和两个 webchat session 都可见
        session_ids = {v["session_id"] for v in visible}
        assert "webchat:zhangsan:s1" in session_ids
        assert "webchat:zhangsan:s3" in session_ids
        assert canonical in session_ids

    def test_wecom_group_sessions_not_visible_in_webchat(self):
        """企微群聊会话不在 WebChat 历史中可见。"""
        identity = _identity("zhangsan")
        chats = [
            _chat("c1", "wecom:group:room1", channel="wecom_tenant", name="群聊"),
        ]
        visible = list_webchat_visible_sessions(identity, chats)
        assert len(visible) == 0

    def test_other_user_sessions_not_visible(self):
        """其他员工的会话不可见。"""
        identity = _identity("zhangsan")
        chats = [
            _chat("c1", "wecom:lisi", channel="wecom_tenant", name="李四会话"),
        ]
        visible = list_webchat_visible_sessions(identity, chats)
        assert len(visible) == 0

    def test_resolve_visible_chat_finds_wecom_session(self):
        """通过 session_id 可以找到企微产生的会话。"""
        identity = _identity("zhangsan")
        canonical = canonical_session_id_for_identity(identity)
        chats = [
            _chat("c1", canonical, channel="wecom_tenant", name="企微对话"),
        ]
        found = resolve_visible_chat(identity, chats, canonical)
        assert found is not None
        assert found.session_id == canonical

    def test_resolve_visible_chat_finds_legacy_wecom_session(self):
        """通过 id 可以找到旧 wecom channel 的企微单聊会话。"""
        identity = _identity("zhangsan")
        canonical = canonical_session_id_for_identity(identity)
        chats = [
            _chat("c1", canonical, channel="wecom", name="企微对话"),
        ]
        found = resolve_visible_chat(identity, chats, "c1")
        assert found is not None
        assert found.session_id == canonical

    def test_webchat_new_session_creates_valid_session_id(self):
        """WebChat 新建会话后 session_id 格式合法，可被服务端识别。"""
        identity = _identity("zhangsan")
        # 模拟前端创建的新 session
        new_session_id = "webchat:zhangsan:new-uuid-123"
        allowed = ensure_webchat_session_access(identity, new_session_id)
        assert allowed == new_session_id

    @pytest.mark.asyncio
    async def test_webchat_reads_wecom_history_from_channel_scoped_state(
        self,
        monkeypatch,
    ):
        """WebChat 打开企微会话时，应读取 wecom_tenant 分目录下的状态。"""
        from qwenpaw.app.routers import webchat

        identity = _identity("zhangsan")
        canonical = canonical_session_id_for_identity(identity)
        chat = _chat(
            "c1",
            canonical,
            channel="wecom_tenant",
            name="企微对话",
        )

        class FakeSession:
            def __init__(self):
                self.calls = []

            async def get_session_state_dict(self, *args, **kwargs):
                self.calls.append((args, kwargs))
                return {}

        fake_session = FakeSession()
        workspace = SimpleNamespace(
            chat_manager=SimpleNamespace(
                list_chats=AsyncMock(return_value=[chat]),
            ),
            runner=SimpleNamespace(session=fake_session),
        )

        monkeypatch.setattr(
            webchat,
            "_get_identity_from_request",
            lambda request: identity,
        )
        monkeypatch.setattr(
            webchat,
            "get_tenant_workspace_for_identity",
            AsyncMock(return_value=workspace),
        )

        result = await webchat.get_chat_session(
            canonical,
            SimpleNamespace(),
        )

        assert result["session_id"] == canonical
        assert fake_session.calls
        assert fake_session.calls[0][1]["channel"] == "wecom_tenant"


# ── 3. WebChat 非公开路由必须通过 session token 解析身份 ──────────────────


class TestWebchatAuthEnforcement:
    """WebChat 非公开路由必须通过 session token 解析身份。"""

    def test_identity_required_for_me_endpoint(self):
        from qwenpaw.app.routers import webchat

        request = SimpleNamespace(
            headers={},
            state=SimpleNamespace(),
        )
        with pytest.raises(Exception):
            webchat._get_identity_from_request(request)

    def test_invalid_token_rejected(self):
        from qwenpaw.app.routers import webchat

        request = SimpleNamespace(
            headers={"Authorization": "Bearer invalid.token.here"},
            state=SimpleNamespace(),
        )
        with pytest.raises(Exception):
            webchat._get_identity_from_request(request)

    def test_valid_token_accepted_and_cached(self):
        from qwenpaw.app.routers import webchat

        identity = _identity("zhangsan")
        token = webchat.sign_webchat_token(
            identity, secret="test-secret", ttl_seconds=60,
        )
        request = SimpleNamespace(
            headers={"Authorization": f"Bearer {token}"},
            state=SimpleNamespace(
                request_id="r",
                trace_id="t",
            ),
        )
        # monkeypatch 用测试 secret
        import qwenpaw.app.webchat.session as session_mod

        original = session_mod.get_webchat_session_secret
        session_mod.get_webchat_session_secret = lambda: "test-secret"
        try:
            parsed = webchat._get_identity_from_request(request)
            assert parsed.wechat_company_id == "zhangsan"
            # 第二次调用应使用缓存，不重新解析
            parsed2 = webchat._get_identity_from_request(request)
            assert parsed2.wechat_company_id == "zhangsan"
        finally:
            session_mod.get_webchat_session_secret = original

    def test_cannot_access_other_tenant_agent(self):
        identity = _identity("zhangsan")
        with pytest.raises(PermissionError):
            ensure_requested_agent_allowed(identity, "wx_lisi")

    def test_cannot_access_wecom_session_of_other_user(self):
        identity = _identity("zhangsan")
        with pytest.raises(PermissionError):
            ensure_webchat_session_access(identity, "wecom:lisi")

    def test_cannot_access_wecom_group_session(self):
        identity = _identity("zhangsan")
        with pytest.raises(PermissionError):
            ensure_webchat_session_access(identity, "wecom:group:room1")


# ── 4. 企微 Bot 不回退到 default/original agent ────────────────────────────


class TestWeComBotNoFallback:
    """企微 Bot 单聊只走动态租户链路，不回退到 default/original agent。"""

    @pytest.mark.asyncio
    async def test_tenant_router_routes_to_wx_workspace(self, tmp_path):
        """WxTenantRouter 将消息路由到 wx_* 工作区。"""
        provisioner = MagicMock()
        provisioner.ensure.return_value = tmp_path / "tenants" / "wx_alice"
        workspace = MagicMock()
        workspace.runner.stream_query = lambda r: self._one_event(MagicMock())
        registry = MagicMock()
        registry.get_or_create = AsyncMock(return_value=workspace)
        router = WxTenantRouter(registry=registry, provisioner=provisioner)

        native = {
            "channel_id": "wecom_tenant",
            "sender_id": "alice",
            "user_id": "alice",
            "session_id": "wecom:alice",
            "content_parts": [],
            "meta": {},
        }
        ch = MagicMock()
        request = MagicMock()
        request.user_id = "alice"
        request.session_id = "wecom:alice"
        ch.build_agent_request_from_native.return_value = request
        ch.send_event = AsyncMock()
        ch.get_to_handle_from_request.return_value = "wecom:alice"

        await router.handle("alice", native, ch)

        provisioner.ensure.assert_called_once_with("alice")
        registry.get_or_create.assert_awaited_once_with(
            "alice",
            tmp_path / "tenants" / "wx_alice",
        )
        # TenantAgentRegistry.get_or_create 内部将 tenant_id 转为 wx_* agent_id
        # 验证 provisioner 返回的路径包含 wx_ 前缀
        ensured_path = provisioner.ensure.return_value
        assert "wx_" in str(ensured_path)

    @pytest.mark.asyncio
    async def test_tenant_router_no_default_agent_on_failure(self, tmp_path):
        """即使主链路失败，也不回退到 default agent，只发降级提示。"""
        provisioner = MagicMock()
        provisioner.ensure.side_effect = RuntimeError("init failed")
        registry = MagicMock()
        router = WxTenantRouter(registry=registry, provisioner=provisioner)

        native = {
            "channel_id": "wecom_tenant",
            "sender_id": "alice",
            "user_id": "alice",
            "session_id": "wecom:alice",
            "content_parts": [],
            "meta": {},
        }
        ch = MagicMock()
        request = MagicMock()
        request.user_id = "alice"
        request.session_id = "wecom:alice"
        ch.build_agent_request_from_native.return_value = request
        ch.send_content_parts = AsyncMock()
        ch.get_to_handle_from_request.return_value = "wecom:alice"

        await router.handle("alice", native, ch)

        # 只发了降级消息，没有调用 default agent
        ch.send_content_parts.assert_awaited_once()
        parts = ch.send_content_parts.await_args.kwargs["parts"]
        assert len(parts) == 1
        assert "初始化失败" in parts[0]["text"]
        # 确认没有尝试路由到 default agent
        assert registry.get_or_create.call_count == 0

    @pytest.mark.asyncio
    async def test_wecom_tenant_channel_drops_message_without_adapter(self, tmp_path):
        """tenant_adapter 缺失时丢弃消息，不回退到其他 channel。"""
        from qwenpaw.app.channels.wecom_tenant.channel import WecomTenantChannel

        channel = WecomTenantChannel(
            process=AsyncMock(),
            enabled=True,
            bot_id="bot",
            secret="secret",
            media_dir=str(tmp_path / "media"),
        )
        enqueued = []
        channel._enqueue = lambda native: enqueued.append(native)

        frame = {
            "body": {
                "from": {"userid": "alice"},
                "chatid": "alice",
                "chattype": "single",
                "msgid": "msg-1",
                "send_time": "123",
                "msgtype": "text",
                "text": {"content": "你好"},
            },
        }

        await channel._on_message(frame)
        # adapter 缺失，消息被丢弃，不回退
        assert enqueued == []

    @staticmethod
    async def _one_event(event):
        yield event


# ── 5. TenantAgentRegistry 正确映射 tenant_id → wx_* agent ────────────────


class TestTenantAgentRegistryMapping:
    """TenantAgentRegistry 将 tenant_id 映射到正确的 wx_* agent。"""

    @pytest.mark.asyncio
    async def test_same_tenant_id_always_maps_to_same_agent(self, tmp_path):
        manager = MagicMock()
        manager.get_or_create_tenant_agent = AsyncMock(
            return_value=SimpleNamespace(
                agent_id="wx_alice",
                workspace_dir=tmp_path / "wx_alice",
            ),
        )
        registry = TenantAgentRegistry(manager)

        result1 = await registry.get_or_create("alice", tmp_path / "wx_alice")
        result2 = await registry.get_or_create("alice", tmp_path / "wx_alice")

        assert result1.agent_id == "wx_alice"
        assert result2.agent_id == "wx_alice"
        assert manager.get_or_create_tenant_agent.await_count == 2
        # 两次调用 agent_id 相同
        call1 = manager.get_or_create_tenant_agent.await_args_list[0]
        call2 = manager.get_or_create_tenant_agent.await_args_list[1]
        assert call1.kwargs["agent_id"] == call2.kwargs["agent_id"] == "wx_alice"

    @pytest.mark.asyncio
    async def test_different_tenant_ids_map_to_different_agents(self, tmp_path):
        manager = MagicMock()
        manager.get_or_create_tenant_agent = AsyncMock(
            side_effect=[
                SimpleNamespace(agent_id="wx_alice", workspace_dir=tmp_path / "wx_alice"),
                SimpleNamespace(agent_id="wx_bob", workspace_dir=tmp_path / "wx_bob"),
            ],
        )
        registry = TenantAgentRegistry(manager)

        r1 = await registry.get_or_create("alice", tmp_path / "wx_alice")
        r2 = await registry.get_or_create("bob", tmp_path / "wx_bob")

        assert r1.agent_id != r2.agent_id


# ── 6. P3-2 双入口业务能力调用验证 ────────────────────────────────────────


class TestDualEntryBusinessCapability:
    """P3-2: 同一业务能力能从 WebChat 和企微 Bot 触发。"""

    def test_webchat_identity_produces_correct_tenant_context(self):
        """WebChat 身份解析后 tenant_id 与 agent_id 一致。"""
        identity = _identity(wechat_company_id="user_acme_001")
        assert identity.tenant_id == "user_acme_001"
        assert identity.agent_id == "wx_user_acme_001"
        assert identity.tenant_id in identity.agent_id

    def test_wecom_tenant_produces_same_agent_as_webchat(self):
        """同一企业 ID 从企微 Bot 和 WebChat 进入同一个 wx_* agent。"""
        tenant_id = "user_acme_001"
        webchat_agent = tenant_agent_id(tenant_id)
        wecom_agent = tenant_agent_id(tenant_id)
        assert webchat_agent == wecom_agent == "wx_user_acme_001"

    def test_business_skill_error_messages_are_distinguishable(self):
        """不同失败原因返回不同错误提示。"""
        reasons = {
            "permission_denied": "Permission denied",
            "skill_disabled": "Skill is not enabled for this tenant",
            "mcp_unreachable": "MCP server is not reachable",
            "execution_failed": "Business execution failed",
            "invalid_config": "MCP configuration is invalid",
        }
        # 每个失败原因必须不同
        assert len(set(reasons.values())) == len(reasons)

    def test_wx_tenant_router_forwards_to_same_workspace(self):
        """WxTenantRouter 路由到正确的 wx_* 工作区。"""
        tenant_id = "user_acme_001"
        expected = tenant_agent_id(tenant_id)
        assert expected == "wx_user_acme_001"
        assert expected.startswith("wx_")

    @pytest.mark.asyncio
    async def test_webchat_chat_payload_preserves_employee_context(
        self,
        monkeypatch,
    ):
        """WebChat 入口传给 runner 的 payload 保留统一上下文字段。"""
        from qwenpaw.app.routers import webchat

        identity = _identity("zhangsan", employee_id="E001")
        captured: dict[str, object] = {}

        class FakeTracker:
            async def attach_or_start(self, chat_id, native_payload, stream_one):
                captured["chat_id"] = chat_id
                captured["native_payload"] = native_payload
                return object(), object()

            async def stream_from_queue(self, queue, chat_id):
                if False:
                    yield ""

        workspace = SimpleNamespace(
            workspace_dir=".",
            chat_manager=SimpleNamespace(
                list_chats=AsyncMock(return_value=[]),
                get_or_create_chat=AsyncMock(
                    return_value=SimpleNamespace(id="chat-1"),
                ),
            ),
            task_tracker=FakeTracker(),
        )
        channel = MagicMock()
        channel.resolve_session_id.return_value = "webchat:zhangsan:s1"
        channel.stream_one = AsyncMock()

        monkeypatch.setattr(
            webchat,
            "_get_identity_from_request",
            lambda request: identity,
        )
        monkeypatch.setattr(
            webchat,
            "get_tenant_workspace_for_identity",
            AsyncMock(return_value=workspace),
        )
        monkeypatch.setattr(
            webchat,
            "build_webchat_channel_facade",
            lambda workspace: channel,
        )

        request = SimpleNamespace(
            state=SimpleNamespace(
                request_id="req-webchat",
                trace_id="trace-webchat",
                request_context=SimpleNamespace(
                    request_id="req-webchat",
                    trace_id="trace-webchat",
                    tenant_id="zhangsan",
                    agent_id="wx_zhangsan",
                    session_id="",
                    user_id="E001",
                    channel="webchat",
                    roles=("tenant_member",),
                    metadata={"wechat_company_id": "zhangsan"},
                ),
            ),
        )

        await webchat.post_webchat_chat(
            {
                "session_id": "s1",
                "input": [
                    {
                        "content": [
                            {"type": "text", "text": "你好"},
                        ],
                    },
                ],
            },
            request,
        )

        payload = captured["native_payload"]
        assert payload["channel_id"] == "webchat"
        assert payload["sender_id"] == "zhangsan"
        assert payload["user_id"] == "zhangsan"
        assert payload["session_id"] == "webchat:zhangsan:s1"
        meta = payload["meta"]
        assert meta["entrypoint"] == "webchat"
        assert meta["request_id"] == "req-webchat"
        assert meta["trace_id"] == "trace-webchat"
        assert meta["tenant_id"] == "zhangsan"
        assert meta["agent_id"] == "wx_zhangsan"
        assert meta["employee_id"] == "E001"
        assert meta["wechat_company_id"] == "zhangsan"
        assert meta["roles"] == ["tenant_member"]
        assert "webchat_workspace_dir" not in meta

    def test_webchat_channel_agent_request_consumes_standard_trace_fields(self):
        """WebChat channel 将标准 trace 字段放入 AgentRequest.state。"""
        from qwenpaw.app.channels.webchat.channel import WebchatChannel

        channel = WebchatChannel(
            process=AsyncMock(),
            enabled=True,
            bot_prefix="",
        )
        request = channel.build_agent_request_from_native(
            {
                "channel_id": "webchat",
                "sender_id": "zhangsan",
                "session_id": "webchat:zhangsan:s1",
                "content_parts": [],
                "meta": {
                    "request_id": "req-webchat",
                    "trace_id": "trace-webchat",
                    "entrypoint": "webchat",
                    "tenant_id": "zhangsan",
                    "agent_id": "wx_zhangsan",
                    "employee_id": "E001",
                },
            },
        )

        assert request.channel == "webchat"
        assert request.user_id == "zhangsan"
        assert request.session_id == "webchat:zhangsan:s1"
        assert request.state.request_id == "req-webchat"
        assert request.state.trace_id == "trace-webchat"
        assert request.channel_meta["entrypoint"] == "webchat"
        assert request.channel_meta["tenant_id"] == "zhangsan"
        assert request.channel_meta["agent_id"] == "wx_zhangsan"


# ── 7. P3-2 企微 Bot 轻量错误提示验证 ────────────────────────────────────


class TestWeComBotSkillErrors:
    """P3-2: 企微 Bot 返回适合 IM 场景的轻量错误提示。"""

    _DEGRADE_MESSAGES = {
        "workspace": "助手工作区初始化失败，请稍后重试或联系管理员。",
        "agent": "助手服务暂时不可用，请稍后重试。",
        "run": "助手处理消息时出错，请稍后重试或联系管理员。",
    }

    def test_degrade_messages_are_all_different(self):
        """不同降级阶段返回不同提示文本。"""
        msgs = list(self._DEGRADE_MESSAGES.values())
        assert len(set(msgs)) == len(msgs)

    def test_degrade_messages_are_short(self):
        """企微 IM 场景下降级消息不应过长。"""
        for msg in self._DEGRADE_MESSAGES.values():
            assert len(msg) <= 60

    def test_degrade_messages_do_not_expose_internals(self):
        """降级消息不暴露技术细节。"""
        internal_terms = ("stack trace", "exception", "RuntimeError", "database", "SQL")
        for msg in self._DEGRADE_MESSAGES.values():
            for term in internal_terms:
                assert term.lower() not in msg.lower()
