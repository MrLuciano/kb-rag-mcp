# KB RAG MCP Server — Instruções do Projeto

> Documento de referência para evolução do projeto via geração de código com LLM.
> Descreve arquitetura atual, decisões técnicas, contratos de interface e direções de melhoria.

---

## 1. Visão Geral

Servidor MCP (Model Context Protocol) que expõe busca semântica sobre uma knowledge base local
de documentação técnica e manuais de produtos.

O servidor é consumido por **Claude Code** e **OpenCode** via protocolo MCP, permitindo que o
LLM recupere automaticamente trechos relevantes de documentação durante tarefas de desenvolvimento.

### Fluxo de dados

```
Documentos locais (PDF, DOCX, XLSX, PPTX, TXT, formatos legados, ZIP, código)
    │
    ▼  ingest/ingest.py
Extração de texto  →  Chunking  →  Embedding (LM Studio / Ollama)
    │
    ▼
Qdrant (vector store local, Docker)
    │
    ▼  kb_server/server.py  [protocolo MCP]
Claude Code / OpenCode
```

---

## 2. Ambiente de Execução

### Local Machine (primary)
- **Hardware:** Local machine with GPU or iGPU
- **OS:** Windows 11 Pro
- **Embedding:** LM Studio rodando no Windows nativo com aceleração Vulkan
- **Servidor MCP:** Python no WSL2 (Ubuntu 24.04)
- **Vector store:** Qdrant em Docker no WSL2
- **Acesso:** LM Studio acessível via `http://<LM_STUDIO_HOST>:1234` (IP fixo na rede local)
- **Transport MCP:** stdio via `wsl.exe` invocado pelo Claude Code no Windows

### LXC Server (secondary / always-on)
- **Hardware:** LXC Ubuntu 24.04, 6 vCPU, 8–12 GB RAM, CPU only
- **Embedding:** Ollama local (`nomic-embed-text`)
- **Transport MCP:** SSE em `http://<ip-lxc>:8765/sse`
- **Serviço:** systemd (`kb-mcp.service`)

---

## 3. Estrutura de Arquivos

```
kb-rag-mcp/
├── kb_server/
│   ├── server.py          # Entrypoint MCP — registra tools, roteia calls
│   ├── embed_client.py    # Abstração de embedding (multi-backend)
│   ├── vector_store.py    # Abstração Qdrant (search, upsert, list, stats)
│   ├── collections/       # Multi-collection routing (FASE 15)
│   │   ├── manager.py     # CollectionManager — CRUD de coleções Qdrant
│   │   └── router.py      # CollectionRouter — resolve/ensure por parâmetro
│   ├── cache/             # LRU cache + Redis opcional
│   ├── retrieval/         # Hybrid search (BM25+dense RRF) + reranker
│   ├── ui/                # Web UI FastAPI+HTMX
│   └── telemetry/         # Query logger SQLite
├── ingest/
│   ├── ingest.py          # Pipeline de ingestão — CLI principal
│   ├── classifier.py      # Inferência de product e doc_type por regex
│   ├── registry.py        # Controle de estado (SQLite) — evita re-ingestão
│   ├── parsers/
│   │   ├── legacy_office.py  # .doc, .xls, .ppt, .odt, .ods, .odp, .wpd
│   │   └── zip_handler.py    # Extração recursiva de arquivos ZIP
│   ├── job/               # Sistema de jobs SQLite com prioridades
│   ├── worker/            # Pool async + rate limiter token bucket
│   ├── validation/        # Validadores de formato, tamanho, conteúdo
│   └── watcher/           # File watcher watchdog para auto-ingestão
├── qa/
│   ├── run_qa.py          # Pipeline de avaliação QA
│   ├── metrics.py         # Hit rate, MRR, p50_score
│   └── queries.json       # Dataset de queries para avaliação
├── observability/
│   └── metrics.py         # 28 métricas Prometheus (kb_* prefix)
├── scripts/
│   ├── migrate/           # Ferramentas de migração (FASE 1.5)
│   │   ├── export.py      # Exporta snapshot Qdrant + env sanitizado
│   │   ├── import_.py     # Importa com validação SHA256
│   │   └── validate.py    # Valida manifesto SHA256
│   ├── kb-migrate.sh      # Wrapper shell: export/import/validate
│   ├── setup.sh           # Instalação de dependências por perfil
│   ├── health_check.py    # Testa embedding + Qdrant + busca end-to-end
│   └── start-kb-rag.ps1   # Autostart WSL2 no Windows (PowerShell)
├── deployment/
│   ├── systemd/           # Units systemd para bare-metal
│   ├── config/
│   │   ├── grafana-dashboard.json          # Dashboard Grafana 18 painéis
│   │   └── grafana-provisioning/           # Datasource + dashboard YAML
│   └── helm/kb-rag-mcp/   # Helm chart Kubernetes (FASE 15)
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/     # Deployment, StatefulSet, HPA, Services, ConfigMap
├── config/
│   ├── .env.local         # Variáveis para local machine
│   ├── .env.lxc           # Variáveis para LXC Server
│   └── mcp-clients.json   # Configs prontas para Claude Code e OpenCode
├── docs/
│   ├── REFERENCE.md       # Referência técnica principal
│   ├── INSTRUCTIONS.md    # Este arquivo (inglês)
│   ├── INSTRUCTIONS.pt-BR.md  # Este arquivo (português)
│   ├── LEGACY_FORMATS.md  # Formatos legados e regras de extração ZIP
│   └── ...
├── data/
│   └── registry.db        # SQLite — gerado automaticamente na primeira ingestão
├── docker-compose.yml     # Qdrant
├── requirements.txt
└── .env                   # Cópia ativa de .env.local ou .env.lxc
```

