# -*- coding: utf-8 -*-
from qwenpaw.enterprise.context_builders import build_context_from_runner_payload


def test_runner_context_contains_agent_and_root_session():
    ctx = build_context_from_runner_payload(
        request_id="r",
        trace_id="t",
        agent_id="default",
        session_id="child",
        root_session_id="root",
        user_id="u1",
        channel="webchat",
    )
    assert ctx.agent_id == "default"
    assert ctx.session_id == "child"
    assert ctx.root_session_id == "root"
    assert ctx.user_id == "u1"
    assert ctx.channel == "webchat"


def test_runner_context_defaults_root_session_to_session():
    ctx = build_context_from_runner_payload(
        request_id="r",
        trace_id="t",
        agent_id="default",
        session_id="s1",
        user_id="u1",
        channel="console",
    )
    assert ctx.root_session_id == "s1"


def test_runner_safe_state_access_without_state():
    """AgentRequest 没有 state 字段时，runner 不会 AttributeError。"""
    from types import SimpleNamespace

    # 模拟真实 AgentRequest：无 state 字段
    request = SimpleNamespace(
        session_id="s1",
        user_id="u1",
        channel="webchat",
        root_session_id="",
    )

    # 模拟 runner.py 中的安全访问逻辑
    _req_state = getattr(request, "state", None)
    _req_id = getattr(_req_state, "request_id", "") if _req_state else ""
    _trace_id = getattr(_req_state, "trace_id", "") if _req_state else ""

    # 应该不会报错，且生成空字符串
    assert _req_id == ""
    assert _trace_id == ""

    ctx = build_context_from_runner_payload(
        request_id=_req_id,
        trace_id=_trace_id,
        agent_id="default",
        session_id=request.session_id,
        user_id=request.user_id,
        channel=getattr(request, "channel", "console"),
    )
    # 缺失时自动生成 UUID
    assert ctx.request_id != ""
    assert ctx.trace_id != ""


# ── P3-2: Skill 命令解析只匹配真实已安装 Skill ─────────────


def test_runner_skill_command_ignores_unknown_slash_command(tmp_path):
    """未知 slash 命令不应触发 skills:call 权限检查或 skill.call 追踪。"""
    from qwenpaw.app.runner.runner import AgentRunner

    skills = {"sales": {"dir": str(tmp_path / "sales_report")}}

    assert (
        AgentRunner._resolve_existing_skill_command("/unknown hello", skills)
        is None
    )


def test_runner_skill_command_matches_installed_skill(tmp_path):
    """只有真实安装的 Skill 命令才进入业务技能调用链路。"""
    from qwenpaw.app.runner.runner import AgentRunner

    skills = {"sales": {"dir": str(tmp_path / "sales_report")}}

    assert AgentRunner._resolve_existing_skill_command(
        "/sales_report hello",
        skills,
    ) == ("sales_report", True)


# ── P3-2: wx_* tenant_id 推导 ──────────────────────────────

def test_runner_context_derives_tenant_from_wx_agent():
    """wx_* agent 未传入 tenant_id 时自动从 agent_id 推导。"""
    ctx = build_context_from_runner_payload(
        request_id="r",
        trace_id="t",
        agent_id="wx_user_acme_001",
        session_id="s1",
        user_id="u1",
        channel="wecom_tenant",
    )
    assert ctx.tenant_id == "user_acme_001"
    assert ctx.agent_id == "wx_user_acme_001"


def test_runner_context_tenant_id_not_overwritten_when_provided():
    """显式传入 tenant_id 时不从 agent_id 推导。"""
    ctx = build_context_from_runner_payload(
        request_id="r",
        trace_id="t",
        agent_id="wx_alice",
        tenant_id="explicit_tenant",
        session_id="s1",
        user_id="u1",
        channel="webchat",
    )
    assert ctx.tenant_id == "explicit_tenant"


def test_runner_context_no_tenant_derivation_for_default_agent():
    """非 wx_* agent 不推导 tenant_id。"""
    ctx = build_context_from_runner_payload(
        request_id="r",
        trace_id="t",
        agent_id="default",
        session_id="s1",
        user_id="u1",
        channel="console",
    )
    assert ctx.tenant_id == ""


