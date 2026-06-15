# Domain Pitfalls

**Domain:** Admin Platform Features for Existing Async MCP RAG System
**Researched:** 2026-06-15
**Overall Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Streamable HTTP Session Orphan at Disconnect

**What goes wrong:**
When an MCP client disconnects without sending `DELETE /mcp` (e.g., browser tab close, network drop, process kill), the server-side session entry and its associated resources (in-memory transport state, rate-limit bucket, subject tracking) remain allocated. Over hours of operation with multiple clients, leaked sessions accumulate — consuming memory, bloating the session lookup table, and eventually causing `Mcp-Session-Id` collisions or OOM.

**Why it happens:**
The MCP Streamable HTTP spec defines session termination via an explicit `DELETE` request carrying `Mcp-Session-Id`. In practice, many clients (Cursor, OpenCode, custom agent code) do not send `DELETE` on disconnect. The server has no mandatory heartbeat or idle-timeout mechanism in the base spec. If the implementation only cleans up on `DELETE`, every dropped connection becomes a leak.

**How to avoid:**
1. **Mandatory idle timeout** — every session gets `MCP_SESSION_TIMEOUT` (env var, default 300s). A background asyncio task periodically scans sessions, removes any whose `last_activity` exceeds the threshold, and closes associated state.
2. **Connection-monitoring on GET stream** — for SSE streams, hook the ASGI disconnect event (`await request.is_disconnected()` in a watchdog coroutine). On disconnect, schedule session cleanup with a short grace period (the client may reconnect for resumption).
3. **Session count limit** — hard cap on concurrent sessions (e.g., `MCP_MAX_SESSIONS=1000`). When exceeded, reject new `POST /mcp` with `429 Too Many Sessions` and log a warning.
4. **Test with forced disconnect** — write a test that opens an MCP session, kills the client connection without DELETE, waits for timeout, and asserts the session is cleaned up.

**Warning signs:**
- Rising memory usage in the MCP server process over hours
- `Mcp-Session-Id` uniqueness errors in logs
- `/metrics` showing growing `active_sessions` gauge without corresponding `DELETE` calls

**Phase to address:**
Phase 28 (Streamable HTTP implementation) — must include session lifecycle management; not deferrable to a later phase.

---

### Pitfall 2: Auth Bypass on MCP Stream Endpoint

**What goes wrong:**
The `/mcp` Streamable HTTP endpoint accepts GET (SSE stream), POST (JSON-RPC), DELETE (session terminate), and OPTIONS (CORS preflight). Auth middleware checks `Authorization: Bearer <key>` on POST requests but omits the check on GET — reasoning that the GET is "just a stream connection." An attacker can open a GET SSE stream without authentication and receive server-to-client notifications, tool results returned via the stream, or session data. Worse: if auth is checked at the Starlette ASGI middleware level but the Streamable HTTP handler's GET route is registered outside that middleware scope, it bypasses auth entirely.

**Why it happens:**
The mental model "POST = mutating, needs auth; GET = reading, safe" does not apply to Streamable HTTP. The GET stream IS the session's return channel — it carries tool call results, error messages, and resource update notifications. A naive middleware layer that discriminates by HTTP method misses this. Also, the existing `kb_server/auth.py:verify_request()` is function-call-based, not middleware-based, making it easy to forget invocation on new routes.

**How to avoid:**
1. **Auth as Starlette Middleware, not function calls** — implement `AuthMiddleware` as a Starlette `BaseHTTPMiddleware` or pure ASGI middleware that runs on every route. The middleware extracts the token, calls `verify_request()`, and returns 401 on failure — before any route handler executes.
2. **Apply to ALL HTTP methods on /mcp** — the middleware check must apply to GET, POST, DELETE, and OPTIONS (OPTIONS can be excluded only if CORS preflight never carries credentials, but the spec says `Mcp-Session-Id` may appear in OPTIONS headers).
3. **Auth bypass test matrix** — write parametrized tests that attempt each HTTP method against `/mcp` without credentials and expect `401`.
4. **Existing SSE transport also needs auth** — if the legacy SSE endpoint is kept alongside Streamable HTTP, apply the same middleware there too.

**Warning signs:**
- SSE GET requests to `/mcp` succeed without any `Authorization` header
- Integration test for unauthenticated GET passes (should fail)
- Code review shows auth check inside route body rather than in middleware

**Phase to address:**
Phase 28 (Streamable HTTP) — auth middleware must be applied to the new /mcp endpoint. Phase 28b (Auth API) should migrate to Starlette middleware pattern so all routes benefit.

---

### Pitfall 3: SQLite WAL File Unbounded Growth Under Concurrent Write Load

**What goes wrong:**
The new auth API (Phase 28b), config API (Phase 40), audit logging, query logging, and access-token operations all write to SQLite stores. Under moderate concurrent load, the WAL file grows without bound — reaching tens of gigabytes — because SQLite's auto-checkpoint cannot run while readers/writers are continuously active. The disk fills, the server crashes, and recovery requires manual `PRAGMA wal_checkpoint(TRUNCATE)`.

