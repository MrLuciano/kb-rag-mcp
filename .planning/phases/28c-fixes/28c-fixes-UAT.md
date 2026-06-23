---
status: testing
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
result: pending

### 2. API key login
expected: Switch to API Key tab → paste the last known key → submit → overlay closes → admin panels load
result: pending

### 3. Generate new API key if current one is lost/revoked
expected: Credentials tab → Generate New Key → new key appears → copy → logout → re-login with new key
result: pending

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps

[none yet]
