import pytest

from qwenpaw.enterprise.context import RequestContext
from qwenpaw.enterprise.quota.models import QuotaDimension, QuotaLimit, QuotaWindow
from qwenpaw.enterprise.quota.service import QuotaService
from qwenpaw.enterprise.quota.store import InMemoryQuotaStore
from qwenpaw.enterprise.quota.tool import consume_tool_call


@pytest.mark.asyncio
async def test_consume_tool_call_denies_over_limit():
    quota = QuotaService(
        store=InMemoryQuotaStore(),
        limits=[
            QuotaLimit(
                dimension=QuotaDimension.TOOL_CALL,
                window=QuotaWindow.MINUTE,
                max_value=0,
                tenant_id="wx_acme",
                resource="execute_shell_command",
            )
        ],
    )
    decision = await consume_tool_call(
        quota,
        RequestContext(request_id="r", trace_id="t", tenant_id="wx_acme"),
        "execute_shell_command",
    )

    assert decision is not None
    assert decision.allowed is False
