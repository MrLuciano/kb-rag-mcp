---
phase: 15-powershell-ports-script
plan: 01
subsystem: infra
tags: [powershell, windows, firewall, wsl2, deployment]

# Dependency graph
requires:
  - phase: 14-health-dashboard
    provides: Health/metrics endpoint on port 8080
provides:
  - Opt-in Windows Firewall configuration via -ConfigureFirewall switch
  - Elevation detection with auto-elevation prompt
  - Idempotent firewall rules for 6 subsystem ports
  - English-only PowerShell script comments
affects: [deployment, windows-setup, operations]

# Tech tracking
tech-stack:
  added: []
  patterns: [PowerShell elevation detection, idempotent firewall rules, hybrid opt-in/default behavior]

key-files:
  created: []
  modified: [scripts/start-kb-rag.ps1]

key-decisions:
  - "Hybrid approach: -ConfigureFirewall switch is opt-in, default behavior unchanged (backward compatible)"
  - "Auto-elevation with user prompt: non-admin users are prompted to re-launch as Administrator"
  - "Idempotent rule creation: checks for existing rules before creating, safe to run multiple times"
  - "Non-fatal failures: script continues with service startup even if firewall config fails"
  - "Domain/Private profiles only: safer default; users can manually enable Public if needed"

patterns-established:
  - "Test-IsAdministrator: reusable function for checking Administrator privileges"
  - "Set-KbRagFirewallRules: idempotent firewall rule creation with per-rule error handling"
  - "Auto-elevation protocol: prompt → Start-Process -Verb RunAs → exit"

requirements-completed: []

# Metrics
duration: ~15min
completed: 2026-05-26
---

# Phase 15 Plan 01: Enhance start-kb-rag.ps1 with Firewall Configuration Summary

**PowerShell automation script enhanced with opt-in Windows Firewall configuration for 6 subsystem ports, elevation detection, and full English translation**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-26T22:35:00Z
- **Completed:** 2026-05-26T22:41:48Z
- **Tasks:** 10 (5 implementation, 5 manual verification deferred to user)
- **Files modified:** 1

## Accomplishments

- Added `-ConfigureFirewall` opt-in switch with elevation detection
- Implemented idempotent firewall rules for 6 ports: Qdrant (6333, 6334), MCP SSE (8765), Health (8080), Prometheus (9090), Grafana (3000)
- Auto-elevation prompt for non-admin users with graceful fallback
- Translated all Portuguese comments to English (17 comments)
- Maintained backward compatibility with existing `-Stop` and `-Status` switches

## Task Commits

1. **Tasks 1-5: Core implementation** - `9b3058e` (feat)
   - Added `Test-IsAdministrator` and `Set-KbRagFirewallRules` functions
   - Added `-ConfigureFirewall` parameter
   - Implemented elevation detection with auto-elevation prompt
   - Integrated firewall configuration into `Start-KbRag` function
   - Translated all comments from Portuguese to English

**Plan metadata:** (included in same commit)

## Files Created/Modified

- `scripts/start-kb-rag.ps1` - Enhanced from 71 to 156 lines (+119 lines, +85 net)
  - Added 2 new functions: `Test-IsAdministrator`, `Set-KbRagFirewallRules`
  - Added elevation detection logic block (19 lines)
  - Integrated firewall configuration into startup flow
  - Translated 17 comments to English

## Decisions Made

**Hybrid opt-in approach:** Default behavior unchanged (local-only access, no elevation required). Users who need LAN access run with `-ConfigureFirewall` once.

**Auto-elevation with user confirmation:** Non-admin users are prompted to re-launch as Administrator, not silently elevated. Preserves user control.

**Idempotent rule management:** `Get-NetFirewallRule` check before `New-NetFirewallRule` prevents duplicates. Safe to run script multiple times.

**Non-fatal firewall failures:** Try/catch per rule with error messages. Script continues with Docker/MCP startup even if firewall config fails. Enables local-only fallback.

**Domain/Private profiles only:** Safer default for home/office networks. Users can manually enable Public profile if needed.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - PowerShell script implementation was straightforward.

## User Setup Required

**Manual verification required** (Tasks 6-9 deferred to user):

1. **Task 6: Idempotency test** - Run script with `-ConfigureFirewall` twice, verify no duplicate rules
2. **Task 7: Elevation prompt test** - Test as non-admin and admin user
3. **Task 8: LAN access test** - Verify services accessible from remote machine (requires second machine on LAN)
4. **Task 9: Backward compatibility test** - Verify default mode, `-Stop`, and `-Status` still work

**Testing commands:**
```powershell
# Idempotency test
Get-NetFirewallRule -Group "KB-RAG-MCP" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
.\scripts\start-kb-rag.ps1 -ConfigureFirewall
.\scripts\start-kb-rag.ps1 -ConfigureFirewall  # Should show "already exists" for all rules

# Elevation test (run as non-admin)
.\scripts\start-kb-rag.ps1 -ConfigureFirewall  # Should prompt for elevation

# LAN access test (from remote machine)
curl http://<WINDOWS_IP>:8080/health
curl http://<WINDOWS_IP>:3000  # Grafana
curl http://<WINDOWS_IP>:6333/collections  # Qdrant

# Backward compatibility test
.\scripts\start-kb-rag.ps1          # Should start without firewall changes
.\scripts\start-kb-rag.ps1 -Stop    # Should stop services
.\scripts\start-kb-rag.ps1 -Status  # Should show status
```

## Next Phase Readiness

Ready for Plan 15-02 (remaining Phase 15 plan, if any) or phase completion.

**Firewall rules are persistent** - no need to run `-ConfigureFirewall` on every startup. Once created, rules remain active across reboots.

**To remove rules:**
```powershell
Get-NetFirewallRule -Group "KB-RAG-MCP" | Remove-NetFirewallRule
```

---
*Phase: 15-powershell-ports-script*
*Completed: 2026-05-26*
