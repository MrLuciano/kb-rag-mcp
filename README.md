# KB RAG MCP Server

**[English](#english) | [Português (Brasil)](#português-brasil)**

---

<a name="english"></a>
## 🇬🇧 English

Production-grade MCP (Model Context Protocol) server for semantic search over
local knowledge bases. Supports PDF, DOCX, XLSX, PPTX, TXT, Markdown, and
source code (~7 GB+). Compatible with **Claude Code**, **OpenCode**, and any
MCP client.

### ✨ Features

- 🔍 **Semantic search** over technical documentation
- 📚 **Multi-format support**: PDF, DOCX, XLSX, PPTX, TXT, code
- 🎯 **Smart classification**: automatic product and doc type detection
- 🚀 **Production-ready**: job management, worker pools, observability
- 💾 **Incremental ingestion**: only processes new/modified files
- 📊 **Metrics**: Prometheus-compatible metrics for monitoring
- 🔄 **Cache system**: LRU with RAM auto-tuning or Redis
- 🔧 **Multi-backend**: LM Studio, Ollama, or OpenAI-compatible APIs

---

### 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [MCP Tools](#mcp-tools)
- [Architecture](#architecture)
- [Development](#development)
- [Documentation](#documentation)
- [License](#license)

---

### 🚀 Quick Start

#### Option 1: Gaming Machine (Windows + WSL2 + LM Studio)

```bash
# 1. Start LM Studio on Windows with nomic-embed-text-v1.5
# 2. In WSL2:
git clone https://github.com/yourusername/kb-rag-mcp ~/kb-rag-mcp
cd ~/kb-rag-mcp
bash scripts/setup.sh gaming

# 3. Ingest documents
source .venv/bin/activate
python ingest/ingest.py --docs /mnt/d/your-docs

# 4. Health check
python scripts/health_check.py

# 5. Configure Claude Code (copy config/mcp-clients.json → gaming block)
```

#### Option 2: Linux Server (Ollama)

```bash
# On Ubuntu 24.04:
git clone https://github.com/yourusername/kb-rag-mcp /opt/kb-rag-mcp
cd /opt/kb-rag-mcp
bash scripts/setup.sh proxmox

# Ingest documents
source .venv/bin/activate
python ingest/ingest.py --docs /opt/docs --workers 4

# Install as systemd service
sudo cp scripts/kb-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now kb-mcp
```

---

### 💻 Installation

#### Prerequisites

- Python 3.11+
- Docker (for Qdrant) or Qdrant embedded
- LM Studio / Ollama / OpenAI-compatible embedding API
- 8+ GB RAM (16+ GB recommended)

#### Step-by-step Installation

**1. Clone the repository**

```bash
git clone https://github.com/yourusername/kb-rag-mcp
cd kb-rag-mcp
```

**2. Run setup script**

```bash
# For gaming machine (LM Studio):
bash scripts/setup.sh gaming

# For Linux server (Ollama):
bash scripts/setup.sh proxmox

# Manual setup:
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**3. Configure environment**

```bash
# Copy appropriate config
cp config/.env.gaming .env  # or .env.proxmox

# Edit .env with your settings
vim .env
```

**4. Start Qdrant**

```bash
docker-compose up -d
```

**5. Verify installation**

```bash
source .venv/bin/activate
python scripts/health_check.py
```

---

### ⚙️ Configuration

#### Environment Variables

Create `.env` file in project root:

```bash
# Embedding Backend
EMBED_BACKEND=openai-compat  # lmstudio-sdk, lmstudio-rest, openai-compat, ollama
EMBED_MODEL=text-embedding-nomic-embed-text-v1.5-embedding
LMS_BASE_URL=http://localhost:1234  # LM Studio URL (without /v1)
OLLAMA_HOST=http://localhost:11434

# Vector Store
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_PATH=  # Leave empty for Docker, set path for embedded
QDRANT_COLLECTION=kb_docs

# Search Settings
SCORE_THRESHOLD=0.35  # Minimum relevance score (0.0-1.0)
DEFAULT_TOP_K=5       # Default search results

# MCP Transport
MCP_TRANSPORT=stdio   # stdio or sse
SSE_HOST=0.0.0.0      # For SSE mode
SSE_PORT=8765

# Cache Settings
CACHE_BACKEND=lru     # lru or redis
CACHE_MAX_SIZE_MB=512 # LRU cache size (auto if not set)
CACHE_TTL=3600        # Cache TTL in seconds
```

#### MCP Client Configuration

**Claude Code (Windows + WSL2)**

`%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kb-rag": {
      "command": "wsl.exe",
      "args": [
        "-d", "Ubuntu-24.04",
        "--",
        "/home/YOUR_USER/kb-rag-mcp/.venv/bin/python",
        "/home/YOUR_USER/kb-rag-mcp/server/server.py"
      ]
    }
  }
}
```

**Claude Code (SSE mode)**

```json
{
  "mcpServers": {
    "kb-rag": {
      "url": "http://192.168.1.200:8765/sse"
    }
  }
}
```

**OpenCode**

`~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "kb-rag": {
      "type": "local",
      "command": [
        "/path/to/kb-rag-mcp/.venv/bin/python",
        "/path/to/kb-rag-mcp/server/server.py"
      ]
    }
  }
}
```

---

### 📖 Usage

#### Ingesting Documents

```bash
source .venv/bin/activate

