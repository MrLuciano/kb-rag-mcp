# KB RAG MCP Server

**Servidor MCP para busca semântica em bases de conhecimento locais**

[🇬🇧 English Version](README.md#english) | **🇧🇷 Versão em Português**

---

## 📖 Sobre

Servidor MCP (Model Context Protocol) pronto para produção que permite busca semântica em bases de conhecimento locais (~7 GB+). Suporta múltiplos formatos de documentos e é compatível com Claude Code, OpenCode e qualquer cliente MCP.

### ✨ Funcionalidades Principais

- 🔍 **Busca Semântica**: Recuperação de documentos por similaridade vetorial
- 📚 **Multi-formato**: PDF, DOCX, XLSX, PPTX, TXT, Markdown, código-fonte
- 🎯 **Classificação Automática**: Detecta produto e tipo de documento via regex
- 🚀 **Pronto para Produção**: Gerenciamento de jobs, pool de workers, observabilidade
- 💾 **Ingestão Incremental**: Processa apenas arquivos novos/modificados (SHA256)
- 📊 **Métricas Prometheus**: 20+ métricas para monitoramento completo
- 🔄 **Cache Inteligente**: LRU com auto-ajuste de RAM ou Redis distribuído
- 🔧 **Multi-backend**: LM Studio (GPU), Ollama, ou APIs compatíveis com OpenAI

---

## 🚀 Início Rápido

### Local Machine (Windows + WSL2 + LM Studio)

```bash
# 1. Inicie o LM Studio no Windows com o modelo nomic-embed-text-v1.5
# 2. No WSL2:
git clone https://github.com/seususername/kb-rag-mcp ~/kb-rag-mcp
cd ~/kb-rag-mcp
bash scripts/setup.sh local

# 3. Ingira seus documentos
source .venv/bin/activate
python ingest/ingest.py --docs /mnt/d/seus-documentos

# 4. Verifique a saúde do sistema
python scripts/health_check.py

# 5. Configure o Claude Code
# Copie o bloco "local" de config/mcp-clients.json para:
# %APPDATA%\Claude\claude_desktop_config.json
```

### Servidor Linux (Ollama)

```bash
# Ubuntu 24.04 ou similar:
git clone https://github.com/seususername/kb-rag-mcp /opt/kb-rag-mcp
cd /opt/kb-rag-mcp
bash scripts/setup.sh lxc

# Ingira documentos com 4 workers
source .venv/bin/activate
python ingest/ingest.py --docs /opt/documentos --workers 4

# Instale como serviço systemd
sudo cp scripts/kb-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now kb-mcp
```

---

## 📦 Instalação Detalhada

### Pré-requisitos

- **Python 3.11+**
- **Docker** (para Qdrant) ou Qdrant embedded
- **LM Studio** / **Ollama** / API de embedding compatível com OpenAI
- **8+ GB RAM** (16+ GB recomendado para performance)
- **30+ GB disco** para vector store e dados

### Passo a Passo

#### 1. Clone o Repositório

```bash
git clone https://github.com/seususername/kb-rag-mcp
cd kb-rag-mcp
```

#### 2. Execute o Setup

```bash
# Local machine (LM Studio com GPU):
bash scripts/setup.sh local

# Servidor Linux (Ollama CPU):
bash scripts/setup.sh lxc

# Setup manual:
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 3. Configure o Ambiente

```bash
# Copie o template apropriado
cp config/.env.local .env     # ou .env.lxc

# Edite com suas configurações
vim .env
```

**Variáveis principais:**

```bash
# Backend de embedding
EMBED_BACKEND=openai-compat    # lmstudio-sdk, openai-compat, ollama
EMBED_MODEL=text-embedding-nomic-embed-text-v1.5-embedding
LMS_BASE_URL=http://<LM_STUDIO_HOST>:1234   # URL do LM Studio (sem /v1)

# Vector store
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=kb_docs

# Cache
CACHE_BACKEND=lru              # lru ou redis
CACHE_MAX_SIZE_MB=512          # Tamanho do cache (auto se vazio)
CACHE_TTL=3600                 # TTL em segundos

# Busca
SCORE_THRESHOLD=0.35           # Relevância mínima (0.0-1.0)
DEFAULT_TOP_K=5                # Resultados padrão
```

#### 4. Inicie o Qdrant

```bash
docker-compose up -d
```

#### 5. Verifique a Instalação

```bash
source .venv/bin/activate
python scripts/health_check.py
```

Saída esperada:
```
✓ Qdrant: OK (connected to localhost:6333)
✓ Embedding API: OK (768 dims via openai-compat)
✓ Collection: kb_docs exists (12,453 vectors)
```

---

## ⚙️ Configuração do Cliente MCP

### Claude Code (Windows + WSL2)

Edite `%APPDATA%\Claude\claude_desktop_config.json`:

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

### Claude Code (Modo SSE - Servidor Remoto)

```json
{
  "mcpServers": {
    "kb-rag": {
      "url": "http://<LXC_SERVER_HOST>:8765/sse"
    }
  }
}
```

### OpenCode

Edite `~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "kb-rag": {
      "type": "local",
      "command": [
        "/home/SEU_USUARIO/kb-rag-mcp/.venv/bin/python",
        "/home/SEU_USUARIO/kb-rag-mcp/server/server.py"
      ]
    }
  }
}
```

---

## 📖 Uso Básico

### Ingestão de Documentos

```bash
source .venv/bin/activate

