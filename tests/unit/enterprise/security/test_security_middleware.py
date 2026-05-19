from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qwenpaw.enterprise.security.middleware import (
    CSRFMiddleware,
    PayloadSizeMiddleware,
    PayloadSizeRule,
    SecurityHeadersMiddleware,
)


def test_payload_size_middleware_rejects_large_body():
    app = FastAPI()
    app.add_middleware(PayloadSizeMiddleware, max_bytes=4)

    @app.post("/api/data")
    async def data():
        return {"ok": True}

    response = TestClient(app).post("/api/data", content=b"12345")
    assert response.status_code == 413


def test_payload_size_middleware_allows_small_body():
    app = FastAPI()
    app.add_middleware(PayloadSizeMiddleware, max_bytes=100)

    @app.post("/api/data")
    async def data():
        return {"ok": True}

    response = TestClient(app).post("/api/data", content=b"12345")
    assert response.status_code == 200


def test_security_headers_are_added():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    response = TestClient(app).get("/api/ping")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "same-origin"


def test_csrf_middleware_requires_header_for_cookie_auth():
    app = FastAPI()
    app.add_middleware(CSRFMiddleware)

    @app.post("/api/config")
    def config():
        return {"ok": True}

    response = TestClient(app).post(
        "/api/config",
        cookies={"qwenpaw_session": "token"},
    )
    assert response.status_code == 403


def test_csrf_middleware_allows_with_matching_header():
    app = FastAPI()
    app.add_middleware(CSRFMiddleware)

    @app.post("/api/config")
    def config():
        return {"ok": True}

    response = TestClient(app).post(
        "/api/config",
        cookies={"qwenpaw_session": "same-token"},
        headers={"x-csrf-token": "same-token"},
    )
    assert response.status_code == 200


def test_csrf_middleware_skips_webchat():
    app = FastAPI()
    app.add_middleware(CSRFMiddleware)

    @app.post("/api/webchat/message")
    def message():
        return {"ok": True}

    response = TestClient(app).post(
        "/api/webchat/message",
        cookies={"qwenpaw_session": "token"},
    )
    assert response.status_code == 200


def test_csrf_middleware_skips_safe_methods():
    app = FastAPI()
    app.add_middleware(CSRFMiddleware)

    @app.get("/api/config")
    def config():
        return {"ok": True}

    response = TestClient(app).get(
        "/api/config",
        cookies={"qwenpaw_session": "token"},
    )
    assert response.status_code == 200


def test_csrf_middleware_allows_no_cookie():
    app = FastAPI()
    app.add_middleware(CSRFMiddleware)

    @app.post("/api/config")
    def config():
        return {"ok": True}

    response = TestClient(app).post("/api/config")
    assert response.status_code == 200


def test_payload_size_middleware_uses_route_specific_limit():
    app = FastAPI()
    app.add_middleware(
        PayloadSizeMiddleware,
        max_bytes=4,
        route_limits=[
            PayloadSizeRule("/api/console/upload", 10),
        ],
    )

    @app.post("/api/console/upload")
    async def upload():
        return {"ok": True}

    response = TestClient(app).post(
        "/api/console/upload",
        content=b"123456789",
    )

    assert response.status_code == 200


def test_payload_size_middleware_rejects_route_above_specific_limit():
    app = FastAPI()
    app.add_middleware(
        PayloadSizeMiddleware,
        max_bytes=4,
        route_limits=[
            PayloadSizeRule("/api/console/upload", 10),
        ],
    )

    @app.post("/api/console/upload")
    async def upload():
        return {"ok": True}

    response = TestClient(app).post(
        "/api/console/upload",
        content=b"12345678901",
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "Payload too large"}


def test_payload_size_middleware_keeps_default_limit_for_json_routes():
    app = FastAPI()
    app.add_middleware(
        PayloadSizeMiddleware,
        max_bytes=4,
        route_limits=[
            PayloadSizeRule("/api/console/upload", 10),
        ],
    )

    @app.post("/api/config")
    async def config():
        return {"ok": True}

    response = TestClient(app).post("/api/config", content=b"12345")

    assert response.status_code == 413


def test_payload_size_middleware_accepts_multipart_file_with_overhead_buffer():
    from io import BytesIO

    app = FastAPI()
    app.add_middleware(
        PayloadSizeMiddleware,
        max_bytes=100,
        route_limits=[
            # File limit 200, with multipart overhead auto-added
            PayloadSizeRule("/api/console/upload", 200, add_multipart_overhead=True),
        ],
    )

    @app.post("/api/console/upload")
    async def upload():
        return {"ok": True}

    # 100-byte file inside multipart (with boundary, headers ~170 bytes overhead)
    # Total Content-Length ~270, but with overhead buffer, limit becomes 200 + 64K
    file_content = b"x" * 100
    response = TestClient(app).post(
        "/api/console/upload",
        files={"file": ("test.txt", BytesIO(file_content), "text/plain")},
    )

    # Pass: multipart overhead is automatically accounted for
    assert response.status_code == 200


def test_payload_size_middleware_rejects_multipart_without_overhead():
    from io import BytesIO

    app = FastAPI()
    app.add_middleware(
        PayloadSizeMiddleware,
        max_bytes=100,
        route_limits=[
            # No overhead added, strict 200 byte limit on total HTTP body
            PayloadSizeRule("/api/console/upload", 200, add_multipart_overhead=False),
        ],
    )

    @app.post("/api/console/upload")
    async def upload():
        return {"ok": True}

    # 100-byte file inside multipart = ~270 total Content-Length
    file_content = b"x" * 100
    response = TestClient(app).post(
        "/api/console/upload",
        files={"file": ("test.txt", BytesIO(file_content), "text/plain")},
    )

    # Rejected: no overhead buffer, 270 > 200
    assert response.status_code == 413


def test_payload_size_middleware_prefix_suffix_matching():
    app = FastAPI()
    app.add_middleware(
        PayloadSizeMiddleware,
        max_bytes=4,  # Default 4 bytes
        route_limits=[
            # Only /tenants/{id}/import gets 100 bytes
            PayloadSizeRule("/api/tenants", 100, path_suffix="/import"),
        ],
    )

    @app.post("/api/tenants/{tenant_id}/import")
    async def import_tenant(tenant_id: str):
        return {"ok": True}

    @app.post("/api/tenants/{tenant_id}/start")
    async def start_tenant(tenant_id: str):
        return {"ok": True}

    @app.post("/api/tenants/batch/start")
    async def batch_start():
        return {"ok": True}

    # Import endpoint gets higher limit - 100 bytes allows 50 byte payload
    response = TestClient(app).post("/api/tenants/test-123/import", content=b"x" * 50)
    assert response.status_code == 200

    # But start endpoint still uses default 4 bytes - 50 bytes gets rejected
    response = TestClient(app).post("/api/tenants/test-123/start", content=b"x" * 50)
    assert response.status_code == 413

    # Batch start also gets default limit
    response = TestClient(app).post("/api/tenants/batch/start", content=b"x" * 50)
    assert response.status_code == 413
