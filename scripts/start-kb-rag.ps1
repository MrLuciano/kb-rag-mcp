# ──────────────────────────────────────────────────────────────────────────────
# start-kb-rag.ps1  —  Inicia o KB RAG no WSL2 (gaming machine)
# Adicione ao startup do Windows: shell:startup
# ──────────────────────────────────────────────────────────────────────────────

param(
    [switch]$Stop,
    [switch]$Status
)

$WSL_DISTRO  = "Ubuntu-24.04"
$PROJECT     = "/home/$env:USERNAME/kb-rag-mcp"  # ajuste se necessário
$PYTHON      = "$PROJECT/.venv/bin/python"
$SERVER      = "$PROJECT/server/server.py"
$LOG         = "$PROJECT/logs/mcp.log"
$PID_FILE    = "$PROJECT/logs/mcp.pid"

function Start-KbRag {
    Write-Host "Iniciando KB RAG no WSL2..." -ForegroundColor Cyan

    # Garante que o WSL está rodando
    wsl -d $WSL_DISTRO echo "WSL2 OK" | Out-Null

    # Inicia Docker (Qdrant) se necessário
    wsl -d $WSL_DISTRO bash -c "
        sudo service docker start 2>/dev/null || true
        docker start kb-qdrant 2>/dev/null || docker compose -f $PROJECT/docker-compose.yml up -d qdrant
        sleep 2
    " | Out-Null

    # Inicia o MCP server em background
    wsl -d $WSL_DISTRO bash -c @"
        mkdir -p $PROJECT/logs
        source $PROJECT/.venv/bin/activate
        export \$(cat $PROJECT/.env | grep -v '^#' | xargs)
        nohup $PYTHON $SERVER > $LOG 2>&1 &
        echo \$! > $PID_FILE
        echo "MCP server iniciado (PID: \$(cat $PID_FILE))"
"@

    Write-Host "KB RAG iniciado. Log: wsl -d $WSL_DISTRO cat $LOG" -ForegroundColor Green
}

function Stop-KbRag {
    Write-Host "Parando KB RAG..." -ForegroundColor Yellow
    wsl -d $WSL_DISTRO bash -c "
        if [ -f $PID_FILE ]; then
            kill \$(cat $PID_FILE) 2>/dev/null && echo 'MCP server parado'
            rm -f $PID_FILE
        else
            echo 'PID file não encontrado'
        fi
    "
}

function Get-KbRagStatus {
    wsl -d $WSL_DISTRO bash -c "
        if [ -f $PID_FILE ] && kill -0 \$(cat $PID_FILE) 2>/dev/null; then
            echo 'STATUS: RODANDO (PID: '\$(cat $PID_FILE)')'
        else
            echo 'STATUS: PARADO'
        fi
        echo ''
        echo '--- Últimas linhas do log ---'
        tail -20 $LOG 2>/dev/null || echo '(sem log)'
    "
}

if ($Stop)   { Stop-KbRag }
elseif ($Status) { Get-KbRagStatus }
else         { Start-KbRag }
