# ──────────────────────────────────────────────────────────────────────────────
# start-kb-rag.ps1  —  Starts KB RAG on WSL2 (Windows + Docker)
# Add to Windows startup: Win+R → shell:startup → paste shortcut
# ──────────────────────────────────────────────────────────────────────────────

param(
    [switch]$Stop,
    [switch]$Status,
    [switch]$ConfigureFirewall
)

$WSL_DISTRO  = "Ubuntu-24.04"
$PROJECT     = "/home/$env:USERNAME/kb-rag-mcp"  # adjust if necessary
$PYTHON      = "$PROJECT/.venv/bin/python"
$SERVER      = "$PROJECT/server/server.py"
$LOG         = "$PROJECT/logs/mcp.log"
$PID_FILE    = "$PROJECT/logs/mcp.pid"

function Test-IsAdministrator {
    <#
    .SYNOPSIS
    Checks if the current PowerShell session has Administrator privileges.
    #>
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]$identity
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Set-KbRagFirewallRules {
    <#
    .SYNOPSIS
    Creates Windows Firewall rules for all kb-rag-mcp subsystem ports.
    .DESCRIPTION
    Idempotently creates inbound TCP rules for Qdrant, MCP SSE, Health/Metrics, Prometheus, and Grafana.
    Rules are grouped under "KB-RAG-MCP" for easy management.
    #>
    
    Write-Host "`nConfiguring Windows Firewall rules..." -ForegroundColor Cyan
    
    $rules = @(
        @{Name="KB-RAG-Qdrant-REST"; Port=6333; Desc="Qdrant vector database REST API"},
        @{Name="KB-RAG-Qdrant-gRPC"; Port=6334; Desc="Qdrant vector database gRPC API"},
        @{Name="KB-RAG-MCP-SSE"; Port=8765; Desc="Model Context Protocol (MCP) SSE endpoint"},
        @{Name="KB-RAG-Health"; Port=8080; Desc="Health check and Prometheus metrics HTTP endpoint"},
        @{Name="KB-RAG-Prometheus"; Port=9090; Desc="Prometheus metrics collection and PromQL queries"},
        @{Name="KB-RAG-Grafana"; Port=3000; Desc="Grafana monitoring dashboard UI"}
    )
    
    foreach ($rule in $rules) {
        $existingRule = Get-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue
        
        if ($null -eq $existingRule) {
            try {
                New-NetFirewallRule `
                    -DisplayName $rule.Name `
                    -Direction Inbound `
                    -Protocol TCP `
                    -LocalPort $rule.Port `
                    -Action Allow `
                    -Profile Domain,Private `
                    -Description $rule.Desc `
                    -Group "KB-RAG-MCP" `
                    -Enabled True `
                    -ErrorAction Stop | Out-Null
                
                Write-Host "  ✓ $($rule.Name) ($($rule.Port)/TCP) — created" -ForegroundColor Green
            } catch {
                Write-Host "  ✗ $($rule.Name) ($($rule.Port)/TCP) — failed: $_" -ForegroundColor Red
            }
        } else {
            Write-Host "  ⊙ $($rule.Name) ($($rule.Port)/TCP) — already exists" -ForegroundColor Yellow
        }
    }
    
    Write-Host ""
}

# If -ConfigureFirewall is specified, check for elevation
if ($ConfigureFirewall -and -not (Test-IsAdministrator)) {
    Write-Host "[!] Firewall configuration requires Administrator privileges." -ForegroundColor Yellow
    $response = Read-Host "[?] Re-launch script as Administrator? [Y/n]"
    
    if ($response -eq '' -or $response -match '^[Yy]') {
        # Build argument list for elevated process
        $argList = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -ConfigureFirewall"
        if ($Stop) { $argList += " -Stop" }
        if ($Status) { $argList += " -Status" }
        
        # Re-launch elevated
        Start-Process powershell.exe -ArgumentList $argList -Verb RunAs
        exit
    } else {
        Write-Host "Skipping firewall configuration (local-only access)." -ForegroundColor Yellow
        $ConfigureFirewall = $false
    }
}

function Start-KbRag {
    Write-Host "Starting KB RAG on WSL2..." -ForegroundColor Cyan

    # Ensure WSL2 is running
    wsl -d $WSL_DISTRO echo "WSL2 OK" | Out-Null

    # Configure Windows Firewall if requested
    if ($ConfigureFirewall) {
        Set-KbRagFirewallRules
    }

    # Start Docker (Qdrant) if needed
    wsl -d $WSL_DISTRO bash -c "
        sudo service docker start 2>/dev/null || true
        docker start kb-qdrant 2>/dev/null || docker compose -f $PROJECT/docker-compose.yml up -d qdrant
        sleep 2
    " | Out-Null

    # Start MCP server in background
    wsl -d $WSL_DISTRO bash -c @"
        mkdir -p $PROJECT/logs
        source $PROJECT/.venv/bin/activate
        export \$(cat $PROJECT/.env | grep -v '^#' | xargs)
        nohup $PYTHON $SERVER > $LOG 2>&1 &
        echo \$! > $PID_FILE
        echo "MCP server started (PID: \$(cat $PID_FILE))"
"@

    Write-Host "KB RAG started. Log: wsl -d $WSL_DISTRO cat $LOG" -ForegroundColor Green
}

function Stop-KbRag {
    Write-Host "Stopping KB RAG..." -ForegroundColor Yellow
    wsl -d $WSL_DISTRO bash -c "
        if [ -f $PID_FILE ]; then
            kill \$(cat $PID_FILE) 2>/dev/null && echo 'MCP server stopped'
            rm -f $PID_FILE
        else
            echo 'PID file not found'
        fi
    "
}

function Get-KbRagStatus {
    wsl -d $WSL_DISTRO bash -c "
        if [ -f $PID_FILE ] && kill -0 \$(cat $PID_FILE) 2>/dev/null; then
            echo 'STATUS: RUNNING (PID: '\$(cat $PID_FILE)')'
        else
            echo 'STATUS: STOPPED'
        fi
        echo ''
        echo '--- Last 20 log lines ---'
        tail -20 $LOG 2>/dev/null || echo '(no log available)'
    "
}

if ($Stop)   { Stop-KbRag }
elseif ($Status) { Get-KbRagStatus }
else         { Start-KbRag }