# Ingest entire directory (incremental)
python ingest/ingest.py --docs /path/to/docs

# With explicit product
python ingest/ingest.py --docs /path/to/docs --product MyProduct

# Single file
python ingest/ingest.py --file /path/to/document.pdf

# Clean and re-ingest everything
python ingest/ingest.py --docs /path/to/docs --clean

# More workers (use with GPU)
python ingest/ingest.py --docs /path/to/docs --workers 4

# Check ingestion status
python ingest/ingest.py --status
python ingest/ingest.py --status --list    # List all files
python ingest/ingest.py --status --errors  # Only errors
```

#### Recommended Directory Structure

```
docs/
├── product-a/
│   ├── api-reference.pdf
│   ├── getting-started.docx
│   └── examples/
│       └── sample.py
├── product-b/
│   ├── manual.pdf
│   └── config.xlsx
└── general/
    └── architecture.pptx
```

Product is automatically inferred from directory name.

---

### 🔧 MCP Tools

#### `search_kb`

Semantic search over knowledge base.

**Parameters:**
- `query` (required): Search query
- `top_k` (optional): Number of results (1-20, default: 5)
- `product` (optional): Filter by product
- `doc_type` (optional): Filter by document type
- `filter_type` (optional): Filter by file format (pdf, docx, xlsx, pptx, txt, code)

**Returns:** List of chunks with `chunk_id`, `score`, `text`, `source_file`,
`product`, `doc_type`, `file_type`, `page`.

#### `list_documents`

List indexed documents with optional filters.

**Parameters:**
- `product` (optional): Filter by product
- `doc_type` (optional): Filter by document type
- `filter_type` (optional): Filter by file format

**Returns:** Documents grouped by `doc_type`.

#### `get_chunk`

Retrieve full chunk with surrounding context.

**Parameters:**
- `chunk_id` (required): Chunk ID from search results
- `context_window` (optional): Number of neighbor chunks (0-3, default: 1)

**Returns:** Chunk with context.

#### `kb_stats`

Knowledge base statistics.

**Returns:** Total documents, chunks, breakdown by doc_type and file format.

---

### 🏗️ Architecture

```
Documents (PDF, DOCX, XLSX, PPTX, TXT, code)
    ↓  ingest/ingest.py
Text Extraction → Chunking → Embedding (LM Studio / Ollama)
    ↓
Qdrant (vector store)
    ↓
server/server.py ←→ MCP (stdio or SSE)
    ↓
Claude Code / OpenCode
```

**Components:**

- **Job Management** (FASE 2): SQLite-backed job queue with priority scheduling
- **Worker Pool** (FASE 3): Async worker pool with rate limiting
- **Observability** (FASE 4): Prometheus metrics, structured logging, progress tracking
- **Cache System** (FASE 5): LRU cache with RAM auto-tuning or Redis backend
- **Document Extractors**: Multi-format support (PDF via PyMuPDF/docling)
- **Classifier**: Automatic product and doc_type detection via regex

---

### 👨‍💻 Development

#### Requirements

See `requirements.in` for human-readable dependencies.

#### Running Tests

```bash
pytest tests/ -v

# With coverage
pytest tests/ --cov=ingest --cov=server --cov=observability

# Specific test file
pytest tests/test_job_system.py -v
```

#### Code Quality

```bash
# Format code
black ingest/ server/ scripts/ tests/
isort ingest/ server/ scripts/ tests/