**Why it happens:**
- The auto-checkpoint threshold defaults to 1000 pages (~4 MB in WAL mode), but the checkpointer requires a moment with no active readers to complete a checkpoint.
- In async Python with FastAPI + uvicorn, multiple concurrent requests hold open read transactions overlapping with write activity. The WAL accumulates frames faster than the checkpointer can flush them.
- The existing codebase already has this problem waiting to happen: `ingest/core/metadata.py` correctly enables WAL, but `kb_server/telemetry/query_logger.py` and `kb_server/ui/routes.py` use `sqlite3.connect()` without any WAL pragmas — they default to rollback journal mode, which blocks writers entirely.

**How to avoid:**
1. **Enable WAL on EVERY SQLite connection** — including `query_logger.py`, `routes.py`, `analytics/query_analyzer.py`, and the new `auth/models.py`. Add a helper: `def enable_wal(conn): conn.execute("PRAGMA journal_mode=WAL")` called after every `sqlite3.connect()`.
2. **Set `journal_size_limit`** — `PRAGMA journal_size_limit=67108864` (64 MB limit) so WAL is truncated after checkpoints.
3. **Set lower auto-checkpoint threshold** — `PRAGMA wal_autocheckpoint=100` (checkpoint after 100 pages, ~400 KB, vs default 1000).
4. **Add a watchdog that monitors WAL size** — a background asyncio task checks WAL file size every 30 seconds. If it exceeds a threshold (e.g., 256 MB), force a passive checkpoint via `PRAGMA wal_checkpoint(PASSIVE)`. If that fails repeatedly, log a warning and schedule a TRUNCATE checkpoint during low activity.
5. **For new auth/config SQLAlchemy models** — set `connect_args={"check_same_thread": False}` and issue `PRAGMA journal_mode=WAL` on engine creation.

**Warning signs:**
- `*.db-wal` files growing past 100 MB
- `SQLITE_BUSY` errors in logs under moderate load
- Latency spikes on write endpoints (checkpoint pressure)
- Disk usage alerts from the deployment

**Phase to address:**
Phase 28b (Auth API) — the new SQLAlchemy engine must configure WAL mode correctly. Phase 39 (Observability) should add WAL-size monitoring. But the *existing* SQLite connections in `query_logger.py` and `routes.py` need a pre-emptive fix in a dedicated cleanup task before high-load writing begins.

---

### Pitfall 4: CSP Conflict Between Grafana Iframe and Alpine.js

**What goes wrong:**
The admin SPA (Phase 28c) loads Alpine.js via CDN `<script src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js" defer>`. Alpine.js uses `Function()` internally, which requires `'unsafe-eval'` in the CSP `script-src` directive. The Grafana iframe embed (Phase 38) requires `frame-src https://grafana.internal:3000`. These two CSP requirements are inherently conflicting — `'unsafe-eval'` opens XSS vectors that the rest of the CSP is designed to prevent. If the admin SPA sets a strict CSP that blocks `'unsafe-eval'`, Alpine.js silently fails (no error, just non-functional UI). If it allows `'unsafe-eval'`, the CSP no longer protects against injected script execution from any XSS vulnerability in the SPA.

**Why it happens:**
- Alpine.js default CDN build uses `new Function(...)` for expression evaluation, which CSP `script-src 'unsafe-eval'` enables. This is a known limitation documented in the Alpine.js CSP build guide.
- Developers commonly copy-paste a CSP header that works for one feature without considering interactions. Adding Grafana's `frame-src` without auditing the full CSP policy creates blind spots.
- The admin spec says "Alpine.js CDN" and "Grafana iframe" independently; the CSP conflict is an emergent property of combining them.

**How to avoid:**
1. **Use Alpine.js CSP build** — load `@alpinejs/csp` instead of the default CDN build. The CSP build moves expression logic into a separate JS file, eliminating the need for `'unsafe-eval'`. It requires minor code changes (no `x-on:click="count++"` inline expressions; must use `@click="increment"` with `increment() { this.count++ }` in a separate `<script>` block).
2. **Explicit CSP header in Starlette middleware** — write a `CSPMiddleware` that sets `Content-Security-Policy` with explicitly enumerated directives:
   - `default-src 'self'`
   - `script-src 'self' 'nonce-{random}'` (with nonce-based loading for inline scripts)
   - `style-src 'self' 'unsafe-inline'` (Bootstrap 5 requires this)
   - `frame-src 'self' https://grafana.internal:3000` (configurable via config API)
   - `frame-ancestors 'self'`
   - `base-uri 'self'`
   - `object-src 'none'`
   - `form-action 'self'`
3. **Nonce-based script loading** — generate a unique nonce per request in the Starlette middleware, pass it to Jinja2 templates, and apply `nonce="{{ csp_nonce }}"` to all `<script>` tags. This eliminates `'unsafe-inline'` for scripts.
4. **Test CSP compliance** — write a test that loads the admin SPA and asserts the CSP header contains `frame-src` matching the configured Grafana URL, and `script-src` does NOT contain `'unsafe-eval'`.

