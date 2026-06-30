---
phase: 28c-fixes
plan: 04
type: execute
wave: 4
depends_on:
  - 28c-fixes-03
files_modified:
  - kb_server/auth/router.py
  - kb_server/auth/deps.py
  - kb_server/auth/service.py
  - kb_server/auth/models.py
  - kb_server/ui/routes_admin.py
  - kb_server/ui/templates/admin/tab_admin.html
  - kb_server/ui/templates/admin/_sessions_table.html
  - kb_server/ui/templates/admin/_credentials_section.html
  - kb_server/ui/static/styles.css
  - tests/test_admin_ui.py
autonomous: true
gap_closure: true
requirements:
  - SPA-01
  - SPA-05
must_haves:
  truths:
    - Session timeout is configurable via env var (default 30 min)
    - JWT session cookie uses the configured timeout as max_age
    - Admin can view a list of active sessions in the Admin tab
    - Admin can revoke specific sessions from the UI
    - Admin can view and manage their API keys from the Admin tab
    - Profile/credentials section shows API key prefix, created date, last used date
    - Admin can generate new API key and revoke existing ones from the UI
  artifacts:
    - path: kb_server/auth/router.py
      provides: Configurable session timeout + session tracking
      contains: "SESSION_TIMEOUT"
    - path: kb_server/auth/models.py
      provides: UserSession table for active session tracking
      contains: "class UserSession"
    - path: kb_server/auth/service.py
      provides: Session CRUD methods
      contains: "create_session_record"
    - path: kb_server/auth/router.py
      provides: Session list + revoke API endpoints
      contains: "auth/sessions"
    - path: kb_server/ui/templates/admin/_sessions_table.html
      provides: Session management UI table
      contains: "Revoke"
    - path: kb_server/ui/templates/admin/_credentials_section.html
      provides: API key management UI section
      contains: "Generate New Key"
  key_links:
    - from: auth/router.py create_session
      to: auth/service.py create_session_record
      via: create_session_record()
      pattern: "create_session_record"
    - from: auth/router.py GET /auth/sessions
      to: auth/service.py list_user_sessions
      via: list_user_sessions()
      pattern: "list_user_sessions"
    - from: tab_admin.html
      to: /admin/tabs/sessions-content
      via: hx-get
      pattern: "sessions-content"
---

<objective>
Add configurable session timeout, session tracking/management, and credential settings page to complete the auth feature set required by UAT.

Purpose: The admin SPA's JWT session cookie has a hardcoded 8-hour timeout with no configurability. There is no way to view active sessions or revoke them. The admin cannot manage credentials (API keys) from within the admin panel. These features are essential for operational security.
Output: Working session management with configurable timeout, active session list with revoke capability, and credential management UI.
</objective>

<execution_context>
@/home/admin/.config/opencode/gsd-core/workflows/execute-plan.md
@/home/admin/.config/opencode/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/phases/28c-fixes/28c-fixes-CONTEXT.md
@.planning/phases/28c-admin-spa-panel/28c-UAT.md