# Lint
flake8 ingest/ server/ scripts/ tests/

# Type check
mypy ingest/ server/ scripts/
```

#### Adding Dependencies

```bash
# Edit requirements.in
vim requirements.in

# Compile and install
pip-compile requirements.in
pip-sync requirements.txt
```

---

### 📚 Documentation

- [TESTING.md](docs/TESTING.md) - Testing strategy
- [FASE1_COMPLETION.md](docs/FASE1_COMPLETION.md) - Foundation & testing infrastructure
- [FASE2_COMPLETION.md](docs/FASE2_COMPLETION.md) - Job management system
- [FASE3_COMPLETION.md](docs/FASE3_COMPLETION.md) - Worker pool & rate limiter
- [FASE4_COMPLETION.md](docs/FASE4_COMPLETION.md) - Observability & metrics
- [FASE5_COMPLETION.md](docs/FASE5_COMPLETION.md) - Cache system
- [INSTRUCTIONS.md](docs/INSTRUCTIONS.md) - Detailed technical instructions
- [PLAN.md](docs/PLAN.md) - Implementation roadmap

---

### 📊 Metrics

Prometheus metrics available at `/metrics` endpoint (when enabled):

- Job creation, completion, duration
- File processing rate, duration
- Worker pool utilization
- Rate limiter tokens
- Cache hit/miss ratio
- API request latency

---

### 🛠️ Troubleshooting

**Embedding API not responding:**
```bash
# Check LM Studio is running and model loaded
curl http://localhost:1234/v1/models

# Check Ollama
curl http://localhost:11434/api/tags
```

**Qdrant connection error:**
```bash
# Check Qdrant is running
docker ps | grep qdrant
curl http://localhost:6333/healthz
```

**No search results:**
- Check `SCORE_THRESHOLD` (lower if too strict)
- Verify documents are indexed: `python ingest/ingest.py --status`
- Check query is in correct language

**Slow ingestion:**
- Reduce `--workers` if CPU-bound
- Check embedding API is not overloaded
- Consider using GPU for LM Studio

---

### 📝 License

[Your License Here]

---

### 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

---

<a name="português-brasil"></a>
## 🇧🇷 Português (Brasil)

Servidor MCP (Model Context Protocol) pronto para produção para busca
semântica em bases de conhecimento locais. Suporta PDF, DOCX, XLSX, PPTX,
TXT, Markdown e código-fonte (~7 GB+). Compatível com **Claude Code**,
**OpenCode** e qualquer cliente MCP.

### ✨ Funcionalidades

- 🔍 **Busca semântica** em documentação técnica
- 📚 **Suporte multi-formato**: PDF, DOCX, XLSX, PPTX, TXT, código
- 🎯 **Classificação inteligente**: detecção automática de produto e tipo de documento
- 🚀 **Pronto para produção**: gerenciamento de jobs, pool de workers, observabilidade
- 💾 **Ingestão incremental**: processa apenas arquivos novos/modificados
- 📊 **Métricas**: métricas compatíveis com Prometheus para monitoramento
- 🔄 **Sistema de cache**: LRU com auto-ajuste de RAM ou Redis
- 🔧 **Multi-backend**: LM Studio, Ollama ou APIs compatíveis com OpenAI

---

### 📋 Índice

- [Início Rápido](#início-rápido)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso](#uso)
- [Ferramentas MCP](#ferramentas-mcp)
- [Arquitetura](#arquitetura)
- [Desenvolvimento](#desenvolvimento)
- [Documentação](#documentação)
- [Licença](#licença)

---

### 🚀 Início Rápido

#### Opção 1: Gaming Machine (Windows + WSL2 + LM Studio)

```bash
# 1. Inicie o LM Studio no Windows com nomic-embed-text-v1.5
# 2. No WSL2:
git clone https://github.com/seususername/kb-rag-mcp ~/kb-rag-mcp
cd ~/kb-rag-mcp
bash scripts/setup.sh gaming

# 3. Ingira documentos
source .venv/bin/activate
python ingest/ingest.py --docs /mnt/d/seus-docs

# 4. Verificação de saúde
python scripts/health_check.py

# 5. Configure o Claude Code (copie config/mcp-clients.json → bloco gaming)
```

#### Opção 2: Servidor Linux (Ollama)

```bash
# No Ubuntu 24.04:
git clone https://github.com/seususername/kb-rag-mcp /opt/kb-rag-mcp
cd /opt/kb-rag-mcp
bash scripts/setup.sh proxmox

