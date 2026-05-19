from fastapi import FastAPI

from qwenpaw.enterprise.authz.permissions import resolve_route_permission
from qwenpaw.enterprise.authz.route_scanner import find_uncovered_api_routes


def test_route_scanner_reports_unknown_api_route():
    app = FastAPI()

    @app.get("/api/new-private")
    def new_private():
        return {"ok": True}

    issues = find_uncovered_api_routes(app)
    assert issues == [("GET", "/api/new-private", ("unknown", "read"))]


def test_real_app_has_no_unknown_api_routes():
    from qwenpaw.app._app import app

    issues = find_uncovered_api_routes(app)
    assert issues == []


def test_auth_verify_route_is_public():
    """verify 自行验证 Bearer Token，无需 Authz 层重复保护。"""
    assert resolve_route_permission("GET", "/api/auth/verify") is None
    assert resolve_route_permission(
        "POST", "/api/auth/revoke-token"
    ) == ("auth", "write")
