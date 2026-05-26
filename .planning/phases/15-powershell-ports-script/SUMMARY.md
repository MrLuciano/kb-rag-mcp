# Phase 15 Summary: PowerShell Ports Script

## Overview

**Goal:** Ensure `scripts/start-kb-rag.ps1` opens the required Windows Firewall ports for all subsystems (Qdrant, MCP server, health server, Prometheus, Grafana) automatically during local/dev setup.

**Status:** ✅ **Planning Complete** (2/2 plans ready for execution)

**Milestone:** v1.3 Post-Ship Polish & Infrastructure

**Completion:** Pending execution

---

## Problem Statement

The existing `scripts/start-kb-rag.ps1` PowerShell script successfully starts the kb-rag-mcp stack on Windows (WSL2 + Docker), but **does not configure Windows Firewall** to enable LAN access. Users wanting to:

- Access Grafana dashboard from other machines
- Connect MCP clients remotely
- Query Qdrant from LAN tools
- Scrape Prometheus metrics from monitoring systems

...must manually create 6 firewall rules via Windows Defender UI or PowerShell commands.

---

## Solution Design

### Hybrid Opt-In Approach

- **`-ConfigureFirewall` switch** (opt-in) — Users explicitly request firewall configuration
- **Elevation detection** — Auto-prompts for Administrator privileges if needed
- **Idempotent rule management** — Safe to run multiple times, no duplicates
- **Non-breaking** — Default behavior unchanged (local-only access)

### Affected Ports

| Port | Service | Purpose |
|------|---------|---------|
| 6333 | Qdrant REST API | Vector database queries |
| 6334 | Qdrant gRPC | Vector database (gRPC protocol) |
| 8765 | MCP SSE | Model Context Protocol endpoint |
| 8080 | Health/Metrics | Health checks + Prometheus metrics |
| 9090 | Prometheus | Metrics scraping + PromQL queries |
| 3000 | Grafana | Monitoring dashboard UI |

**Firewall Profile:** Domain + Private (not Public for security)

---

## Plans

### Plan 15-01: Script Enhancement (Implementation)
**Objective:** Add firewall configuration logic to `start-kb-rag.ps1`

**Key Changes:**
- New `-ConfigureFirewall` parameter
- `Test-IsAdministrator()` function for elevation detection
- `Set-KbRagFirewallRules()` function with idempotent rule creation
- Auto-elevation prompt with `Start-Process -Verb RunAs`
- English translation of all Portuguese comments (Phase 12 consistency)

**Test Coverage:**
- Idempotency test (run twice, verify no duplicates)
- Elevation prompt test (non-admin → admin)
- LAN access test (remote machine → Windows IP)
- Backward compatibility test (existing `-Stop`/`-Status` unchanged)

**Estimated Time:** 2.5 hours

---

### Plan 15-02: Documentation Updates
**Objective:** Document new firewall feature across all user-facing docs

**Files Updated:**
1. **README.md** — "Enabling LAN Access" section with port table
2. **README.pt-BR.md** — Portuguese translation
3. **README.es.md** — Spanish translation
4. **docs/OPERATIONS.md** — Comprehensive "Windows Firewall Management" section:
   - Automatic vs. manual configuration
   - Troubleshooting (5+ scenarios: network profiles, WSL forwarding, Docker binding)
   - Group Policy deployment for enterprise
   - Security best practices

**Estimated Time:** 3.5 hours

---

## Requirements

### Functional Requirements (Proposed)

- **WIN-01:** PowerShell startup script automatically configures Windows Firewall rules via opt-in `-ConfigureFirewall` switch
- **WIN-02:** Firewall configuration is idempotent — safe to run multiple times without duplicating rules
- **WIN-03:** Elevation detection prompts non-admin users to re-launch with Administrator privileges when `-ConfigureFirewall` is used

### Documentation Requirements

- **DOCS-04:** Windows firewall configuration documented in README.md (all three languages) and OPERATIONS.md
- **DOCS-05:** Troubleshooting guidance covers LAN access issues, network profiles, and WSL port forwarding

---

## Dependencies

- **Phase 14 (Health Dashboard):** Defines port 8080 for health/metrics endpoint
- **Phase 13 (Docs Sync):** Establishes three-language documentation pattern (EN, PT, ES)
- **Phase 12 (English Sweep):** Sets precedent for English-only inline comments
- **docker-compose.yml:** Source of truth for all port mappings (6 ports)

---

## Testing Strategy

### Manual Testing

1. **Idempotency Test**
   - Run script with `-ConfigureFirewall` twice
   - Verify: 1st run creates 6 rules, 2nd run skips all (no duplicates)

2. **Elevation Test**
   - Run as non-admin → expect elevation prompt
   - Run as admin → expect no prompt, direct execution

3. **LAN Access Test** (requires 2 machines)
   - Windows host: `.\scripts\start-kb-rag.ps1 -ConfigureFirewall`
   - Remote machine: `curl http://<WINDOWS_IP>:8080/health`
   - Verify: All 6 ports accessible from LAN

4. **Backward Compatibility Test**
   - Run without `-ConfigureFirewall` → expect local-only access
   - Run with `-Stop` → expect clean shutdown
   - Run with `-Status` → expect status output

### Validation Criteria

- [ ] 6 firewall rules created with correct ports, profiles, descriptions
- [ ] Rules grouped under "KB-RAG-MCP" in Windows Firewall UI
- [ ] No duplicate rules after multiple runs
- [ ] Services accessible from LAN after configuration
- [ ] Script works without elevation for default (local-only) mode
- [ ] Error messages are clear if firewall operations fail
- [ ] Existing `-Stop`/`-Status` unchanged

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| User declines elevation, expects LAN access | Medium | Clear message: "Skipping firewall configuration (local-only access)" |
| Corporate firewall/VPN blocks ports | Medium | Document in OPERATIONS.md troubleshooting, suggest SSH tunneling |
| WSL2 networking changes in future Windows versions | Low | Script uses PowerShell APIs (version-independent) |
| Users forget rules exist, causing confusion later | Low | Add `-ListFirewallRules` switch in future (out of scope) |

