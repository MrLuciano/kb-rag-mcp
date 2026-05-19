#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# setup.sh — Instala dependências e configura o ambiente
# Execute uma vez após clonar o projeto.
#
# Uso:
#   bash scripts/setup.sh local    # local machine (WSL2 + LM Studio)
#   bash scripts/setup.sh lxc      # LXC Server (Ollama)
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail
PROFILE="${1:-local}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "================================================"
echo " KB RAG MCP — Setup ($PROFILE)"
echo "================================================"

# ── Python venv ───────────────────────────────────────────────────────────────
echo "[1/5] Criando virtualenv..."
python3 -m venv "$PROJECT_ROOT/.venv"
source "$PROJECT_ROOT/.venv/bin/activate"
pip install --upgrade pip --quiet

# ── Dependências base ─────────────────────────────────────────────────────────
echo "[2/5] Instalando dependências..."
pip install -r "$PROJECT_ROOT/requirements.txt" --quiet

# ── Dependências específicas por perfil ───────────────────────────────────────
echo "[3/5] Configurando perfil: $PROFILE"
if [ "$PROFILE" = "lxc" ]; then
    pip install ollama --quiet
    # Instala Ollama se não existir
    if ! command -v ollama &>/dev/null; then
        echo "  Instalando Ollama..."
        curl -fsSL https://ollama.ai/install.sh | sh
    fi
    echo "  Baixando modelo de embedding nomic-embed-text..."
    ollama pull nomic-embed-text || true
elif [ "$PROFILE" = "local" ]; then
    echo "  → Certifique-se de que o LM Studio está rodando no Windows"
    echo "  → Carregue o modelo nomic-embed-text-v1.5 no LM Studio"
    echo "  → Inicie o servidor local (porta 1234)"
fi

# ── Docker / Qdrant ───────────────────────────────────────────────────────────
echo "[4/5] Iniciando Qdrant via Docker..."
mkdir -p "$PROJECT_ROOT/data/qdrant"
if command -v docker &>/dev/null; then
    cd "$PROJECT_ROOT"
    docker compose up -d qdrant
    echo "  Qdrant iniciado em localhost:6333"
else
    echo "  Docker não encontrado. Instale Docker ou use Qdrant embedded (QDRANT_PATH)."
fi

# ── Copia .env ────────────────────────────────────────────────────────────────
echo "[5/5] Configurando .env..."
ENV_SRC="$PROJECT_ROOT/config/.env.$PROFILE"
ENV_DST="$PROJECT_ROOT/.env"
if [ ! -f "$ENV_DST" ]; then
    cp "$ENV_SRC" "$ENV_DST"
    echo "  .env criado a partir de $ENV_SRC"
    echo "  ⚠ Revise as configurações em $ENV_DST"
else
    echo "  .env já existe, mantendo."
fi

echo ""
echo "================================================"
echo " Setup concluído!"
echo ""
echo " Próximos passos:"
echo "   1. Revise o arquivo .env"
echo "   2. Rode a ingestão:"
echo "      source .venv/bin/activate"
echo "      python ingest/ingest.py --docs /caminho/para/seus/docs"
echo "   3. Teste o servidor:"
echo "      python server/server.py"
echo "   4. Configure o MCP client (veja config/mcp-clients.json)"
echo "================================================"
