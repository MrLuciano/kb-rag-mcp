import uuid
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def get_current_request_id() -> str:
    """Return the request ID for the current request context."""
    return _request_id_ctx.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns or preserves X-Request-Id on every request.

    If the client sends an ``X-Request-Id`` header, it is preserved.
    Otherwise a UUID v4 is generated. The value is propagated via
    ``ContextVar`` for downstream access via ``get_current_request_id()``.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-Id")
        if not request_id:
            request_id = str(uuid.uuid4())

        token = _request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-Id"] = request_id
            return response
        finally:
            _request_id_ctx.reset(token)
