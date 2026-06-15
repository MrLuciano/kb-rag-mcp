# Architecture Research

**Domain:** Admin Platform for kb-rag-mcp (Streamable HTTP, Auth API, Admin SPA, Grafana Embed, Observability, Config, Provider Aliases)
**Researched:** 2026-06-15
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL CONSUMERS                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Claude  │  │ OpenCode │  │  Cursor  │  │ Browser  │  │Prometheus│  │
│  │   Code   │  │          │  │          │  │ (Admin)  │  │/Grafana  │  │
│  └─────┬────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬────┘  │
│        │             │             │             │              │       │
├────────┼─────────────┼─────────────┼─────────────┼──────────────┼───────┤
│        │             │             │             │              │       │
│  ┌─────┴─────────────┴─────────────┴──────┐ ┌────┴──────┐ ┌────┴─────┐ │
│  │         MCP SERVER (Port 8765)         │ │  HEALTH   │ │  EXISTING│ │
│  │  ┌─────────────────────────────────┐   │ │  SERVER   │ │  UI      │ │
│  │  │  StreamableHTTPSessionManager   │   │ │ (Port8080)│ │ (Port8001)│ │
│  │  │  (GET/POST/DELETE/OPTIONS /mcp) │◄──┤ │ ┌────────┐│ │ ┌──────┐ │ │
│  │  └─────────────┬───────────────────┘   │ │ │Health  ││ │ │Browse│ │ │
│  │  ┌─────────────┴───────────────────┐   │ │ │Checks  ││ │ │Search│ │ │
│  │  │  SseServerTransport (/sse)      │   │ │ │Metrics ││ │ │      │ │ │
│  │  └─────────────────────────────────┘   │ │ └────────┘│ │ └──────┘ │ │
│  │  ┌─────────────────────────────────┐   │ └────┬──────┘ └────┬─────┘ │
│  │  │  stdio_server()                 │   │      │              │       │
│  │  └─────────────────────────────────┘   │      │              │       │
│  └────────────────┬───────────────────────┘      │              │       │
├───────────────────┼──────────────────────────────┼──────────────┼───────┤
│                   │  NEW ADMIN API LAYER         │              │       │
│  ┌────────────────┴──────────────────────────────┴──────────────┴───┐  │
│  │                     UI SERVER (Port 8001)                        │  │
│  │                      FastAPI + Jinja2                            │  │
│  │                                                                  │  │
│  │  ┌─────────────┐  ┌──────────────────┐  ┌────────────────────┐  │  │
│  │  │ Admin SPA   │  │ Admin API        │  │ Existing UI Routes │  │  │
│  │  │ Template    │  │ /api/v1/auth/    │  │ /ui/browse         │  │  │
│  │  │ Shell +     │  │ /api/v1/users/   │  │ /ui/search         │  │  │
│  │  │ Tab Partials│  │ /api/v1/api-keys/│  │ /ui/document/{id}  │  │  │
│  │  │ (HTMX+Alpine│  │ /api/v1/config/  │  │                    │  │  │
│  │  │ +Bootstrap) │  │ /api/v1/health   │  │                    │  │  │
│  │  └─────────────┘  │ /api/v1/jobs/    │  └────────────────────┘  │  │
│  │                    │ /api/v1/documents│                          │  │
│  │                    │ /api/v1/evaluation│                         │  │
│  │                    └──────────────────┘                          │  │
│  └───────────────────────────┬──────────────────────────────────────┘  │
│                              │                                         │
├──────────────────────────────┼─────────────────────────────────────────┤
│                  SERVICE & DATA LAYER                                  │
│                                                                        │
│  ┌──────────┐  ┌──────────┐  ┌────────────────┐  ┌─────────────────┐  │
│  │ Auth     │  │ Config   │  │ Auth Registry  │  │ Embed Client    │  │
│  │ Service  │  │ Loader   │  │ (SQLite)       │  │ (Multi-backend  │  │
│  │ (SQLAlch)│  │ (Hot-    │  │ api_keys table │  │  + CB + Alias)  │  │
│  │          │  │  reload) │  │                │  │                 │  │
│  └────┬─────┘  └────┬─────┘  └────────────────┘  └────────┬────────┘  │
│       │              │                                      │          │
│  ┌────┴──────┐  ┌───┴──────┐  ┌──────────────┐  ┌──────────┴────────┐ │
│  │ User/Key  │  │ Config   │  │ Ingestion    │  │ Vector Store     │  │
│  │ + Audit   │  │ SQLite   │  │ Pipeline     │  │ (Qdrant Client)  │  │
│  │ + Erasure │  │ Table    │  │ (File Worker │  │                  │  │
│  │ Models    │  │          │  │  + Registry) │  │                  │  │
│  └───────────┘  └──────────┘  └──────┬───────┘  └────────┬─────────┘  │
├──────────────────────────────────────┼────────────────────┼───────────┤│
│                              STORAGE LAYER                 │          ││
│  ┌──────────┐  ┌──────────┐  ┌──────┴───────┐  ┌─────────┴─────────┐ │
│  │  Auth DB  │  │ Config   │  │  Registry DB │  │  Qdrant           │ │
│  │  auth.db  │  │ same DB  │  │  registry.db │  │  (Vector Store)   │ │
│  │ (SQLite)  │  │ (SQLite) │  │  (SQLite)    │  │  + Metadata       │ │
│  └──────────┘  └──────────┘  └──────────────┘  └───────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities — Existing

