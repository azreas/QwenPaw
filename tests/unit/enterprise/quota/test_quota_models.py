from qwenpaw.enterprise.quota.models import (
    QuotaDimension,
    QuotaLimit,
    QuotaWindow,
)


def test_quota_limit_builds_stable_counter_key():
    limit = QuotaLimit(
        dimension=QuotaDimension.HTTP_REQUEST,
        window=QuotaWindow.MINUTE,
        max_value=60,
        tenant_id="wx_acme",
        resource="POST:/api/agent/query",
    )

    assert limit.counter_key("202605090101") == (
        "quota:wx_acme:http.request:POST:/api/agent/query:minute:202605090101"
    )


def test_quota_window_ttl_seconds():
    assert QuotaWindow.MINUTE.ttl_seconds == 60
    assert QuotaWindow.DAY.ttl_seconds == 86400
