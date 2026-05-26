# Phase 15: PowerShell Ports Script — Context & Design

## Problem Statement

The `scripts/start-kb-rag.ps1` PowerShell script starts the kb-rag-mcp stack on Windows (WSL2 + Docker), but **does not configure Windows Firewall to open the required ports** for external access. This means:

1. **MCP clients on the Windows host** cannot connect to the SSE endpoint (port 8765)
2. **Health checks from Windows apps** cannot reach the health/metrics endpoint (port 8080)
3. **Monitoring tools on the LAN** cannot scrape Prometheus (port 9090) or view Grafana (port 3000)
4. **External clients** cannot query Qdrant REST API (port 6333) or gRPC (port 6334)

Users must manually run `New-NetFirewallRule` commands or open Windows Defender Firewall UI to enable access.

## Goal

Enhance `scripts/start-kb-rag.ps1` to **automatically configure Windows Firewall rules** for all subsystem ports during startup, with proper error handling and idempotency.

## Constraints

- **PowerShell 5.1+ compatibility** (Windows 10/11 built-in)
- **Elevation handling** — Firewall rules require Administrator privileges; script must detect elevation and prompt if needed
- **Idempotency** — Running the script multiple times should not duplicate firewall rules
- **Non-breaking** — Existing `-Stop` and `-Status` parameters must continue to work
- **WSL2 port forwarding** — Windows 11 22H2+ has automatic WSL port forwarding, but explicit rules may still be needed for LAN access
- **Backward compatibility** — Users who don't want firewall changes should be able to opt-out via parameter

## Affected Ports

Based on `docker-compose.yml` and Phase 14 Health Dashboard:

| Port | Service | Protocol | Purpose | Default Binding |
|------|---------|----------|---------|-----------------|
| **6333** | Qdrant REST API | TCP | Vector database queries | `0.0.0.0:6333` |
| **6334** | Qdrant gRPC | TCP | Vector database (gRPC) | `0.0.0.0:6334` |
| **8765** | MCP SSE | TCP | Model Context Protocol (AI clients) | `0.0.0.0:8765` |
| **8080** | Health/Metrics HTTP | TCP | `/health`, `/metrics` endpoints | `0.0.0.0:8080` |
| **9090** | Prometheus | TCP | Metrics scraping + PromQL queries | `0.0.0.0:9090` |
| **3000** | Grafana | TCP | Monitoring dashboard UI | `0.0.0.0:3000` |

**Note:** WSL2 uses Hyper-V NAT by default. Ports are forwarded from `127.0.0.1` (Windows) to WSL IP, but **external LAN access requires explicit Windows Firewall rules**.

## Current Script Behavior

`scripts/start-kb-rag.ps1` currently:

1. Validates WSL2 is running (`wsl -d $WSL_DISTRO echo "WSL2 OK"`)
2. Starts Docker service in WSL (`sudo service docker start`)
3. Starts Qdrant container (`docker compose up -d qdrant`)
4. Starts MCP server in background (`nohup python server/server.py &`)
5. Writes PID to `logs/mcp.pid` for `-Stop` functionality

**Missing:** Windows Firewall configuration for WSL2 port forwarding to LAN.

## Design Approach

### Option A: Inline Firewall Rules (Recommended)

Add firewall configuration directly to `start-kb-rag.ps1`:

**Pros:**
- Single script to maintain
- Atomic start + firewall setup
- Easier for users (no additional script to run)

**Cons:**
- Requires Administrator elevation (UAX prompt on first run)
- Mixes concerns (service startup + firewall config)

### Option B: Separate Firewall Script

Create `scripts/configure-firewall.ps1` invoked by `start-kb-rag.ps1`:

**Pros:**
- Separation of concerns
- Can be run independently by IT/admins
- `start-kb-rag.ps1` can work without elevation for local-only access

**Cons:**
- Two scripts to maintain
- Extra step for users
- Requires coordination (run firewall script first, then start script)

### Option C: Hybrid Approach (Selected)

Enhance `start-kb-rag.ps1` with:
- **`-ConfigureFirewall` switch** (opt-in) — Creates/updates firewall rules when specified
- **Elevation detection** — Checks `[Security.Principal.WindowsIdentity]::GetCurrent().Groups` for Administrator role
- **Auto-elevation prompt** — If `-ConfigureFirewall` is used without elevation, re-launch with `Start-Process -Verb RunAs`
- **Idempotent rule management** — Check if rule exists before creating, update if ports/profiles change