# Ingestão incremental de diretório inteiro
python ingest/ingest.py --docs /caminho/para/documentos

# Com produto explícito (sobrescreve detecção automática)
python ingest/ingest.py --docs /caminho/docs --product MeuProduto

# Arquivo único
python ingest/ingest.py --file /caminho/documento.pdf

# Limpar e reingerir tudo do zero
python ingest/ingest.py --docs /caminho/docs --clean

# Processar com 4 workers (requer GPU ou CPU potente)
python ingest/ingest.py --docs /caminho/docs --workers 4
```

### Verificar Status da Ingestão

```bash
# Resumo geral
python ingest/ingest.py --status

# Lista todos os arquivos
python ingest/ingest.py --status --list

# Apenas arquivos com erro
python ingest/ingest.py --status --errors
```

### Estrutura de Pastas Recomendada

```
documentos/
├── produto-a/
│   ├── referencia-api.pdf
│   ├── guia-instalacao.docx
│   └── exemplos/
│       └── codigo-exemplo.py
├── produto-b/
│   ├── manual-usuario.pdf
│   └── planilha-config.xlsx
└── geral/
    └── apresentacao-arquitetura.pptx
```

O **produto** é inferido automaticamente pelo nome da pasta raiz. O **tipo de documento** (doc_type) é classificado por regex no nome do arquivo.

---

## 🔧 Ferramentas MCP Disponíveis

O servidor expõe 4 ferramentas via protocolo MCP:

### 1. `search_kb` — Busca Semântica

Busca chunks de documentos por similaridade vetorial.

**Parâmetros:**
- `query` (string, obrigatório): Pergunta ou termo de busca
- `top_k` (int, opcional): Número de resultados (1-20, padrão: 5)
- `product` (string, opcional): Filtrar por produto específico
- `doc_type` (string, opcional): Filtrar por tipo de documento
- `filter_type` (string, opcional): Filtrar por formato (pdf, docx, xlsx, pptx, txt, code)

**Retorno:**
```json
{
  "results": [
    {
      "chunk_id": "abc123",
      "score": 0.87,
      "text": "Texto do chunk...",
      "source_file": "docs/produto-a/api.pdf",
      "product": "produto-a",
      "doc_type": "api_guide",
      "file_type": "pdf",
      "page": 42
    }
  ]
}
```

### 2. `list_documents` — Listar Documentos

Lista todos os documentos indexados com filtros opcionais.

**Parâmetros:** Mesmos filtros de `search_kb` (exceto `query` e `top_k`)

**Retorno:** Documentos agrupados por `doc_type`

### 3. `get_chunk` — Obter Chunk com Contexto

Recupera um chunk completo com chunks vizinhos para contexto adicional.

**Parâmetros:**
- `chunk_id` (string, obrigatório): ID retornado por `search_kb`
- `context_window` (int, opcional): Número de chunks vizinhos (0-3, padrão: 1)

### 4. `kb_stats` — Estatísticas da KB

Retorna estatísticas gerais da base de conhecimento.

**Retorno:**
```json
{
  "total_documents": 1234,
  "total_chunks": 45678,
  "by_doc_type": { "api_guide": 234, "user_guide": 189, ... },
  "by_file_type": { "pdf": 789, "docx": 345, ... }
}
```

---

## 🏗️ Arquitetura

### Fluxo de Dados

```
Documentos (PDF, DOCX, XLSX, PPTX, TXT, código)
    │
    ├─► Extração de Texto (PyMuPDF, docling, python-docx, etc)
    │
    ├─► Chunking (RecursiveCharacterTextSplitter)
    │   └─► Tamanho variável por tipo: PDF=800, DOCX=700, CODE=400
    │
    ├─► Classificação (ingest/classifier.py)
    │   └─► Detecção automática de product + doc_type via regex
    │
    ├─► Embedding API (LM Studio / Ollama)
    │   └─► Vetores de 768 dims (nomic-embed-text-v1.5)
    │
    ├─► Cache (LRU com auto-tune de RAM ou Redis)
    │   └─► Evita chamadas repetidas à API de embedding
    │
    └─► Qdrant (vector store)
        └─► Indexação com payload: {product, doc_type, file_type, page, ...}