---

## 4. Variáveis de Ambiente

Todas lidas via `.env` na raiz do projeto. O `load_dotenv` é chamado **antes de qualquer import**
que leia `os.getenv()` — padrão crítico mantido em todos os entrypoints.

| Variável | Padrão | Descrição |
|---|---|---|
| `EMBED_BACKEND` | `openai-compat` | Backend de embedding: `lmstudio-sdk`, `lmstudio-rest`, `openai-compat`, `ollama` |
| `EMBED_MODEL` | `text-embedding-nomic-embed-text-v1.5-embedding` | Nome exato do modelo conforme listado pelo servidor |
| `LMS_BASE_URL` | `http://localhost:1234` | URL base do LM Studio — **sem** path (`/v1` ou `/api/v0` são adicionados automaticamente por backend) |
| `OLLAMA_HOST` | `http://localhost:11434` | URL do Ollama |
| `QDRANT_HOST` | `localhost` | Host do Qdrant |
| `QDRANT_PORT` | `6333` | Porta REST do Qdrant |
| `QDRANT_PATH` | _(vazio)_ | Se definido, usa Qdrant embedded (sem Docker) |
| `QDRANT_COLLECTION` | `kb_docs` | Nome da coleção no Qdrant |
| `SCORE_THRESHOLD` | `0.35` | Score mínimo de relevância (0.0–1.0) para retornar resultados |
| `MCP_TRANSPORT` | `stdio` | `stdio` (Claude Code local) ou `sse` (acesso via URL) |
| `SSE_HOST` | `0.0.0.0` | Bind address para modo SSE |
| `SSE_PORT` | `8765` | Porta para modo SSE |
| `DEFAULT_TOP_K` | `5` | Número padrão de resultados por busca |
| `LOG_PATH` | `/tmp/kb-mcp.log` | Caminho do arquivo de log |
| `REGISTRY_DB` | `data/registry.db` | Caminho do SQLite de controle de ingestão |

### Normalização de URL (embed_client.py)

O código normaliza `LMS_BASE_URL` removendo qualquer path final:
```python
LMS_BASE_URL = re.sub(r"/(api/v\d+|v\d+)/?$", "", raw_url).rstrip("/")
# "http://<LM_STUDIO_HOST>:1234/api/v1"  →  "http://<LM_STUDIO_HOST>:1234"
# "http://<LM_STUDIO_HOST>:1234/v1"      →  "http://<LM_STUDIO_HOST>:1234"
```
Cada backend então adiciona o path correto:
- `openai-compat` → `{LMS_BASE_URL}/v1/embeddings`
- `lmstudio-rest`  → `{LMS_BASE_URL}/api/v0/embeddings`
- `lmstudio-sdk`   → WebSocket `ws://{LMS_HOST}:{LMS_PORT}`

---

## 5. MCP Tools Expostas

### `search_kb`
Busca semântica principal. Parâmetros:

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `query` | string | ✓ | Pergunta ou termo |
| `top_k` | integer | — | Resultados (1–20, padrão: 5) |
| `product` | string | — | Filtro de produto (inferido pelo classifier) |
| `doc_type` | string | — | Filtro: ver taxonomia abaixo |
| `filter_type` | string | — | Formato do arquivo: `pdf`, `docx`, `xlsx`, `pptx`, `txt`, `code` |

**Retorno:** lista de chunks com `chunk_id`, `score`, `text`, `source_file`, `product`, `doc_type`, `file_type`, `page`.

