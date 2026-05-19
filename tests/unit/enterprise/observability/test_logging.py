import json
import logging

from qwenpaw.enterprise.context import RequestContext, set_current_request_context, clear_current_request_context
from qwenpaw.enterprise.observability.logging import EnterpriseJsonFormatter


def test_enterprise_json_formatter_injects_context():
    formatter = EnterpriseJsonFormatter()
    token = set_current_request_context(
        RequestContext(
            request_id="r1",
            trace_id="t1",
            tenant_id="wx_acme",
            agent_id="wx_acme",
        )
    )
    try:
        record = logging.LogRecord(
            name="qwenpaw.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="hello",
            args=(),
            exc_info=None,
        )
        payload = json.loads(formatter.format(record))
    finally:
        clear_current_request_context(token)

    assert payload["message"] == "hello"
    assert payload["tenant_id"] == "wx_acme"
    assert payload["request_id"] == "r1"