# Ingira documentos
source .venv/bin/activate
python ingest/ingest.py --docs /opt/docs --workers 4

# Instale como serviço systemd
sudo cp scripts/kb-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now kb-mcp
```

---

### 💻 Instalação

#### Pré-requisitos

- Python 3.11+
- Docker (para Qdrant) ou Qdrant embedded
- LM Studio / Ollama / API de embedding compatível com OpenAI
- 8+ GB RAM (16+ GB recomendado)

#### Instalação Passo a Passo

**1. Clone o repositório**

```bash
git clone https://github.com/seususername/kb-rag-mcp
cd kb-rag-mcp
```

**2. Execute o script de setup**

```bash
# Para gaming machine (LM Studio):
bash scripts/setup.sh gaming

# Para servidor Linux (Ollama):
bash scripts/setup.sh proxmox

# Setup manual:
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**3. Configure o ambiente**

```bash
# Copie a config apropriada
cp config/.env.gaming .env  # ou .env.proxmox

# Edite .env com suas configurações
vim .env
```

**4. Inicie o Qdrant**

```bash
docker-compose up -d
```

**5. Verifique a instalação**

```bash
source .venv/bin/activate
python scripts/health_check.py
```

---

### ⚙️ Configuração

#### Variáveis de Ambiente

Crie o arquivo `.env` na raiz do projeto:

```bash
# Backend de Embedding
EMBED_BACKEND=openai-compat  # lmstudio-sdk, lmstudio-rest, openai-compat, ollama
EMBED_MODEL=text-embedding-nomic-embed-text-v1.5-embedding
LMS_BASE_URL=http://localhost:1234  # URL do LM Studio (sem /v1)
OLLAMA_HOST=http://localhost:11434

# Vector Store
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_PATH=  # Deixe vazio para Docker, defina caminho para embedded
QDRANT_COLLECTION=kb_docs

# Configurações de Busca
SCORE_THRESHOLD=0.35  # Score mínimo de relevância (0.0-1.0)
DEFAULT_TOP_K=5       # Resultados padrão de busca

# Transporte MCP
MCP_TRANSPORT=stdio   # stdio ou sse
SSE_HOST=0.0.0.0      # Para modo SSE
SSE_PORT=8765

# Configurações de Cache
CACHE_BACKEND=lru     # lru ou redis
CACHE_MAX_SIZE_MB=512 # Tamanho do cache LRU (auto se não definido)
CACHE_TTL=3600        # TTL do cache em segundos
```

#### Configuração do Cliente MCP

**Claude Code (Windows + WSL2)**

`%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kb-rag": {
      "command": "wsl.exe",
      "args": [
        "-d", "Ubuntu-24.04",
        "--",
        "/home/SEU_USUARIO/kb-rag-mcp/.venv/bin/python",
        "/home/SEU_USUARIO/kb-rag-mcp/server/server.py"
      ]
    }
  }
}
```

**Claude Code (modo SSE)**

```json
{
  "mcpServers": {
    "kb-rag": {
      "url": "http://192.168.1.200:8765/sse"
    }
  }
}
```

---

### 📖 Uso

#### Ingestão de Documentos

```bash
source .venv/bin/activate

# Ingere diretório inteiro (incremental)
python ingest/ingest.py --docs /caminho/para/docs

# Com produto explícito
python ingest/ingest.py --docs /caminho/para/docs --product MeuProduto

# Arquivo único
python ingest/ingest.py --file /caminho/para/documento.pdf

# Limpa e reingere tudo
python ingest/ingest.py --docs /caminho/para/docs --clean

# Mais workers (use com GPU)
python ingest/ingest.py --docs /caminho/para/docs --workers 4

# Verifica status da ingestão
python ingest/ingest.py --status
python ingest/ingest.py --status --list    # Lista todos os arquivos
python ingest/ingest.py --status --errors  # Somente erros
```

#### Estrutura de Diretórios Recomendada

```
docs/
├── produto-a/
│   ├── referencia-api.pdf
│   ├── primeiros-passos.docx
│   └── exemplos/
│       └── exemplo.py
├── produto-b/
│   ├── manual.pdf
│   └── config.xlsx
└── geral/
    └── arquitetura.pptx
```

O produto é automaticamente inferido pelo nome do diretório.

---