### `list_documents`
Lista documentos indexados. Aceita os mesmos filtros de `search_kb` exceto `query` e `top_k`. Retorna documentos agrupados por `doc_type`.

### `get_chunk`
Retorna chunk completo com contexto vizinho.

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `chunk_id` | string | ✓ | ID retornado pelo `search_kb` |
| `context_window` | integer | — | Chunks vizinhos a incluir (0–3, padrão: 1) |

### `kb_stats`
Estatísticas da KB: total de documentos e chunks, breakdown por `doc_type` e por formato de arquivo.

---

## 6. Taxonomia de Conteúdo (doc_type)

Inferida automaticamente por `ingest/classifier.py` via regex no nome do arquivo e caminho.
Nenhuma reorganização de pastas é necessária.

| doc_type | Descrição | Exemplos de padrões |
|---|---|---|
| `admin_guide` | Guias de administração | Administration Guide, ACN, AGD |
| `install_guide` | Guias de instalação | Installation Guide, IGW, IASW, IGU |
| `upgrade_guide` | Guias de upgrade/migração | Upgrading, Update Installation, Migration |
| `config_guide` | Guias de configuração | Configuration Guide, CGD, STORM, Cookbook |
| `user_guide` | Guias de usuário | User Guide, UGD |
| `api_guide` | APIs / SDKs / programação | Programming Guide, API, SDK, PSA, Endpoints |
| `release_notes` | Notas de release | Release Notes, What's New, Changelog |
| `howto` | Tutoriais / case studies | How-to, Case Study, Troubleshoot, KB\d+ |
| `training` | Treinamentos / webinars | Training, VILT, Webinar, Module N, Study Guide |
| `overview` | Visão geral / introdução | Overview, What is, Understanding, Architecture |
| `standard` | Normas e regulamentos | ISO, 15489, LGPD, Lei Geral |
| `reference` | Referência técnica | Technical Paper, Terminology, Spec |
| `meeting` | Gravações de reuniões | Meeting Recording, Knowledge Sharing |
| `release_artifact` | Artefatos binários | .zip, .patch, pat\d{9} |
| `document` | Fallback genérico | Qualquer arquivo não classificado |

### Mapeamento de produtos (pasta raiz → product)

| Pasta | product |
|---|---|
| `Archive/` | `product_archive` |
| `AppServer/` | `product_content` |
| `ECM/` | `product_ecm` |
| `DirectoryServices/` | `product_directory` |
| `wem/` | `product_wem` |
| `Adobe/` | `Adobe` |
| `RecordsManagement/` | `RecordsManagement` |
| `varios/`, raiz | `geral` |

Produtos também são inferidos do nome do arquivo quando o arquivo está em `varios/` ou na raiz.

---

## 7. Pipeline de Ingestão

### Fluxo por arquivo

```
1. classifier.classify(file_path) → {product, doc_type}
2. registry.needs_ingest(file_path) → (bool, razão)
   ├── False → skip (SHA256 idêntico, status ok)
   └── True  → continuar
3. EXTRACTOR[file_type](file_path) → [{text, page}]
4. chunk_text(text, file_type) → [chunks]
5. embed_client.get_embeddings_batch(chunks) → [vectors]
6. store.delete_document(source_file)  # remove versão anterior
7. store.upsert_chunks(chunks + vectors + metadata)
8. registry.mark_ok(...)  # salva SHA256 + timestamp + doc_type
```

### Extratores por tipo

| file_type | Extensões | Biblioteca | Fallback |
|---|---|---|---|
| `pdf` | .pdf | docling | PyMuPDF (fitz) |
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
| `code` | .py .ts .js .java .go .rs .cpp .c .cs .yaml .yml .json .xml .sh .sql | built-in | — |
| `zip` | .zip | stdlib zipfile (recursivo) | — (máx 2 níveis, 500 MB/entry) |

Veja [LEGACY_FORMATS.md](LEGACY_FORMATS.md) para detalhes sobre formatos legados e extração ZIP.

Arquivos ignorados: `.mp4`, `.avi`, `.jpg`, `.png`, `.ini`, `.exe`, `.dll`.

### Configurações de chunking por tipo

| file_type | chunk_size | overlap |
|---|---|---|
| pdf | 800 | 100 |
| docx | 700 | 80 |
| xlsx | 500 | 50 |
| pptx | 600 | 80 |
| txt | 600 | 80 |
| code | 400 | 60 |

Implementado com `RecursiveCharacterTextSplitter` do LangChain com separadores `["\n\n", "\n", ". ", " ", ""]`.

### Registry (SQLite)

Tabela `files` em `data/registry.db`:

