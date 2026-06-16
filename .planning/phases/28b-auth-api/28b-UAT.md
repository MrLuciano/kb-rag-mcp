---
status: partial
phase: 28b-auth-api
source: 28b-01-SUMMARY.md
started: 2026-06-16T17:00:00Z
updated: 2026-06-16T17:05:00Z
---

## Current Test

number: 1
name: Admin creates a user
expected: |
  POST /api/v1/users with admin auth creates a new user. Response includes user id, username, role, created_at.
result: issue
reported: "docker endpoint is not even loading"
severity: blocker

## Tests

### 1. Admin creates a user
expected: |
  POST /api/v1/users with admin auth creates a new user. Response includes user id, username, role, created_at.
result: blocked
blocked_by: server
reason: "docker endpoint is not even loading"

### 2. Admin lists all users
expected: |
  GET /api/v1/users returns a list of all users with id, username, role, status.
result: blocked
blocked_by: server
reason: "Server not running — blocked by Test 1"

### 3. User gets own profile
expected: |
  GET /api/v1/users/me returns the authenticated user's own profile (id, username, role, created_at).
result: blocked
blocked_by: server
reason: "Server not running — blocked by Test 1"

### 4. Admin creates an API key for a user
expected: |
  POST /api/v1/api-keys creates a new API key. Response includes the raw key value (shown only once), prefix, status, created_at.
result: blocked
blocked_by: server
reason: "Server not running — blocked by Test 1"

### 5. User lists own API keys
expected: |
  GET /api/v1/api-keys returns the authenticated user's API keys with prefix, status, created_at. Raw key value is NOT exposed.
result: blocked
blocked_by: server
reason: "Server not running — blocked by Test 1"

### 6. User revokes an API key
expected: |
  DELETE /api/v1/api-keys/{id} marks the key as revoked. Subsequent requests with that key return 401.
result: blocked
blocked_by: server
reason: "Server not running — blocked by Test 1"

### 7. Role-based access control (admin vs user)
expected: |
  Non-admin user calling POST /api/v1/users receives 403 Forbidden. Admin calling it succeeds.
result: blocked
blocked_by: server
reason: "Server not running — blocked by Test 1"

### 8. GDPR data export
expected: |
  POST /api/v1/users/me/export returns a JSON blob with all personal data (profile, API keys, audit logs). Download triggers as file attachment.
result: blocked
blocked_by: server
reason: "Server not running — blocked by Test 1"

### 9. GDPR erasure workflow
expected: |
  User requests erasure → status becomes "requested". Admin approves → status becomes "approved". Admin executes → user is erased (blocked from auth, data removed).
result: blocked
blocked_by: server
reason: "Server not running — blocked by Test 1"

### 10. Authentication with API key
expected: |
  Requests to protected endpoints without a valid API key return 401. With a valid key, they succeed.
result: blocked
blocked_by: server
reason: "Server not running — blocked by Test 1"

## Summary

total: 10
passed: 0
issues: 0
pending: 0
skipped: 0
blocked: 10

## Gaps

[none yet]