| Component | Responsibility | Implementation |
|-----------|---------------|----------------|
| `kb_server/server.py` | MCP tool registration, dispatch, transport management (stdio/SSE/streamable-http) | `mcp.server.Server("kb-rag")`, `SseServerTransport`, `StreamableHTTPSessionManager` |
| `kb_server/vector_store.py` | Qdrant abstraction — CRUD, search, stats | `AsyncQdrantClient` wrapper |
| `kb_server/embed_client.py` | Multi-backend embedding gen + caching + circuit breakers | Module-level functions, `httpx`, `CacheManager`, `CircuitBreaker` |
| `kb_server/auth.py` | Bearer token extraction + verification | `verify_request()` calls `AuthRegistry.verify_key()` |
| `kb_server/auth_registry.py` | SQLite-backed API key hash storage | Thread-safe singleton, SHA-256 hashes, prefix lookup |
| `kb_server/collections/router.py` | Collection name resolution + multi-KB routing | `CollectionRouter` with `resolve()`/`resolve_multi()` |
| `kb_server/retrieval/hybrid_search.py` | Dense+BM25 RRF fusion | Singleton `HybridSearcher`, fastembed sparse |
| `kb_server/retrieval/reranker.py` | Cross-encoder reranking | `CrossEncoder` model reranking |
| `kb_server/health.py` | Component health checks | `HealthStatus` checks for embedding/vector/cache/DB/filesystem |
| `kb_server/health_server.py` | HTTP health/metrics endpoint (port 8080) | FastAPI app with `/health`, `/health/detailed`, `/metrics` |
| `kb_server/ui/app.py` | FastAPI UI app (port 8001) | FastAPI + Jinja2 templates |
| `kb_server/ui/routes.py` | Existing UI routes | `/ui/browse`, `/ui/search`, `/ui/document/{id}` |
| `observability/metrics.py` | Prometheus metrics definitions | `Counter`, `Gauge`, `Histogram` from prometheus_client |
| `ingest/job/manager.py` | Job CRUD + lifecycle | `MetadataStore`, `Job`, `JobStatus` |
| `ingest/job/scheduler.py` | Priority-based job dispatch | `JobScheduler` with concurrency control |
| `kb_server/evaluation/dataset.py` | Golden dataset management | `GoldenDataset` JSON/CSV load + save |

### Component Responsibilities — NEW for Admin Platform

| Component | Responsibility | Implementation |
|-----------|---------------|----------------|
| `kb_server/auth/models.py` | SQLAlchemy models: User, ApiKey, AuditLog, ErasureRequest | SQLAlchemy `declarative_base()`, UUID PKs, FK relationships |
| `kb_server/auth/schemas.py` | Pydantic request/response schemas | Pydantic v2 models with validation |
| `kb_server/auth/deps.py` | FastAPI `Depends()` guards: `get_current_user`, `require_admin`, `require_auth` | Chain: API key → JWT cookie → user lookup → role check |
| `kb_server/auth/service.py` | Business logic: user CRUD, key gen, erasure flow | Services calling SQLAlchemy session + auth_registry |
| `kb_server/auth/router.py` | REST endpoints: `/api/v1/auth/*`, `/api/v1/users/*`, `/api/v1/api-keys/*` | FastAPI `APIRouter`, all CRUD operations + GDPR endpoints |
| `kb_server/config/api.py` | REST endpoints: `/api/v1/config` | FastAPI `APIRouter`, grouped config CRUD |
| `kb_server/config/loader.py` | Config chain: SQLite → `.env` → env var defaults | `ConfigLoader` with layered lookup |
| `kb_server/config/hotreload.py` | Hot-reload event system | Event bus: config `PUT` → notify watchers → `reload_if_changed()` |
| `kb_server/ui/routes_admin.py` | Admin SPA routes + tab partials | FastAPI routes returning HTMX partials |
| `kb_server/ui/templates/admin/shell.html` | Admin SPA shell with sidebar | Alpine.js + Bootstrap 5 layout |
| `kb_server/ui/templates/admin/tab_*.html` | Tab partials (6+) | HTMX-loadable fragments |
| `kb_server/ui/templates/admin/modal_*.html` | Login/logout/confirm modals | Alpine.js `x-show` modals |
| `kb_server/observability/middleware.py` | Request ID middleware | Starlette middleware: `X-Request-Id` gen + `contextvars` propagation |
| `kb_server/observability/percentiles.py` | Per-operation percentile metrics | HDR histogram (sorted-list), p50/p95/p99, Prometheus gauge export |
| `ingest/scheduler.py` | Background schedule runner | asyncio task reading schedules table, triggering `JobManager.create_job()` |