```sql
CREATE TABLE files (
    path        TEXT PRIMARY KEY,  -- caminho relativo a docs_root
    sha256      TEXT NOT NULL,     -- hash do conteúdo
    file_type   TEXT,              -- pdf | docx | xlsx | pptx | txt | code
    product     TEXT,              -- produto inferido
    doc_type    TEXT,              -- tipo de conteúdo inferido
    chunks      INTEGER,           -- chunks gerados
    status      TEXT,              -- ok | error | deleted
    error_msg   TEXT,
    indexed_at  REAL,              -- Unix timestamp
    file_mtime  REAL,
    file_size   INTEGER
);
```

**Migração automática:** se a tabela já existia sem `doc_type`, a coluna é adicionada via `ALTER TABLE`.

### CLI do ingest.py

```bash
# Ingestão incremental (só novos e modificados)
python ingest/ingest.py --docs /path/to/docs

# Com produto explícito (override do classifier)
python ingest/ingest.py --docs /path --product AppServer

# Arquivo único
python ingest/ingest.py --file /path/to/doc.pdf

# Forçar re-ingestão de tudo
python ingest/ingest.py --docs /path --force

# Limpa KB e registry, reinicia do zero
python ingest/ingest.py --docs /path --clean

# Marca como deleted arquivos removidos do disco
python ingest/ingest.py --docs /path --sync

# Paralelismo (padrão: 2 workers)
python ingest/ingest.py --docs /path --workers 4

# Status do registry
python ingest/ingest.py --status
python ingest/ingest.py --status --errors   # só com erro
python ingest/ingest.py --status --list     # lista todos
```

---

## 8. Configuração dos Clientes MCP

### Claude Code — Local Machine (WSL2)

Arquivo: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "kb-rag": {
      "command": "wsl.exe",
      "args": [
        "-d", "Ubuntu-24.04",
        "--",
        "/home/SEU_USER/kb-rag-mcp/.venv/bin/python",
        "/home/SEU_USER/kb-rag-mcp/kb_server/server.py"
      ]
    }
  }
}
```

### Claude Code — LXC Server (SSE)

Arquivo: `~/.claude/settings.json`

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

Arquivo: `opencode.json` (raiz do projeto ou `~/.config/opencode/`)

```json
{
  "mcp": {
    "kb-rag": {
      "type": "local",
      "command": ["wsl.exe", "-d", "Ubuntu-24.04", "--",
        "/home/SEU_USER/kb-rag-mcp/.venv/bin/python",
        "/home/SEU_USER/kb-rag-mcp/kb_server/server.py"]
    }
  }
}
```

---

## 9. Dependências

```
# Core
mcp>=1.0.0
qdrant-client>=1.9.0       # API: query_points() — NÃO search() (deprecated)
httpx>=0.27.0
python-dotenv>=1.0.0

# Embedding (instalar conforme backend)
lmstudio>=1.0.0             # lmstudio>=1.0.0 (local machine with LM Studio)
# ollama>=0.2.0             # lxc server

# Extratores
python-docx>=1.1.0
openpyxl>=3.1.0
python-pptx>=0.6.23
pymupdf>=1.24.0             # fallback PDF
# docling>=2.0.0            # PDF avançado (opcional)

# Chunking
langchain-text-splitters>=0.2.0

# SSE transport (só se MCP_TRANSPORT=sse)
uvicorn>=0.30.0
starlette>=0.37.0
```

---

## 10. Decisões Técnicas e Restrições Conhecidas

### Qdrant client API
A versão ≥1.7 do `qdrant-client` removeu `client.search()`. Usar sempre:
```python
# CORRETO
response = await client.query_points(collection_name=..., query=vector, ...)
results = response.points  # lista de ScoredPoint

# ERRADO — gera AttributeError
results = await client.search(query_vector=vector, ...)
```

Para delete com filtro, usar `FilterSelector`:
```python
await client.delete(
    collection_name=...,
    points_selector=qmodels.FilterSelector(filter=Filter(must=[...]))
)
```

### load_dotenv deve ser o primeiro import
Em qualquer entrypoint (`server.py`, `ingest.py`, `health_check.py`), o `load_dotenv` deve
rodar **antes** de importar módulos do projeto, pois `embed_client.py` e `vector_store.py`
leem `os.getenv()` no nível de módulo (fora de funções).

```python
# PADRÃO CORRETO — sempre no topo, antes de imports do projeto
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

# Só depois:
from embed_client import get_embedding
from vector_store import VectorStore
```

### LM Studio remoto vs local
- `lmstudio-sdk` conecta via WebSocket ao daemon LM Studio. Só funciona se o daemon
  estiver na mesma máquina ou acessível por WebSocket (não via HTTP simples).
- Para LM Studio em outro IP na rede: usar `openai-compat` com `LMS_BASE_URL=http://ip:porta`.
- O nome do modelo deve ser exatamente como aparece em `/v1/models` — verificar antes de configurar.

