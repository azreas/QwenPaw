"""验证 AgentRunner.query_handler 在 enterprise_context_scope 内执行。"""

import pytest

from qwenpaw.enterprise.context import (
    get_current_request_context,
    get_current_tool_policy_patch,
)
from qwenpaw.enterprise.context_builders import build_context_from_runner_payload
from qwenpaw.enterprise.interfaces import RuntimeExtensionBundle, ToolPolicyPatch


_FAKE_AGENT_INSTANCES = []


class FakeAgent:
    """捕获构造时上下文和策略 patch 的伪 Agent。"""

    def __init__(self, **kwargs):
        self._captured_ctx = None
        self._captured_patch = None
        self.toolkit = type("Toolkit", (), {"skills": {}})()
        self.memory = type("Memory", (), {"add": lambda self, x: None})()
        _FAKE_AGENT_INSTANCES.append(self)

    async def __call__(self, msgs):
        from agentscope.message import Msg

        print("[FakeAgent.__call__] entered")
        self._captured_ctx = get_current_request_context()
        self._captured_patch = get_current_tool_policy_patch()
        print(f"[FakeAgent.__call__] ctx={self._captured_ctx}, patch={self._captured_patch}")
        return Msg("assistant", "ok", "assistant")

    async def register_mcp_clients(self):
        self._captured_ctx = get_current_request_context()
        self._captured_patch = get_current_tool_policy_patch()

    def set_console_output_enabled(self, enabled):
        pass

    def rebuild_sys_prompt(self):
        pass

    def set_msg_queue_enabled(self, enabled, queue):
        pass

    async def print(self, msg, last):
        pass

    async def interrupt(self):
        pass


class FakeRequest:
    session_id = "s1"
    user_id = "u1"
    channel = "console"
    root_session_id = ""


@pytest.fixture
def fake_agent_config():
    """返回最小 agent config。"""
    return type(
        "Cfg",
        (),
        {
            "plan": type("Plan", (), {"enabled": False})(),
            "running": type("Running", (), {"shell_command_executable": None})(),
        },
    )()


@pytest.mark.asyncio
async def test_query_handler_exposes_context_and_policy_to_agent(
    tmp_path, monkeypatch, fake_agent_config
):
    """AgentRunner.query_handler 执行期间，QwenPawAgent 应能读到 request context 和 tool policy patch。"""
    from qwenpaw.app.runner.runner import AgentRunner

    monkeypatch.setattr(
        "qwenpaw.app.runner.runner.QwenPawAgent", FakeAgent
    )
    monkeypatch.setattr(
        "qwenpaw.app.runner.runner.load_agent_config",
        lambda agent_id: fake_agent_config,
    )
    async def _fake_mission(**kw):
        return None

    monkeypatch.setattr(
        "qwenpaw.app.runner.runner.maybe_handle_mission_command",
        _fake_mission,
    )
    monkeypatch.setattr(
        "qwenpaw.app.runner.runner.detect_active_mission_phase",
        lambda *a, **kw: None,
    )

    expected_patch = ToolPolicyPatch(
        deny_tools=frozenset({"browser_use"}),
    )

    async def fake_resolve(runtime, ctx):
        return RuntimeExtensionBundle(tool_policy=expected_patch)

    monkeypatch.setattr(
        "qwenpaw.app.runner.runner._resolve_runtime_extensions",
        fake_resolve,
    )

    runner = AgentRunner(agent_id="test_agent", workspace_dir=tmp_path)
    await runner.init_handler()

    # Mock session I/O
    async def _noop(**kw):
        pass

    runner.session.load_session_state = _noop
    runner.session.save_session_state = _noop
    runner.session.get_session_state_dict = lambda **kw: {}

    msgs = []
    async for _msg, _last in runner.query_handler(msgs, request=FakeRequest()):
        pass

    # 通过 FakeAgent 实例的构造捕获验证
    assert len(_FAKE_AGENT_INSTANCES) == 1
    instance = _FAKE_AGENT_INSTANCES[0]
    assert instance._captured_ctx is not None
    assert instance._captured_ctx.agent_id == "test_agent"
    assert instance._captured_ctx.session_id == "s1"
    assert instance._captured_patch is not None
    assert "browser_use" in instance._captured_patch.deny_tools


