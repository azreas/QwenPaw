# -*- coding: utf-8 -*-
"""P3-2 业务能力调用追踪测试：审计事件 payload 和指标标签。"""
import pytest
from agentscope.message import Msg

from qwenpaw.agents.mcp_tracer import McpToolTrace
from qwenpaw.enterprise.audit.emit import (
    emit_audit_event,
    emit_business_call_event,
    emit_platform_invocation_event,
)
from qwenpaw.enterprise.audit.models import AuditEventType, AuditOutcome
from qwenpaw.enterprise.context import RequestActor, RequestContext
from qwenpaw.enterprise.observability.metrics import MetricsRegistry
from qwenpaw.enterprise.interfaces import RuntimeExtensionBundle


class CaptureBus:
    def __init__(self):
        self.events = []

    async def emit(self, event):
        self.events.append(event)


class AllowAuthz:
    async def check_permission(self, ctx, resource, action):
        from qwenpaw.enterprise.interfaces import AuthzDecision

        return AuthzDecision(allowed=True, reason="test")


def _make_request(ctx: RequestContext | None = None):
    """构造带有 enterprise_runtime 和 request_context 的 request 对象。"""
    bus = CaptureBus()
    runtime = type("Runtime", (), {"audit": bus})()
    app = type(
        "App",
        (),
        {"state": type("State", (), {"enterprise_runtime": runtime})()},
    )()
    state = type("State", (), {"request_id": "r1", "trace_id": "t1", "request_context": ctx})()
    return type("Request", (), {"app": app, "state": state})(), bus


class FakeBusinessAgent:
    """Simulate an installed Skill path that invokes one MCP tool."""

    instances = []

    def __init__(self, **kwargs):
        skill_dir = kwargs["workspace_dir"] / "skills" / "sales_report"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: sales_report\ndescription: sales report\n---\nRun report.\n",
            encoding="utf-8",
        )
        self.toolkit = type(
            "Toolkit",
            (),
            {
                "skills": {
                    "sales_report": {
                        "dir": str(skill_dir),
                    },
                },
            },
        )()
        self._mcp_tool_traces = [
            McpToolTrace(
                tool_name="query_sales",
                mcp_name="sales_mcp",
                duration_ms=12.0,
                status="success",
            )
        ]
        self.seen_user_text = ""
        FakeBusinessAgent.instances.append(self)

    async def __call__(self, msgs):
        self.seen_user_text = msgs[-1].get_text_content()
        return Msg("assistant", "done", "assistant")

    async def register_mcp_clients(self):
        return None

    def set_console_output_enabled(self, enabled):
        return None

    def rebuild_sys_prompt(self):
        return None

    def set_msg_queue_enabled(self, enabled, queue):
        return None

    async def interrupt(self):
        return None


class FakeRunnerRequest:
    def __init__(self, *, session_id: str, user_id: str, channel: str):
        self.session_id = session_id
        self.user_id = user_id
        self.channel = channel
        self.root_session_id = ""
        self.channel_meta = {}
        self.state = type("State", (), {"request_id": "req-run", "trace_id": "trace-run"})()


# ── skill.call / mcp.call 审计事件 ────────────────────────────


@pytest.mark.asyncio
async def test_emit_skill_call_event_has_required_fields():
    ctx = RequestContext(
        request_id="req-s",
        trace_id="trace-s",
        tenant_id="wx_acme",
        agent_id="wx_acme",
        session_id="wecom:u1",
        user_id="u1",
        channel="wecom_tenant",
        actor=RequestActor(actor_id="u1", actor_type="channel_user"),
    )
    request, bus = _make_request(ctx)

    await emit_business_call_event(
        request=request,
        ability_type="skill",
        ability_name="data_analysis",
        status="success",
        duration_ms=123.4,
        entrypoint="wecom_tenant",
    )

    assert len(bus.events) == 1
    event = bus.events[0]
    assert event.event_type == AuditEventType.SKILL_CALLED
    assert event.outcome == AuditOutcome.SUCCESS
    payload = event.payload
    assert payload["entrypoint"] == "wecom_tenant"
    assert payload["tenant_id"] == "wx_acme"
    assert payload["agent_id"] == "wx_acme"
    assert payload["session_id"] == "wecom:u1"
    assert payload["ability_type"] == "skill"
    assert payload["ability_name"] == "data_analysis"
    assert payload["duration_ms"] == 123.4
    assert payload["status"] == "success"
    assert payload["error_reason"] == ""


