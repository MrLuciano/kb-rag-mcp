# KB RAG MCP Server — Instruções do Projeto

> Documento de referência para evolução do projeto via geração de código com LLM.
> Descreve arquitetura atual, decisões técnicas, contratos de interface e direções de melhoria.

---

## 1. Visão Geral

Servidor MCP (Model Context Protocol) que expõe busca semântica sobre uma knowledge base local
de ~7 GB de documentação técnica de produtos OpenText e padrões como ISO 15489.

O servidor é consumido por **Claude Code** e **OpenCode** via protocolo MCP, permitindo que o
LLM recupere automaticamente trechos relevantes de documentação durante tarefas de desenvolvimento.

### Fluxo de dados

```
Documentos locais (PDF, DOCX, XLSX, PPTX, TXT, código)
    │
    ▼  ingest/ingest.py
Extração de texto  →  Chunking  →  Embedding (LM Studio / Ollama)
    │
    ▼
Qdrant (vector store local, Docker)
    │
    ▼  server/server.py  [protocolo MCP]
Claude Code / OpenCode
```

---

## 2. Ambiente de Execução

### Gaming Machine (primária)
- **Hardware:** AMD Ryzen 7 8845HS, 32 GB RAM, iGPU Radeon 780M (RDNA 3)
- **OS:** Windows 11 Pro
- **Embedding:** LM Studio rodando no Windows nativo com aceleração Vulkan
- **Servidor MCP:** Python no WSL2 (Ubuntu 24.04)
- **Vector store:** Qdrant em Docker no WSL2
- **Acesso:** LM Studio acessível via `http://192.168.1.177:1234` (IP fixo na rede local)
- **Transport MCP:** stdio via `wsl.exe` invocado pelo Claude Code no Windows

### Proxmox LXC (secundário / always-on)
- **Hardware:** LXC Ubuntu 24.04, 6 vCPU, 8–12 GB RAM, CPU only
- **Embedding:** Ollama local (`nomic-embed-text`)
- **Transport MCP:** SSE em `http://<ip-lxc>:8765/sse`
- **Serviço:** systemd (`kb-mcp.service`)

---

## 3. Estrutura de Arquivos

```
kb-rag-mcp/
├── server/
│   ├── server.py          # Entrypoint MCP — registra tools, roteia calls
│   ├── embed_client.py    # Abstração de embedding (multi-backend)
│   └── vector_store.py    # Abstração Qdrant (search, upsert, list, stats)
├── ingest/
│   ├── ingest.py          # Pipeline de ingestão — CLI principal
│   ├── classifier.py      # Inferência de product e doc_type por regex
│   └── registry.py        # Controle de estado (SQLite) — evita re-ingestão
├── config/
│   ├── .env.gaming        # Variáveis para gaming machine
│   ├── .env.proxmox       # Variáveis para Proxmox LXC
│   └── mcp-clients.json   # Configs prontas para Claude Code e OpenCode
├── scripts/
│   ├── setup.sh           # Instalação de dependências por perfil
│   ├── health_check.py    # Testa embedding + Qdrant + busca end-to-end
│   ├── start-kb-rag.ps1   # Autostart WSL2 no Windows (PowerShell)
│   └── kb-mcp.service     # Unit systemd para Proxmox
├── data/
│   └── registry.db        # SQLite — gerado automaticamente na primeira ingestão
├── docker-compose.yml     # Qdrant
├── requirements.txt
└── .env                   # Cópia ativa de .env.gaming ou .env.proxmox
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
# "http://192.168.1.177:1234/api/v1"  →  "http://192.168.1.177:1234"
# "http://192.168.1.177:1234/v1"      →  "http://192.168.1.177:1234"
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
| `product` | string | — | Filtro: `ArchiveCenter`, `ContentServer`, `xECM`, `OTDS`, `WEM`, `AppWorks`, `ProcessSuite`, `Adobe`, `SAP`, `ISO`, `geral` |
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
| `Archive/` | `ArchiveCenter` |
| `ContentServer/` | `ContentServer` |
| `xECM/` | `xECM` |
| `OTDS/` | `OTDS` |
| `wem/` | `WEM` |
| `Adobe/` | `Adobe` |
| `ReccordsManagement/` | `RecordsManagement` |
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
| `docx` | .docx, .doc | python-docx | — |
| `xlsx` | .xlsx, .xls | openpyxl | — |
| `pptx` | .pptx, .ppt | python-pptx | — |
| `txt` | .txt, .md, .rst | built-in | — |
| `code` | .py .ts .js .java .go .rs .cpp .c .cs .yaml .yml .json .xml .sh .sql | built-in | — |

Arquivos ignorados: `.mp4`, `.avi`, `.jpg`, `.png`, `.ini`, `.zip` (exceto indexados como `release_artifact`).

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
python ingest/ingest.py --docs /path --product ArchiveCenter

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

### Claude Code — Gaming Machine (WSL2)

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
        "/home/SEU_USER/kb-rag-mcp/server/server.py"
      ]
    }
  }
}
```