# Current state after Plans 01-03 (auth flow, router mount, auth gating)
@kb_server/auth/router.py
@kb_server/auth/deps.py
@kb_server/auth/service.py
@kb_server/auth/models.py
@kb_server/ui/routes_admin.py
@kb_server/ui/templates/admin/tab_admin.html
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Configurable session timeout with session tracking (D-11)</name>
  <files>
    kb_server/auth/router.py
    kb_server/auth/deps.py
    kb_server/auth/service.py
    kb_server/auth/models.py
  </files>
  <behavior>
    - Test: SESSION_TIMEOUT env var (default "1800") is read at module level in router.py
    - Test: create_session uses max_age=int(SESSION_TIMEOUT) and expires_at = time.time() + int(SESSION_TIMEOUT)
    - Test: create_session calls service.create_session_record() after setting cookie
    - Test: service.create_session_record() creates a UserSession record in DB
    - Test: UserSession stores user_id, session_token fingerprint (first 16 chars of HMAC), ip_address, user_agent
    - Test: get_current_user checks if session cookie's UserSession is_revoked (returns 401 if revoked)
    - Test: get_current_user updates last_used_at on the UserSession for valid sessions
    - Test: UserSession model exists with all required columns (id, user_id, session_token, ip_address, user_agent, created_at, last_used_at, is_revoked)
  </behavior>
  <action>
     1. In kb_server/auth/models.py: Add `UserSession` table with columns (plan 03 intentionally defers this to Plan 04 per D-11 session management scope):
       - `id` (String 36, PK, UUID default)
       - `user_id` (String 36, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index)
       - `session_token` (String 64, unique, nullable=False) — HMAC fingerprint of session for lookup
       - `ip_address` (String 45, nullable)
       - `user_agent` (String 255, nullable)
       - `created_at` (DateTime, default=datetime.now(timezone.utc).replace(tzinfo=None))
       - `last_used_at` (DateTime, default same as created_at)
       - `is_revoked` (Boolean, default=False)

    2. In kb_server/auth/router.py:
       - Add SESSION_TIMEOUT env var: `_SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "1800"))` (30 min default)
       - Import `hashlib` if not already present (it is, from the hmac block)
       - In `create_session()`:
         - Change `expires_at = int(time.time()) + 28800` to `expires_at = int(time.time()) + _SESSION_TIMEOUT`
         - Change `max_age=28800` to `max_age=_SESSION_TIMEOUT`
         - After setting the cookie, import `Request` from starlette and get client details:
           ```python
           ip = request.client.host if request.client else "unknown"
           ua = request.headers.get("User-Agent", "unknown")
           ```
         - Call service method to create session record:
           ```python
           service.create_session_record(
               user_id=str(current_user.id),
               session_token=signature,  # Store the HMAC signature as fingerprint
               ip_address=ip,
               user_agent=ua,
           )
           ```
         - NOTE: The `signature` variable is computed earlier. Store it (or its full HMAC value) for session lookup. The `session_token` stored should be the full `<user_id>:<expires_at>:<signature>` token minus the expires_at and user_id parts. Just store the signature (last segment) as the session fingerprint. Actually, store the full raw token that was set as the cookie value — this way session lookup can verify by checking the signature portion.
         - Simplify: store `raw = f"{current_user.id}:{expires_at}"` and `signature = hmac.new(...)` — store the ENTIRE `session_token` string `f"{raw}:{signature}"` in the UserSession. But hashed! Store `hashlib.sha256(session_token.encode()).hexdigest()` — this way the stored token is not the raw token but a hash for security.
         - Actually, simplest approach: store the raw `signature` string (16 hex chars) as the session_token. This is enough to look up the session by the last segment of the cookie. The cookie value is `user_id:expires_at:signature` — extracting the signature part gives us the lookup key.

       - Response model: add `expires_in=_SESSION_TIMEOUT` to SessionResponse (was 28800)

    3. In kb_server/auth/service.py: Add session CRUD methods:
       - `create_session_record(self, user_id: str, session_token: str, ip_address: str = "unknown", user_agent: str = "unknown") -> None`:
         - Creates a new UserSession record
         - `self._session.add(session)`
         - `self._session.commit()`
       - `get_user_session(self, user_id: str, session_token: str) -> Optional[UserSession]`:
         - Queries UserSession by user_id + session_token + not is_revoked
       - `list_user_sessions(self, user_id: str) -> list[UserSession]`:
         - Returns all non-revoked sessions for a user, ordered by last_used_at DESC
       - `revoke_session(self, session_id: str, user_id: str) -> bool`:
         - Sets is_revoked = True on matching session (also verify user_id for ownership)
         - Commits and returns True, or False if not found

    4. In kb_server/auth/deps.py: Update `get_current_user()` session cookie path:
       - After looking up user from session cookie, also check session validity:
       - Extract `signature` from the parsed cookie (last segment)
       - Call `service.get_user_session(user.id, signature)` to check if session exists and is not revoked
       - If session is revoked: raise HTTPException(401, detail="Session has been revoked")
       - If session is valid: update `last_used_at`:
         ```python
         session.last_used_at = datetime.now(timezone.utc).replace(tzinfo=None)
         service.session.commit()
         ```
       - Import datetime: `from datetime import datetime, timezone`
  </action>
  <verify>
    <automated>pytest tests/test_admin_ui.py -v -k "session or timeout"</automated>
  </verify>
  <done>
    - SESSION_TIMEOUT env var controls JWT max_age (default 1800 = 30 min)
    - Active sessions tracked in UserSession table
    - get_current_user checks session validity and updates last_used_at
    - Revoked sessions are rejected with 401
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Session management and credential settings page (D-12, D-13)</name>
  <files>
    kb_server/auth/router.py
    kb_server/ui/routes_admin.py
    kb_server/ui/templates/admin/tab_admin.html
    kb_server/ui/templates/admin/_sessions_table.html
    kb_server/ui/templates/admin/_credentials_section.html
    tests/test_admin_ui.py
  </files>
  <behavior>
    - Test: GET /api/v1/auth/sessions returns list of active sessions for current user
    - Test: POST /api/v1/auth/sessions/{id}/revoke revokes the session (returns 200 with {"revoked": true})
    - Test: Revoking a session of another user returns 403 (ownership check)
    - Test: tab_admin.html loads _sessions_table.html and _credentials_section.html via hx-get
    - Test: _sessions_table.html shows session rows with ip_address, user_agent, created_at, last_used_at, Revoke button
    - Test: Revoke button has hx-confirm and hx-post to revoke endpoint
    - Test: _credentials_section.html shows API keys table with prefix, created_at, last_used_at, Revoke button
    - Test: _credentials_section.html has "Generate New Key" button
    - Test: Generating new key returns the raw key in a flash message
    - Test: Empty session state reads "No active sessions"
    - Test: Empty API key state reads "No API keys configured"
  </behavior>
  <action>
    1. In kb_server/auth/router.py: Add session management endpoints (admin-only):
       - `GET /auth/sessions` — returns list of active sessions for the current user (or all sessions if admin)
         - `current_user: User = Depends(get_current_user)`
         - Call `service.list_user_sessions(current_user.id)`
         - Return JSON list with id, ip_address, user_agent, created_at, is_revoked, last_used_at
       - `POST /auth/sessions/{session_id}/revoke` — revoke a session
         - `current_user: User = Depends(require_admin)` (only admin can revoke sessions)
         - Call `service.revoke_session(session_id, current_user.id)`
         - Return {"revoked": true, "session_id": session_id} or 404

    2. In kb_server/ui/routes_admin.py: Add admin tab content endpoints for sessions and credentials:
       - `GET /tabs/sessions-content` — renders `admin/_sessions_table.html` partial
         - Requires `Depends(get_current_user)`
         - Get sessions from auth service: `request.app.state.auth_service.list_user_sessions(current_user.id)`
         - Pass sessions list to template
       - `GET /tabs/credentials-content` — renders `admin/_credentials_section.html` partial
         - Requires `Depends(get_current_user)`
         - Get API keys from auth service: `request.app.state.auth_service.list_api_keys(current_user.id)`
         - Pass keys list to template
       - Import `from kb_server.auth.deps import get_current_user` if not already (should be from Plan 03)
       - Import your own module's `router` for the new routes, OR use the existing `router` that already has auth gating on tab content endpoints

    3. Create `kb_server/ui/templates/admin/_sessions_table.html`:
       ```html
       <div x-data="sessionManager()">
         <h3 class="h5 mb-3">Active Sessions</h3>
         <p class="text-muted small">Sessions where your account is currently logged in.</p>
         <div x-show="sessions.length === 0" class="text-muted py-3">
           <p>No active sessions.</p>
         </div>
         <table x-show="sessions.length > 0" class="table table-sm">
           <thead>
             <tr>
               <th>IP Address</th>
               <th>User Agent</th>
               <th>Created</th>
               <th>Last Used</th>
               <th>Actions</th>
             </tr>
           </thead>
           <tbody>
             <template x-for="session in sessions" :key="session.id">
               <tr>
                 <td x-text="session.ip_address"></td>
                 <td x-text="session.user_agent" class="text-truncate" style="max-width: 200px"></td>
                 <td x-text="session.created_at"></td>
                 <td x-text="session.last_used_at"></td>
                 <td>
                   <button class="btn btn-sm btn-outline-danger"
                           hx-post="/api/v1/auth/sessions/${session.id}/revoke"
                           hx-confirm="Revoke session: Are you sure you want to revoke this session? The user will be logged out immediately."
                           hx-target="closest tr"
                           hx-swap="delete">Revoke</button>
                 </td>
               </tr>
             </template>
           </tbody>
         </table>
       </div>
       <script nonce="{{ get_nonce(request) }}">
         function sessionManager() {
           return {
             sessions: [],
             init() {
               fetch('/api/v1/auth/sessions')
                 .then(r => r.json())
                 .then(data => { this.sessions = data; })
                 .catch(() => {});
             }
           };
         }
       </script>
       ```

    4. Create `kb_server/ui/templates/admin/_credentials_section.html`:
       ```html
       <div x-data="credentialManager()">
         <h3 class="h5 mb-3">API Keys</h3>
         <p class="text-muted small">Manage your API keys. Keys are used to authenticate with the KB-RAG API and admin panel.</p>
         <button class="btn btn-primary btn-sm mb-3" @click="generateKey()">Generate New Key</button>
         <div x-show="newKey" class="alert alert-success mt-2" x-text="'New API Key: ' + newKey" role="alert"></div>
         <div x-show="sessions.length === 0 && keys.length === 0" class="text-muted py-3">
           <p>No API keys configured.</p>
         </div>
         <table x-show="keys.length > 0" class="table table-sm">
           <thead>
             <tr>
               <th>Prefix</th>
               <th>Description</th>
               <th>Created</th>
               <th>Last Used</th>
               <th>Status</th>
               <th>Actions</th>
             </tr>
           </thead>
           <tbody>
             <template x-for="key in keys" :key="key.id">
               <tr>
                 <td><code x-text="key.prefix + '...'"></code></td>
                 <td x-text="key.description"></td>
                 <td x-text="key.created_at"></td>
                 <td x-text="key.last_used_at || 'Never'"></td>
                 <td>
                   <span x-show="!key.is_revoked" class="badge bg-success">Active</span>
                   <span x-show="key.is_revoked" class="badge bg-danger">Revoked</span>
                 </td>
                 <td>
                   <button x-show="!key.is_revoked" class="btn btn-sm btn-outline-danger"
                           hx-delete="/api/v1/api-keys/${key.id}"
                           hx-confirm="Revoke API key: Are you sure you want to revoke this key? Applications using this key will lose access immediately."
                           hx-target="closest tr"
                           hx-swap="delete">Revoke</button>
                 </td>
               </tr>
             </template>
           </tbody>
         </table>
       </div>
       <script nonce="{{ get_nonce(request) }}">
         function credentialManager() {
           return {
             keys: [],
             newKey: '',
             init() {
               fetch('/api/v1/api-keys')
                 .then(r => r.json())
                 .then(data => { this.keys = data; })
                 .catch(() => {});
             },
             generateKey() {
               fetch('/api/v1/api-keys', {
                 method: 'POST',
                 headers: {'Content-Type': 'application/json'},
                 body: JSON.stringify({description: 'Admin panel key'})
               })
               .then(r => r.json())
               .then(data => {
                 this.newKey = data.raw_key;
                 this.keys.unshift({id: data.id, prefix: data.prefix, description: data.description, created_at: data.created_at, last_used_at: null, is_revoked: false});
                 setTimeout(() => { this.newKey = ''; }, 15000);
               })
               .catch(() => {});
             }
           };
         }
       </script>
       ```

    5. In `kb_server/ui/templates/admin/tab_admin.html`: Update to load sessions and credentials partials:
       - Add sub-sections after the existing config table content:
         ```html
         <hr class="my-4">
         <div id="sessions-content"
              hx-get="/admin/tabs/sessions-content"
              hx-trigger="load"
              hx-swap="innerHTML">
           <p class="text-muted">Loading sessions...</p>
         </div>
         <hr class="my-4">
         <div id="credentials-content"
              hx-get="/admin/tabs/credentials-content"
              hx-trigger="load"
              hx-swap="innerHTML">
           <p class="text-muted">Loading credentials...</p>
         </div>
         ```

    6. In `tests/test_admin_ui.py`: Add test cases:
       - `test_session_timeout_configurable` — verify SESSION_TIMEOUT env var is read by router.py
       - `test_session_list_endpoint` — verify GET /api/v1/auth/sessions returns list
       - `test_session_revoke_endpoint` — verify POST /api/v1/auth/sessions/{id}/revoke works
       - `test_session_revoke_ownership` — verify non-admin cannot revoke others' sessions
       - `test_credentials_section_loads` — verify /admin/tabs/credentials-content returns 200
  </action>
  <verify>
    <automated>pytest tests/test_admin_ui.py -v -k "session or credential or timeout or settings"</automated>
  </verify>
  <done>
    - Session list API works: GET /api/v1/auth/sessions returns active sessions
    - Session revoke API works: POST /api/v1/auth/sessions/{id}/revoke — ownership verified
    - Admin tab shows active sessions with IP, user agent, timestamps, and Revoke button
    - Admin tab shows API keys with prefix, status badge, and Revoke button
    - "Generate New Key" button creates new key and displays it once
    - Empty states: "No active sessions", "No API keys configured"
    - All new tests pass
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| admin→API | Session management endpoints allow admins to list/revoke sessions |
| cookie→auth DB | Session cookies map to UserSession records in auth.db |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-28c-13 | Spoofing | Session timeout bypass | mitigate | SESSION_TIMEOUT enforced server-side (cookie expiry check in get_current_user) |
| T-28c-14 | Repudiation | Session revocation without ownership check | mitigate | Per D-12: revoke_session verifies user_id ownership; only admin can revoke others |
| T-28c-15 | Information Disclosure | Session list exposes user_agent/IP | accept | Shows only the current user's sessions; user_agent and IP are non-sensitive for own sessions |
| T-28c-16 | Elevation of Privilege | API key generation without auth | mitigate | POST /api/v1/api-keys requires Depends(get_current_user) (already gated in router.py) |
</threat_model>

<verification>
- Run admin UI session tests: `pytest tests/test_admin_ui.py -v -k "session or credential or timeout or settings"`
- Run full admin UI test suite: `pytest tests/test_admin_ui.py -v`
- Run UI regression tests: `pytest tests/test_ui_routes.py -v`
- Run linting: `flake8 kb_server/auth/router.py kb_server/auth/deps.py kb_server/auth/service.py kb_server/ui/routes_admin.py`
</verification>

<success_criteria>
- [ ] SESSION_TIMEOUT env var (default 1800) controls JWT cookie max_age
- [ ] Active sessions tracked in UserSession table with IP, user_agent, fingerprint
- [ ] get_current_user validates session validity (not expired, not revoked) and updates last_used_at
- [ ] Session list API returns active sessions for the current user
- [ ] Session revoke API invalidates a session (ownership enforced)
- [ ] Admin tab has "Active Sessions" section with table and Revoke buttons
- [ ] Admin tab has "API Keys" section with key list and Generate New Key button
- [ ] All new tests pass; no regressions in existing 666+ tests
- [ ] Flake8 clean on all modified files
</success_criteria>

<output>
Create `.planning/phases/28c-fixes/28c-fixes-04-SUMMARY.md` when done
</output>
