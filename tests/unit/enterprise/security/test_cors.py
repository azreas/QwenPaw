from __future__ import annotations

import pytest

from qwenpaw.enterprise.security.cors import build_cors_options


def test_cors_options_parse_origins(monkeypatch):
    monkeypatch.setenv("QWENPAW_CORS_ORIGINS", "https://a.example,https://b.example")

    options = build_cors_options()

    assert options["allow_origins"] == ["https://a.example", "https://b.example"]
    assert options["allow_credentials"] is True


def test_cors_rejects_wildcard_with_credentials(monkeypatch):
    monkeypatch.setenv("QWENPAW_CORS_ORIGINS", "*")
    monkeypatch.setenv("QWENPAW_CORS_ALLOW_CREDENTIALS", "true")

    with pytest.raises(ValueError, match="wildcard"):
        build_cors_options()


def test_cors_allows_wildcard_without_credentials(monkeypatch):
    monkeypatch.setenv("QWENPAW_CORS_ORIGINS", "*")
    monkeypatch.setenv("QWENPAW_CORS_ALLOW_CREDENTIALS", "false")

    options = build_cors_options()
    assert options["allow_origins"] == ["*"]
    assert options["allow_credentials"] is False


def test_cors_empty_origins_returns_empty_list(monkeypatch):
    monkeypatch.setenv("QWENPAW_CORS_ORIGINS", "")

    options = build_cors_options()
    assert options["allow_origins"] == []


def test_cors_allow_methods_are_restricted(monkeypatch):
    monkeypatch.setenv("QWENPAW_CORS_ORIGINS", "https://example.com")

    options = build_cors_options()
    assert "OPTIONS" in options["allow_methods"]
    assert "GET" in options["allow_methods"]
    assert "POST" in options["allow_methods"]
    assert "TRACE" not in options["allow_methods"]


def test_cors_allow_headers_are_restricted(monkeypatch):
    monkeypatch.setenv("QWENPAW_CORS_ORIGINS", "https://example.com")

    options = build_cors_options()
    assert "Authorization" in options["allow_headers"]
    assert "X-CSRF-Token" in options["allow_headers"]