@pytest.mark.asyncio
async def test_emit_mcp_call_event_failure_with_reason():
    ctx = RequestContext(
        request_id="req-m",
        trace_id="trace-m",
        tenant_id="wx_acme",
        agent_id="wx_acme",
        session_id="s1",
        user_id="u1",
        channel="webchat",
        actor=RequestActor(actor_id="u1", actor_type="webchat_user"),
    )
    request, bus = _make_request(ctx)

    await emit_business_call_event(
        request=request,
        ability_type="mcp",
        ability_name="doris_query",
        status="failure",
        duration_ms=5030.0,
        error_reason="MCP server unreachable: connection refused",
        entrypoint="webchat",
    )

    assert len(bus.events) == 1
    event = bus.events[0]
    assert event.event_type == AuditEventType.MCP_CALLED
    assert event.outcome == AuditOutcome.FAILURE
    payload = event.payload
    assert payload["entrypoint"] == "webchat"
    assert payload["ability_type"] == "mcp"
    assert payload["ability_name"] == "doris_query"
    assert payload["duration_ms"] == 5030.0
    assert payload["status"] == "failure"
    assert "connection refused" in payload["error_reason"]


@pytest.mark.asyncio
async def test_emit_platform_invocation_event_for_builtin_tool():
    ctx = RequestContext(
        request_id="req-tool",
        trace_id="trace-tool",
        tenant_id="wx_acme",
        agent_id="wx_acme",
        session_id="s1",
        user_id="u1",
        channel="webchat",
        actor=RequestActor(actor_id="u1", actor_type="webchat_user"),
    )
    request, bus = _make_request(ctx)

    await emit_platform_invocation_event(
        request=request,
        call_type="builtin_tool",
        call_name="file_search",
        status="success",
        duration_ms=10.5,
    )

    event = bus.events[0]
    assert event.event_type == AuditEventType.PLATFORM_INVOCATION
    assert event.payload["call_type"] == "builtin_tool"
    assert event.payload["call_name"] == "file_search"
    assert event.payload["status"] == "success"
    assert event.payload["trace_id"] == "trace-tool"


@pytest.mark.asyncio
async def test_emit_business_call_uses_channel_as_fallback_entrypoint():
    ctx = RequestContext(
        request_id="req",
        trace_id="trace",
        channel="wecom_tenant",
        actor=RequestActor(actor_id="u1"),
    )
    request, bus = _make_request(ctx)

    await emit_business_call_event(
        request=request,
        ability_type="skill",
        ability_name="sales_report",
        status="success",
        duration_ms=50.0,
    )

    assert bus.events[0].payload["entrypoint"] == "wecom_tenant"