### 🔧 Ferramentas MCP

#### `search_kb`

Busca semântica na base de conhecimento.

**Parâmetros:**
- `query` (obrigatório): Consulta de busca
- `top_k` (opcional): Número de resultados (1-20, padrão: 5)
- `product` (opcional): Filtrar por produto
- `doc_type` (opcional): Filtrar por tipo de documento
- `filter_type` (opcional): Filtrar por formato de arquivo (pdf, docx, xlsx, pptx, txt, code)

**Retorna:** Lista de chunks com `chunk_id`, `score`, `text`, `source_file`,
`product`, `doc_type`, `file_type`, `page`.

#### `list_documents`

Lista documentos indexados com filtros opcionais.

**Parâmetros:**
- `product` (opcional): Filtrar por produto
- `doc_type` (opcional): Filtrar por tipo de documento
- `filter_type` (opcional): Filtrar por formato de arquivo

**Retorna:** Documentos agrupados por `doc_type`.

#### `get_chunk`

Recupera chunk completo com contexto ao redor.

**Parâmetros:**
- `chunk_id` (obrigatório): ID do chunk dos resultados de busca
- `context_window` (opcional): Número de chunks vizinhos (0-3, padrão: 1)

**Retorna:** Chunk com contexto.

#### `kb_stats`

Estatísticas da base de conhecimento.

**Retorna:** Total de documentos, chunks, breakdown por doc_type e formato de arquivo.

---

### 🏗️ Arquitetura

```
Documentos (PDF, DOCX, XLSX, PPTX, TXT, código)
    ↓  ingest/ingest.py
Extração de Texto → Chunking → Embedding (LM Studio / Ollama)
    ↓
Qdrant (vector store)
    ↓
server/server.py ←→ MCP (stdio ou SSE)
    ↓
Claude Code / OpenCode
```

**Componentes:**

- **Gerenciamento de Jobs** (FASE 2): Fila de jobs baseada em SQLite com agendamento por prioridade
- **Pool de Workers** (FASE 3): Pool de workers assíncronos com limitação de taxa
- **Observabilidade** (FASE 4): Métricas Prometheus, logging estruturado, rastreamento de progresso
- **Sistema de Cache** (FASE 5): Cache LRU com auto-ajuste de RAM ou backend Redis
- **Extratores de Documentos**: Suporte multi-formato (PDF via PyMuPDF/docling)
- **Classificador**: Detecção automática de produto e doc_type via regex

---

### 📚 Documentação

- [TESTING.md](docs/TESTING.md) - Estratégia de testes
- [FASE1_COMPLETION.md](docs/FASE1_COMPLETION.md) - Fundação e infraestrutura de testes
- [FASE2_COMPLETION.md](docs/FASE2_COMPLETION.md) - Sistema de gerenciamento de jobs
- [FASE3_COMPLETION.md](docs/FASE3_COMPLETION.md) - Pool de workers e limitador de taxa
- [FASE4_COMPLETION.md](docs/FASE4_COMPLETION.md) - Observabilidade e métricas
- [FASE5_COMPLETION.md](docs/FASE5_COMPLETION.md) - Sistema de cache
- [INSTRUCTIONS.md](docs/INSTRUCTIONS.md) - Instruções técnicas detalhadas
- [PLAN.md](docs/PLAN.md) - Roadmap de implementação

---

### 🛠️ Solução de Problemas

**API de embedding não responde:**
```bash
# Verifique se o LM Studio está rodando e o modelo carregado
curl http://localhost:1234/v1/models

# Verifique o Ollama
curl http://localhost:11434/api/tags
```

**Erro de conexão com Qdrant:**
```bash
# Verifique se o Qdrant está rodando
docker ps | grep qdrant
curl http://localhost:6333/healthz
```

**Sem resultados de busca:**
- Verifique `SCORE_THRESHOLD` (diminua se muito rigoroso)
- Verifique se documentos estão indexados: `python ingest/ingest.py --status`
- Verifique se a consulta está no idioma correto

**Ingestão lenta:**
- Reduza `--workers` se limitado por CPU
- Verifique se a API de embedding não está sobrecarregada
- Considere usar GPU para LM Studio

---

### 📝 Licença

[Sua Licença Aqui]

---

### 🤝 Contribuindo

Contribuições são bem-vindas! Por favor, leia [CONTRIBUTING.md](CONTRIBUTING.md) primeiro.