## Recommended Project Structure — New/Modified Files

```
kb_server/
├── auth/                          # NEW: Auth & User Management (Phase 28b)
│   ├── __init__.py
│   ├── models.py                  # SQLAlchemy: User, ApiKey, AuditLog, ErasureRequest
│   ├── schemas.py                 # Pydantic: request/response models
│   ├── deps.py                    # FastAPI Depends() guards (chain auth)
│   ├── service.py                 # CRUD business logic + GDPR erasure
│   └── router.py                  # REST endpoints for auth/user/key management
├── config/                        # NEW: Configuration Management (Phase 40)
│   ├── __init__.py
│   ├── api.py                     # Config REST API endpoints
│   ├── loader.py                  # SQLite→.env→default chain loader
│   └── hotreload.py               # Hot-reload event system (pub/sub)
├── observability/                 # NEW: Observability middleware (Phase 39)
│   ├── __init__.py
│   ├── middleware.py              # Request ID middleware (OBS-02)
│   └── percentiles.py             # HDR histograms per operation (METRICS-01)
├── ui/
│   ├── routes_admin.py            # NEW: Admin SPA routes + tab partial endpoints
│   ├── templates/
│   │   ├── base.html              # MODIFY: Add Alpine.js CDN + admin nav link
│   │   ├── browse.html            # MODIFY: Add cleanup controls (SPA-04/05)
│   │   └── admin/                 # NEW: Admin SPA templates (Phase 28c)
│   │       ├── shell.html         # SPA shell with sidebar
│   │       ├── tab_documents.html # Documents tab (advanced filters)
│   │       ├── tab_monitoring.html# Grafana embed + monitor lights
│   │       ├── tab_ingestion.html # Ingestion controls + schedules
│   │       ├── tab_ragas.html     # RAGAS evaluation
│   │       ├── tab_admin.html     # Config editor
│   │       ├── tab_profile.html   # Profile + API keys + GDPR
│   │       ├── modal_login.html   # Login modal
│   │       └── modal_confirm.html # Confirmation dialog
│   └── app.py                     # MODIFY: Register admin router + CSP middleware
│
├── server.py                      # MODIFY: Add streamable-http transport branch (Phase 28)
├── health.py                      # MODIFY: Add Grafana connectivity check (OBS-01)
├── evaluation/dataset.py          # MODIFY: Add CRUD operations for golden set
├── __init__.py                    # (unchanged)
├── auth.py                        # (unchanged — existing bearer auth still used by MCP)
├── auth_registry.py               # (unchanged — still feeds MCP auth, new Auth service adds SQLAlchemy layer)
├── vector_store.py                # (unchanged)
├── embed_client.py                # MODIFY: Add provider alias resolution (Phase 41)
├── ...                            # (all other existing files unchanged)

ingest/
├── scheduler.py                   # NEW: Background schedule runner (Phase 28c)
├── job/manager.py                 # MODIFY: Add programmatic `create_job()` for API calls
├── ...                            # (all other existing files unchanged)

observability/
├── metrics.py                     # MODIFY: Add percentile metrics and request ID metrics
├── ...                            # (unchanged)

tests/
├── test_server_streamable_http.py # NEW
├── test_auth_api.py               # NEW
├── test_config_api.py             # NEW
├── test_admin_ui.py               # NEW
├── ...                            # (all 1165 existing tests continue passing)
```

### Structure Rationale