↓

MCP Server (server/server.py)
    │
    ├─► Transport: stdio (Claude Code local) ou SSE (remoto)
    │
    └─► Tools: search_kb, list_documents, get_chunk, kb_stats

↓

Claude Code / OpenCode
```

### Componentes Principais

| Componente | Descrição | Localização |
|------------|-----------|-------------|
| **Job System** (FASE 2) | Fila de jobs SQLite com prioridades | `ingest/job/` |
| **Worker Pool** (FASE 3) | Pool assíncrono com rate limiting | `ingest/worker/` |
| **Observability** (FASE 4) | Métricas, logging, progress tracking | `observability/` |
| **Cache System** (FASE 5) | LRU/Redis com auto-tune de RAM | `server/cache/` |
| **Extractors** | Extração multi-formato | `ingest/ingest.py` |
| **Classifier** | Detecção product/doc_type | `ingest/classifier.py` |
| **Registry** | Controle de estado (SQLite) | `ingest/registry.py` |
| **Embed Client** | Abstração multi-backend | `server/embed_client.py` |
| **Vector Store** | Wrapper do Qdrant | `server/vector_store.py` |

---

## 📊 Métricas e Monitoramento

### Métricas Prometheus

Disponíveis no endpoint `/metrics` (quando habilitado):

#### Jobs
- `kb_ingest_jobs_created_total` (por prioridade)
- `kb_ingest_jobs_completed_total` (por status: completed/failed/cancelled)
- `kb_ingest_jobs_active` (por status: pending/running/paused)
- `kb_ingest_job_duration_seconds` (histograma)

#### Arquivos
- `kb_ingest_files_processed_total` (por status: ok/skipped/error)
- `kb_ingest_file_processing_seconds` (histograma)
- `kb_ingest_chunks_generated_total` (por product e doc_type)

#### Workers
- `kb_ingest_worker_pool_size`
- `kb_ingest_worker_pool_queue_size`
- `kb_ingest_worker_pool_utilization`

#### Cache
- `kb_rag_cache_hits_total` / `kb_rag_cache_misses_total` (por backend)
- `kb_rag_cache_evictions_total` (por backend e motivo)
- `kb_rag_cache_size_bytes` / `kb_rag_cache_entries`

#### API
- `kb_ingest_api_requests_total` (por endpoint e status)
- `kb_ingest_api_latency_seconds` (histograma por endpoint)

### Queries Úteis (Prometheus)

**Taxa de hit do cache:**
```promql
rate(kb_rag_cache_hits_total[5m]) /
(rate(kb_rag_cache_hits_total[5m]) + rate(kb_rag_cache_misses_total[5m]))
```

**Latência P95 de busca:**
```promql
histogram_quantile(0.95, rate(kb_ingest_api_latency_seconds_bucket[5m]))
```

**Utilização do pool de workers:**
```promql
kb_ingest_worker_pool_utilization
```

---

## 🛠️ Solução de Problemas

### API de Embedding Não Responde

```bash
# Verifique se o LM Studio está rodando e modelo carregado
curl http://localhost:1234/v1/models

# Ou Ollama
curl http://localhost:11434/api/tags
```

**Causa comum:** IP incorreto. No WSL2, use o IP da máquina Windows na rede local, não `localhost`.

### Erro de Conexão com Qdrant

```bash
# Verifique se o container está rodando
docker ps | grep qdrant

# Health check
curl http://localhost:6333/healthz