**Warning signs:**
- Browser console shows "Refused to evaluate a string as JavaScript" (Alpine.js broken by CSP)
- Browser console shows "Refused to frame 'https://grafana.internal:3000'" (iframe blocked)
- Admin SPA sidebar navigation stops working (Alpine.js silently failing)
- Grafana dashboard tab shows empty or "refused to connect"

**Phase to address:**
Phase 28c (Admin SPA) — must include CSP configuration upfront. Phase 38 (Grafana Embed) — must update CSP to include frame-src. Both phases must coordinate on a single CSP policy; do not treat them independently.

---

### Pitfall 5: Hot-Reload Race Condition in Config Layer

**What goes wrong:**
The config hot-reload chain (Phase 40) works as: `PUT /api/v1/config/{key}` → broadcast change event → each component's `reload_if_changed()` hook reads the updated SQLite value. If component A and component B both read the SQLite config table concurrently during reload, and component A's internal state depends on component B also having the new value, a window exists where A sees the new value but B still has the old one. This causes inconsistent behavior — e.g., embedding backend changes halfway through a batch of indexing operations, or rate-limit parameters changing mid-request.

**Why it happens:**
- The broadcast-and-hook pattern is inherently non-atomic. Each component re-reads independently.
- Python asyncio runs on a single thread but interleaves coroutines at `await` points. If `reload_if_changed()` has an `await` inside its critical section (e.g., `await asyncio.sleep(0)` or an `await` during config DB re-read), another coroutine can start using the half-applied config.
- The config spec says "Each component exposes a `reload_if_changed()` hook" but does not specify ordering or atomicity guarantees.

**How to avoid:**
1. **Config generation version counter** — every config write increments a monotonic `config_version` integer. Components cache their last-seen version. On `reload_if_changed()`, if `stored_version != last_seen_version`, the component re-reads and applies. Any component that sees a version > its own applies a full flush (not incremental).
2. **No atomicity guarantees needed by design** — make each config key independently toggleable. If a change requires coordinated toggles (e.g., changing both embedding model AND endpoint URL), clients must write them one at a time; the system remains functional in the intermediate state (e.g., uses old model with new URL — may fail, but fails safe by logging error and falling back instead of silently corrupting).
3. **Avoid await in reload hot-path** — `reload_if_changed()` should be synchronous or use `asyncio.get_event_loop().run_in_executor()` for DB reads, with the state transition happening before returning so no interleaving occurs between "read new config" and "apply new config."
4. **Test with concurrent updates** — write a test that spawns 10 concurrent coroutines, each updating a different config key, while 10 other coroutines continuously read config. Assert no stale reads after all updates complete.

**Warning signs:**
- Embedding model changes without matching endpoint URL change cause 500 errors
- Rate-limit window shifts mid-request, dropping valid requests
- Intermittent "Config value for X changed during request" log messages

**Phase to address:**
Phase 40 (Config Backlog) — the hot-reload architecture must bake in version-based change detection and no-await reload hooks from the start.

---

### Pitfall 6: Admin SPA Bearer Token in localStorage — XSS Exfiltration

**What goes wrong:**
The admin SPA auth flow stores the API key in `localStorage` under key `kb_api_key`, then reads it for every HTMX request via `htmx:beforeRequest` event handler. Any XSS vulnerability in the SPA — even a single unescaped user-generated string rendered via Jinja2 without escaping — allows an attacker to execute `localStorage.getItem('kb_api_key')` and exfiltrate the key to their server. The attacker now has persistent API access to the MCP server, able to search the full knowledge base and retrieve any chunk.

**Why it happens:**
- The admin spec explicitly says "stores key in localStorage." This is a well-known security anti-pattern (Auth0, OWASP, and every major auth guide warn against it).
- The rationale is simplicity: "no password infrastructure needed." But the convenience comes at the cost of making any XSS vulnerability a total account compromise.
- SPA uses Alpine.js + Bootstrap 5 + HTMX all from CDN — any of these could have a transient XSS in a specific version, or a compromised CDN could inject malicious code.
- The existing Jinja2 templates use `{{ variable }}` (auto-escaped) in most places, but the admin spec mentions config values rendered as editable inputs. A config value containing `"><script>...</script>` stored in the SQLite config table could become a stored XSS.

**How to avoid:**
1. **Use HttpOnly cookie instead of localStorage** — exchange the API key for a short-lived JWT stored in an `HttpOnly`, `SameSite=Lax`, `Secure` cookie (in production). The admin SPA never has programmatic access to the token. CSRF protection via `Double Submit Cookie` pattern or custom header requirement (`X-KB-Requested-By: SPA`).
2. **If localStorage is unavoidable** (e.g., for MCP client header use), use **in-memory-only** storage with a non-persistent pattern: store the key in a JavaScript closure or Alpine.js data object. On page refresh, the user re-authenticates. Accept the UX tradeoff and document it.
3. **Sanitize ALL config values before rendering** — config values are user-editable strings. They must be HTML-escaped when rendered in the admin template, even in editable input fields. Use Jinja2's `{{ value }}` auto-escaping (default), never `{{ value | safe }}` unless explicitly reviewed.
4. **Subresource Integrity (SRI) for all CDN scripts** — load HTMX, Alpine.js, and Bootstrap with `integrity="sha384-..."` attributes so a compromised CDN cannot inject malicious code.
5. **Test for XSS in config rendering** — write a test that sets a config value to `"><script>alert(1)</script>`, renders admin config page, and asserts the script tag appears as escaped text content, not executable HTML.