### WSL2 → Windows networking
O WSL2 acessa o Windows host pelo IP em `/etc/resolv.conf` (nameserver) ou pelo IP da rede local.
Se `localhost` não funcionar para o LM Studio, usar o IP real da máquina Windows na rede local.

### Ingestão paralela
O semáforo de workers limita chamadas simultâneas ao servidor de embedding.
Com LM Studio em CPU, manter `--workers 1` ou `2`. Com GPU: até `4`.
Ingestão dos 7 GB leva estimadamente 3–6 horas em CPU only.

---

## 11. Melhorias Planejadas (backlog)

> **Nota:** Este backlog está mapeado para FASE 11-16 em docs/PLAN.md.  
> Cada item contém detalhes técnicos suficientes para implementação autônoma.

---

### Alta prioridade

#### ✅ Formatos legados (FASE 11 — implementado)

Suporte completo a formatos legados implementado em `ingest/parsers/`:

- `.doc` — docx2txt → python-docx fallback
- `.xls` — xlrd (Excel 97-2003)
- `.ppt` — python-pptx best-effort
- `.odt`, `.ods`, `.odp` — odfpy (OpenDocument)
- `.wpd` — extração heurística latin-1
- `.zip` — stdlib zipfile, recursivo até 2 níveis, 500 MB/entry limit

Consulte [LEGACY_FORMATS.md](LEGACY_FORMATS.md) para detalhes completos.

---

#### Reranking (FASE 12)
**Problema:** Resultados vetoriais incluem falsos positivos (similaridade semântica sem 
relevância factual). Top-5 pode conter documentos irrelevantes.

**Solução técnica:**
- Criar `server/retrieval/reranker.py` com cross-encoder:
  - Modelo: `cross-encoder/ms-marco-MiniLM-L-6-v2` via `sentence-transformers`
  - Pipeline: `search_kb` retorna top-20 → reranker → top-k ao usuário
  - Batch processing: grupos de 20 pares (query, chunk) por vez
  - Async: não bloquear thread principal
- Adicionar parâmetro `rerank: bool = False` ao tool `search_kb` (opt-in)
- Cache de resultados rerankeados (key: hash(query + results))

**Arquivos afetados:**
- `requirements.in`: adicionar `sentence-transformers>=2.2.0`
- `server/retrieval/reranker.py`: novo módulo
- `server/mcp_server.py`: integrar reranker no `search_kb`
- `server/cache/cache_manager.py`: adicionar cache de reranking
- `tests/test_reranker.py`: testes unitários
- `tests/e2e/test_reranking_quality.py`: testes de qualidade

**Configuração:**
```bash
# .env
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RERANKER_BATCH_SIZE=20
RERANKER_CACHE_TTL=3600  # 1 hora
```

**Testes:**
- Dataset de golden queries com expected top doc
- Métrica: NDCG@5 antes/depois do reranking
- Teste de performance: latência p95 <500ms
- Validação: ordem de resultados muda corretamente

**Critério de aceitação:**
- NDCG@5 melhora >20% no dataset de teste
- Latência adicional <200ms (p95)
- Opt-in não quebra comportamento existente

---

#### Busca híbrida (FASE 12)
**Problema:** Busca puramente vetorial falha em termos técnicos específicos 
(nomes de produto, versões, códigos). Exemplo: "Archive Center 22.3" não 
ranqueia documentos com esse termo exato no topo.

**Solução técnica:**
- Qdrant `SparseVector` + BM25 via `fastembed`:
  - Dense vector: embedding atual (nomic-embed-text)
  - Sparse vector: BM25 tokenization com fastembed
  - Fusão: **RRF (Reciprocal Rank Fusion)** ou weighted sum
- Adicionar parâmetro `hybrid: bool = False` ao `search_kb` (opt-in)
- Armazenar sparse vector junto com dense no upsert

**Arquivos afetados:**
- `requirements.in`: adicionar `fastembed>=0.2.0` (BM25 support)
- `server/retrieval/hybrid_search.py`: novo módulo
- `ingest/core/document_processor.py`: gerar sparse vector no chunking
- `server/vector_store.py`: upsert com sparse vector
- `server/mcp_server.py`: integrar hybrid search
- `tests/test_hybrid_search.py`: testes unitários
- `tests/e2e/test_recall_improvement.py`: métricas de recall

