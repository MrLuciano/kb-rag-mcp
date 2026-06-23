---
status: partial
phase: 28c-fixes
source: 28c-fixes-01-SUMMARY.md, 28c-fixes-02-SUMMARY.md, 28c-fixes-03-SUMMARY.md, 28c-fixes-04-SUMMARY.md, 28c-fixes-05-SUMMARY.md
started: 2026-06-23T16:00:00Z
updated: 2026-06-23T16:00:00Z
---

## Current Test

number: 1
name: Password login with admin/admin
expected: |
  Open browser to http://host/admin
  Login overlay appears with Password tab selected.
  Enter username: admin, password: admin
  Click "Log in" → POST /api/v1/auth/login succeeds → overlay closes → admin panels load
awaiting: user response

## Tests

### 1. Password login with admin/admin
expected: Login overlay → enter admin/admin → submit → overlay closes → admin panels load
result: issue
reported: "No"
severity: major

### 2. API key login
expected: Switch to API Key tab → paste the last known key → submit → overlay closes → admin panels load
result: issue
reported: "No"
severity: major

### 3. Generate new API key if current one is lost/revoked
expected: Credentials tab → Generate New Key → new key appears → copy → logout → re-login with new key
result: blocked
blocked_by: prior-phase
reason: "Cannot log in (tests 1 and 2 both fail) — prerequisite for generating new key"

## Summary

total: 3
passed: 0
issues: 2
pending: 0
skipped: 0
blocked: 1

## Gaps

- truth: "Login overlay → enter admin/admin → submit → overlay closes → admin panels load"
  status: failed
  reason: "User reported: No"
  severity: major
  test: 1
  artifacts: []
  missing: []
  debug_session: ""
- truth: "API Key tab → paste key → submit → overlay closes → admin panels load"
  status: failed
  reason: "User reported: No"
  severity: major
  test: 2
  artifacts: []
  missing: []
  debug_session: ""
