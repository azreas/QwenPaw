from fastapi import FastAPI
from fastapi.testclient import TestClient

from qwenpaw.enterprise.middleware import RequestIdentityMiddleware


def test_request_identity_middleware_sets_request_id():
    app = FastAPI()
    app.add_middleware(RequestIdentityMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    response = TestClient(app).get("/ping")
    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.headers["x-trace-id"]


def test_request_identity_middleware_respects_incoming_request_id():
    app = FastAPI()
    app.add_middleware(RequestIdentityMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    response = TestClient(app).get("/ping", headers={"x-request-id": "req-fixed"})
    assert response.headers["x-request-id"] == "req-fixed"
