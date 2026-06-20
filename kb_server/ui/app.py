"""FastAPI application for KB-RAG Web UI."""

import json
import os
import secrets
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

try:
    _version = version("kb-rag-mcp")
except PackageNotFoundError:
    _version = "dev"


class CSPMiddleware(BaseHTTPMiddleware):
    """Middleware that injects a CSP nonce into every response."""

    CSP_DIRECTIVES = (
        "default-src 'self'; "
        "script-src 'self' 'nonce-{nonce}' "
        "https://cdn.jsdelivr.net https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' "
        "https://cdn.jsdelivr.net; "
        "frame-src 'self' https:; "
        "object-src 'none'"
    )

    async def dispatch(self, request: Request, call_next):
        nonce = secrets.token_hex(16)
        request.state.nonce = nonce
        response = await call_next(request)
        csp = self.CSP_DIRECTIVES.format(nonce=nonce)
        response.headers["Content-Security-Policy"] = csp
        return response


# Initialize FastAPI app
app = FastAPI(
    title="KB-RAG Web UI",
    description="Document browser and search tester for KB-RAG system",
    version=_version,
)

# Template directory
template_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))
templates.env.globals["get_nonce"] = lambda request: getattr(
    request.state, "nonce", ""
)
templates.env.filters["fromjson"] = json.loads

# CSP middleware
app.add_middleware(CSPMiddleware)

# Static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Admin routes
from kb_server.ui import routes_admin  # noqa: E402, F811

app.include_router(routes_admin.router)
app.include_router(routes_admin.api_router)
templates.env.globals["build_grafana_embed_url"] = (
    routes_admin.build_grafana_embed_url
)
templates.env.globals["build_grafana_embed_url_with_range"] = (
    routes_admin.build_grafana_embed_url_with_range
)

# Auth router (mounted for session/login endpoints on UI port)
from kb_server.auth.router import router as auth_router  # noqa: E402, F811
from kb_server.auth.service import AuthService  # noqa: E402

app.include_router(auth_router)

# Config router (mounted for config API endpoint on UI port)
from kb_server.config.router import router as config_router  # noqa: E402

app.include_router(config_router)


@app.on_event("startup")
async def startup_init():
    """Initialize auth service, config loader, and seed default admin account."""
    db_path = Path(os.getenv("AUTH_DB_PATH", "data/auth.db"))
    auth_service = AuthService(db_path)
    app.state.auth_service = auth_service
    app.state.auth_service.ensure_admin_account()

    from kb_server.config.loader import ConfigLoader

    config_db_path = Path(os.getenv("CONFIG_DB_PATH", "data/config.db"))
    config_loader = ConfigLoader(config_db_path)
    config_loader.load_from_env()
    app.state.config_loader = config_loader


def highlight_term(text: str, query: str | None) -> str:
    """Wrap occurrences of query in <mark> tags (XSS-safe)."""
    import html as html_mod
    import re

    if not text:
        return ""
    if not query:
        return html_mod.escape(text)
    escaped = re.escape(query)
    parts: list[str] = []
    last = 0
    for m in re.finditer(escaped, text, re.IGNORECASE):
        parts.append(html_mod.escape(text[last : m.start()]))
        parts.append("<mark>")
        parts.append(html_mod.escape(m.group()))
        parts.append("</mark>")
        last = m.end()
    parts.append(html_mod.escape(text[last:]))
    return "".join(parts)


templates.env.globals["highlight_term"] = highlight_term


# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "kb-rag-ui"}


@app.get("/")
async def root():
    """Root redirect to browse page."""

    return RedirectResponse(url="/ui/browse")


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Render user-friendly 404 page."""
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "request": request,
            "code": 404,
            "title": "Not Found",
            "detail": "The page you requested does not exist.",
        },
        status_code=404,
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc: HTTPException):
    """Render user-friendly 500 page."""
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "request": request,
            "code": 500,
            "title": "Server Error",
            "detail": "An internal server error occurred. Please try again later.",
        },
        status_code=500,
    )


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc: HTTPException):
    """Render user-friendly 403 page."""
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "request": request,
            "code": 403,
            "title": "Forbidden",
            "detail": "You do not have permission to access this resource.",
        },
        status_code=403,
    )
