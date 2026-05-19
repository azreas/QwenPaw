import os

from .models import ReadinessCheck, ReadinessSummary

REQUIRED_SECRET_MESSAGE = "enterprise test requires explicit configuration"


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def summarize_readiness(checks: list[ReadinessCheck]) -> ReadinessSummary:
    blockers = [
        check.name
        for check in checks
        if check.required and check.status == "fail"
    ]
    if blockers:
        status = "blocked"
    elif any(check.status in {"warn", "fail"} for check in checks):
        status = "degraded"
    else:
        status = "ready"
    return ReadinessSummary(status=status, checks=checks, blockers=blockers)


def collect_enterprise_readiness() -> ReadinessSummary:
    checks: list[ReadinessCheck] = []
    storage_backend = _env("QWENPAW_STORAGE_BACKEND")
    quota_enabled = _env("QWENPAW_QUOTA_ENABLED").lower() in {"1", "true", "yes"}

    checks.append(
        ReadinessCheck(
            name="database_url",
            status="pass" if storage_backend != "postgres" or _env("QWENPAW_DATABASE_URL") else "fail",
            required=storage_backend == "postgres",
            message="postgres storage requires QWENPAW_DATABASE_URL",
        )
    )
    checks.append(
        ReadinessCheck(
            name="redis_url",
            status="pass" if not quota_enabled or _env("QWENPAW_REDIS_URL") else "fail",
            required=quota_enabled,
            message="quota requires QWENPAW_REDIS_URL",
        )
    )
    checks.append(
        ReadinessCheck(
            name="webchat_session_secret",
            status="pass" if _env("QWENPAW_WEBCHAT_SESSION_SECRET") else "fail",
            required=True,
            message=REQUIRED_SECRET_MESSAGE,
        )
    )
    checks.append(
        ReadinessCheck(
            name="sso_login_url",
            status="pass" if _env("QWENPAW_WEBCHAT_SSO_LOGIN_URL") else "warn",
            required=False,
            message="SSO login is not configured",
        )
    )
    checks.append(
        ReadinessCheck(
            name="wecom_qrcode_login_url",
            status="pass" if _env("QWENPAW_WEBCHAT_QRCODE_LOGIN_URL") else "warn",
            required=False,
            message="WeCom QR login is not configured",
        )
    )
    checks.append(
        ReadinessCheck(
            name="cors_origins",
            status="pass" if _env("QWENPAW_CORS_ORIGINS") else "warn",
            required=False,
            message="CORS origins are not configured",
        )
    )
    return summarize_readiness(checks)