**Warning signs:**
- Code review shows `localStorage.getItem`/`localStorage.setItem` in SPA code
- Config admin page renders values using `{{ value | safe }}`
- No `HttpOnly` or `SameSite` attributes on JWT cookie `Set-Cookie` header
- CDN script tags missing `integrity` attribute

**Phase to address:**
Phase 28c (Admin SPA) — must use cookie-based auth, not localStorage, from day one. Retrofit is much harder after the SPA code is written around localStorage.

---

### Pitfall 7: Percentile Histogram Memory Leak (Unbounded In-Memory Sorted List)

**What goes wrong:**
Phase 39's METRICS-01 specifies "in-memory HDR histogram (via `py-metrics` or manual sorted-list) per operation." If implemented as a manual sorted list (appending every latency measurement), the list grows without bound until the scrape interval resets it. Between scrapes, the list can accumulate millions of entries under load, consuming gigabytes of memory. Even with the spec's "reset every scrape interval" (default 15s), peak memory during that window can be enormous — a busy MCP server handling 1000 req/s × 4 operations × 15s = 60,000 entries per list, each ~24 bytes = ~6 MB per list, × 4 operations = 24 MB. At 10,000 req/s it's 240 MB — noticeable but not catastrophic. The real danger: if the scrape interval is missed (Prometheus scrape fails, server restart), the list accumulates for hours.

**Why it happens:**
- The spec says "reset every scrape interval" but provides no mechanism for guaranteed reset if the Prometheus scrape doesn't arrive on schedule.
- Python's `list.append()` has amortized O(1) but the list object's backing array grows with each append, never shrinking until reset.
- Sorting the list on every `/metrics` scrape (to compute percentiles) is O(n log n) — at 60k entries this is noticeable latency on the metrics endpoint itself.

**How to avoid:**
1. **Use a fixed-size ring buffer** — pre-allocate a circular buffer of `MAX_SAMPLES` (e.g., 10,000) per operation, overwriting oldest entries when full. Compute percentiles from the buffer at scrape time. This bounds memory to `MAX_SAMPLES × 4 operations × 8 bytes = 320 KB` regardless of load.
2. **Or use HdrHistogram** — the `hdrhistogram` Python library provides a proper HDR histogram implementation with configurable precision and value range. It uses fixed memory (~256 KB typical) and supports `get_value_at_percentile()` in O(1). This is the standard approach for percentile monitoring.
3. **Self-triggered snapshot** — if using list-based implementation, do NOT rely on Prometheus scrape for reset. Instead, use a background asyncio task that snapshots and resets the list on a fixed cadence (15s), writing the snapshot to a thread-safe atomic reference. The `/metrics` handler reads the latest snapshot.
4. **Test memory bound** — write a test that inserts 1M entries into the histogram and asserts memory stays below 5 MB.

**Warning signs:**
- `kb_server` process RSS growing steadily over time
- `/metrics` endpoint latency increasing (sorting larger list)
- Garbage collection pauses becoming noticeable

**Phase to address:**
Phase 39 (Observability Backlog) — METRICS-01 implementation must use bounded-memory histogram from the start.

---

### Pitfall 8: GDPR Erasure — Audit Log Retains Identifiable PII via Tombstone Failures

**What goes wrong:**
The GDPR erasure flow (Phase 28b) specifies: "tombstone pattern: anonymize username, clear hash, hard-delete API keys, keep UUID. Audit log retained with UUID-only reference." The pitfall: audit log entries may contain free-text `details` fields that include the user's name, email, IP address, or other PII not captured in structured columns. When the user is erased, the structured columns are anonymized but the `details` JSON field still contains readable PII. A data subject access request (Art 15) or audit by a data protection authority would find that the "erased" data is still present in the audit logs.

**Why it happens:**
- The spec assumes PII only lives in structured model fields (username, key_hash). In practice, audit log `details` often includes request parameters, error messages, or context that contains unintentional PII.
- The erasure workflow only scrubs the `User` and `ApiKey` tables. It doesn't define a "scrub free-text" step for audit logs, query logs, or other stores that may contain PII references.
- The 90-day auto-prune on audit logs deletes old entries but does not clean entries within the retention period.

**How to avoid:**
1. **PII inventory before implementing erasure** — create a machine-readable data inventory (Phase 28b deliverable `docs/DATA_INVENTORY.md`) that maps every PII field to its storage location. Include free-text fields (audit log `details`, query log `query_text`, config `description`).
2. **Structured erasure policy per table** — define for each storage location what erasure means:
   - `User`: anonymize username, nullify email, clear hash (spec does this correctly)
   - `ApiKey`: hard-delete all rows for user (spec does this correctly)
   - `AuditLog.details`: scrub PII patterns (email regex, IP regex, name patterns) or replace with `"erased"` string
   - `QueryLog.query_text`: similarly scrub or replace with `"erased"` for queries owned by the erased user
   - Backup copies: document retention period and that erasure will be effective after the next backup rotation