# Se não estiver rodando:
docker-compose up -d
```

### Busca Não Retorna Resultados

1. **Verifique o threshold:** `SCORE_THRESHOLD=0.35` pode ser muito rigoroso. Tente `0.25`.
2. **Confirme documentos indexados:**
   ```bash
   python ingest/ingest.py --status
   ```
3. **Idioma da consulta:** Embeddings são sensíveis ao idioma. Use português se os docs são em português.

### Ingestão Muito Lenta

1. **Reduza workers se CPU-bound:**
   ```bash
   python ingest/ingest.py --docs /caminho --workers 1
   ```
2. **Verifique sobrecarga da API de embedding:** LM Studio em CPU pode levar 200-500ms por chunk.
3. **Use GPU se disponível:** LM Studio com GPU reduz latência para ~50ms.

### Cache Não Funciona

1. **Verifique inicialização:**
   ```python
   from server.embed_client import init_cache, get_cache_stats
   from observability.metrics import MetricsCollector
   from server.cache import CacheManager
   
   metrics = MetricsCollector()
   cache = CacheManager(backend="lru", metrics=metrics)
   init_cache(cache, metrics)
   
   print(get_cache_stats())
   ```

2. **Verifique métricas:**
   ```bash
   curl http://localhost:9090/metrics | grep cache
   ```

---

## 👨‍💻 Desenvolvimento

### Executando Testes

```bash
# Todos os testes
pytest tests/ -v

# Com cobertura
pytest tests/ --cov=ingest --cov=server --cov=observability

# Testes específicos
pytest tests/test_job_system.py -v
pytest tests/test_worker_system.py::test_rate_limiter_basic -v
```

**Status atual:** 59 testes passando

### Qualidade de Código

```bash
# Formatar código
black ingest/ server/ scripts/ tests/
isort ingest/ server/ scripts/ tests/

# Linter
flake8 ingest/ server/ scripts/ tests/

# Type checking
mypy ingest/ server/ scripts/
```

**Configurações:**
- **Linha máxima:** 79 caracteres (PEP 8 strict)
- **Black profile:** black
- **isort profile:** black (compatível)

### Adicionar Dependências

```bash
# Edite requirements.in
vim requirements.in

# Compile e instale
pip-compile requirements.in
pip-sync requirements.txt
```

**Workflow pip-tools:**
1. Edite `requirements.in` (dependências top-level)
2. `pip-compile` gera `requirements.txt` (com todas as transições pinadas)
3. `pip-sync` instala exatamente o que está em `requirements.txt`

---

## 📚 Documentação Completa

### Guias de Implementação (FASE Reports)

- [FASE1_COMPLETION.md](docs/FASE1_COMPLETION.md) — Fundação e infraestrutura de testes
- [FASE2_COMPLETION.md](docs/FASE2_COMPLETION.md) — Sistema de gerenciamento de jobs
- [FASE3_COMPLETION.md](docs/FASE3_COMPLETION.md) — Pool de workers e rate limiter
- [FASE4_COMPLETION.md](docs/FASE4_COMPLETION.md) — Observabilidade e métricas
- [FASE5_COMPLETION.md](docs/FASE5_COMPLETION.md) — Sistema de cache

### Referência Técnica

- [TESTING.md](docs/TESTING.md) — Estratégia de testes e guias de contribuição
- [HYGIENE_STATUS.md](docs/HYGIENE_STATUS.md) — Status de qualidade do código
- [PLAN.md](docs/PLAN.md) — Roadmap completo de implementação (12 fases)
- [INSTRUCTIONS.md](docs/INSTRUCTIONS.md) — Instruções detalhadas do projeto

---

## 📊 Requisitos de Sistema

| Cenário | CPU | RAM | Disco | GPU |
|---------|-----|-----|-------|-----|
| **Local Machine** (local CPU + LM Studio) | 8 cores | 32 GB | 30 GB | iGPU |
| **Servidor** (Ollama CPU-only) | 6 vCPU | 8-12 GB | 30 GB | Não |
| **Produção** (Alta demanda) | 16 cores | 64 GB | 100 GB | NVIDIA RTX |

**Estimativas de Ingestão:**
- ~7 GB de documentos PDF/DOCX
- ~12.000 documentos
- ~45.000 chunks
- Tempo de ingestão:
  - GPU (LM Studio): 2-3 horas
  - CPU (Ollama): 6-10 horas

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Leia [CONTRIBUTING.md](CONTRIBUTING.md) (se disponível)
2. Siga os padrões de código (black, isort, flake8)
3. Adicione testes para novas funcionalidades
4. Atualize a documentação conforme necessário

---

## 📝 Licença

[Defina sua licença aqui]

---

## 🔗 Links Úteis

- [Documentação do MCP](https://modelcontextprotocol.io)
- [LM Studio](https://lmstudio.ai)
- [Ollama](https://ollama.ai)
- [Qdrant](https://qdrant.tech)
- [Claude Code](https://claude.ai)
- [OpenCode](https://opencode.ai)

---

**Última atualização:** 2026-05-15  
**Versão:** 2.0 (FASE 1-5 completas)