def test_runner_context_full_fields_for_wx_tenant():
    """P3-2: wx_* agent 的 RequestContext 包含入口、用户、租户、agent、session。"""
    ctx = build_context_from_runner_payload(
        request_id="req-1",
        trace_id="trace-1",
        agent_id="wx_user_acme_001",
        session_id="wecom:user_acme_001",
        user_id="user_acme_001",
        channel="wecom_tenant",
    )
    assert ctx.agent_id == "wx_user_acme_001"
    assert ctx.tenant_id == "user_acme_001"
    assert ctx.session_id == "wecom:user_acme_001"
    assert ctx.user_id == "user_acme_001"
    assert ctx.channel == "wecom_tenant"
    assert ctx.request_id == "req-1"
    assert ctx.trace_id == "trace-1"
    # P3-2 审查修复：wx_* agent 默认角色为 tenant_member，
    # 使 skills:call / mcp:call 权限检查在真实调用路径生效
    assert ctx.roles == ("tenant_member",)


# ── P3-2 修复：roles 不被默认值覆盖 ──────────────────────


def test_runner_context_explicit_roles_preserved():
    """显式传入 roles 时，不使用默认的 tenant_member。"""
    ctx = build_context_from_runner_payload(
        request_id="r",
        trace_id="t",
        agent_id="wx_user_acme_001",
        session_id="s1",
        user_id="u1",
        channel="webchat",
        roles=("tenant_readonly",),
    )
    assert ctx.roles == ("tenant_readonly",)


def test_runner_context_explicit_empty_roles_not_escalated():
    """显式传入空 roles 时，不默认提升为 tenant_member。

    这确保 tenant_readonly 或显式无 roles 的 WebChat 用户
    不会在 runner 重建 context 时被提升权限。
    """
    ctx = build_context_from_runner_payload(
        request_id="r",
        trace_id="t",
        agent_id="wx_user_acme_001",
        session_id="s1",
        user_id="u1",
        channel="webchat",
        roles=(),
    )
    assert ctx.roles == ()


def test_runner_context_no_roles_default_for_wx():
    """wx_* agent 未传 roles 时，默认 tenant_member（企微 Bot 兼容）。"""
    ctx = build_context_from_runner_payload(
        request_id="r",
        trace_id="t",
        agent_id="wx_acme",
        session_id="s1",
        user_id="u1",
        channel="wecom_tenant",
    )
    assert ctx.roles == ("tenant_member",)


def test_runner_context_no_roles_default_for_non_wx():
    """非 wx_* agent 未传 roles 时，默认空元组。"""
    ctx = build_context_from_runner_payload(
        request_id="r",
        trace_id="t",
        agent_id="default",
        session_id="s1",
        user_id="u1",
        channel="console",
    )
    assert ctx.roles == ()


# ── P3-2 修复：runner meta 提取层 roles 传递 ────────────


def test_runner_meta_empty_roles_list_not_escalated():
    """runner 从 channel_meta 提取 roles 时，空列表不提升为 tenant_member。

    模拟 runner.py 中的 channel_meta 提取逻辑：
    WebChat 传入 identity.roles=() → meta["roles"]=[] → runner 应传 roles=()
    而非 None（None 会触发默认 tenant_member）。
    """
    channel_meta = {"roles": []}
    _raw_roles = channel_meta.get("roles")

    # 与 runner.py 一致的提取逻辑
    _upstream_roles = None
    if isinstance(_raw_roles, (list, tuple)):
        _upstream_roles = tuple(str(r) for r in _raw_roles)

    ctx = build_context_from_runner_payload(
        request_id="r",
        trace_id="t",
        agent_id="wx_user_acme_001",
        session_id="s1",
        user_id="u1",
        channel="webchat",
        roles=_upstream_roles,
    )
    assert ctx.roles == ()


def test_runner_meta_roles_list_preserved():
    """runner 从 channel_meta 提取的 roles 列表正确传递。"""
    channel_meta = {"roles": ["tenant_readonly"]}
    _raw_roles = channel_meta.get("roles")

    _upstream_roles = None
    if isinstance(_raw_roles, (list, tuple)):
        _upstream_roles = tuple(str(r) for r in _raw_roles)

    ctx = build_context_from_runner_payload(
        request_id="r",
        trace_id="t",
        agent_id="wx_user_acme_001",
        session_id="s1",
        user_id="u1",
        channel="webchat",
        roles=_upstream_roles,
    )
    assert ctx.roles == ("tenant_readonly",)


def test_runner_meta_no_roles_key_defaults_to_tenant_member():
    """channel_meta 中无 roles 键时，wx_* 默认 tenant_member。"""
    channel_meta = {"user_name": "alice"}
    _raw_roles = channel_meta.get("roles")

    _upstream_roles = None
    if isinstance(_raw_roles, (list, tuple)):
        _upstream_roles = tuple(str(r) for r in _raw_roles)

    ctx = build_context_from_runner_payload(
        request_id="r",
        trace_id="t",
        agent_id="wx_acme",
        session_id="s1",
        user_id="u1",
        channel="wecom_tenant",
        roles=_upstream_roles,
    )
    assert ctx.roles == ("tenant_member",)