- **`kb_server/auth/` as a package:** Groups all auth concerns (models, schemas, guards, service, router) into a single bounded context. The existing `auth.py` and `auth_registry.py` remain for MCP transport auth; the new package adds user management, JWT sessions, and GDPR on top. Clear separation: MCP auth is key-only; Admin API auth is key+JWT+role.
- **`kb_server/config/` as a package:** Configuration is a cross-cutting concern with its own data model, API surface, and hot-reload lifecycle. Isolating it prevents import cycles and makes the hot-reload event system testable independently.
- **`kb_server/observability/` as a package:** Request ID middleware and percentile histograms are shared infrastructure used by both MCP and Admin API paths. Placing them in `observability/` keeps them alongside existing Prometheus metrics patterns.
- **Admin templates in `kb_server/ui/templates/admin/`:** Follows the existing Jinja2 template organization. `base.html` already has Bootstrap+HTMX; Alpine.js is the only new CDN dependency. No build step needed.
- **Scheduler in `ingest/scheduler.py`:** Lives in the `ingest/` package because it drives `JobManager.create_job()` — keeps the scheduling concern close to the job execution code.

## Architectural Patterns

### Pattern 1: Config Chain (Layered Override)

**What:** Configuration values resolve through a priority chain: SQLite config table → `.env` file → hardcoded env var defaults. Each layer has a `reload_if_changed()` hook that components call to pick up changes.

**When to use:** Any configuration value that should be editable at runtime without restarting the server. All env vars that currently use `os.getenv("KEY", default)`.

**Trade-offs:**
- Pros: No-downtime configuration changes, admin UI edits persist, backward compatible with existing `.env` usage
- Cons: One SQLite query per config read (mitigated by in-memory cache with TTL), complexity of the event system for hot-reload

**Example:**
```python
# config/loader.py — layered lookup
class ConfigLoader:
    def __init__(self, db_path: Path):
        self._cache: dict[str, str] = {}
        self._last_check: float = 0
        self._ttl = 5.0  # seconds
        self._conn = sqlite3.connect(str(db_path))

    def get(self, key: str) -> str | None:
        # 1. Check SQLite overrides (with TTL cache)
        if self._cache.get(key) is not None:
            return self._cache[key]
        row = self._conn.execute(
            "SELECT value FROM config WHERE key = ?", (key,)
        ).fetchone()
        if row:
            self._cache[key] = row[0]
            return row[0]
        return None

# Usage in embed_client.py:
def _resolve_backend(name: str) -> str:
    """Resolve provider alias via config, falling back to name as-is."""
    loader = ConfigLoader(Path("data/kb_metadata.db"))
    alias = loader.get(f"provider_alias.{name}")
    return alias or name

EMBED_BACKEND = _resolve_backend(os.getenv("EMBED_BACKEND", "openai-compat"))
```

### Pattern 2: FastAPI Depends Authorization Chain

**What:** Authentication and authorization are expressed as a chain of FastAPI `Depends()` dependencies. Each dependency validates one aspect and passes the user object to the next.

**When to use:** All admin API endpoints that need auth. Clear, testable, and follows FastAPI best practices.

**Trade-offs:**
- Pros: Reusable across all endpoints, easy to unit test, clear error propagation (401/403)
- Cons: Adds import boilerplate to every router; overkill for a single endpoint

**Example:**
```python
# auth/deps.py
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract user from API Key (Bearer header) or JWT session cookie."""
    # 1. Check Authorization header (API key)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return await _resolve_api_key_user(auth_header[7:], db)
    # 2. Check session cookie (JWT)
    session_token = request.cookies.get("kb_session")
    if session_token:
        return await _resolve_jwt_user(session_token, db)
    raise HTTPException(status_code=401, detail="No credentials provided")

async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user

# Usage in router:
@router.get("/users", response_model=list[UserResponse])
async def list_users(admin: User = Depends(require_admin)):
    ...
```

### Pattern 3: Hot-Reload Event Bus

**What:** A simple in-process pub/sub event bus. When config changes via `PUT /api/v1/config/{key}`, the bus notifies all registered watchers. Each watcher calls its `reload_if_changed()` method.

**When to use:** Any component that reads config at startup and should pick up runtime changes without restarting.