**Why Hybrid:**
- Default behavior unchanged (no breaking changes)
- Users who need LAN access can run with `-ConfigureFirewall` once
- Firewall logic is centralized in the main script
- IT/admins can pre-configure via GPO (rules persist across reboots)

## Firewall Rule Design

### Rule Naming Convention

```
KB-RAG-{ServiceName}
```

Examples:
- `KB-RAG-Qdrant-REST`
- `KB-RAG-Qdrant-gRPC`
- `KB-RAG-MCP-SSE`
- `KB-RAG-Health`
- `KB-RAG-Prometheus`
- `KB-RAG-Grafana`

### Rule Parameters

```powershell
New-NetFirewallRule `
    -DisplayName "KB-RAG-MCP-SSE" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 8765 `
    -Action Allow `
    -Profile Domain,Private `
    -Description "Model Context Protocol (MCP) SSE endpoint for kb-rag-mcp" `
    -Group "KB-RAG-MCP" `
    -Enabled True
```

**Key decisions:**
- **`-Profile Domain,Private`** (not Public) — Safer default; users can manually enable Public if needed
- **`-Group "KB-RAG-MCP"`** — Groups all rules together in Windows Firewall UI
- **`-Description`** — Clear purpose for each port
- **`-Enabled True`** — Active immediately on creation

### Idempotency Strategy

Before creating a rule, check if it exists:

```powershell
$existingRule = Get-NetFirewallRule -DisplayName "KB-RAG-MCP-SSE" -ErrorAction SilentlyContinue
if ($null -eq $existingRule) {
    New-NetFirewallRule ...
} else {
    Write-Host "Firewall rule 'KB-RAG-MCP-SSE' already exists (skipping)" -ForegroundColor Yellow
}
```

**Alternative:** Use `Set-NetFirewallRule` to update existing rules (ensures parameters stay current even if manually modified).

## User Experience Flow

### Scenario 1: First-time local-only user

```powershell
PS> .\scripts\start-kb-rag.ps1
Iniciando KB RAG no WSL2...
MCP server iniciado (PID: 12345)
KB RAG iniciado. Log: wsl -d Ubuntu-24.04 cat /home/luck/kb-rag-mcp/logs/mcp.log
```

**Result:** Services start, accessible from `127.0.0.1` on Windows, no firewall changes.

### Scenario 2: User needs LAN access (first run)

```powershell
PS> .\scripts\start-kb-rag.ps1 -ConfigureFirewall
[!] Firewall configuration requires Administrator privileges.
[?] Re-launch script as Administrator? [Y/n]: Y

[Elevated window opens]

Configurando regras de firewall do Windows...
✓ KB-RAG-Qdrant-REST (6333/TCP) — criada
✓ KB-RAG-Qdrant-gRPC (6334/TCP) — criada
✓ KB-RAG-MCP-SSE (8765/TCP) — criada
✓ KB-RAG-Health (8080/TCP) — criada
✓ KB-RAG-Prometheus (9090/TCP) — criada
✓ KB-RAG-Grafana (3000/TCP) — criada

Iniciando KB RAG no WSL2...
MCP server iniciado (PID: 12345)
KB RAG iniciado. Log: wsl -d Ubuntu-24.04 cat /home/luck/kb-rag-mcp/logs/mcp.log
```

**Result:** 6 firewall rules created, services start, accessible from LAN via Windows IP.

### Scenario 3: User runs again with `-ConfigureFirewall`

```powershell
PS> .\scripts\start-kb-rag.ps1 -ConfigureFirewall
Configurando regras de firewall do Windows...
⊙ KB-RAG-Qdrant-REST (6333/TCP) — já existe
⊙ KB-RAG-Qdrant-gRPC (6334/TCP) — já existe
⊙ KB-RAG-MCP-SSE (8765/TCP) — já existe
⊙ KB-RAG-Health (8080/TCP) — já existe
⊙ KB-RAG-Prometheus (9090/TCP) — já existe
⊙ KB-RAG-Grafana (3000/TCP) — já existe

Iniciando KB RAG no WSL2...
...
```

**Result:** No duplicate rules, idempotent behavior.

### Scenario 4: User stops services with firewall configured

```powershell
PS> .\scripts\start-kb-rag.ps1 -Stop
Parando KB RAG...
MCP server parado
```

**Firewall rules:** Left in place (persist across service restarts). User can manually remove via:

```powershell
PS> Get-NetFirewallRule -Group "KB-RAG-MCP" | Remove-NetFirewallRule
```