@pytest.mark.asyncio
async def test_emit_business_call_unknown_type_is_silent():
    """未知能力类型不发送事件。"""
    ctx = RequestContext(request_id="r", trace_id="t")
    request, bus = _make_request(ctx)

    await emit_business_call_event(
        request=request,
        ability_type="unknown_type",
        ability_name="whatever",
        status="success",
        duration_ms=1.0,
    )

    assert len(bus.events) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("channel", "session_id"),
    [
        ("webchat", "webchat:acme:s1"),
        ("wecom_tenant", "wecom:acme"),
    ],
)
async def test_runner_records_skill_and_mcp_business_trace_for_dual_entry(
    tmp_path,
    monkeypatch,
    channel,
    session_id,
):
    """入口触发样例 Skill 后，Runner 应消费 MCP trace 并记录业务追踪。"""
    from qwenpaw.app.runner.runner import AgentRunner

    FakeBusinessAgent.instances.clear()
    monkeypatch.setattr("qwenpaw.app.runner.runner.QwenPawAgent", FakeBusinessAgent)
    monkeypatch.setattr(
        "qwenpaw.app.runner.runner.load_agent_config",
        lambda agent_id: type("Cfg", (), {"plan": type("Plan", (), {"enabled": False})(), "running": type("Running", (), {"shell_command_executable": None})()})(),
    )
    async def no_mission(**kwargs):
        return None

    monkeypatch.setattr(
        "qwenpaw.app.runner.runner.maybe_handle_mission_command",
        no_mission,
    )
    monkeypatch.setattr(
        "qwenpaw.app.runner.runner.detect_active_mission_phase",
        lambda *args, **kwargs: None,
    )

    async def fake_resolve(runtime, ctx):
        return RuntimeExtensionBundle()

    monkeypatch.setattr(
        "qwenpaw.app.runner.runner._resolve_runtime_extensions",
        fake_resolve,
    )

    bus = CaptureBus()
    runner = AgentRunner(agent_id="wx_acme", workspace_dir=tmp_path)
    runner._enterprise_runtime = type(
        "Runtime",
        (),
        {"audit": bus, "authz": AllowAuthz()},
    )()
    await runner.init_handler()

    async def noop(**kwargs):
        return None

    async def empty_state(**kwargs):
        return {}

    runner.session.load_session_state = noop
    runner.session.save_session_state = noop
    runner.session.get_session_state_dict = empty_state

    msgs = [Msg("user", "/sales_report 本周销售", "user")]
    request = FakeRunnerRequest(
        session_id=session_id,
        user_id="acme",
        channel=channel,
    )

    async for _msg, _last in runner.query_handler(msgs, request=request):
        pass

    assert "Use the [sales_report] skill" in FakeBusinessAgent.instances[0].seen_user_text
    assert [event.payload.get("call_type") for event in bus.events] == [
        "agent",
        "skill",
        "mcp",
    ]
    agent_event, skill_event, mcp_event = bus.events
    assert agent_event.event_type == AuditEventType.PLATFORM_INVOCATION
    assert agent_event.payload["status"] == "success"
    assert agent_event.payload["trace_id"] == "trace-run"
    assert skill_event.payload["entrypoint"] == channel
    assert skill_event.payload["tenant_id"] == "acme"
    assert skill_event.payload["agent_id"] == "wx_acme"
    assert skill_event.payload["session_id"] == session_id
    assert skill_event.payload["ability_type"] == "skill"
    assert skill_event.payload["call_type"] == "skill"
    assert skill_event.payload["ability_name"] == "sales_report"
    assert skill_event.payload["status"] == "success"
    assert mcp_event.payload["entrypoint"] == channel
    assert mcp_event.payload["ability_type"] == "mcp"
    assert mcp_event.payload["call_type"] == "mcp"
    assert mcp_event.payload["ability_name"] == "sales_mcp/query_sales"
    assert mcp_event.payload["mcp_name"] == "sales_mcp"
    assert mcp_event.payload["status"] == "success"


# ── 审计事件类型覆盖 ──────────────────────────────────────────


def test_all_p3_2_audit_types_defined():
    """P3-2 需要的中审计事件类型已定义。"""
    expected_types = {
        "skill.installed",
        "skill.enabled",
        "skill.disabled",
        "skill.deleted",
        "skill.called",
        "mcp.created",
        "mcp.updated",
        "mcp.enabled",
        "mcp.disabled",
        "mcp.deleted",
        "mcp.connection_test",
        "mcp.called",
    }
    for et in expected_types:
        assert hasattr(AuditEventType, et.upper().replace(".", "_"))


# ── 指标标签低基数验证 ────────────────────────────────────────


def test_metrics_reject_high_cardinality_labels():
    """指标标签不能包含 user_id/session_id/request_id/trace_id 等高基数字段。"""
    registry = MetricsRegistry()

    # 低基数字段正常
    registry.inc("business_call_total", labels={
        "ability_type": "skill",
        "status": "success",
        "entrypoint": "webchat",
    })
    assert len(registry.samples()) == 1

    # 高基数字段应拒绝
    with pytest.raises(ValueError, match="high-cardinality"):
        registry.inc("business_call_total", labels={
            "ability_type": "skill",
            "user_id": "u1",
        })


def test_metrics_low_cardinality_labels_accepted():
    """业务能力调用指标的低基数标签应正常通过。"""
    registry = MetricsRegistry()
    low_card_labels = [
        {"ability_type": "skill", "status": "success"},
        {"ability_type": "mcp", "status": "failure", "entrypoint": "wecom_tenant"},
        {"ability_type": "skill", "error_category": "permission_denied"},
    ]
    for labels in low_card_labels:
        registry.inc("business_call_total", labels=labels)

    samples = registry.samples()
    assert len(samples) == 3  # 每组标签一个独立计数器
