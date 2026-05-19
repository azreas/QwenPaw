from __future__ import annotations

from dataclasses import dataclass, field

from qwenpaw.constant import EnvVarLoader

from .models import QuotaDimension, QuotaLimit, QuotaWindow


@dataclass(frozen=True, slots=True)
class QuotaConfig:
    enabled: bool = False
    redis_url: str = ""
    default_limits: tuple[QuotaLimit, ...] = field(default_factory=tuple)

    @classmethod
    def from_env(cls) -> "QuotaConfig":
        enabled = EnvVarLoader.get_str("QWENPAW_QUOTA_ENABLED", "").lower() in {
            "true",
            "1",
            "yes",
        }
        redis_url = EnvVarLoader.get_str("QWENPAW_REDIS_URL", "").strip()
        http_per_minute = int(
            EnvVarLoader.get_str("QWENPAW_QUOTA_HTTP_PER_MINUTE", "300")
        )
        tokens_per_day = int(
            EnvVarLoader.get_str("QWENPAW_QUOTA_LLM_TOKENS_PER_DAY", "1000000")
        )
        login_per_minute = int(
            EnvVarLoader.get_str("QWENPAW_QUOTA_AUTH_LOGIN_PER_MINUTE", "20")
        )
        return cls(
            enabled=enabled,
            redis_url=redis_url,
            default_limits=(
                QuotaLimit(
                    dimension=QuotaDimension.HTTP_REQUEST,
                    window=QuotaWindow.MINUTE,
                    max_value=http_per_minute,
                ),
                QuotaLimit(
                    dimension=QuotaDimension.HTTP_REQUEST,
                    window=QuotaWindow.MINUTE,
                    max_value=login_per_minute,
                    resource="POST:/api/auth/login",
                ),
                QuotaLimit(
                    dimension=QuotaDimension.LLM_TOKEN,
                    window=QuotaWindow.DAY,
                    max_value=tokens_per_day,
                ),
            ),
        )