Or add `-RemoveFirewall` switch to stop operation (future enhancement).

## Error Handling

### Elevation Detection

```powershell
function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]$identity
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}
```

### Auto-Elevation

```powershell
if ($ConfigureFirewall -and -not (Test-IsAdministrator)) {
    Write-Host "[!] Firewall configuration requires Administrator privileges." -ForegroundColor Yellow
    $response = Read-Host "[?] Re-launch script as Administrator? [Y/n]"
    if ($response -eq '' -or $response -eq 'Y' -or $response -eq 'y') {
        $args = "-File `"$PSCommandPath`" -ConfigureFirewall"
        Start-Process powershell.exe -ArgumentList $args -Verb RunAs
        exit
    } else {
        Write-Host "Skipping firewall configuration." -ForegroundColor Yellow
    }
}
```

### Firewall Rule Creation Errors

```powershell
try {
    New-NetFirewallRule -DisplayName "KB-RAG-MCP-SSE" ... -ErrorAction Stop
    Write-Host "✓ KB-RAG-MCP-SSE (8765/TCP) — criada" -ForegroundColor Green
} catch {
    Write-Host "✗ KB-RAG-MCP-SSE (8765/TCP) — falhou: $_" -ForegroundColor Red
}
```

**Non-fatal:** If firewall configuration fails, script continues with service startup (user gets local-only access).

## Testing Strategy

### Manual Tests

1. **Idempotency test**
   ```powershell
   .\start-kb-rag.ps1 -ConfigureFirewall
   .\start-kb-rag.ps1 -ConfigureFirewall  # Should skip existing rules
   ```

2. **Elevation prompt test** (run as non-admin)
   ```powershell
   .\start-kb-rag.ps1 -ConfigureFirewall
   # Should prompt for elevation
   ```

3. **LAN access test** (from another machine)
   ```bash
   curl http://<WINDOWS_IP>:8080/health
   curl http://<WINDOWS_IP>:3000  # Grafana UI
   ```

4. **Rule cleanup test**
   ```powershell
   Get-NetFirewallRule -Group "KB-RAG-MCP" | Remove-NetFirewallRule
   .\start-kb-rag.ps1 -ConfigureFirewall  # Should recreate all rules
   ```

5. **Backward compatibility test**
   ```powershell
   .\start-kb-rag.ps1          # Should work without firewall changes
   .\start-kb-rag.ps1 -Stop    # Should work
   .\start-kb-rag.ps1 -Status  # Should work
   ```

### Validation Checks

- [ ] Firewall rules created with correct ports, profiles, descriptions
- [ ] Rules grouped under "KB-RAG-MCP" in Windows Firewall UI
- [ ] No duplicate rules after multiple runs
- [ ] Services accessible from LAN after firewall configuration
- [ ] Script works without elevation for default (local-only) mode
- [ ] Elevation prompt appears when `-ConfigureFirewall` used without admin
- [ ] Error messages are clear if firewall rule creation fails
- [ ] Existing `-Stop` and `-Status` functionality unchanged

## Documentation Requirements

### README.md Updates

Add section under **Windows Quick Start**:

```markdown
#### Enabling LAN Access (Optional)

By default, services are accessible only from `localhost`. To enable access from other machines:

1. Run the startup script with `-ConfigureFirewall` (requires Administrator):
   ```powershell
   .\scripts\start-kb-rag.ps1 -ConfigureFirewall
   ```

2. This creates Windows Firewall rules for:
   - Qdrant (6333, 6334)
   - MCP SSE endpoint (8765)
   - Health/Metrics (8080)
   - Prometheus (9090)
   - Grafana (3000)

3. Services are then accessible via Windows IP:
   ```
   http://<YOUR_WINDOWS_IP>:3000     # Grafana
   http://<YOUR_WINDOWS_IP>:8080/health  # Health check
   ```

**Note:** Firewall rules persist across reboots. To remove:
```powershell
Get-NetFirewallRule -Group "KB-RAG-MCP" | Remove-NetFirewallRule
```
```

### README.pt-BR.md / README.es.md Equivalent

Add translated versions of the above section (Phase 13 pattern).

### OPERATIONS.md Updates

Add **Windows Firewall Management** section:

```markdown
### Windows Firewall Management

#### Automatic Configuration

The `start-kb-rag.ps1` script includes firewall configuration:

```powershell
.\scripts\start-kb-rag.ps1 -ConfigureFirewall
```

