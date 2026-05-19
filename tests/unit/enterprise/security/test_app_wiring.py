from __future__ import annotations


def test_app_has_security_middlewares():
    from qwenpaw.app._app import app
    from qwenpaw.enterprise.security.middleware import (
        CSRFMiddleware,
        PayloadSizeMiddleware,
        SecurityHeadersMiddleware,
    )

    middleware_classes = [item.cls for item in app.user_middleware]
    assert SecurityHeadersMiddleware in middleware_classes
    assert PayloadSizeMiddleware in middleware_classes
    assert CSRFMiddleware in middleware_classes


def test_quota_config_has_login_rate_limit():
    from qwenpaw.enterprise.quota.config import QuotaConfig

    config = QuotaConfig.from_env()

    login_limits = [
        limit
        for limit in config.default_limits
        if hasattr(limit, "resource") and limit.resource == "POST:/api/auth/login"
    ]
    assert len(login_limits) >= 1


def test_app_payload_size_middleware_has_upload_route_limits():
    from qwenpaw.app._app import app
    from qwenpaw.enterprise.security.middleware import PayloadSizeMiddleware

    middleware = next(
        item for item in app.user_middleware if item.cls is PayloadSizeMiddleware
    )
    rules = middleware.kwargs["route_limits"]

    assert middleware.kwargs["max_bytes"] == 2 * 1024 * 1024

    # Simple prefix routes
    simple_limits = {
        rule.path_prefix: rule.max_bytes
        for rule in rules
        if rule.path_suffix is None
    }
    assert simple_limits["/api/console/upload"] == 10 * 1024 * 1024
    assert simple_limits["/api/webchat/upload"] == 10 * 1024 * 1024
    assert simple_limits["/api/workspace/upload"] == 100 * 1024 * 1024
    assert simple_limits["/api/backups/import"] == 100 * 1024 * 1024
    assert simple_limits["/api/skills/upload"] == 100 * 1024 * 1024

    # WeCom tenant config import uses prefix + suffix matching
    wecom_import_rule = next(
        rule for rule in rules if rule.path_suffix == "/import"
    )
    assert wecom_import_rule.path_prefix == "/api/config/channels/wecom_tenant/tenants"
    assert wecom_import_rule.max_bytes == 100 * 1024 * 1024
    assert wecom_import_rule.add_multipart_overhead is True
