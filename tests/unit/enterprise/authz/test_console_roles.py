from __future__ import annotations

from fastapi import Request

from qwenpaw.enterprise.authz.middleware import _build_context_for_request


class FakeRequest:
    """模拟 Request 对象，用于测试 request.state.roles。"""

    def __init__(self, state_dict=None):
        class FakeState:
            pass

        self.state = FakeState()
        if state_dict:
            for k, v in state_dict.items():
                setattr(self.state, k, v)

    @property
    def method(self):
        return "GET"

    @property
    def url(self):
        class FakeUrl:
            path = "/api/audit/events"

        return FakeUrl()


def test_console_roles_are_read_from_request_state():
    """验证 AuthzMiddleware 从 request.state.roles 读取角色而不是硬编码。"""

    # 测试 1: tenant_operator 角色
    request = FakeRequest(
        {
            "request_id": "test-1",
            "trace_id": "trace-1",
            "user": "operator",
            "roles": ("tenant_operator",),
            "tenant_id": "acme",
        }
    )

    result = _build_context_for_request(request)
    assert result is not None
    ctx, roles = result
    assert roles == ("tenant_operator",)
    assert ctx.actor.actor_id == "operator"
    assert ctx.tenant_id == "acme"

    # 测试 2: platform_admin 角色
    request2 = FakeRequest(
        {
            "request_id": "test-2",
            "trace_id": "trace-2",
            "user": "admin",
            "roles": ("platform_admin",),
        }
    )

    result2 = _build_context_for_request(request2)
    assert result2 is not None
    ctx2, roles2 = result2
    assert roles2 == ("platform_admin",)
    assert ctx2.actor.actor_id == "admin"

    # 测试 3: 回退到默认 platform_admin（未设置 roles 时）
    request3 = FakeRequest(
        {
            "request_id": "test-3",
            "trace_id": "trace-3",
            "user": "legacy-user",
        }
    )

    result3 = _build_context_for_request(request3)
    assert result3 is not None
    ctx3, roles3 = result3
    assert roles3 == ("platform_admin",)  # 向后兼容


def test_console_roles_are_not_hardcoded():
    """验证自定义角色可以正确传递，而不是被硬编码覆盖。"""

    request = FakeRequest(
        {
            "request_id": "test",
            "trace_id": "trace",
            "user": "member",
            "roles": ("tenant_member", "custom_role"),
        }
    )

    result = _build_context_for_request(request)
    assert result is not None
    _, roles = result
    assert roles == ("tenant_member", "custom_role")
    assert "platform_admin" not in roles  # 没有被硬编码覆盖


def test_console_tenant_id_is_read_from_request_state():
    """Console token 中的 tenant_id 应进入 RequestContext。"""

    request = FakeRequest(
        {
            "request_id": "test",
            "trace_id": "trace",
            "user": "tenant-admin",
            "roles": ("tenant_admin",),
            "tenant_id": "acme",
        }
    )

    result = _build_context_for_request(request)
    assert result is not None
    ctx, _ = result
    assert ctx.tenant_id == "acme"
    assert ctx.agent_id == "wx_acme"