**Implementação RRF:**
```python
def rrf_fusion(dense_results, sparse_results, k=60):
    """Reciprocal Rank Fusion."""
    scores = {}
    for rank, result in enumerate(dense_results):
        scores[result.id] = scores.get(result.id, 0) + 1/(k + rank + 1)
    for rank, result in enumerate(sparse_results):
        scores[result.id] = scores.get(result.id, 0) + 1/(k + rank + 1)
    return sorted(scores.items(), key=lambda x: -x[1])
```

**Configuração:**
```bash
# .env
HYBRID_DENSE_WEIGHT=0.7
HYBRID_SPARSE_WEIGHT=0.3
HYBRID_RRF_K=60
```

**Testes:**
- Queries com termos técnicos específicos (versões, códigos)
- Métrica: Recall@10 antes/depois
- Validação: documentos com match exato ranqueiam melhor

**Critério de aceitação:**
- Recall@10 melhora >15% em queries técnicas
- Compatibilidade com filtros existentes (product, doc_type)
- Performance: latência <100ms adicional

---

#### Payload indexing (FASE 12)
**Problema:** Queries filtradas (`product=X`, `doc_type=Y`) são lentas em 
coleções grandes (>100k chunks) porque Qdrant scana todos os payloads.

**Solução técnica:**
- Criar índices Qdrant nos campos `product` e `doc_type`:
  ```python
  client.create_payload_index(
      collection_name="kb_docs",
      field_name="product",
      field_schema="keyword"  # index como string exato
  )
  ```
- Script de migração: `scripts/migrations/create_payload_indexes.py`
  - Idempotente: verifica se índice já existe
  - Progress bar para coleções grandes
  - Pode rodar em produção sem downtime
- Integrar criação de índices em `vector_store.py` ao criar collection

**Arquivos afetados:**
- `scripts/migrations/create_payload_indexes.py`: novo script
- `server/vector_store.py`: adicionar index creation ao `create_collection()`
- `docs/MIGRATIONS.md`: documentar migração
- `tests/test_payload_indexes.py`: validar criação de índices

**Script de migração:**
```python
# scripts/migrations/create_payload_indexes.py
import asyncio
from qdrant_client import QdrantClient

async def create_indexes():
    client = QdrantClient(url=QDRANT_URL)
    fields = ["product", "doc_type"]
    
    for field in fields:
        # Check if index exists
        collection_info = client.get_collection("kb_docs")
        if field not in collection_info.config.params.index_fields:
            print(f"Creating index on {field}...")
            client.create_payload_index(
                collection_name="kb_docs",
                field_name=field,
                field_schema="keyword"
            )
            print(f"✓ Index created on {field}")
        else:
            print(f"✓ Index already exists on {field}")

if __name__ == "__main__":
    asyncio.run(create_indexes())
```

**Testes:**
- Benchmark: filtro antes/depois de criar índices
- Validação: query com filtro retorna resultados corretos
- Performance: queries filtradas <50ms em coleção de 100k chunks

**Critério de aceitação:**
- Índices criados com sucesso em produção
- Queries filtradas >10x mais rápidas
- Script idempotente (pode rodar múltiplas vezes)

---

### Média prioridade

#### ✅ Suporte a ZIP (FASE 11 — implementado)

Implementado em `ingest/parsers/zip_handler.py`. Extração recursiva até 2 níveis,
limite de 500 MB por entry, preservação de `source_path` no payload.
Consulte [LEGACY_FORMATS.md](LEGACY_FORMATS.md) para as regras completas.

---

#### Versão no payload (FASE 13)
**Problema:** Documentos de versões diferentes do mesmo produto não são 
distinguíveis. Usuário não pode filtrar por versão específica.

**Solução técnica:**
- Extrator de versão: `ingest/core/version_extractor.py`
  - Regex patterns:
    - `(\d{2}\.\d+)` → "22.3", "16.2"
    - `(CE \d{2}\.\d+)` → "CE 24.4"
    - `(v\d+\.\d+\.\d+)` → "v3.2.1"
    - `(\d{4}R\d)` → "2024R1" (SAP style)
  - Buscar em: filename, parent directory, primeiro parágrafo do texto
  - Retornar primeira match ou `None`
- Adicionar campo `version: str | None` ao payload Qdrant
- Filtro `version` no `search_kb` tool

**Arquivos afetados:**
- `ingest/core/version_extractor.py`: novo módulo
- `ingest/core/metadata.py`: integrar extração de versão
- `server/mcp_server.py`: adicionar parâmetro `version` ao `search_kb`
- `tests/test_version_extractor.py`: testes com diversos formatos

