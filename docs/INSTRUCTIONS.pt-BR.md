# KB RAG MCP Server — Instruções do Projeto (Português)

> Documento de referência técnica completa para desenvolvimento e manutenção do projeto.
> Descreve arquitetura, decisões técnicas, contratos de interface e guias de desenvolvimento.

**[🇬🇧 English Version](INSTRUCTIONS.md) | 🇧🇷 Versão em Português**

---

## 📑 Índice

1. [Visão Geral](#visão-geral)
2. [Ambientes de Execução](#ambientes-de-execução)
3. [Estrutura de Arquivos](#estrutura-de-arquivos)
4. [Variáveis de Ambiente](#variáveis-de-ambiente)
5. [Ferramentas MCP](#ferramentas-mcp)
6. [Taxonomia de Conteúdo](#taxonomia-de-conteúdo)
7. [Pipeline de Ingestão](#pipeline-de-ingestão)
8. [Sistema de Jobs (PHASE 2)](#sistema-de-jobs-PHASE-2)
9. [Pool de Workers (PHASE 3)](#pool-de-workers-PHASE-3)
10. [Observabilidade (PHASE 4)](#observabilidade-PHASE-4)
11. [Sistema de Cache (PHASE 5)](#sistema-de-cache-PHASE-5)
12. [Configuração de Clientes MCP](#configuração-de-clientes-mcp)
13. [Dependências](#dependências)
14. [Decisões Técnicas](#decisões-técnicas)
15. [Melhorias Planejadas](#melhorias-planejadas)
16. [Comandos de Operação](#comandos-de-operação)
17. [Contexto de Negócio](#contexto-de-negócio)

---

## 1. Visão Geral

Servidor MCP (Model Context Protocol) que expõe busca semântica sobre base de conhecimento local
de documentação técnica e manuais de produtos.

O servidor é consumido por **Claude Code** e **OpenCode** via protocolo MCP, permitindo que LLMs
recuperem automaticamente trechos relevantes de documentação durante tarefas de desenvolvimento.

### Fluxo de Dados Completo

\`\`\`
Documentos locais (PDF, DOCX, XLSX, PPTX, TXT, código)
    │
    ▼ ingest/ingest.py
Extração de texto → Chunking → Classificação (product/doc_type)
    │
    ▼ Job System (PHASE 2) → Worker Pool (PHASE 3)
Embedding (LM Studio / Ollama) + Cache (PHASE 5)
    │
    ▼
Qdrant (vector store local)
    │
    ▼ server/server.py [protocolo MCP]
Claude Code / OpenCode
    │
    ▼ Observability (PHASE 4)
Métricas Prometheus + Logging Estruturado
\`\`\`

---

## 2. Ambientes de Execução

### Local Machine (Primary)

- **Hardware:** Local machine with GPU or iGPU
- **OS:** Windows 11 Pro
- **Embedding:** LM Studio no Windows com aceleração Vulkan
- **Servidor MCP:** Python no WSL2 (Ubuntu 24.04)
- **Vector Store:** Qdrant em Docker no WSL2
- **Acesso:** LM Studio via `http://<LM_STUDIO_HOST>:1234` (IP fixo LAN)
- **Transport:** stdio via `wsl.exe` invocado pelo Claude Code no Windows

### LXC Server (Secondary / Always-On)

- **Hardware:** LXC Ubuntu 24.04, 6 vCPU, 8-12 GB RAM, CPU only
- **Embedding:** Ollama local (`nomic-embed-text`)
- **Transport:** SSE em `http://<ip-lxc>:8765/sse`
- **Serviço:** systemd (`kb-mcp.service`)

---

## 3. Estrutura de Arquivos

```
kb-rag-mcp/
├── kb_server/
│   ├── server.py          # Entrypoint MCP — registra tools, roteia chamadas
│   ├── embed_client.py    # Abstração multi-backend de embedding
│   ├── vector_store.py    # Wrapper do Qdrant (search, upsert, list, stats)
│   ├── collections/       # Roteamento multi-coleção (PHASE 15)
│   │   ├── manager.py     # CollectionManager — CRUD de coleções Qdrant
│   │   └── router.py      # CollectionRouter — resolve/ensure por parâmetro
│   ├── auth.py            # Autenticação opcional via Bearer token (PHASE 32)
│   ├── auth_registry.py   # Registry de chaves SHA-256 (PHASE 32)
│   ├── rate_limiter.py    # Rate limiting por assunto (PHASE 33)
│   ├── circuit_breaker.py # State machine CLOSED/OPEN/HALF_OPEN (PHASE 36)
│   ├── provider_budget.py # Orçamento por provider com sliding window (PHASE 36)
│   ├── prompts.py         # Templates de prompt MCP (PHASE 31)
│   ├── cache/             # Sistema de cache (LRU + Redis opcional)
│   │   ├── lru.py         # Cache LRU com auto-tune de RAM
│   │   ├── redis.py       # Backend Redis opcional
│   │   ├── manager.py     # Interface unificada
│   │   └── request_cache.py # Cache de busca em nível de requisição (PHASE 37)
│   ├── retrieval/         # Busca híbrida (BM25+dense RRF) + reranker
│   ├── ui/                # Web UI FastAPI+HTMX
│   └── telemetry/         # Query logger SQLite (90 dias de retenção)
├── ingest/
│   ├── ingest.py          # Pipeline de ingestão — CLI principal
│   ├── classifier.py      # Classificação product/doc_type via regex
│   ├── registry.py        # Controle de estado (SQLite)
│   ├── parsers/
│   │   ├── legacy_office.py  # .doc, .xls, .ppt, .odt, .ods, .odp, .wpd
│   │   └── zip_handler.py    # Extração recursiva de arquivos ZIP
│   ├── connectors/        # Conectores empresariais (PHASE 29)
│   │   ├── factory.py     # Registry + create_connector
│   │   ├── base.py        # ConnectorBase ABC
│   │   ├── confluence.py  # Conector Confluence (Cloud + Server/DC)
│   │   ├── jira.py        # Conector JIRA (Cloud + Data Center)
│   │   ├── git.py         # Conector Git (clone/pull, incremental)
│   │   └── staging.py     # Stage de documentos remotos
│   ├── graph_builder.py   # Metadados de grafo de conhecimento (PHASE 30)
│   ├── core/
│   │   └── metadata.py    # Schema v4 (jobs, job_progress, files, quotas)
│   ├── job/               # Sistema de jobs SQLite com prioridades
│   │   ├── models.py      # Dataclasses Job/JobStatus/JobPriority
│   │   ├── manager.py     # JobManager (CRUD + lifecycle)
│   │   └── scheduler.py   # Scheduler com prioridades
│   └── worker/            # Pool async + rate limiter token bucket
│       ├── limiter.py     # Rate limiter (token bucket)
│       ├── worker.py      # FileWorker com retry logic
│       ├── pool.py        # WorkerPool assíncrono
│       └── executor.py    # JobExecutor (scheduler + workers)
├── observability/
│   ├── logging.py         # Logging estruturado (JSON)
│   ├── metrics.py         # 28 métricas Prometheus (kb_* prefix)
│   └── progress.py        # Progress tracking com ETA
├── qa/
│   ├── run_qa.py          # Pipeline de avaliação QA
│   ├── metrics.py         # Hit rate, MRR, p50_score
│   └── queries.json       # Dataset de queries para avaliação
├── config/
│   ├── .env.local         # Variáveis para local machine
│   ├── .env.lxc           # Variáveis para LXC Server
│   └── mcp-clients.json   # Configs para Claude Code e OpenCode
├── scripts/
│   ├── migrate/           # Ferramentas de migração (PHASE 1.5)
│   │   ├── export.py      # Exporta snapshot Qdrant + env sanitizado
│   │   ├── import_.py     # Importa com validação SHA256
│   │   └── validate.py    # Valida manifesto SHA256
│   ├── kb-migrate.sh      # Wrapper shell: export/import/validate
│   ├── setup.sh           # Instalação de dependências por perfil
│   ├── health_check.py    # Testa embedding + Qdrant + busca E2E
│   └── start-kb-rag.ps1   # Autostart WSL2 no Windows
├── deployment/
│   ├── systemd/           # Units systemd para bare-metal
│   ├── config/
│   │   ├── grafana-dashboard.json       # Dashboard Grafana 18 painéis
│   │   └── grafana-provisioning/        # Datasource + dashboard YAML
│   └── helm/kb-rag-mcp/  # Helm chart Kubernetes (PHASE 15)
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/     # Deployment, StatefulSet, HPA, Services, ConfigMap
├── tests/
│   ├── conftest.py        # Fixtures pytest
│   ├── test_legacy_parsers.py # Formatos legados (.doc, .xls, .odt, ...)
│   ├── test_zip_handler.py    # Extração ZIP (profundidade, tamanho)
│   └── e2e/               # Testes end-to-end
├── docs/
│   ├── REFERENCE.md       # Referência técnica principal
│   ├── LEGACY_FORMATS.md  # Formatos legados e regras ZIP
│   ├── PLAN.md            # Roadmap de 16+ PHASEs
│   └── INSTRUCTIONS.pt-BR.md  # Este documento
├── data/
│   └── kb_metadata.db     # SQLite v2 (jobs + files)
├── docker-compose.yml     # Qdrant
├── requirements.in        # Dependências top-level
├── requirements.txt       # Dependências pinadas (pip-compile)
├── pyproject.toml         # Config black/isort/mypy/pytest
└── .env                   # Config ativa (cópia de .env.local ou .env.lxc)
```

---

## 4. Variáveis de Ambiente

Todas lidas via `.env` na raiz. O `load_dotenv` é chamado **antes de qualquer import**
que leia `os.getenv()` — padrão crítico mantido em todos os entrypoints.

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `EMBED_BACKEND` | `openai-compat` | Backend: `lmstudio-sdk`, `lmstudio-rest`, `openai-compat`, `ollama` |
| `EMBED_MODEL` | `text-embedding-nomic-embed-text-v1.5-embedding` | Nome exato do modelo |
| `LMS_BASE_URL` | `http://localhost:1234` | URL do LM Studio **sem** `/v1` ou `/api/v0` |
| `OLLAMA_HOST` | `http://localhost:11434` | URL do Ollama |
| `QDRANT_HOST` | `localhost` | Host do Qdrant |
| `QDRANT_PORT` | `6333` | Porta REST do Qdrant |
| `QDRANT_PATH` | _(vazio)_ | Se definido, usa Qdrant embedded (sem Docker) |
| `QDRANT_COLLECTION` | `kb_docs` | Nome da coleção |
| `SCORE_THRESHOLD` | `0.35` | Score mínimo de relevância (0.0-1.0) |
| `DEFAULT_TOP_K` | `5` | Resultados padrão por busca |
| `MCP_TRANSPORT` | `stdio` | `stdio` (local) ou `sse` (remoto) |
| `SSE_HOST` | `0.0.0.0` | Bind address para SSE |
| `SSE_PORT` | `8765` | Porta para SSE |
| `CACHE_BACKEND` | `lru` | Cache: `lru` ou `redis` |
| `CACHE_MAX_SIZE_MB` | `512` | Tamanho do cache LRU (auto se vazio) |
| `CACHE_TTL` | `3600` | TTL do cache em segundos |
| `LOG_PATH` | `/tmp/kb-mcp.log` | Caminho do arquivo de log |
| `REGISTRY_DB` | `data/registry.db` | SQLite v1 (legado) |
| `METADATA_DB` | `data/kb_metadata.db` | SQLite v2 (jobs + files) |
| `AUTH_ENABLED` | `false` | Habilita autenticação Bearer token no SSE (PHASE 32) |
| `AUTH_DB_PATH` | `data/auth.db` | Caminho do SQLite de chaves de API |
| `RATE_LIMIT_ENABLED` | `false` | Habilita rate limiting por assunto (PHASE 33) |
| `RATE_LIMIT_REQUESTS` | `100` | Máx. requisições por janela de tempo |
| `RATE_LIMIT_WINDOW` | `60` | Janela de tempo em segundos |
| `CIRCUIT_BREAKER_THRESHOLD` | `5` | Falhas consecutivas antes de OPEN (PHASE 36) |
| `CIRCUIT_BREAKER_COOLDOWN` | `30` | Cooldown inicial em segundos |
| `RETRIEVAL_CACHE_TTL` | `300` | TTL do cache de busca em segundos (PHASE 37) |

### Normalização de URL (embed_client.py)

O código normaliza `LMS_BASE_URL` removendo path final:

\`\`\`python
LMS_BASE_URL = re.sub(r"/(api/v\d+|v\d+)/?$", "", raw_url).rstrip("/")
# "http://<LM_STUDIO_HOST>:1234/api/v1" → "http://<LM_STUDIO_HOST>:1234"
\`\`\`

Cada backend adiciona o path correto:
- `openai-compat` → `{LMS_BASE_URL}/v1/embeddings`
- `lmstudio-rest` → `{LMS_BASE_URL}/api/v0/embeddings`
- `lmstudio-sdk` → WebSocket `ws://{LMS_HOST}:{LMS_PORT}`

---

## 5. Ferramentas MCP

### `search_kb` — Busca Semântica

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `query` | string | ✓ | Pergunta ou termo |
| `top_k` | integer | — | Resultados (1-20, padrão: 5) |
| `product` | string | — | Filtro de produto |
| `doc_type` | string | — | Filtro de tipo de documento |
| `filter_type` | string | — | Formato: `pdf`, `docx`, `xlsx`, `pptx`, `txt`, `code` |
| `version` | string | — | Filtro por versão do produto (PHASE 13) |
| `vendor` | string | — | Filtro por fornecedor (PHASE 11.1) |
| `subsystem` | string | — | Filtro por subsistema (PHASE 11.1) |
| `module` | string | — | Filtro por módulo (PHASE 17) |
| `hybrid` | boolean | — | Busca híbrida dense + BM25 sparse (PHASE 12) |
| `rerank` | boolean | — | Re-ranking com cross-encoder (PHASE 12) |
| `collection` | string | — | Coleção Qdrant alvo (PHASE 15) |
| `kb_ids` | string[] | — | Busca multi-KB agregada (PHASE 35) |

**Retorno:** Lista de chunks com `chunk_id`, `score`, `text`, `source_file`,
`product`, `doc_type`, `file_type`, `page`.

### `list_documents` — Listar Documentos

Lista documentos indexados. Aceita os mesmos filtros de `search_kb` exceto `query` e `top_k`.
Retorna documentos agrupados por `doc_type`.

### `get_chunk` — Obter Chunk com Contexto

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `chunk_id` | string | ✓ | ID retornado por `search_kb` |
| `context_window` | integer | — | Chunks vizinhos (0-3, padrão: 1) |

### `kb_stats` — Estatísticas

Estatísticas da KB: total de documentos, chunks, breakdown por `doc_type` e formato.

### `list_collections` — Listar Coleções (PHASE 15)

Lista todas as coleções Qdrant disponíveis.

### `list_filter_options` — Listar Opções de Filtro (PHASE 17)

Lista valores disponíveis para atributos (product, vendor, doc_type, etc.).

### `get_related_documents` — Documentos Relacionados (PHASE 30)

Retorna chunks de documentos relacionados por grafo de conhecimento.

### `explore_topic` — Explorar Tópico (PHASE 30)

Busca documentos por tópicos do grafo de conhecimento.

### Prompts MCP (PHASE 31)

- **`extract_answer`** — Prompt para extrair resposta fundamentada de resultados de busca
- **`summarize_documents`** — Prompt para resumir documentos com seções

---

## 6. Taxonomia de Conteúdo

Inferida automaticamente por `ingest/classifier.py` via regex no nome do arquivo.

| doc_type | Descrição | Padrões de Exemplo |
|----------|-----------|-------------------|
| `admin_guide` | Guias de administração | Administration Guide, ACN, AGD |
| `install_guide` | Guias de instalação | Installation Guide, IGW, IASW |
| `upgrade_guide` | Guias de upgrade | Upgrading, Migration |
| `config_guide` | Guias de configuração | Configuration Guide, CGD, Cookbook |
| `user_guide` | Guias de usuário | User Guide, UGD |
| `api_guide` | APIs/SDKs | Programming Guide, API, SDK |
| `release_notes` | Notas de release | Release Notes, What's New |
| `howto` | Tutoriais | How-to, Case Study, KB\d+ |
| `training` | Treinamentos | Training, VILT, Webinar |
| `overview` | Visão geral | Overview, Understanding |
| `standard` | Normas | ISO, 15489, LGPD |
| `reference` | Referência técnica | Technical Paper |
| `document` | Fallback genérico | Qualquer não classificado |

---

## 7. Pipeline de Ingestão

### Fluxo por Arquivo

\`\`\`
1. classifier.classify(file_path) → {product, doc_type}
2. registry.needs_ingest(file_path) → (bool, reason)
   └─ SHA256 check: skip se idêntico e status=ok
3. EXTRACTOR[file_type](file_path) → [{text, page}]
4. chunk_text(text, file_type) → [chunks]
5. embed_client.get_embeddings_batch(chunks) → [vectors]
   └─ Cache check (PHASE 5): hit = skip API call
6. store.delete_document(source_file)
7. store.upsert_chunks(chunks + vectors + metadata)
8. registry.mark_ok(...) → salva SHA256 + timestamp + doc_type
\`\`\`

### Extratores por Tipo

| file_type | Extensões | Biblioteca | Fallback |
|-----------|-----------|------------|----------|
| `pdf` | .pdf | docling ^ | PyMuPDF (fitz) |

> ^ `docling` é opcional — requer instalação separada. Veja [Instalação do docling](#instalação-do-docling) abaixo.
| `docx` | .docx | python-docx | — |
| `doc` | .doc | docx2txt | python-docx |
| `xlsx` | .xlsx | openpyxl | — |
| `xls` | .xls | xlrd | — |
| `pptx` | .pptx | python-pptx | — |
| `ppt` | .ppt | python-pptx (best-effort) | — (falha com binary .ppt) |
| `odt` | .odt | odfpy | — |
| `ods` | .ods | odfpy | — |
| `odp` | .odp | odfpy | — |
| `wpd` | .wpd | heuristic latin-1 | — (qualidade baixa) |
| `txt` | .txt, .md, .rst | built-in | — |
| `code` | .py .ts .js .java .go ... | built-in | — |
| `zip` | .zip | stdlib zipfile (recursivo) | — (máx 2 níveis, 500 MB/entry) |

Veja [LEGACY_FORMATS.md](LEGACY_FORMATS.md) para detalhes sobre formatos legados e extração ZIP.

**Conectores empresariais (PHASE 29):** Também é possível ingerir de fontes remotas como Confluence, JIRA e Git. Consulte [AUTO_INGESTION.md](AUTO_INGESTION.md) para configuração de conectores.

### Configurações de Chunking

| file_type | chunk_size | overlap |
|-----------|------------|---------|
| pdf | 800 | 100 |
| docx | 700 | 80 |
| xlsx | 500 | 50 |
| pptx | 600 | 80 |
| txt | 600 | 80 |
| code | 400 | 60 |

Implementado com `RecursiveCharacterTextSplitter` do LangChain.

---

## 8. Sistema de Jobs (PHASE 2)

### Schema v2 (ingest/core/metadata.py)

**Tabela `jobs`:**
\`\`\`sql
CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL,           -- pending | running | paused | completed | failed | cancelled
    priority INTEGER DEFAULT 5,     -- 1 (low) - 10 (high)
    max_retries INTEGER DEFAULT 3,
    created_at REAL NOT NULL,
    started_at REAL,
    completed_at REAL,
    error_msg TEXT,
    options TEXT                     -- JSON
);
\`\`\`

**Tabela `job_progress`:**
\`\`\`sql
CREATE TABLE job_progress (
    job_id TEXT PRIMARY KEY,
    total_files INTEGER DEFAULT 0,
    processed_files INTEGER DEFAULT 0,
    failed_files INTEGER DEFAULT 0,
    skipped_files INTEGER DEFAULT 0,
    current_file TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);
\`\`\`

**Tabela `files`:**
\`\`\`sql
CREATE TABLE files (
    path TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL,
    file_type TEXT,
    product TEXT,
    doc_type TEXT,
    chunks INTEGER,
    status TEXT,                    -- ok | error | deleted
    error_msg TEXT,
    indexed_at REAL,
    file_mtime REAL,
    file_size INTEGER
);
\`\`\`

### Componentes

**ingest/job/models.py:**
- `JobStatus` (enum): PENDING, RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED
- `JobPriority` (enum): LOW=1, NORMAL=5, HIGH=10
- `Job` (dataclass): job_id, name, status, priority, created_at, options, ...
- Lógica de transição de estado: `is_terminal()`, `can_pause()`, `can_resume()`

**ingest/job/manager.py:**
- `JobManager`: CRUD + lifecycle
- `create_job()`, `get_job()`, `list_jobs()`, `update_status()`
- `start_job()`, `complete_job()`, `fail_job()`, `cancel_job()`
- `pause_job()`, `resume_job()`, `update_progress()`

**ingest/job/scheduler.py:**
- `JobScheduler`: Agendamento com prioridades
- `get_next_job()`: Retorna job PENDING com maior prioridade
- `get_runnable_jobs()`: Lista jobs que podem ser executados
- `set_max_concurrent_jobs()`: Controle de concorrência
- `cancel_all_pending()`, `pause_all_running()`, `resume_all_paused()`

---

## 9. Pool de Workers (PHASE 3)

### Rate Limiter (ingest/worker/limiter.py)

**Token Bucket Algorithm:**
- `RateLimiter`: Async-safe com `asyncio.Lock`
- Configuração: `max_requests_per_minute` (padrão: 60)
- `acquire()`: Aguarda até token disponível
- `try_acquire()`: Non-blocking check
- Permite bursts, mantém taxa média

**MultiRateLimiter:**
- Gerencia múltiplos limiters (ex: `embedding_api`, `vector_store`)
- `acquire(limiter_name)`: Roteamento por nome

### Worker (ingest/worker/worker.py)

**FileWorker:**
- Processa um arquivo com retry logic
- `process_file(file_path, job_id)`: Main method
- Retry exponencial: 1s, 2s, 4s
- `WorkerStats`: Rastreia sucessos/falhas/skips
- Integração com rate limiter

### Worker Pool (ingest/worker/pool.py)

**WorkerPool:**
- Pool assíncrono com fila de tarefas
- `start()` / `stop()`: Lifecycle
- `submit_task()`: Adiciona tarefa à fila
- `get_result(task_id, timeout)`: Espera resultado
- `batch_submit()`: Submete múltiplas tarefas
- Graceful shutdown: aguarda tarefas em progresso

### Executor (ingest/worker/executor.py)

**JobExecutor:**
- Integra scheduler + worker pool
- `execute_job(job_id)`: Orquestra execução completa
- Pull jobs via `scheduler.get_next_job()`
- Distribui arquivos via `worker_pool.submit_task()`
- Atualiza progresso via `job_manager.update_progress()`

---

## 10. Observabilidade (PHASE 4)

### Logging Estruturado (observability/logging.py)

**StructuredFormatter:**
- Formato JSON para logs
- Campos: `timestamp`, `level`, `message`, `module`, `func`, extras

**ContextLogger:**
- Injeta contexto (job_id, worker_id, etc.)
- `with_context(job_id=...)`: Retorna logger com contexto
- Uso:
  \`\`\`python
  logger = ContextLogger(__name__)
  logger = logger.with_context(job_id="job-123")
  logger.info("Processing file", file="doc.pdf")
  # Output: {"timestamp": ..., "level": "INFO", "job_id": "job-123", ...}
  \`\`\`

### Métricas Prometheus (observability/metrics.py)

**28+ métricas (v1.4):**

**Jobs:**
- `kb_ingest_jobs_created_total` (Counter, labels: priority)
- `kb_ingest_jobs_completed_total` (Counter, labels: status)
- `kb_ingest_jobs_active` (Gauge, labels: status)
- `kb_ingest_job_duration_seconds` (Histogram)

**Files:**
- `kb_ingest_files_processed_total` (Counter, labels: status)
- `kb_ingest_file_processing_seconds` (Histogram)
- `kb_ingest_chunks_generated_total` (Counter, labels: product, doc_type)

**Workers:**
- `kb_ingest_worker_pool_size` (Gauge)
- `kb_ingest_worker_pool_queue_size` (Gauge)
- `kb_ingest_worker_pool_utilization` (Gauge)

**Rate Limiter:**
- `kb_ingest_rate_limiter_tokens` (Gauge, labels: limiter)
- `kb_ingest_rate_limiter_waits_total` (Counter, labels: limiter)
- `kb_ingest_rate_limiter_wait_seconds` (Histogram, labels: limiter)

**API:**
- `kb_ingest_api_requests_total` (Counter, labels: endpoint, status)
- `kb_ingest_api_latency_seconds` (Histogram, labels: endpoint)

**Cache (PHASE 5):**
- `kb_rag_cache_hits_total` / `kb_rag_cache_misses_total` (Counter, labels: backend)
- `kb_rag_cache_evictions_total` (Counter, labels: backend, reason)
- `kb_rag_cache_size_bytes` / `kb_rag_cache_entries` (Gauge, labels: backend)

**Provider Resilience (PHASE 36):**
- `kb_provider_requests_total{provider}` — Total de requisições por provider
- `kb_provider_errors_total{provider}` — Total de erros por provider
- `kb_provider_circuit_state{provider,state}` — Estado do circuit breaker (1=CLOSED, 2=OPEN, 3=HALF_OPEN)
- `kb_provider_fallbacks_total{from,to}` — Eventos de fallback entre providers
- `kb_provider_skipped_circuit_open_total{provider}` — Requisições ignoradas por OPEN
- `kb_provider_skipped_budget_exhausted_total{provider}` — Requisições ignoradas por orçamento esgotado
- `kb_provider_circuit_opened_total{provider}` — Transições para estado OPEN

**Retrieval Cache (PHASE 37):**
- `kb_retrieval_cache_hits_total` — Cache hit no cache de busca
- `kb_retrieval_cache_misses_total` — Cache miss no cache de busca

**MetricsCollector:**
- Container para todas as métricas
- Simplifica passagem para componentes
- Uso:
  \`\`\`python
  from observability.metrics import MetricsCollector
  metrics = MetricsCollector()
  metrics.jobs_created.labels(priority="high").inc()
  \`\`\`

### Progress Tracking (observability/progress.py)

**ProgressTracker:**
- Rastreamento de progresso individual
- ETA calculation baseado em taxa de processamento
- `update(processed, total)`: Atualiza estado
- `get_progress()`: Retorna dict com % e ETA

**BatchProgressTracker:**
- Rastreamento de múltiplos jobs
- Rich terminal UI (barra de progresso colorida)
- Atualização em tempo real (configurável: 2s default)
- `start()` / `stop()`: Lifecycle

---

## 11. Sistema de Cache (PHASE 5)

### LRU Cache (server/cache/lru.py)

**Características:**
- Thread-safe (OrderedDict + RLock)
- Auto-tuning: 10% da RAM disponível (min 100 MB, max 4 GB)
- TTL por entrada
- Size tracking em bytes
- Eviction callback para métricas

**LRUCache:**
- `__init__(max_size_mb=None, default_ttl=None, on_evict=None)`
- `get(key)`: Retorna valor, atualiza LRU order
- `put(key, value, size_bytes=None, ttl=None)`: Insere/atualiza
- `invalidate(key)`: Remove entrada
- `clear()`: Limpa tudo
- `stats()`: Retorna estatísticas (size_mb, entries, utilization_pct)
- `hash_key(*parts)`: Cria SHA256 de partes

**Auto-tuning:**
\`\`\`python
import psutil
available_mb = psutil.virtual_memory().available // (1024 * 1024)
auto_mb = max(100, min(4096, available_mb // 10))  # 10% da RAM
\`\`\`

### Redis Cache (server/cache/redis.py)

**Características:**
- Backend distribuído opcional
- Serialização: pickle ou JSON
- Namespace isolation via `key_prefix`
- TTL via Redis SETEX
- Graceful fallback se redis-py não instalado

**RedisCache:**
- `__init__(host, port, db, password, key_prefix, serialize_method)`
- Mesma interface de LRUCache: `get()`, `put()`, `invalidate()`, `clear()`, `stats()`
- Requer: `pip install redis>=4.5.0`

### Cache Manager (server/cache/manager.py)

**Características:**
- Interface unificada para LRU e Redis
- Auto-fallback: Redis fail → LRU
- Integração com métricas
- Eviction callback routing

**CacheManager:**
- `__init__(backend="lru", metrics=None, **backend_kwargs)`
- `get(key)`: Retorna valor + registra hit/miss
- `put(key, value, size_bytes=None, ttl=None)`: Insere
- `stats()`: Estatísticas do backend ativo
- `backend_type`: Retorna "lru" ou "redis"

**Integração com embed_client.py:**
\`\`\`python
from kb_server.cache import CacheManager
from kb_server.embed_client import init_cache
from observability.metrics import MetricsCollector

metrics = MetricsCollector()
cache = CacheManager(backend="lru", metrics=metrics, max_size_mb=512)
init_cache(cache, metrics)

# Embeddings agora são cacheados automaticamente
vector = await get_embedding("test")  # Cache miss, API call
vector = await get_embedding("test")  # Cache hit, <1ms
\`\`\`

**Cache key structure:**
\`\`\`
SHA256(backend + model + text)
hash("embed", "openai-compat", "nomic-embed-text-v1.5", "<text>")
\`\`\`

---

## 12. Configuração de Clientes MCP

[Conteúdo do README.pt-BR.md seção "Configuração do Cliente MCP"]

---

## 13. Dependências

Ver `requirements.in` para dependências top-level legíveis.

**Core:**
- mcp>=1.0.0
- qdrant-client>=1.9.0 (API: `query_points()`, NÃO `search()`)
- httpx>=0.27.0
- python-dotenv>=1.0.0
- psutil>=5.9.0 (para auto-tuning de RAM)

**Embedding:**
- lmstudio>=1.0.0 (local machine with LM Studio)
- ollama>=0.2.0 (opcional, lxc server)

**Extratores:**
- python-docx, openpyxl, python-pptx, pymupdf (obrigatórios)
- docling (opcional, ~400 MB extra)

  Para instalar:
  ```bash
  pip install -e ".[pdf]"                              # todos os sistemas
  ./scripts/install-pdf-extras.sh                      # Linux — detecta GPU
  .\scripts\install-pdf-extras.ps1                     # Windows — detecta GPU
  ```

  Para remover:
  ```bash
  ./scripts/remove-pdf-extras.sh                       # Linux
  .\scripts\remove-pdf-extras.ps1                      # Windows
  ```

  Sem docling, o sistema usa PyMuPDF como fallback automático.
  Em máquinas AMD/Intel (sem GPU NVIDIA), o script evita instalar
  ~1 GB de pacotes CUDA desnecessários.

**Dev/Test:**
- pytest, pytest-asyncio, mypy, black, isort, flake8
- prometheus-client, rich

**Workflow pip-tools:**
\`\`\`bash
vim requirements.in           # Edite dependências top-level
pip-compile requirements.in   # Gera requirements.txt pinado
pip-sync requirements.txt     # Instala exatamente o que está pinado
\`\`\`

---

## 14. Decisões Técnicas

### Qdrant Client API (≥1.7)

**CORRETO:**
\`\`\`python
response = await client.query_points(
    collection_name=...,
    query=vector,
    limit=top_k,
    ...
)
results = response.points  # Lista de ScoredPoint
\`\`\`

**ERRADO (deprecated):**
\`\`\`python
results = await client.search(query_vector=vector, ...)  # AttributeError
\`\`\`

### load_dotenv Primeiro Sempre

Em entrypoints (`server.py`, `ingest.py`, `health_check.py`):

\`\`\`python
# SEMPRE no topo, antes de imports do projeto
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

# Só depois:
from kb_server.embed_client import get_embedding
\`\`\`

**Razão:** `embed_client.py` e `vector_store.py` leem `os.getenv()` no nível de módulo.

### LM Studio Remoto vs Local

- **lmstudio-sdk**: Conecta via WebSocket. Só funciona se daemon acessível por WS.
- **Para LM Studio em outro IP:** Usar `openai-compat` com `LMS_BASE_URL=http://ip:porta`.
- **Verificar modelo:** `curl http://ip:1234/v1/models` → copiar nome exato.

### WSL2 → Windows Networking

- WSL2 acessa Windows via IP em `/etc/resolv.conf` (nameserver).
- Se `localhost` não funcionar para LM Studio, usar IP real da máquina Windows na LAN.
- **Alternativa:** `LMS_BASE_URL=http://$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):1234`

---

## 15. Melhorias Planejadas

Todas as PHASEs v1.3 (PHASEs 1-16) e v1.4 (PHASEs 29-37) foram implementadas.

### v1.4 — Platform, Analytics & Enterprise (PHASEs 29-37)

| PHASE | Título | Entregas |
|------|--------|----------|
| 29 | Conectores Enterprise | Confluence, JIRA, Git via factory pattern |
| 30 | Grafo de Conhecimento | Metadados de grafo, get_related_documents, explore_topic |
| 31 | Prompts MCP | extract_answer, summarize_documents |
| 32 | Autenticação por API Key | AUTH_ENABLED, CLI auth create/list/revoke |
| 33 | Rate Limiting | RATE_LIMIT_ENABLED, token bucket por assunto |
| 34 | Cotas de Upload | CLI quota show/set/reset, schema v3→v4 |
| 35 | Busca Multi-KB Agregada | kb_ids, resolve_multi, merge com RRF |
| 36 | Circuit Breaker & Budget | Provider resilience, fallback chain |
| 37 | Cache de Busca | Request-level cache com invalidação |

---

## 16. Comandos de Operação

\`\`\`bash
# Setup inicial
bash scripts/setup.sh local        # ou lxc
python scripts/health_check.py

# Ingestão local
source .venv/bin/activate
python ingest/ingest.py --docs /caminho/docs
python ingest/ingest.py --status --list

# Ingestão via conectores empresariais (PHASE 29)
python -m ingest.cli.main connectors list
python -m ingest.cli.main connectors stage --type confluence --source-key wiki

# Gerenciamento de chaves de API (PHASE 32)
python -m ingest.cli.main auth create --scope global --description "minha-chave"
python -m ingest.cli.main auth list
python -m ingest.cli.main auth revoke <prefixo>

# Gerenciamento de cotas (PHASE 34)
python -m ingest.cli.main quota show
python -m ingest.cli.main quota set --max-files 50000
python -m ingest.cli.main quota reset

# Servidor (teste manual)
python kb_server/server.py

# Local machine — autostart
pwsh scripts/start-kb-rag.ps1
pwsh scripts/start-kb-rag.ps1 -Status
pwsh scripts/start-kb-rag.ps1 -Stop

# LXC Server — systemd
sudo systemctl status kb-mcp
sudo journalctl -u kb-mcp -f

# Qdrant
docker ps
curl http://localhost:6333/healthz
curl http://localhost:6333/collections

# Métricas (se endpoint habilitado)
curl http://localhost:8081/metrics | grep kb_
\`\`\`

---

## Instalação do docling (PDF Extra)

> O docling é um extrator de PDF avançado (tabelas, figuras, layout analysis) que
> substitui o PyMuPDF quando instalado. Sem ele, o sistema usa PyMuPDF como fallback
> automático — nenhuma perda de funcionalidade em PDFs simples.

**Requisito:** ~400 MB adicionais (ou ~1.4 GB se o pip instalar torch com CUDA).

```bash
# Opção 1 — instalação básica (todos os sistemas)
pip install -e ".[pdf]"

# Opção 2 — Linux, com detecção automática de GPU
./scripts/install-pdf-extras.sh

# Opção 3 — Windows (PowerShell), com detecção automática de GPU
.\scripts\install-pdf-extras.ps1
```

**GPU vs CPU:** Em máquinas AMD/Intel sem GPU NVIDIA, o script `install-pdf-extras.sh`
pré-instala `torch` do canal CPU (`download.pytorch.org/whl/cpu`), evitando que o pip
baixe ~1 GB de pacotes CUDA (nvidia-cublas, nvidia-cudnn, etc.) que são inúteis sem GPU.

**Verificação:**
```bash
python -c "from docling.document_converter import DocumentConverter; print('docling OK')"
```

### Otimização de performance (GPU)

Em máquinas com GPU NVIDIA, docling pode ser **6-10× mais rápido** que CPU.
A lib `ingest/docling_utils.py` já configura GPU e batch sizes automaticamente.

**Configuração recomendada:**

```bash
# 1. Verifique se torch CUDA está instalado
python -c "import torch; print('CUDA:', torch.cuda.is_available())"

# 2. Pré-download dos modelos (evita acessos ao HuggingFace durante a ingestão)
./scripts/download-docling-models.sh

# 3. Defina o caminho dos modelos (adicione ao .env)
export DOCLING_ARTIFACTS_PATH="$PWD/models/docling"
```

**Variáveis de ambiente úteis:**

| Variável | Efeito |
|---|---|
| `DOCLING_ARTIFACTS_PATH=/path/to/models` | Diretório persistente de modelos |
| `HF_HUB_ENABLE_HF_TRANSFER=1` | Download mais rápido (Rust) |
| `HF_HUB_DOWNLOAD_TIMEOUT=120` | Timeout de download (default 60s) |

**Importante:** O `DocumentConverter` é criado uma única vez (singleton via
`functools.lru_cache`) e reusado por todos os PDFs — sem recriar modelos
ou validar contra HuggingFace entre arquivos.

**Remoção:**
```bash
# Remove apenas docling + dependências exclusivas
./scripts/remove-pdf-extras.sh

# Também remove pacotes CUDA e reinstala torch CPU (para AMD/CPU)
./scripts/remove-pdf-extras.sh --purge

# Windows (PowerShell)
.\scripts\remove-pdf-extras.ps1
.\scripts\remove-pdf-extras.ps1 -Purge
```

> O `--purge` é seguro: `torch` permanece instalado (exigido pelo reranker
> sentence-transformers), mas troca a variante CUDA pela CPU (~1 GB liberado).

---

## 17. Contexto de Negócio

A KB pode conter qualquer documentação técnica. Nomes de produtos e tipos de documentos são classificados automaticamente via metadados.

**Objetivo:** Apoiar engenheiros e consultores no dia a dia de
desenvolvimento, configuração e troubleshooting, usando LLMs (Claude Code)
para acelerar o trabalho.

---

**Última atualização:** 2026-06-11  
**Versão:** 4.0 (v1.4 completo — PHASEs 1-37)
