import uuid

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from kb_server.observability.middleware import (
    RequestIDMiddleware,
    get_current_request_id,
)


def _handler(request: Request):
    return JSONResponse({"request_id": get_current_request_id()})


app = Starlette(
    routes=[Route("/", _handler)],
    middleware=[Middleware(RequestIDMiddleware)],
)

client = TestClient(app)


def test_request_id_generated():
    resp = client.get("/")
    assert resp.status_code == 200
    request_id = resp.json()["request_id"]
    assert request_id != ""
    # Verify UUID format
    uuid.UUID(request_id)


def test_request_id_header_in_response():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "X-Request-Id" in resp.headers
    request_id = resp.headers["X-Request-Id"]
    uuid.UUID(request_id)


def test_request_id_preserved_from_client():
    client_id = "client-specified-id-12345"
    resp = client.get("/", headers={"X-Request-Id": client_id})
    assert resp.status_code == 200
    assert resp.headers["X-Request-Id"] == client_id
    assert resp.json()["request_id"] == client_id


def test_request_id_unique_per_request():
    ids = set()
    for _ in range(10):
        resp = client.get("/")
        ids.add(resp.headers["X-Request-Id"])
    assert len(ids) == 10
