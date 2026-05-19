from qwenpaw.enterprise.context import (
    RequestActor,
    RequestContext,
    clear_current_request_context,
    get_current_request_context,
    set_current_request_context,
)


def test_request_context_minimal_fields():
    ctx = RequestContext(
        request_id="req-1",
        trace_id="trace-1",
        tenant_id="wx_acme",
        agent_id="wx_acme",
        session_id="s1",
        channel="webchat",
        actor=RequestActor(actor_id="u1", actor_type="webchat_user"),
    )

    assert ctx.tenant_id == "wx_acme"
    assert ctx.actor.actor_id == "u1"
    assert ctx.roles == tuple()


def test_contextvar_roundtrip():
    ctx = RequestContext(request_id="req-1", trace_id="trace-1")
    token = set_current_request_context(ctx)
    try:
        assert get_current_request_context() is ctx
    finally:
        clear_current_request_context(token)

    assert get_current_request_context() is None