**Implementação:**
```python
import re

class VersionExtractor:
    PATTERNS = [
        r'(\d{2}\.\d+(?:\.\d+)?)',  # 22.3, 16.2.1
        r'(CE \d{2}\.\d+)',          # CE 24.4
        r'(v\d+\.\d+(?:\.\d+)?)',    # v3.2.1, v2.0
        r'(\d{4}R\d)',               # 2024R1
    ]
    
    def extract(self, filename: str, parent_dir: str, 
                text_preview: str) -> str | None:
        """Extract version from filename, directory, or text."""
        sources = [filename, parent_dir, text_preview[:500]]
        
        for source in sources:
            for pattern in self.PATTERNS:
                match = re.search(pattern, source)
                if match:
                    return match.group(1)
        
        return None
```

**Testes:**
- `"ProductName_22.3_Admin_Guide.pdf"` → `"22.3"`
- `"/docs/ecm/CE 24.4/manual.pdf"` → `"CE 24.4"`
- `"Release Notes for version 16.2"` → `"16.2"`
- Arquivo sem versão → `None`

**Critério de aceitação:**
- Extrai versão corretamente de 90% dos arquivos de teste
- Campo `version` indexado no Qdrant
- Filtro `version` funciona no search_kb

---

#### `_meta.json` por pasta (FASE 13)
**Problema:** Classificação automática erra em alguns arquivos. Mover arquivos 
para reestruturar pastas é trabalhoso. Precisa de override pontual.

**Solução técnica:**
- Arquivo `_meta.json` por diretório:
  ```json
  {
    "product": "DefaultProductForDir",
    "doc_type": "default_doc_type",
    "files": {
      "specific_file.pdf": {
        "product": "OverrideProduct",
        "doc_type": "api_guide"
      },
      "another_file.docx": {
        "doc_type": "manual"
      }
    }
  }
  ```
- Precedência: file-specific > directory-level > auto-inference
- Validação: rejeitar `product`/`doc_type` inválidos (lista permitida)
- Carregar em `FileScanner` antes de classificar

**Arquivos afetados:**
- `ingest/core/meta_loader.py`: novo módulo
- `ingest/core/file_scanner.py`: integrar meta loader
- `ingest/core/metadata.py`: usar override se disponível
- `tests/test_meta_loader.py`: testes de precedência

**Implementação:**
```python
import json
from pathlib import Path

class MetaLoader:
    VALID_DOC_TYPES = [
        "admin_guide", "install_guide", "api_guide", 
        "release_notes", "manual", "training", "overview"
    ]
    
    def load_meta(self, directory: Path) -> dict:
        """Load _meta.json from directory."""
        meta_file = directory / "_meta.json"
        if not meta_file.exists():
            return {}
        
        with open(meta_file) as f:
            meta = json.load(f)
        
        # Validate
        if "doc_type" in meta:
            if meta["doc_type"] not in self.VALID_DOC_TYPES:
                raise ValueError(f"Invalid doc_type: {meta['doc_type']}")
        
        if "files" in meta:
            for file, overrides in meta["files"].items():
                if "doc_type" in overrides:
                    if overrides["doc_type"] not in self.VALID_DOC_TYPES:
                        raise ValueError(
                            f"Invalid doc_type for {file}: "
                            f"{overrides['doc_type']}"
                        )
        
        return meta
    
    def get_metadata(self, file_path: Path, meta: dict) -> dict:
        """Get metadata for file considering precedence."""
        filename = file_path.name
        
        # File-specific override
        if "files" in meta and filename in meta["files"]:
            file_meta = meta["files"][filename]
            return {
                "product": file_meta.get("product", meta.get("product")),
                "doc_type": file_meta.get("doc_type", meta.get("doc_type"))
            }
        
        # Directory-level default
        return {
            "product": meta.get("product"),
            "doc_type": meta.get("doc_type")
        }
```

**Testes:**
- `_meta.json` com default → aplicado a todos os arquivos
- `_meta.json` com file-specific → override funciona
- Precedência: file > dir > auto
- Validação: doc_type inválido → erro

**Critério de aceitação:**
- `_meta.json` carregado e validado corretamente
- Precedência funciona (file > dir > auto)
- Validação rejeita valores inválidos
- Classificação manual tem prioridade sobre automática

---

### Baixa prioridade

#### UI de inspeção (FASE 14)
**Solução resumida:**
- FastAPI em `server/ui/` com HTMX
- Rotas: `/ui` (browse), `/ui/search` (tester), `/ui/doc/{id}` (detail)
- Bootstrap 5 ou Tailwind para styling
- Sem autenticação (internal only)
- Paginação: 50 documentos por página

**Arquivos:** `server/ui/{app.py, templates/, static/}`

---

