from __future__ import annotations

from typing import Any

SENSITIVE_KEYWORDS = ("token", "secret", "password", "api_key", "cookie")


def _is_sensitive_key(key: str) -> bool:
    lower = key.lower()
    return any(word in lower for word in SENSITIVE_KEYWORDS)


def redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if _is_sensitive_key(str(key)) else redact_payload(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    return value
