from __future__ import annotations

from qwenpaw.constant import EnvVarLoader


def build_cors_options() -> dict:
    """构建严格的 CORS 配置。

    不允许 wildcard origin 与 credentials 同时启用。
    """
    origins_raw = EnvVarLoader.get_str("QWENPAW_CORS_ORIGINS", "").strip()
    origins = [origin.strip() for origin in origins_raw.split(",") if origin.strip()]
    allow_credentials = (
        EnvVarLoader.get_str("QWENPAW_CORS_ALLOW_CREDENTIALS", "true").lower()
        in {"true", "1", "yes"}
    )
    if "*" in origins and allow_credentials:
        raise ValueError(
            "CORS wildcard origin cannot be used with credentials enabled"
        )
    return {
        "allow_origins": origins,
        "allow_credentials": allow_credentials,
        "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Authorization", "Content-Type", "X-CSRF-Token", "X-Request-Id"],
        "expose_headers": ["Content-Disposition", "X-Request-Id", "X-Trace-Id"],
    }