3. **Erasure ledger** — write the erasure to a dedicated `ErasureLedger` table BEFORE performing the operational deletion. If the process crashes mid-flow, the ledger record ensures the erasure is retried. This is critical for audit defensibility.
4. **Restore drill** — test that a backup restore + ledger replay produces a system where the erased user's PII is not restored. Document this as a quarterly operations exercise.
5. **Test erasure completeness** — write an integration test that creates a user with PII in every possible field (including audit log `details`), performs erasure, and asserts no regex patterns matching that user's PII appear in any table.

**Warning signs:**
- Audit log `details` rendered in admin SPA config change history (showing user ID or IP)
- `DELETE /api/v1/users/{id}` implementation only touches `users` and `api_keys` tables
- No test asserts "erased user's PII is absent from all stores"
- Backup restore brings back erased user's PII

**Phase to address:**
Phase 28b (Auth & User Management API) — the erasure workflow MUST include free-text scrubbing and a data inventory. The `docs/DATA_INVENTORY.md` must be created before any erasure code is written.

---

### Pitfall 9: JWT Without Rotation Enables Session Hijacking

**What goes wrong:**
The auth design uses JWT session cookies (8h expiry) exchanged for API keys. If the JWT is stolen (via XSS, network interception, or log exposure), the attacker has an 8-hour window to impersonate the user. There is no refresh token rotation, no reuse detection, and no mechanism to revoke a JWT before expiry (the JWT is self-contained and stateless). The attacker only needs to steal the JWT once to maintain access until it expires.

**Why it happens:**
- The spec says "JWT session cookie (HttpOnly, SameSite=Lax, Secure in production, 8h expiry)" but does not mention refresh tokens, rotation, or revocation.
- JWT-based auth is commonly implemented as "issue once, trust until expiry" in FastAPI tutorials, which normalizes the anti-pattern.
- The design chooses stateless JWTs for simplicity but the admin SPA is a browser application where stateful sessions with server-side revocation are feasible and more appropriate.

**How to avoid:**
1. **Use opaque server-side sessions instead of JWTs for browser SPA** — the admin SPA is a first-party web application, not a distributed API. Store a random session token (e.g., `secrets.token_urlsafe(32)`) in the `sessions` table (SQLAlchemy model in auth DB), mapped to the user ID and expiry. The browser gets this token as an `HttpOnly` cookie. Revocation = `DELETE FROM sessions WHERE id = ?`.
2. **If JWTs are required** (e.g., for MCP client header use), implement **refresh token rotation with reuse detection**:
   - Short access token (15 min) + longer refresh token (24h) stored hashed in DB
   - Every `/refresh` replaces both the access and refresh tokens
   - If a rotated-away refresh token is presented → revoke ALL tokens for that user (strong signal of theft)
3. **Token family concept** — group refresh tokens into families. If any token in a family is reused after rotation, revoke the entire family. This limits blast radius of a single token theft.
4. **Server-side blocklist** — maintain a short-lived blocklist (using cache or DB) for tokens that were explicitly revoked before expiry (e.g., "logout everywhere" feature).

**Warning signs:**
- JWT `exp` claim is 8+ hours
- No `/refresh` endpoint exists
- No `refresh_tokens` table in auth models
- Revoking a user's session requires changing the JWT secret (killing all sessions)

**Phase to address:**
Phase 28b (Auth API) — the auth model must include session/refresh token tables. The JWT-only approach does not provide revocation capability.

---

### Pitfall 10: Existing Non-WAL SQLite Connections Cause `SQLITE_BUSY` Under New Concurrent Load

**What goes wrong:**
The new auth API, config API, and audit logging add concurrent write operations to SQLite databases. The existing `kb_server/telemetry/query_logger.py`, `kb_server/ui/routes.py`, and `kb_server/analytics/query_analyzer.py` all connect to `kb_metadata.db` without enabling WAL mode (they use the default rollback journal). In the rollback journal mode, a writer blocks ALL readers and other writers. When the new auth API writes audit entries or config updates while the existing query logger writes query logs, both database connections contend for the same lock. Result: `sqlite3.OperationalError: database is locked`.

**Why it happens:**
- The codebase grew organically — each SQLite consumer independently opened connections without coordinating on journal mode.
- Rollback journal is SQLite's default, so the issue only manifests under concurrent load that exceeds what the old code experienced.
- Phase 28b's new SQLAlchemy models will add MORE concurrent writes (audit log, config updates, session tokens) to the same database files, pushing concurrency past the tipping point.

**How to avoid:**
1. **Audit all SQLite connections** — find every `sqlite3.connect()` call in the codebase. List:
   - `kb_server/telemetry/query_logger.py` — 4 connect calls, no WAL
   - `kb_server/ui/routes.py` — 2 connect calls, no WAL
   - `kb_server/analytics/query_analyzer.py` — 4 connect calls, no WAL
   - `kb_server/auth_registry.py` — 1 connect call, no WAL
   - `ingest/core/metadata.py` — WAL enabled (good)
   - New auth API SQLAlchemy engine — MUST enable WAL
