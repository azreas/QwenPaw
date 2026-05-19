from qwenpaw.enterprise.quota.config import QuotaConfig
from qwenpaw.enterprise.quota.models import QuotaDimension, QuotaWindow


def test_quota_config_from_env(monkeypatch):
    monkeypatch.setenv("QWENPAW_REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("QWENPAW_QUOTA_HTTP_PER_MINUTE", "120")
    monkeypatch.setenv("QWENPAW_QUOTA_LLM_TOKENS_PER_DAY", "500000")

    config = QuotaConfig.from_env()

    assert config.redis_url == "redis://localhost:6379/1"

    # Find limits by type instead of relying on position
    http_limits = [
        l for l in config.default_limits if l.dimension is QuotaDimension.HTTP_REQUEST
    ]
    llm_limits = [
        l for l in config.default_limits if l.dimension is QuotaDimension.LLM_TOKEN
    ]
    login_limits = [
        l for l in config.default_limits if l.resource == "POST:/api/auth/login"
    ]

    assert len(http_limits) >= 1
    assert len(llm_limits) >= 1
    assert len(login_limits) >= 1

    general_http = [l for l in http_limits if l.resource == "*"][0]
    assert general_http.window is QuotaWindow.MINUTE
    assert general_http.max_value == 120

    assert llm_limits[0].max_value == 500000
    assert login_limits[0].max_value == 20  # default
