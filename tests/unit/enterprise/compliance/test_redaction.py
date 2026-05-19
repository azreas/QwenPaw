from qwenpaw.enterprise.compliance.redaction import redact_payload


def test_redact_payload_masks_sensitive_keys():
    payload = {
        "token": "abc",
        "password": "secret",
        "safe": "visible",
        "nested": {"api_key": "key"},
    }

    redacted = redact_payload(payload)

    assert redacted["token"] == "***"
    assert redacted["password"] == "***"
    assert redacted["safe"] == "visible"
    assert redacted["nested"]["api_key"] == "***"


def test_redact_payload_handles_list():
    payload = [
        {"token": "abc", "safe": "visible"},
        {"secret": "xyz"},
    ]

    redacted = redact_payload(payload)

    assert redacted[0]["token"] == "***"
    assert redacted[0]["safe"] == "visible"
    assert redacted[1]["secret"] == "***"


def test_redact_payload_handles_cookie_key():
    payload = {"cookie": "session=abc123", "name": "test"}

    redacted = redact_payload(payload)

    assert redacted["cookie"] == "***"
    assert redacted["name"] == "test"


def test_redact_payload_preserves_scalars():
    assert redact_payload("hello") == "hello"
    assert redact_payload(42) == 42
    assert redact_payload(None) is None


def test_redact_payload_substring_match():
    """包含敏感子串的 key 也应脱敏。"""
    payload = {"access_token": "abc", "my_password_hash": "xyz"}

    redacted = redact_payload(payload)

    assert redacted["access_token"] == "***"
    assert redacted["my_password_hash"] == "***"