2. **Create a `db_utils.py` helper** — single function `get_db_connection(path)` that opens a connection, enables WAL, sets `synchronous=NORMAL`, sets `journal_size_limit`, and returns. Migrate all existing connections to use it.
3. **Add retry logic** — even with WAL, `SQLITE_BUSY` can occur under extreme contention. Use the `sqlite3` connection's `timeout` parameter (default 5 seconds) to retry automatically: `sqlite3.connect(path, timeout=10)`.
4. **Test under concurrent load** — write a stress test that spawns 20 concurrent coroutines writing to `kb_metadata.db` and reading from it, asserting zero `SQLITE_BUSY` errors.

**Warning signs:**
- "database is locked" errors appearing in logs after deploying new auth/config endpoints
- Query logger silently dropping entries on write failure
- Admin SPA config page showing stale data or 500 errors

**Phase to address:**
Phase 28b pre-requisite — a dedicated task to migrate all existing SQLite connections to WAL mode. Without this, the new concurrent writes will cause regressions.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| localStorage Bearer token storage | 0 lines of backend session code; SPA just reads key | Any XSS = total account takeover; no revocation; key visible in devtools | Never — use HttpOnly cookie |
| Stateless JWT with no refresh | No DB table for sessions; simple verify | No revocation; 8h hijack window; cannot force logout | For read-only MCP client tokens (where API key itself is the revocable credential), but NOT for browser SPA sessions |
| In-memory sorted list for percentiles | No library dependency; simple implementation | Unbounded memory growth under load; O(n log n) scrape latency | Only for <100 req/s with self-triggered snapshot reset; never for production use with Prometheus scrape |
| Single global SQLite connection (no WAL) | Connection reuse; simpler code | Blocking contention when multiple writers appear | Acceptable only in single-threaded contexts with zero concurrent writes (current query logger is borderline) |
| Skip Origin header validation on /mcp | Fewer bytes to code; works immediately | DNS rebinding attack; CSRF on MCP tools | Never — MCP spec mandates Origin validation for Streamable HTTP |
| CDN-loaded libraries without SRI | Faster iteration; always "latest" | Compromised CDN = arbitrary JS execution in admin SPA | Never for production — always pin versions and add integrity hashes |
| CSP as an afterthought | No debug time fighting CSP blocks | Retroactive CSP breaks features; team scrambles to relax policy | Never — set CSP middleware in Phase 28c before any feature template is written |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Grafana iframe embed | CSP `frame-src` mismatch; Grafana's `allow_embedding = false` default; missing `frame-ancestors` on Grafana side | Set `GF_SECURITY_ALLOW_EMBEDDING=true` in Grafana; add `frame-ancestors 'self'` to Grafana CSP; add `frame-src <grafana_url>` to admin SPA CSP; verify with `curl -I` |
| Streamable HTTP /mcp + FastAPI middleware | Auth middleware applied to `/mcp` POST but not GET (SSE stream) | Apply auth as ASGI middleware (runs on every request regardless of method); test GET, POST, DELETE, OPTIONS |
| SQLite + SQLAlchemy async `create_async_engine` | Using `sqlite+aiosqlite:///` without `check_same_thread=False` and WAL pragmas | `create_async_engine("sqlite+aiosqlite:///path", connect_args={"check_same_thread": False})` and `@event.listens_for(engine.sync_engine, "connect")` to set WAL pragmas |
| Prometheus `/metrics` + HDR histogram | Exposing raw sorted list as histogram buckets (wrong cardinality) | Use Prometheus `Histogram` metric with predefined buckets, or expose as `Summary` for percentile computation on client side |
| HTMX + CSP nonce | HTMX processes server responses as HTML fragments; if CSP has strict `script-src`, inline handlers from HTMX-swapped content may be blocked | Use HTMX's `hx-headers` for auth, not inline `onclick`; keep all JS in nonce-protected scripts loaded at page init; use HTMX events (`htmx:beforeRequest`) bound via `addEventListener` in the nonce script |
| Config hot-reload + EmbedClient reload | Embedding model change requires reloading the ML model (multi-GB RAM spike) | Do NOT hot-reload embedding models. Require a server restart (document this). The config API should warn "some changes require restart" |
| Provider alias + embedding backend switch | Alias resolves to a backend name that changes the embedding dimension | Validate on config write: if `provider_alias.X=Y`, verify that backend Y returns a dimension matching current Qdrant collection. Reject the write if dimensions don't match |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Session lookup on every /mcp request (linear scan of session dict) | Latency grows with number of concurrent sessions | Use `dict` (O(1)) keyed by session ID, not a list scan | >100 concurrent sessions |
| WAL auto-checkpoint under constant write load | WAL file grows to GBs; disk fills | Use watchdog to force checkpoint during idle windows; set `wal_autocheckpoint` low (100); enable `journal_size_limit` | Continuous writes >5 min without idle gap |
| Sorted-list percentile computation on every Prometheus scrape | `/metrics` endpoint latency spikes; Prometheus scrape timeout | Use HDR histogram with O(1) percentile lookup; compute percentile in a background task, cache result for scrape | >10k entries in list |
| SQLite without `synchronous=NORMAL` in WAL mode | Write throughput limited by fsync on every transaction | Set `PRAGMA synchronous=NORMAL` (safe with WAL) for 5-10x write throughput improvement | >100 writes/second |
| Jinja2 template re-compilation on every request (admin SPA with many partials) | Template render latency for HTMX partials | Enable Jinja2 cache: `app.env.globals.update` is fine, but template loader should use `FileSystemLoader` with `auto_reload=False` in production | >50 partials per page load |
| `verify_request()` calling `get_registry()` on every MCP tool call | Registry object re-created or DB re-queried per request | Cache `AuthRegistry` singleton; use in-memory key cache with periodic refresh | >50 requests/second |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Not validating `Origin` header on `/mcp` endpoint | DNS rebinding attack; cross-site MCP tool invocation | `verify_origin()`: reject requests where `Origin` doesn't match configured `MCP_ALLOWED_ORIGINS` (default `http://localhost:*`) |
| API key exposed in server error response | Key logged, sent to monitoring, visible in MCP client debug output | Ensure `verify_request()` returns `401` without revealing what was wrong with the key ("invalid credentials" vs "missing header") |
| Audit log stores raw `Authorization` header | API key or JWT captured in logs | Strip `Authorization` header from all log entries; log `user_id` (after resolution) instead |
| Config API `PUT` accepts arbitrary strings without type validation | Stored XSS: script injected via config value rendered in admin template | `ConfigService.set(key, value)` validates `value` against `type` column; rejects type mismatches with 422 |
| Admin SPA does not validate Grafana URL before embedding frame | Open redirect / phishing: attacker-controlled Grafana URL rendered as trusted iframe | Whitelist `GRAFANA_URL` against a regex pattern during config write; validate it points to internal domain |
| No rate limiting on auth session endpoint (`POST /api/v1/auth/session`) | API key brute-force; attacker enumerates valid keys | Apply existing token-bucket rate limiter to auth endpoints with stricter limits (5 req/min per IP) |
| Erasure request approved without secondary verification | Malicious admin can erase any user without oversight | Erasure workflow should require 2-person approval: one admin requests, a different admin approves. Log both actions |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Grafana iframe keyboard navigation trapped | User presses Tab and focus enters Grafana iframe, cannot tab out | Add `<iframe sandbox="allow-scripts allow-same-origin">` and a "Return to Admin Panel" skip-link rendered outside the iframe |
| Config hot-reload changes embedding model without warning | Active queries fail with dimension mismatch errors | Show "Restart Required" badge next to config keys that need restart; block writes to embedding-related config if collection has data |
| Admin key shown only once, no way to regenerate | User loses key, locked out of admin; cannot create new key until another admin helps | Add "Regenerate" button that creates new key and revokes old one; show the new key once (standard pattern) |
| Erasure request status "completed" but login still works | User thinks data is erased but tombstone not fully processed | Erasure should immediately invalidate all sessions/tokens for that user; return "completed" only after all session tokens are revoked |
| HTMX 401 on tab content load shows bare error | Tab contents replaced with "401 Unauthorized" JSON text | HTMX global `htmx:responseError` handler should show login modal on 401, not render the error response body |
| Config table shows all keys in one flat list | Admin overwhelmed by 50+ config keys with no grouping | The spec's "group" column is correct; implement a group-filter dropdown and collapsible sections by default |
| "Select All" checkbox for document cleanup selects across pages | Admin accidentally deletes 10k documents instead of the 50 visible on page 1 | "Select All" should be page-scoped by default with a "Select All X,XXX documents across all pages" link for batch operations |