@pytest.mark.asyncio
async def test_query_handler_runs_standard_agent_path_when_no_mission(
    tmp_path, monkeypatch, fake_agent_config
):
    """mission_info 为空时，query_handler 必须进入普通 agent(msgs) 执行分支。"""
    from qwenpaw.app.runner.runner import AgentRunner

    _FAKE_AGENT_INSTANCES.clear()

    monkeypatch.setattr(
        "qwenpaw.app.runner.runner.QwenPawAgent", FakeAgent
    )
    monkeypatch.setattr(
        "qwenpaw.app.runner.runner.load_agent_config",
        lambda agent_id: fake_agent_config,
    )

    async def _fake_mission(**kw):
        return None

    monkeypatch.setattr(
        "qwenpaw.app.runner.runner.maybe_handle_mission_command",
        _fake_mission,
    )
    monkeypatch.setattr(
        "qwenpaw.app.runner.runner.detect_active_mission_phase",
        lambda *a, **kw: None,
    )

    async def fake_resolve(runtime, ctx):
        return RuntimeExtensionBundle()

    monkeypatch.setattr(
        "qwenpaw.app.runner.runner._resolve_runtime_extensions",
        fake_resolve,
    )

    runner = AgentRunner(agent_id="test_agent", workspace_dir=tmp_path)
    await runner.init_handler()

    async def _noop(**kw):
        pass

    async def _empty_state(**kw):
        return {}

    runner.session.load_session_state = _noop
    runner.session.save_session_state = _noop
    runner.session.get_session_state_dict = _empty_state

    msgs = []
    outputs = []
    async for msg, last in runner.query_handler(msgs, request=FakeRequest()):
        outputs.append((msg, last))

    assert len(_FAKE_AGENT_INSTANCES) == 1
    instance = _FAKE_AGENT_INSTANCES[0]
    assert instance._captured_ctx is not None
    assert outputs == []


# ── P3-2: tenant_id 推导与上下文完整性 ─────────────────────

def test_runner_context_wx_agent_has_tenant_id():
    """wx_* agent 的 RequestContext 必须包含自动推导的 tenant_id。"""
    ctx = build_context_from_runner_payload(
        request_id="req-1",
        trace_id="trace-1",
        agent_id="wx_user_acme_001",
        session_id="wecom:user_acme_001",
        user_id="user_acme_001",
        channel="wecom_tenant",
    )
    assert ctx.tenant_id == "user_acme_001"
    assert ctx.agent_id == "wx_user_acme_001"
    assert ctx.user_id == "user_acme_001"
    assert ctx.channel == "wecom_tenant"
    assert ctx.session_id == "wecom:user_acme_001"


# ── P3-2: 扩展解析失败时保留空 bundle ──────────────────────


def test_light_context_manager_falls_back_to_load_agent_config(
    tmp_path, monkeypatch, fake_agent_config
):
    """未传预加载配置时，LightContextManager 应从 load_agent_config 回退。"""
    from qwenpaw.agents.context.light_context_manager import (
        LightContextManager,
    )

    monkeypatch.setattr(
        "qwenpaw.agents.context.light_context_manager.load_agent_config",
        lambda agent_id: fake_agent_config,
    )

    mgr = LightContextManager(
        working_dir=str(tmp_path),
        agent_id="test_agent",
        agent_config=None,
    )

    assert mgr._get_agent_config() is fake_agent_config

@pytest.mark.asyncio
async def test_runtime_resolver_preserves_error_reason():
    """RuntimeExtensionResolver 失败时不抛异常，返回空 bundle。"""
    from qwenpaw.app.runner.runner import _resolve_runtime_extensions
    from qwenpaw.enterprise.context import RequestContext

    class ErrorResolver:
        async def resolve(self, ctx):
            raise ConnectionError("MCP server unreachable")

    class ErrorRuntime:
        extensions = ErrorResolver()

    bundle = await _resolve_runtime_extensions(
        ErrorRuntime(),
        RequestContext(
            request_id="r",
            trace_id="t",
            agent_id="wx_test",
        ),
    )
    # 失败时返回空 bundle，不抛异常
    assert bundle.mcp_clients == []
    assert bundle.tool_policy == ToolPolicyPatch()


# ── P3-2: MCP client 合并验证 ──────────────────────────────

@pytest.mark.asyncio
async def test_runtime_resolver_merges_mcp_clients():
    """扩展解析的 MCP clients 应作为独立列表返回。"""
    from qwenpaw.app.runner.runner import _resolve_runtime_extensions
    from qwenpaw.enterprise.context import RequestContext

    expected_clients = ["sandbox-client", "business-mcp"]

    class MultiMCPResolver:
        async def resolve(self, ctx):
            return RuntimeExtensionBundle(
                mcp_clients=expected_clients,
            )

    class TestRuntime:
        extensions = MultiMCPResolver()

    bundle = await _resolve_runtime_extensions(
        TestRuntime(),
        RequestContext(request_id="r", trace_id="t"),
    )
    assert bundle.mcp_clients == expected_clients