**Trade-offs:**
- Pros: No polling, immediate update propagation, single ownership of reload logic per component
- Cons: In-process only (doesn't scale across processes), adds coupling if overused

**Example:**
```python
# config/hotreload.py
import asyncio
from typing import Callable, Any

class HotReloadBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable[[str, Any], None]]] = {}

    def subscribe(self, key_pattern: str, callback: Callable):
        self._subscribers.setdefault(key_pattern, []).append(callback)

    async def publish(self, key: str, value: Any):
        for pattern, callbacks in self._subscribers.items():
            if pattern == "*" or fnmatch.fnmatch(key, pattern):
                for cb in callbacks:
                    await cb(key, value)

# In router.py — triggers on PUT:
@router.put("/config/{key}")
async def update_config(key: str, body: ConfigUpdate, bus=Depends(get_bus)):
    _save_to_sqlite(key, body.value)
    await bus.publish(key, body.value)
    return {"status": "updated"}
```

### Pattern 4: In-Process HDR Histogram (Percentile Metrics)

**What:** Track per-operation latency using an in-memory sorted list of observations. At Prometheus scrape time, compute p50/p95/p99 from the sorted data and export as gauges. Reset after each scrape to avoid unbounded memory.

**When to use:** Granular latency tracking per MCP tool operation where Prometheus Histogram buckets don't provide enough precision.

**Trade-offs:**
- Pros: Exact percentiles (no bucket approximation), low overhead for moderate request rates
- Cons: O(n log n) sort per scrape; doesn't scale to millions of observations per interval

**Example:**
```python
# observability/percentiles.py
import time
import bisect

class HDRHistogram:
    def __init__(self, name: str):
        self.name = name
        self._observations: list[float] = []

    def observe(self, value: float):
        bisect.insort(self._observations, value)

    def percentiles(self) -> dict[str, float]:
        if not self._observations:
            return {"p50": 0, "p95": 0, "p99": 0}
        n = len(self._observations)
        def _p(p: float) -> float:
            return self._observations[int(n * p)]
        result = {
            "p50": _p(0.50),
            "p95": _p(0.95),
            "p99": _p(0.99),
            "count": n,
        }
        self._observations.clear()
        return result

# Usage:
_percentile_histograms: dict[str, HDRHistogram] = {}

def record_tool_latency(tool: str, latency_ms: float):
    if tool not in _percentile_histograms:
        _percentile_histograms[tool] = HDRHistogram(tool)
    _percentile_histograms[tool].observe(latency_ms)
```

## Data Flow

### Admin SPA Request Flow

```
Browser ─── GET /admin/ ─────────────────────────────────────────────┐
  │                                                                   │
  │  ← HTML shell (Alpine.js manages tabs by x-show)                 │
  │                                                                   │
  │  (no API key in localStorage?)                                    │
  │  └── Show login modal                                             │
  │       └── POST /api/v1/auth/session {Authorization: Bearer <key>} │
  │            ├── 200 → JWT cookie set, localStorage.setItem         │
  │            ├── 401 → "Invalid key" error                          │
  │            └── store user.role from response body                 │
  │                                                                   │
  │  (authenticated — tab content via HTMX hx-trigger="load")         │
  │  ├── hx-get="/admin/tabs/documents" → tab_documents.html partial  │
  │  ├── hx-get="/admin/tabs/monitoring" → tab_monitoring.html        │
  │  ├── hx-get="/admin/tabs/ingestion"  → tab_ingestion.html         │
  │  ├── hx-get="/admin/tabs/ragas"      → tab_ragas.html             │
  │  ├── hx-get="/admin/tabs/admin"      → tab_admin.html (admin only)│
  │  └── hx-get="/admin/tabs/profile"    → tab_profile.html           │
  │                                                                   │
  │  All HTMX requests include:                                       │
  │    hx-headers='{"Authorization": "Bearer ${apiKey}"}'             │
  │    + global htmx:beforeRequest handler                            │
  │                                                                   │
  │  On 401 response → htmx:responseError → clear key → show login    │
  └───────────────────────────────────────────────────────────────────┘
```

### Config Change Flow (Hot-Reload)

```
Admin User clicks "Save" on config row
        │
        ▼
PUT /api/v1/config/EMBED_BACKEND {"value": "ollama"}
        │
        ▼
FastAPI Router → validate type → write to SQLite config table
        │
        ▼
HotReloadBus.publish("EMBED_BACKEND", "ollama")
        │
        ├──▶ EmbedClient.reload_if_changed()
        │       └── recreates HTTP client with new base URL
        ├──▶ CircuitBreaker.reset()
        └──▶ Health check picks up new backend on next check
```

### Percentile Metrics Flow

```
MCP Tool Call (search_kb, list_documents, etc.)
        │
        ▼
record_tool_latency("search_kb", 234.5)  ← called at end of handler
        │
        ▼
HDRHistogram.observe(234.5) → bisect.insort into sorted list
        │
        ▼
Prometheus scrape GET /metrics (every 15s)
        │
        ▼
HDRHistogram.percentiles() → compute p50/p95/p99, clear observations
        │
        ▼
Set Prometheus gauges:
  kb_rag_tool_latency_p50{tool="search_kb"} 185.0
  kb_rag_tool_latency_p95{tool="search_kb"} 420.3
  kb_rag_tool_latency_p99{tool="search_kb"} 891.7
```

### Auth API Data Model ER

```
 ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
 │    User      │       │   ApiKey     │       │  AuditLog    │
 ├──────────────┤       ├──────────────┤       ├──────────────┤
 │ id (UUID PK) │◄──────┤ user_id (FK) │       │ id (UUID PK) │
 │ username     │       │ id (UUID PK) │       │ timestamp    │
 │ role         │       │ key_hash     │       │ actor_id     │
 │ is_active    │       │ prefix       │       │ action       │
 │ created_at   │       │ description  │       │ resource_type│
 │ updated_at   │       │ is_revoked   │       │ resource_id  │
 └──────────────┘       │ last_used_at │       │ details (JSON)
         │              │ created_at   │       └──────────────┘
         │              └──────────────┘
         │
         │              ┌──────────────────┐
         └─────────────►│  ErasureRequest  │
                        ├──────────────────┤
                        │ id (UUID PK)     │
                        │ user_id (FK)     │
                        │ status (enum)    │
                        │ requested_by     │
                        │ approved_by      │
                        │ reason           │
                        │ timestamps       │
                        └──────────────────┘
```

### Config Data Model

```
SQLite: kb_metadata.db (or separate config.db)
  Table: config
  ┌─────────────┬──────────┬──────────┬───────────┬─────────────┐
  │ key (TEXT)  │ value    │ type     │ group     │ description │
  │ (PK)        │ (TEXT)   │ (TEXT)   │ (TEXT)    │ (TEXT)      │
  ├─────────────┼──────────┼──────────┼───────────┼─────────────┤
  │EMBED_BACKEND│ ollama   │ str      │ Embedding │ Which back..│
  │QDRANT_HOST  │ qdrant   │ str      │ Qdrant    │ Qdrant host │
  │...          │ ...      │ ...      │ ...       │ ...         │
  └─────────────┴──────────┴──────────┴───────────┴─────────────┘
```

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Qdrant | Async HTTP/gRPC via `qdrant_client` | Already existing; no change needed |
| LM Studio / Ollama | HTTP via `httpx` | Provider alias resolution in Phase 41 updates the backend URL at runtime |
| Grafana | Iframe embed via CSP `frame-src` | No API integration — just URL construction + CSP config |
| Prometheus | Scrape `/metrics` endpoint | Phase 39 adds new gauge metrics for percentiles |
| Browser | SSE (MCP) + HTTP (REST) + WebSocket (future?) | Streamable HTTP makes MCP work in browser contexts |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| MCP Server ↔ Vector Store | Direct async method calls | Shared `VectorStore` instance — no change needed |
| Admin API ↔ Auth Service | `auth/service.py` → SQLAlchemy | New package; creates new user/key tables in addition to existing `auth_registry` |
| Admin API ↔ Config API | `config/api.py` → `config/loader.py` | Config loader wraps both SQLite reads and env var fallback |
| Config API ↔ Hot-Reload Bus | `hotreload.py` pub/sub | In-process event bus; components subscribe with callbacks |
| Config API ↔ Embed Client | `HotReloadBus` → `EmbedClient.reload_if_changed()` | Provider alias resolution reads config on every request |
| Admin API ↔ Ingestion | REST → `JobManager.create_job()` | API creates jobs; existing pipeline executes them |
| Admin API ↔ Evaluation | REST → `GoldenDataset` CRUD | Dataset stored as JSON file; evaluation uses existing `RAGASEvaluator` |
| Auth Middleware (MCP) ↔ Auth Registry | Direct `auth_registry.py` call | Existing MCP auth unchanged; new Auth service uses separate SQLAlchemy tables |
| Percentile Metrics ↔ Prometheus | Gauge values computed per scrape | New `percentiles.py` module adds to existing `/metrics` endpoint |

### What Stays Unchanged

The following existing interfaces and behaviors are preserved exactly (no regressions):

- **MCP transport selection:** `MCP_TRANSPORT` env var still chooses stdio/SSE/streamable-http. Admin platform adds a third option without removing existing ones.
- **Auth for MCP:** Existing `auth.py` + `auth_registry.py` still handle MCP key verification. The new Auth service (`auth/`) adds user management but does not replace the existing MCP auth path.
- **Ingestion pipeline:** `ingest/ingest.py` and CLI unchanged. The admin API adds programmatic wrappers but doesn't modify core pipeline logic.
- **UI routes:** `/ui/browse` and `/ui/search` remain functional. `browse.html` gets cleanup controls added but existing query params still work.
- **Health server:** `health_server.py` remains on port 8080. Admin API adds a `GET /api/v1/health` endpoint that wraps the same checks.
- **Metrics endpoint:** `/metrics` on port 8080 unchanged. Percentile metrics are additional gauge metrics served alongside existing Prometheus metrics.
- **All 1165+ existing tests:** Must continue passing. New tests are additive.

### Deployment Integration

| Component | Docker Compose | systemd | Kubernetes |
|-----------|---------------|---------|------------|
| MCP Server (stdio/SSE/streamable-http) | `kb-rag-mcp` service (port 8765) | `kb-mcp.service` | Existing deployment |
| Health Server (port 8080) | Same container, different port | Same service | Existing probes |
| UI Server (port 8001) | `web-ui` service | Separate service (existing pattern) | Existing deployment |
| **Admin SPA** | Inside existing `web-ui` container | Inside existing UI service | Same pod as UI |
| **Auth DB** | SQLite volume (`./data`) | Same filesystem | PVC |
| **Config DB** | SQLite volume (`./data`) | Same filesystem | PVC (same DB as auth) |

The admin platform adds **no new containers or services** to the deployment topology. All new functionality lives inside the existing `web-ui` (FastAPI) container, augmented with new routes and templates.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-10 users | Current architecture is fine. SQLite handles this easily, single-process admin UI is responsive |
| 10-100 users | Consider moving from SQLite to PostgreSQL for auth/config (if concurrent writes become contention). Add rate limiting on auth endpoints (already exists for MCP) |
| 100+ users | Split admin API into separate process (scale independently from MCP). Add Redis-backed session store (replaces JWT cookie for sticky sessions). Switch from in-process HDR histograms to proper histograms library or push to dedicated metrics system |

### Scaling Priorities

1. **First bottleneck:** SQLite concurrent writes on auth/config when many admin users edit settings simultaneously. Mitigation: FastAPI runs async workers; SQLite has poor write concurrency. If this becomes an issue, migrate auth/config to the same PostgreSQL used for the registry.
2. **Second bottleneck:** Admin SPA loading tab content that queries Qdrant (e.g., documents tab listing thousands of docs). Mitigation: Add server-side pagination and debounced search — already designed into the API.
3. **Third bottleneck:** Percentile memory usage at high request volumes (1000+ req/s). Mitigation: Replace sorted-list HDR with `py-metrics` or a streaming quantile estimator (T-Digest) for high-throughput paths.

## Anti-Patterns

### Anti-Pattern 1: Mixing MCP Auth and Admin Auth

**What people do:** Using the same API key verification for both MCP tools and admin API, or trying to unify them into a single auth path.

**Why it's wrong:** MCP auth needs a simple key check that returns success/failure with minimal latency (adds <1ms to a query). Admin auth needs user management, role checks, session cookies, GDPR erasure workflows, and audit logging. Forcing both through the same code path either bloats the MCP auth path (adding overhead to every query) or cripples the admin auth (losing user management features).

**Do this instead:** Keep the existing `auth.py` → `auth_registry.py` for MCP transport auth. Build a parallel `auth/` package with SQLAlchemy models, FastAPI Depends guards, and a separate auth DB for admin features. The `auth_registry` already has its own SQLite table and singleton pattern — leave it alone. The new Auth service creates its own tables (`users`, `api_keys`, `audit_log`, `erasure_requests`). If you want key sharing, write a compatibility adapter that checks both registries — but don't merge them.

### Anti-Pattern 2: Rewriting os.getenv Calls to Use Config Loader

**What people do:** Removing all `os.getenv("KEY", default)` calls and replacing them with `ConfigLoader.get("KEY")` in a bulk refactor.

**Why it's wrong:** Every `os.getenv` call works today. A bulk rewrite touches every module, introduces import changes, breaks tests, and risks regression. Many env vars are read once at startup and never change (e.g., log paths, port numbers). Hot-reload is only valuable for values that change during operation (embedding backend, Qdrant host, rate limits, cache TTL).

**Do this instead:** Add the config loader as an *override layer*, not a replacement. Each component keeps its `os.getenv("KEY", default)` default. The config loader wraps existing env reads: `os.getenv("KEY", default)` stays as fallback. Only add config loader lookups for values where runtime change is meaningful. Mark those with registry entries so the admin UI shows them as editable. The config loader's chain is: SQLite override → `os.getenv` → hardcoded default.

### Anti-Pattern 3: Admin SPA with Full Build Toolchain

**What people do:** Adding webpack/vite/parcel to compile React/Vue/Svelte for the admin panel, requiring `node_modules`, build steps, and npm scripts.

**Why it's wrong:** The admin panel is a management UI, not a customer-facing application. It doesn't need complex state management, routing, or animation. Adding a JavaScript build step doubles the container build time, adds npm dependency management, and creates a second build pipeline alongside the Python/uvicorn deployment.

**Do this instead:** Alpine.js + HTMX + Bootstrap 5 (exactly as specified in the design). Zero build step — Alpine and HTMX are CDN-loaded. Templates are server-rendered Jinja2 partials. The existing Jinja2 FastAPI backend already serves Bootstrap 5 and HTMX. Adding Alpine.js is one `<script>` tag. Tab switching is `x-show`, not client-side routing. Data fetching is HTMX `hx-get`, not `fetch()` + DOM manipulation.

### Anti-Pattern 4: Config Hot-Reload via File Polling

**What people do:** Polling `config.toml` or `.env` file every N seconds to detect changes.

**Why it's wrong:** File polling is wasteful (disk I/O every N seconds even when nothing changes), has latency proportional to poll interval, and misses rapid edits. For an admin UI where a user clicks "Save" and expects immediate effect, polling creates a poor experience.

**Do this instead:** Use the event bus pattern: config change → `PUT` endpoint → SQLite write → event bus publish → subscriber reacts. No polling, instant propagation. For the rare case where a change happens outside the admin UI (e.g., operator edits SQLite directly), add a lightweight `watchdog`-style monitor as a safety net with a long interval (60s).

## Build Order & Dependency Graph

### Phase Dependency Map

```
Phase 28 (Streamable HTTP) ──────────────┐
    (no deps; Plan 28-01 already done)    │
                                          ▼
Phase 28b (Auth & User API) ─────────► Phase 28c (Admin SPA)
    ├─ deps: Config (Phase 40)             ├─ deps: Phase 28b (auth endpoints)
    │   (needs config for JWT secret)      ├─ deps: Phase 38 (Grafana tab)
    │                                      └─ deps: Phase 41 (monitor lights)
    ▼
Phase 39 (Observability)
    ├─ OBS-01 (Health): deps: Phase 28b (health API endpoint)
    ├─ OBS-02 (Request ID): no deps
    └─ METRICS-01 (Percentiles): no deps

Phase 40 (Config) ──────────────────────► Phase 41 (Provider Aliases)
    ├─ Config Loader: no deps               └─ deps: Phase 40 (config table)
    ├─ Config API: no deps
    └─ Hot-Reload: no deps

Phase 38 (Grafana Embed)
    └─ deps: Phase 28c (admin shell exists, monitoring tab)

SPA-04 (Export): deps: Phase 28c (SPA exists)
SPA-05 (Advanced Filters): deps: Phase 28c (SPA exists), browse.html modify
```

### Suggested Execution Order

1. **Phase 28 (Streamable HTTP)** — Already started (Plan 28-01 complete). Finish the transport branch in `server.py`. Foundation for browser-based MCP access.
2. **Phase 40 (Config Backlog)** — No dependencies on other phases. Config loader and API are needed by Auth (JWT secret), Provider Aliases, and admin config tab. Build early.
3. **Phase 28b (Auth & User API)** — Depends on Config (JWT signing key). Core dependency for Admin SPA (login, role gating, user management).
4. **Phase 41 (Provider Aliases)** — Depends on Config table. Small, self-contained change to `embed_client.py`. Can be done in parallel with Phase 28b.
5. **Phase 39 (Observability Backlog)** — OBS-02 (Request ID) and METRICS-01 (Percentiles) have no deps and can run in parallel with Phase 28b. OBS-01 (Health API endpoint) depends on Phase 28b for the `/api/v1/health` route.
6. **Phase 28c (Admin SPA Panel)** — Depends on Phase 28b (auth endpoints). Main UI effort.
7. **Phase 38 (Grafana Embed)** — Depends on Phase 28c admin shell existing for the monitoring tab.
8. **SPA-04 (Export)** — After Phase 28c shell exists. Browse page modification.
9. **SPA-05 (Advanced Filters)** — After Phase 28c shell exists. Browse page modification.

### Parallelizable Groups

- **Group A (Foundation):** Phase 28, Phase 40 — can run concurrently
- **Group B (Backend Services):** Phase 28b, Phase 41, Phase 39 (OBS-02 + METRICS-01) — can run concurrently
- **Group C (UI):** Phase 28c, Phase 38, SPA-04, SPA-05 — sequential within group (Phase 28c first)

## Sources

- Design spec: `docs/superpowers/specs/2026-06-13-admin-platform-design.md`
- Existing server.py streamable-http implementation (Plan 28-01)
- Existing `auth.py` + `auth_registry.py` patterns (Phase 32)
- Existing `health.py` component check patterns
- Existing `observability/metrics.py` Prometheus histogram patterns
- Existing `kb_server/ui/app.py` FastAPI + Jinja2 template patterns
- Existing `ingest/job/manager.py` job CRUD patterns
- Existing `kb_server/evaluation/dataset.py` golden dataset patterns

---
*Architecture research for: kb-rag-mcp v0.1.5 Admin Platform*
*Researched: 2026-06-15*
