"""FastAPI application for KB-RAG Web UI."""

import secrets
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
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


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render the login page."""
    return templates.TemplateResponse(
        request,
        "admin/login.html",
        {
            "request": request,
        },
    )


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