### Claude Code — Proxmox (SSE)

Arquivo: `~/.claude/settings.json`

```json
{
  "mcpServers": {
    "kb-rag": {
      "url": "http://192.168.1.200:8765/sse"
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
        "/home/SEU_USER/kb-rag-mcp/server/server.py"]
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
lmstudio>=1.0.0             # gaming machine — SDK nativo
# ollama>=0.2.0             # proxmox

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

### Alta prioridade
- [ ] **Reranking:** cross-encoder local (`cross-encoder/ms-marco-MiniLM-L-6-v2`) aplicado
  sobre os top-20 resultados antes de retornar os top-k ao LLM. Reduz ruído sem custo de embedding.
- [ ] **Busca híbrida:** combinar score vetorial com BM25 (sparse). Qdrant suporta nativamente
  com `SparseVector`. Melhora recall em termos técnicos específicos (nomes de produto, versões).
- [ ] **Payload indexing:** criar índices Qdrant nos campos `product` e `doc_type` para
  acelerar queries filtradas em coleções grandes.

### Média prioridade
- [ ] **Watcher de arquivos:** `watchdog` monitorando `DOCS_PATH`, triggering ingestão incremental
  automática quando arquivos são adicionados/modificados. Útil para manter KB atualizada.
- [ ] **Suporte a ZIP:** extrair e ingerir conteúdo de `.zip` com documentação
  (vários presentes na KB atual).
- [ ] **Versão no payload:** extrair versão do produto do nome do arquivo
  (ex: `22.3`, `16.2`, `CE 24.4`) e indexar como campo separado para filtro.
- [ ] **`_meta.json` por pasta:** arquivo opcional para override de `product`/`doc_type`
  por arquivo sem mover nada, útil para pasta `varios/`.

### Baixa prioridade
- [ ] **UI de inspeção:** interface web leve (FastAPI + HTMX) para navegar documentos
  indexados, testar queries e ver classificações.
- [ ] **Métricas de uso:** logar quais queries são feitas, quais documentos são retornados
  e scores, para avaliar qualidade do RAG ao longo do tempo.
- [ ] **Suporte a múltiplas coleções:** coleção por produto ou por contexto de projeto,
  selecionável via parâmetro na tool ou variável de ambiente.
- [ ] **Export do registry:** comando para gerar CSV/JSON com todos os documentos indexados
  e suas classificações, para auditoria.

---

## 12. Comandos de Operação

```bash
# Setup inicial
bash scripts/setup.sh gaming        # gaming machine
bash scripts/setup.sh proxmox       # Proxmox LXC

# Verificar saúde dos componentes
python scripts/health_check.py

# Ingestão
cd ~/kb-rag-mcp                     # sempre rodar da raiz
source .venv/bin/activate
python ingest/ingest.py --docs /mnt/c/Recebedor/learning

# Status
python ingest/ingest.py --status --list

# Iniciar servidor (teste manual)
python server/server.py

# Gaming machine — autostart
pwsh scripts/start-kb-rag.ps1
pwsh scripts/start-kb-rag.ps1 -Status
pwsh scripts/start-kb-rag.ps1 -Stop

# Proxmox — systemd
sudo systemctl status kb-mcp
sudo journalctl -u kb-mcp -f

# Qdrant
docker ps                           # verifica se container está rodando
curl http://localhost:6333/healthz  # health check
curl http://localhost:6333/collections  # lista coleções
```

---

## 13. Contexto de Negócio

A KB contém documentação técnica de produtos **OpenText** (ECM/EIM):

- **Archive Center** — servidor de arquivamento, múltiplas versões (10.x até 24.x)
- **Content Server** — repositório de conteúdo empresarial
- **Extended ECM (xECM)** — ECM integrado com SAP e outras plataformas
- **OTDS** — OpenText Directory Services (autenticação/autorização)
- **WEM** — Web Experience Management
- **AppWorks / Process Suite** — BPM e automação de processos
- **Adobe Sign / DocuSign** — assinatura eletrônica
- **Padrões:** ISO 15489 (gestão de documentos), LGPD

Documentos incluem: guias de administração e instalação, release notes, upgrade guides,
guias de configuração de cenários, APIs, materiais de treinamento (VILT), apresentações,
case studies, normas ISO e artefatos de release.

O objetivo principal é apoiar **engenheiros e consultores** que trabalham com esses produtos
no dia a dia de desenvolvimento, configuração e troubleshooting, usando LLMs como Claude Code
para acelerar o trabalho.