---

## Success Criteria

### Functional
- [ ] `-ConfigureFirewall` creates 6 Windows Firewall rules
- [ ] Rules are idempotent (safe to run multiple times)
- [ ] Elevation prompt works for non-admin users
- [ ] Services accessible from LAN after configuration

### Non-Functional
- [ ] Backward compatible (default behavior unchanged)
- [ ] Clear user feedback (✓/⊙/✗ symbols for each rule)
- [ ] Non-fatal failures (script continues if firewall config errors)
- [ ] English-only comments throughout script

### Documentation
- [ ] All three READMEs document firewall feature (EN, PT, ES)
- [ ] OPERATIONS.md has comprehensive troubleshooting section
- [ ] Examples are copy-pasteable and correct
- [ ] Security warnings are prominent

---

## Out of Scope (Future Enhancements)

- **`-RemoveFirewall` switch** — Clean up rules during `-Stop` operation
- **`-ListFirewallRules` switch** — Show current KB-RAG firewall state
- **Automatic WSL IP detection** — Adjust rules if WSL IP changes (Windows 11 22H2+ dynamic IPs)
- **GPO template generator** — Export rules for enterprise deployment
- **Profile selection** — `-Profile Public` to enable internet-facing access
- **IPv6 rule support** — Currently TCP/IPv4 only

---

## Execution Strategy

### Sequential Execution (Plans depend on each other)

1. **Plan 15-01** — Script implementation + manual testing
   - Estimated: 2.5 hours
   - Blocker for 15-02 (documentation references actual script behavior)

2. **Plan 15-02** — Documentation updates across 4 files
   - Estimated: 3.5 hours
   - Requires 15-01 complete for accurate examples

**Total Phase Duration:** ~6 hours (1 day)

### Verification Steps

1. **Post-15-01:** Run all 4 manual tests, verify LAN access from remote machine
2. **Post-15-02:** Review documentation for consistency, test all example commands
3. **Phase Complete:** Update ROADMAP.md, mark Phase 15 complete, commit all changes

---

## Deliverables

### Code Changes
- `scripts/start-kb-rag.ps1` — Enhanced with firewall configuration logic (~180 lines, up from 71)

### Documentation Changes
- `README.md` — "Enabling LAN Access" section (~30 lines)
- `README.pt-BR.md` — Portuguese translation (~30 lines)
- `README.es.md` — Spanish translation (~30 lines)
- `docs/OPERATIONS.md` — "Windows Firewall Management" section (~180 lines)

### Planning Artifacts
- `.planning/phases/15-powershell-ports-script/CONTEXT.md` — Design decisions (45 sections)
- `.planning/phases/15-powershell-ports-script/15-01-PLAN.md` — Script implementation plan
- `.planning/phases/15-powershell-ports-script/15-02-PLAN.md` — Documentation update plan
- `.planning/phases/15-powershell-ports-script/SUMMARY.md` — This file

---

## References

- **Phase 14 CONTEXT.md** — Port 8080 health endpoint definition
- **Phase 13 SUMMARY.md** — Three-language documentation pattern
- **Phase 12 SUMMARY.md** — English-only comment enforcement
- **docker-compose.yml** — Port mappings (6333, 6334, 8765, 8080, 9090, 3000)
- **Microsoft Docs:** [New-NetFirewallRule](https://learn.microsoft.com/en-us/powershell/module/netsecurity/new-netfirewallrule)
- **Microsoft Docs:** [WSL Networking](https://learn.microsoft.com/en-us/windows/wsl/networking)

---

## Commit Strategy

### Commit 1: Script Enhancement
```
feat(15-01): add Windows Firewall configuration to start-kb-rag.ps1

- Add -ConfigureFirewall switch (opt-in)
- Implement elevation detection with auto-elevation prompt
- Create idempotent firewall rules for 6 ports
- Translate all Portuguese comments to English
- Non-fatal: script continues if firewall config fails

Phase 15, Plan 01
```

### Commit 2: Documentation Updates
```
docs(15-02): document Windows Firewall configuration feature

- README.md: Add "Enabling LAN Access" section
- README.pt-BR.md: Portuguese translation
- README.es.md: Spanish translation
- OPERATIONS.md: Comprehensive firewall management section
- ROADMAP.md: Mark Phase 15 complete

Phase 15, Plan 02
```

---

## Timeline

| Date | Milestone | Status |
|------|-----------|--------|
| 2026-05-26 | Planning complete | ✅ Done |
| TBD | Plan 15-01 execution | 🔲 Pending |
| TBD | Plan 15-02 execution | 🔲 Pending |
| TBD | Phase 15 complete | 🔲 Pending |

**Estimated Completion:** 1 day after execution starts

---

## Notes

- **PowerShell Version:** Requires 5.1+ (Windows 10/11 built-in)
- **Testing Environment:** Windows 10 and Windows 11 (both WSL2)
- **LAN Testing:** Requires second machine on same network for validation
- **Security Profile:** Domain + Private only (Public requires explicit user action)
- **Persistence:** Firewall rules survive reboots (user must manually remove if no longer needed)

---

**Phase Status:** ✅ Planning Complete — Ready for Execution  
**Next Step:** Run `/gsd-execute-phase 15` or execute Plan 15-01 manually
