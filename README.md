# KB RAG MCP Server

MCP Server para busca semântica em knowledge base local de documentação de produtos.  
Suporta PDF, DOCX, XLSX, PPTX, TXT, Markdown e código fonte (~7 GB+).  
Compatível com **Claude Code**, **OpenCode** e qualquer cliente MCP.

---

## Arquitetura

```
Documentos (PDF, DOCX, XLSX, PPTX, TXT, código)
    ↓  ingest/ingest.py
Embedding (LM Studio ou Ollama)
    ↓
Qdrant (vector store local)
    ↓
server/server.py  ←→  MCP (stdio ou SSE)
    ↓
Claude Code / OpenCode
```

---

## Setup Rápido

### Gaming Machine (Windows + WSL2 + LM Studio)

```bash
# 1. No LM Studio (Windows): carregue nomic-embed-text-v1.5 e inicie o servidor
# 2. No WSL2:
git clone <repo> ~/kb-rag-mcp
cd ~/kb-rag-mcp
bash scripts/setup.sh gaming

# 3. Ingira os documentos
source .venv/bin/activate
python ingest/ingest.py --docs /mnt/d/seus-docs

# 4. Verifique
python scripts/health_check.py

# 5. Configure o Claude Code (config/mcp-clients.json → bloco gaming)
```

**Autostart no Windows:** Crie um atalho em `shell:startup` apontando para:
```
powershell -WindowStyle Hidden -File C:\caminho\kb-rag-mcp\scripts\start-kb-rag.ps1
```

---

### Proxmox LXC (Linux + Ollama)

```bash
# No LXC Ubuntu 24.04:
git clone <repo> /opt/kb-rag-mcp
cd /opt/kb-rag-mcp
bash scripts/setup.sh proxmox

# Ingira os documentos
source .venv/bin/activate
python ingest/ingest.py --docs /opt/kb-rag-mcp/docs --workers 4

# Instala como serviço systemd
cp scripts/kb-mcp.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now kb-mcp
```

---

## Tools MCP disponíveis

| Tool | Descrição |
|---|---|
| `search_kb` | Busca semântica — retorna top-K chunks relevantes |
| `list_documents` | Lista documentos indexados com filtros |
| `get_chunk` | Chunk completo + contexto vizinho |
| `kb_stats` | Estatísticas da KB (total docs, chunks, tamanho) |

### Exemplo de uso no Claude Code

```
Me mostra como configurar autenticação OAuth na API do produto-x
```
O Claude Code chamará `search_kb` automaticamente e retornará os chunks mais relevantes da sua documentação.

---

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `EMBED_BACKEND` | `lmstudio-sdk` | `lmstudio-sdk`, `lmstudio-rest`, `openai-compat`, `ollama` |
| `EMBED_MODEL` | `nomic-embed-text-v1.5` | Modelo de embedding |
| `LMS_BASE_URL` | `http://localhost:1234` | URL base do LM Studio |
| `OLLAMA_HOST` | `http://localhost:11434` | URL do Ollama |
| `QDRANT_HOST` | `localhost` | Host do Qdrant |
| `QDRANT_PORT` | `6333` | Porta do Qdrant |
| `QDRANT_PATH` | _(vazio)_ | Se definido, usa Qdrant embedded (sem Docker) |
| `QDRANT_COLLECTION` | `kb_docs` | Nome da coleção |
| `SCORE_THRESHOLD` | `0.35` | Score mínimo de relevância (0-1) |
| `MCP_TRANSPORT` | `stdio` | `stdio` ou `sse` |
| `SSE_HOST` | `0.0.0.0` | Host para modo SSE |
| `SSE_PORT` | `8765` | Porta para modo SSE |
| `DEFAULT_TOP_K` | `5` | Resultados padrão por busca |

---

## Ingestão

```bash
# Pasta completa (detecta produto pela estrutura de pastas)
python ingest/ingest.py --docs /caminho/docs

# Com produto explícito
python ingest/ingest.py --docs /caminho/docs --product meu-produto

# Arquivo único
python ingest/ingest.py --file /caminho/doc.pdf

# Reingestão completa (limpa antes)
python ingest/ingest.py --docs /caminho/docs --clean

# Mais workers para ingestão mais rápida (use com cuidado em CPU only)
python ingest/ingest.py --docs /caminho/docs --workers 4
```

### Estrutura de pastas recomendada

```
docs/
├── produto-a/
│   ├── api-reference.pdf
│   ├── getting-started.docx
│   └── examples/
│       └── sample.py
├── produto-b/
│   ├── manual.pdf
│   └── config.xlsx
└── geral/
    └── arquitetura.pptx
```

O produto é inferido automaticamente pelo nome da pasta raiz.

---

## Comandos úteis

```bash
# Health check
python scripts/health_check.py

# Stats da KB
python -c "
import asyncio
from server.vector_store import VectorStore
async def main():
    s = VectorStore()
    await s.connect()
    print(await s.get_stats())
asyncio.run(main())
"

# Logs em tempo real (Proxmox)
journalctl -u kb-mcp -f

# Status gaming machine
pwsh scripts/start-kb-rag.ps1 -Status
```

---

## Requisitos mínimos

| Cenário | CPU | RAM | Disco |
|---|---|---|---|
| Gaming (8845HS + LM Studio) | 8 cores | 32 GB | 30 GB livres |
| Proxmox LXC (CPU only) | 6 vCPU | 8 GB | 30 GB livres |