#### Métricas de uso (FASE 14)
**Solução resumida:**
- Tabela SQLite `query_log`: query, results, scores, latency_ms, timestamp
- Log após cada `search_kb` invocation
- Auto-rotação: keep 90 dias, archive mensalmente
- Query para stats: top queries, low-score queries

**Arquivos:** `server/telemetry/query_logger.py`

---

#### ✅ Múltiplas coleções (FASE 15 — implementado)
**Solução implementada:**
- `CollectionManager` em `kb_server/collections/manager.py` — CRUD (list/create/delete/exists)
  - Espelha HNSW config e payload indexes do VectorStore
- `CollectionRouter` em `kb_server/collections/router.py`
  - `resolve()` — estrito, lança `CollectionNotFoundError` se coleção não existe (paths de leitura)
  - `ensure()` — cria automaticamente se não existe (paths de ingestão)
- Parâmetro opcional `collection` em `search_kb` e `list_documents`
- Nova MCP tool: `list_collections` — lista todas as coleções disponíveis
- Backward compatible: sem `collection` roteia para `QDRANT_COLLECTION` (padrão `kb_docs`)

**Arquivos:** `kb_server/collections/{__init__.py, manager.py, router.py}`,
              `kb_server/server.py` (modificado), `kb_server/vector_store.py` (modificado)
**Testes:** `tests/test_collection_manager.py` (10 testes), `tests/test_collection_router.py` (7 testes)

---

#### Export do registry (FASE 14)
**Solução resumida:**
- Comando: `kb-rag registry export --format csv|json`
- Filtros: `--product`, `--doc_type`, `--status`
- Streaming export (não carregar tudo em memória)

**Arquivos:** `ingest/cli/export.py`

---

#### ✅ Kubernetes support (FASE 15 — implementado)
**Solução implementada:**
- Helm chart em `deployment/helm/kb-rag-mcp/`
  - `Deployment` para kb-server com liveness/readiness probes
  - `StatefulSet` para Qdrant + PVC (50 Gi padrão)
  - `HorizontalPodAutoscaler` (2–10 réplicas, target 70% CPU)
  - `Services` para kb-server e Qdrant
  - `ConfigMap` para env vars
  - `_helpers.tpl` com macros de labels
- `values.yaml` com defaults configuráveis (réplicas, recursos, Redis opcional, Ingress)
- Suporte a `ServiceMonitor` para Prometheus Operator

**Arquivos:** `deployment/helm/kb-rag-mcp/{Chart.yaml, values.yaml, templates/}`
**Docs:** `docs/KUBERNETES.md`

---

#### RAG performance and accuracy (FASE 16)
**Solução resumida:**
- Golden dataset: 50+ (query, expected_answer, expected_docs)
- RAGAS pipeline: context_precision, answer_relevancy, faithfulness
- LLM-as-judge via Ollama local ou OpenAI API
- Query analyzer: identificar padrões, low-score queries
- Otimizações: chunk size, score thresholds, query expansion
- CI job semanal de avaliação

**Arquivos:** `server/evaluation/{ragas_pipeline.py, dataset.py}`, 
            `server/analytics/query_analyzer.py`

---
---

## 12. Comandos de Operação

```bash
# Setup inicial
bash scripts/setup.sh local         # local machine
bash scripts/setup.sh lxc           # LXC Server

# Verificar saúde dos componentes
python scripts/health_check.py

# Ingestão
cd ~/kb-rag-mcp                     # sempre rodar da raiz
source .venv/bin/activate
python ingest/ingest.py --docs /mnt/c/Recebedor/learning

# Status
python ingest/ingest.py --status --list

# Iniciar servidor (teste manual)
python kb_server/server.py

# Local machine — autostart
pwsh scripts/start-kb-rag.ps1
pwsh scripts/start-kb-rag.ps1 -Status
pwsh scripts/start-kb-rag.ps1 -Stop

# LXC Server — systemd
sudo systemctl status kb-mcp
sudo journalctl -u kb-mcp -f

# Qdrant
docker ps                           # verifica se container está rodando
curl http://localhost:6333/healthz  # health check
curl http://localhost:6333/collections  # lista coleções
```

---

## 13. Contexto de Negócio

A KB pode conter qualquer documentação técnica. Nomes de produtos e tipos de documentos são classificados automaticamente via metadados.

Documentos incluem: guias de administração e instalação, release notes, upgrade guides,
guias de configuração de cenários, APIs, materiais de treinamento, apresentações,
case studies, normas e artefatos de release.

O objetivo principal é apoiar **engenheiros e consultores** no dia a dia de
desenvolvimento, configuração e troubleshooting, usando LLMs como Claude Code
para acelerar o trabalho.