This creates rules for all kb-rag-mcp ports with Domain/Private profiles enabled.

#### Manual Configuration

If you prefer manual control:

```powershell
# Create MCP SSE rule
New-NetFirewallRule `
    -DisplayName "KB-RAG-MCP-SSE" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 8765 `
    -Action Allow `
    -Profile Domain,Private `
    -Group "KB-RAG-MCP"

# List all KB-RAG rules
Get-NetFirewallRule -Group "KB-RAG-MCP"

# Remove all KB-RAG rules
Get-NetFirewallRule -Group "KB-RAG-MCP" | Remove-NetFirewallRule
```

#### Troubleshooting

**Problem:** Cannot access services from LAN despite firewall rules.

**Solutions:**
1. Check WSL IP forwarding: `netsh interface portproxy show v4tov4`
2. Verify Windows IP: `ipconfig` (look for Ethernet/Wi-Fi adapter IP)
3. Check Docker port mapping: `docker ps` (ensure ports are `0.0.0.0:xxxx`)
4. Confirm firewall rule is active: `Get-NetFirewallRule -DisplayName "KB-RAG-*" | Select-Object DisplayName, Enabled`
```

## Implementation Complexity

### Low Complexity
- Elevation detection (`Test-IsAdministrator`)
- Idempotency check (`Get-NetFirewallRule` before create)
- Single rule creation pattern (repeated 6 times)

### Medium Complexity
- Auto-elevation logic (`Start-Process -Verb RunAs`)
- Parameter validation (ensure `-ConfigureFirewall` doesn't conflict with `-Stop`)
- Error handling for individual rule failures (continue script execution)

### High Complexity
- None (PowerShell firewall APIs are straightforward)

**Estimated Effort:** 2-3 hours (implementation + testing)

## Dependencies

- **Phase 14 (Health Dashboard):** Defines port 8080 for health/metrics — must be included in firewall rules
- **docker-compose.yml:** Source of truth for all port mappings
- **.env / config/.env.*** Port defaults (SSE_PORT, HEALTH_PORT, QDRANT_PORT)

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| User runs without elevation, firewall fails silently | Medium | Explicit elevation check + prompt before attempting firewall config |
| Duplicate rules if script run multiple times | Low | Idempotency check with `Get-NetFirewallRule` |
| Firewall rules interfere with VPN/corporate policies | Medium | Use Domain/Private profiles (not Public), document manual removal |
| WSL2 networking changes in future Windows versions | Low | Script is version-independent (uses PowerShell APIs, not netsh) |
| Users forget firewall rules exist, causing confusion later | Low | Add `-ListFirewallRules` switch for visibility |

## Future Enhancements (Out of Scope for Phase 15)

- [ ] `-RemoveFirewall` switch to clean up rules during `-Stop`
- [ ] `-ListFirewallRules` to show current KB-RAG firewall state
- [ ] Automatic detection of WSL IP changes (Windows 11 22H2+ dynamic IPs)
- [ ] GPO template for enterprise deployment
- [ ] Profile selection (`-Profile Public` to enable internet-facing access)
- [ ] IPv6 rule support (currently TCP/IPv4 only)

## Success Criteria

1. **Functional:**
   - [ ] Firewall rules created for all 6 ports when `-ConfigureFirewall` used
   - [ ] Services accessible from LAN after configuration
   - [ ] No duplicate rules on repeated runs
   - [ ] Elevation prompt works correctly

2. **Non-functional:**
   - [ ] Backward compatible (existing usage unchanged)
   - [ ] Clear error messages if elevation/firewall fails
   - [ ] Idempotent (safe to run multiple times)
   - [ ] Documentation updated (README.md, OPERATIONS.md)

3. **Quality:**
   - [ ] Manual testing on Windows 10 and Windows 11
   - [ ] Tested with/without Administrator privileges
   - [ ] Tested with existing firewall rules (idempotency)
   - [ ] LAN access verified from remote machine

## References

- **PowerShell NetSecurity module:** [New-NetFirewallRule](https://learn.microsoft.com/en-us/powershell/module/netsecurity/new-netfirewallrule)
- **WSL2 networking:** [Accessing WSL from LAN](https://learn.microsoft.com/en-us/windows/wsl/networking)
- **Phase 14 Health Dashboard:** `.planning/phases/14/CONTEXT.md` (port 8080 definition)
- **Current script:** `scripts/start-kb-rag.ps1` (71 lines, Portuguese comments)