---

## "Looks Done But Isn't" Checklist

- [ ] **Streamable HTTP:** Session idle timeout is implemented and tested. `DELETE /mcp` works. `Mcp-Session-Id` header is validated on every request. Origin validation is in place. Tested with missing/expired/invalid session IDs returning appropriate errors (not 500).
- [ ] **Auth middleware:** Applied to all HTTP methods (GET, POST, DELETE, OPTIONS) on both `/mcp` and legacy SSE endpoint. Tested unauthenticated GET returns 401. Tested with malformed/missing/expired tokens.
- [ ] **CSP:** Policy includes `frame-src` matching `GRAFANA_URL`. Alpine.js CSP build is used (not default CDN). No `'unsafe-eval'` in `script-src`. Jinja2 nonce passed to every `<script>` tag. Tested by loading admin SPA and asserting no CSP violations in console. Grafana iframe loads without error.
- [ ] **WAL mode:** ALL SQLite connections use WAL mode. `PRAGMA journal_size_limit` set. `PRAGMA wal_autocheckpoint` lowered from default. Verified via integration test that concurrent writes do not produce `SQLITE_BUSY`.
- [ ] **Config hot-reload:** Version counter implemented. `reload_if_changed()` is synchronous (no intermediary state). Changing embedding model config key warns "requires restart." Tested with concurrent writes and reads.
- [ ] **Percentile metrics:** Bounded-memory implementation (ring buffer or HDR histogram). Self-snapshotting on fixed cadence (not relying on Prometheus scrape). Memory tested with 1M+ data points.
- [ ] **GDPR erasure:** Data inventory complete. Audit log free-text scrubbing implemented. Erasure ledger written before operational deletion. Backup restore + ledger replay tested. Erasure invalidates all active sessions.
- [ ] **Auth session management:** SPA uses HttpOnly cookie (not localStorage). Token refresh with rotation implemented. Server-side session revocation supported. "Logout everywhere" invalidates all sessions.
- [ ] **API key safety:** Keys shown only once. SHA-256 hashed in DB. Prefix stored for identification. Error messages do not reveal key validity. Rate-limited session endpoint.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| WAL file grown to fill disk (2+ GB) | MEDIUM | 1. Stop all write activity. 2. Run `PRAGMA wal_checkpoint(TRUNCATE)` on each DB. 3. Verify WAL files shrink. 4. Add WAL monitoring. 5. Set `journal_size_limit` and lower `wal_autocheckpoint`. |
| CSP misconfigured, admin SPA broken (white screen) | LOW | 1. Remove CSP header temporarily (set `ENABLE_CSP=false` env var). 2. Debug which directive is blocking via browser console. 3. Fix CSP and re-enable. 4. Add test that asserts CSP header and functional UI. |
| Stored XSS via config value | HIGH | 1. Revoke all admin sessions. 2. Delete the offending config row. 3. Rotate all API keys. 4. Audit audit logs for exfiltration. 5. Verify Jinja2 auto-escaping is on for config templates. |
| Memory OOM from percentile histogram | MEDIUM | 1. Restart server process. 2. Implement bounded-memory histogram. 3. Deploy. 4. Add RSS memory alerting to catch recurrence. |
| GDPR erasure not fully completed | HIGH | 1. Review erasure ledger for in-progress items. 2. Manually scrub PII from audit logs, query logs, backups. 3. Update erasure workflow to include free-text scrubbing. 4. Notify data subject of completion within 30-day SLA. |
| Auth bypass on /mcp discovered in production | CRITICAL | 1. Set `AUTH_ENABLED=true` (if it was disabled). 2. Review access logs for unauthorized queries. 3. Rotate all API keys. 4. Deploy middleware-based auth as hotfix. 5. Conduct incident post-mortem. |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Streamable HTTP session orphan | Phase 28 | Test: forced disconnect + timeout → session cleaned. Metric: active_sessions gauge does not leak |
| Auth bypass on MCP stream | Phase 28 | Test: unauthenticated GET/POST/DELETE all return 401. Middleware applied to ALL routes |
| WAL unbounded growth | Phase 28b pre-req (dedicated task) | Test: 20 concurrent writers → no SQLITE_BUSY. Monitor: WAL file size < 128 MB |
| CSP conflict (Grafana + Alpine) | Phase 28c | Test: admin page loads without CSP violations. Test: Grafana iframe renders with correct frame-src |
| Hot-reload race condition | Phase 40 | Test: concurrent config read/write → no stale values. `reload_if_changed()` is synchronous |
| localStorage API key XSS | Phase 28c | Test: admin SPA uses HttpOnly cookie, not localStorage. Test: config XSS payload is escaped |
| Percentile histogram memory leak | Phase 39 | Test: 1M data points → memory < 5 MB. Metric: histogram reset on cadence |
| GDPR erasure audit-log PII | Phase 28b | Test: erased user's PII absent from all tables. Doc: DATA_INVENTORY.md maps all PII locations |
| JWT no-rotation session hijack | Phase 28b | Test: token revocation works. Test: refresh rotation invalidates old tokens. No JWT-only session for browser SPA |
| Non-WAL connections under load | Phase 28b pre-req | Test: all sqlite3.connect() calls route through db_utils.py with WAL. PRAGMA check returns "wal" |
| Origin header validation | Phase 28 | Test: request with spoofed Origin returns 403. MCP_ALLOWED_ORIGINS env var enforced |
| Config XSS via stored value | Phase 40 | Test: `<script>` in config value is HTML-escaped when rendered. `{{ value | safe }}` not used |

---

## Sources

- MCP Streamable HTTP specification 2025-03-26/2025-11-25 — session lifecycle, Origin validation requirements
- HTMX Web Security Basics — CSS/HTML injection prevention, CSP interaction
- Alpine.js CSP build documentation — `@alpinejs/csp` as alternative to default build
- SQLite WAL mode documentation — auto-checkpoint behavior, journal_size_limit
- SQLite Forum: WAL file unbounded growth — auto-checkpoint starvation under continuous writes
- Auth0 Token Storage Best Practices — localStorage vs HttpOnly cookie for SPA auth
- OWASP JWT Cheat Sheet — refresh token rotation, reuse detection
- GDPR Right to Erasure Engineering (Wolf-Tech) — tombstone patterns, audit-log PII scrubbing
- FastAPI + SQLAlchemy async + SQLite WAL — `create_async_engine` connection pragma setup
- Prometheus Histogram best practices — bounded-memory percentile computation
- Starlette Middleware CSP implementation — nonce-based script-src
- Grafana embedding documentation — `allow_embedding`, `frame-ancestors` configuration

---

*Pitfalls research for: Admin Platform Features for kb-rag-mcp v0.1.5*
*Researched: 2026-06-15*
