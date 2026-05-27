# Servidor MCP KB-RAG

**[English](#english) | [Português (Brasil)](#português-brasil) | [Español](#español)**

---

<a name="português-brasil"></a>
## 🇧🇷 Português (Brasil)

Servidor MCP (Model Context Protocol) pronto para produção para busca
semântica em bases de conhecimento locais. Suporta PDF, DOCX, XLSX, PPTX,
TXT, Markdown e código-fonte. Compatível com **Claude Code**,
**OpenCode** e qualquer cliente MCP.

### ✨ Funcionalidades

- 🔍 **Busca semântica** em documentação técnica
- 📚 **Suporte multi-formato**: PDF, DOCX, XLSX, PPTX, TXT, código
- ✅ **585 testes** — Isolamento total via mocks, sem dependências externas para testes unitários
- ✅ **Pipeline CI/CD** — Cobertura mínima (90% branch), auditoria de logging, Helm lint
- ✅ **Transporte SSE** — Starlette 1.0.0 com tratamento estável de desconexão
- ✅ **Python 3.13** — Matriz CI testa 3.11, 3.12, 3.13
- ✅ **Auto-classificação** — Inferência de fabricante, produto, subsistema e versão a partir de nomes de arquivo e metadados
- ✅ **Cross-encoder lazy** — ~10s mais rápido na inicialização do servidor, modelo carrega na primeira consulta com reranking
- ✅ **Kubernetes/Helm** — Helm chart para deployment multi-réplica
- 🎯 **Classificação inteligente**: detecção automática de produto e tipo de documento
- 🚀 **Pronto para produção**: serviços systemd, health checks, auto-restart
- 💾 **Ingestão incremental**: processa apenas arquivos novos/modificados
- 📊 **Monitoramento**: métricas Prometheus, regras de alerta, endpoints de health
- 🔄 **Sistema de cache**: LRU com auto-ajuste de RAM ou Redis (80%+ hit rate)
- 🔧 **Multi-backend**: LM Studio, Ollama ou APIs compatíveis com OpenAI
- ⚡ **Processamento em lote**: ingestão 3-5x mais rápida com connection pooling
- 🛠️ **Operações**: instalação automatizada, backup/restore, atualizações
- 👁️ **Auto-ingestão**: monitor de arquivos para atualizações automáticas de documentos
- 🏷️ **Filtragem por versão**: busca por versão de documento (22.3, CE 24.4)
- 📝 **Sobrescrita de metadados**: controle de classificação por diretório/arquivo

---

### 📋 Índice

- [Início Rápido](#início-rápido)
- [Deploy em Produção](#deploy-em-produção)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso](#uso)
- [Verificações de Saúde](#verificações-de-saúde)
- [Gerenciamento de Serviços](#gerenciamento-de-serviços)
- [Ferramentas MCP](#ferramentas-mcp)
- [Arquitetura](#arquitetura)
- [Monitoramento](#monitoramento)
- [Operações](#operações)
- [Desenvolvimento](#desenvolvimento)
- [Documentação](#documentação)
- [Licença](#licença)

---

### 🚀 Início Rápido

> **Pré-requisitos:** Python 3.11+, 3.12, 3.13 suportados, Docker (para Qdrant), e um backend de embedding
> (LM Studio, Ollama ou qualquer servidor compatível com OpenAI).

#### Opção 1: Configuração com um comando (recomendado)

```bash
git clone https://github.com/MrLuciano/kb-rag-mcp
cd kb-rag-mcp

# Inicia Qdrant, instala dependências, lança o servidor MCP
bash scripts/quickstart.sh --docs /caminho/para/seus/docs
```

O script:
1. Copia `config/.env.template` → `.env` (edite `EMBED_URL`, `EMBED_MODEL` antes de executar novamente)
2. Cria `.venv/` e instala todas as dependências Python
3. Inicia Qdrant via Docker Compose
4. Lança o servidor MCP em segundo plano (`logs/kb-rag-mcp.log`)
5. Ingere documentos do caminho fornecido

#### Opção 2: Docker Compose (stack completo)

```bash
cp config/.env.template .env   # preencha EMBED_URL e EMBED_MODEL
docker compose up -d
```

#### Opção 3: Configuração manual

```bash
# 1. Inicie o Qdrant
docker compose up -d qdrant

# 2. Instale dependências Python
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .

# 3. Configure
cp config/.env.template .env
#    → edite .env: defina EMBED_URL, EMBED_MODEL, DOCS_PATH

# 4. Inicie o servidor MCP
python -m kb_server.server

# 5. Ingira seus documentos
python ingest/ingest.py --docs /caminho/para/seus/docs
```

#### Conecte seu assistente de IA

Adicione à configuração do seu cliente MCP (Claude, OpenCode, Cursor, Copilot):

```json
{
  "mcpServers": {
    "kb-rag": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

Para **modo stdio** (sem SSE, padrão para Claude Code):

```json
{
  "mcpServers": {
    "kb-rag": {
      "command": "python",
      "args": ["-m", "kb_server.server"],
      "cwd": "/caminho/para/kb-rag-mcp",
      "env": { "MCP_TRANSPORT": "stdio" }
    }
  }
}
```

#### Verifique se tudo está funcionando

```bash
# Qdrant
curl http://localhost:6333/healthz

# Saúde do servidor MCP
curl http://localhost:8080/health

# Ou use o health check via CLI
kb-rag check health

# Pergunte ao seu assistente de IA:
# "Busque na base de conhecimento por <tópico em seus docs>"
```

#### Habilitando Acesso via LAN (Windows)

Por padrão, os serviços do kb-rag-mcp são acessíveis apenas via `localhost` (127.0.0.1) no host Windows. Para habilitar acesso de outras máquinas na rede:

**1. Execute o script de inicialização com a opção `-ConfigureFirewall`:**

```powershell
.\scripts\start-kb-rag.ps1 -ConfigureFirewall
```

**Nota:** Requer privilégios de Administrador. Se não estiver executando como admin, o script solicitará permissão para reiniciar elevado.

**2. Regras de firewall serão criadas para:**

| Porta | Serviço | Propósito |
|-------|---------|-----------|
| 6333 | Qdrant REST API | Consultas ao banco vetorial |
| 6334 | Qdrant gRPC | Banco vetorial (protocolo gRPC) |
| 8765 | MCP SSE | Endpoint do Model Context Protocol |
| 8080 | Health/Metrics | Health checks e métricas Prometheus |
| 9090 | Prometheus | Coleta de métricas e PromQL |
| 3000 | Grafana | Dashboard de monitoramento |

**3. Acesse os serviços via endereço IP do Windows:**

```bash
# Encontre o IP do Windows
ipconfig  # Procure pelo endereço IPv4 do adaptador Ethernet/Wi-Fi (ex: 192.168.1.100)

# De outra máquina na rede:
curl http://192.168.1.100:8080/health          # Health check
curl http://192.168.1.100:3000                 # Interface Grafana
curl http://192.168.1.100:6333/collections     # API Qdrant
```

**Idempotência:** Executar com `-ConfigureFirewall` múltiplas vezes é seguro — regras existentes são detectadas e puladas.

**Removendo Regras de Firewall:**

Se não precisar mais de acesso via LAN:

```powershell
Get-NetFirewallRule -Group "KB-RAG-MCP" | Remove-NetFirewallRule
```

Ou desabilite manualmente as regras em **Firewall do Windows Defender com Segurança Avançada** (busque pelo grupo "KB-RAG-MCP").

---

### 🏭 Deploy em Produção

**Instalação automatizada para servidores Debian/Ubuntu de produção com serviços systemd, health checks e monitoramento.**

#### Instalação Rápida para Produção

```bash
# 1. Clone o repositório
git clone https://github.com/MrLuciano/kb-rag-mcp
cd kb-rag-mcp

# 2. Execute o instalador automatizado (requer root)
sudo ./deployment/scripts/install.sh

# 3. Configure (edite conforme necessário)
sudo nano /opt/kb-rag/config/kb-rag.env

# 4. Reinicie os serviços
sudo systemctl restart kb-rag.target

# 5. Verifique a saúde
curl http://localhost:8000/health/detailed
```

#### O Que É Instalado

O instalador automatizado (`deployment/scripts/install.sh`) realiza:

- ✅ Dependências do sistema (Python 3.11+, SQLite, logrotate)
- ✅ Criação de usuário (`kb-rag` usuário do sistema)
- ✅ Estrutura de diretórios (`/opt/kb-rag/{data,logs,config}`)
- ✅ Ambiente virtual Python com dependências
- ✅ Geração de arquivo de configuração
- ✅ Instalação de serviços systemd:
  - `kb-rag-server.service` - Servidor MCP (stdio/SSE)
  - `kb-rag-health.service` - Servidor HTTP de health check (porta 8000)
  - `kb-rag-scheduler.service` - Agendador de jobs
  - `kb-rag-watcher.service` - File watcher
  - `kb-rag.target` - Gerenciamento unificado de serviços
- ✅ Rotação de logs (retenção de 14 dias, tamanho máximo 100MB)
- ✅ Hardening de segurança (isolamento de usuário, proteção de filesystem)
- ✅ Inicialização automática de serviços e verificação de saúde

#### Gerenciamento de Serviços

```bash
# Iniciar todos os serviços
sudo systemctl start kb-rag.target

# Parar todos os serviços
sudo systemctl stop kb-rag.target

# Reiniciar todos os serviços
sudo systemctl restart kb-rag.target

# Verificar status
sudo systemctl status kb-rag.target

# Ver logs
sudo journalctl -u kb-rag-server -f
sudo journalctl -u kb-rag-health -f
sudo journalctl -u kb-rag-watcher -f  # Logs do file watcher

# Habilitar auto-start no boot
sudo systemctl enable kb-rag.target
```

#### Verificações de Saúde

O servidor de saúde (porta 8000) fornece 4 endpoints:

```bash
# Saúde básica (load balancers)
curl http://localhost:8000/health

# Saúde detalhada de componentes (monitoramento)
curl http://localhost:8000/health/detailed

# Readiness estilo Kubernetes
curl http://localhost:8000/ready

# Liveness estilo Kubernetes
curl http://localhost:8000/alive

# Métricas Prometheus
curl http://localhost:8000/metrics
```

#### Backup e Restore

```bash
# Criar backup
./deployment/scripts/backup.sh

# Restaurar de backup
sudo ./deployment/scripts/restore.sh /caminho/para/backup.tar.gz

# Backups agendados (cron)
# Adicione a /etc/cron.daily/kb-rag-backup:
#!/bin/bash
/opt/kb-rag/deployment/scripts/backup.sh /backups/kb-rag-$(date +%Y%m%d).tar.gz
```

#### Atualizações

```bash
# Atualizar para versão mais recente
sudo ./deployment/scripts/update.sh

# Atualizar para versão específica
sudo ./deployment/scripts/update.sh v1.3

# Rollback em caso de falha (automático)
# Se os serviços falharem ao iniciar, o script de update restaura automaticamente do backup
```

#### Desinstalação

```bash
# Remover tudo (incluindo dados)
sudo ./deployment/scripts/uninstall.sh

# Remover mas manter dados
sudo ./deployment/scripts/uninstall.sh --keep-data
```

#### Requisitos de Recursos

| Componente | Memória | CPU | Disco | Notas |
|-----------|---------|-----|------|-------|
| Servidor MCP | 200-500MB | 50-100% | - | Uso baseline (v1.3) |
| Servidor de Saúde | 30-50MB | 5-10% | - | Monitoramento leve |
| Agendador | 50-100MB | 10-20% | - | Gerenciamento de jobs |
| File Watcher | 50-100MB | 5-15% | - | Daemon de auto-ingestão |
| Qdrant | 500MB-2GB | 50-100% | Variável | Armazenamento de vetores |
| **Total** | **~1-3.5GB** | **150-250%** | **10GB+** | Recomendado: 4GB RAM, 4 vCPU |

#### Recursos de Segurança

- **Isolamento de Usuário**: Serviços executam como usuário não-root `kb-rag`
- **Proteção de Filesystem**: `ProtectSystem=strict`, `ProtectHome=true`
- **Limites de Recursos**: Quotas de memória e CPU previnem esgotamento de recursos
- **No New Privileges**: `NoNewPrivileges=true` previne escalação
- **/tmp Privado**: `PrivateTmp=true` isola arquivos temporários
- **Permissões Mínimas**: Apenas diretórios de dados e logs graváveis

#### Checklist de Produção

- [ ] Qdrant rodando e acessível
- [ ] Serviço de embedding (LM Studio/Ollama) acessível
- [ ] Configuração customizada (`/opt/kb-rag/config/kb-rag.env`)
- [ ] Serviços habilitados e rodando
- [ ] Health checks passando (`curl localhost:8000/health/detailed`)
- [ ] Monitoramento Prometheus configurado (opcional)
- [ ] Regras de alerta deployadas (opcional)
- [ ] Backup agendado (cron)
- [ ] Firewall configurado (se acesso externo necessário)
- [ ] SSL/TLS via reverse proxy (se acesso externo necessário)

Veja [docs/OPERATIONS.md](docs/OPERATIONS.md) para documentação completa de deployment.

---

### 💻 Instalação

> **Para deployment em produção**, veja a seção [Deploy em Produção](#deploy-em-produção) acima para instalação automatizada com serviços systemd.

Esta seção cobre instalação manual para desenvolvimento.

#### Pré-requisitos

- Python 3.11, 3.12, 3.13 suportados
- Docker (para Qdrant) ou Qdrant embedded
- LM Studio / Ollama / API de embedding compatível com OpenAI
- 8+ GB RAM (16+ GB recomendado)

#### Instalação para Desenvolvimento

**1. Clone o repositório**

```bash
git clone https://github.com/MrLuciano/kb-rag-mcp
cd kb-rag-mcp
```

**2. Crie o ambiente virtual**

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

**3. Instale dependências**

```bash
# Usando pip-tools (recomendado)
pip install pip-tools
pip-sync requirements.txt

# Ou diretamente com pip
pip install -r requirements.txt
```

**4. Configure o ambiente**

```bash
# Copie o template
cp deployment/config/kb-rag.env.template .env

# Edite com suas configurações
vim .env
```

**5. Inicie o Qdrant**

```bash
# Usando Docker
docker run -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/data/qdrant:/qdrant/storage \
  qdrant/qdrant

# Ou com Docker Compose
docker compose up -d
```

**6. Verifique a instalação**

```bash
# Inicie o servidor MCP
python -m kb_server.server

# Em outro terminal, verifique a saúde
kb-rag check health
curl http://localhost:8000/health/detailed
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
QDRANT_PATH=  # Deixe vazio para Docker, defina caminho para modo embedded
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

# Processamento em Lote
EMBED_BATCH_SIZE=32        # Tamanho do lote de embedding (25-64)
FILE_BATCH_SIZE=50         # Lote de processamento de arquivos (50-100)
QDRANT_BATCH_SIZE=100      # Lote de upsert no Qdrant (80-200)
HTTP_POOL_CONNECTIONS=20   # Tamanho do pool de conexões HTTP
MAX_CONCURRENT_UPLOADS=3   # Uploads concorrentes (1-5)

# Pool de Workers
WORKER_POOL_SIZE=4         # Quantidade de workers (padrão: 4)
WORKER_RATE_LIMIT=10       # Requisições/seg por worker (padrão: 10)

# Auto-Ingestão (File Watcher)
WATCH_PATH=                # Diretório para monitorar mudanças
WATCH_DEBOUNCE_SECONDS=30  # Intervalo de debounce em segundos
WATCH_RECURSIVE=true       # Monitorar subdiretórios
WATCH_IGNORE_PATTERNS=     # Padrões glob separados por vírgula para ignorar

# Servidor de Saúde
HEALTH_PORT=8000           # Porta do servidor HTTP de health check

# Geral
LOG_LEVEL=INFO             # Nível de logging (DEBUG, INFO, WARNING, ERROR)
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
        "-d", "Debian",
        "--",
        "/home/SEU_USUARIO/kb-rag-mcp/.venv/bin/python",
        "-m", "kb_server.server"
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
      "url": "http://<LXC_SERVER_HOST>:8765/sse"
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
        "/caminho/para/kb-rag-mcp/.venv/bin/python",
        "-m", "kb_server.server"
      ]
    }
  }
}
```

---

### 📖 Uso

#### Ingestão de Documentos

```bash
# Usando a CLI kb-rag (recomendado)
kb-rag ingest --docs /caminho/para/docs

# Ou diretamente com Python
source .venv/bin/activate
python ingest/ingest.py --docs /caminho/para/docs

# Com produto e vendor explícitos
python ingest/ingest.py --docs /caminho/para/docs --product MeuProduto --vendor Acme

# Arquivo único
python ingest/ingest.py --file /caminho/para/documento.pdf

# Limpar e reingerir tudo
python ingest/ingest.py --docs /caminho/para/docs --clean

# Mais workers (use com GPU)
python ingest/ingest.py --docs /caminho/para/docs --workers 4

# Verificar status da ingestão via CLI
kb-rag status
kb-rag status --source /caminho/para/docs

# Ou os comandos de status legados
python ingest/ingest.py --status
python ingest/ingest.py --status --list    # Listar todos os arquivos
python ingest/ingest.py --status --errors  # Apenas erros
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

O produto é automaticamente inferido do nome do diretório. Documentos também são
auto-classificados com metadados de **vendor**, **subsistema** e **versão**
extraídos de nomes de arquivo e estrutura de diretórios (veja funcionalidades da Fase 11).

#### Auto-Ingestão

Monitore diretórios para mudanças e dispare ingestão automaticamente:

```bash
# Iniciar serviço de file watcher
sudo systemctl start kb-rag-watcher

# Ou executar standalone
python -m ingest.watcher.file_watcher

# Configure no .env
WATCH_PATH=/caminho/para/docs
WATCH_DEBOUNCE_SECONDS=30
```

**Veja [AUTO_INGESTION.md](docs/AUTO_INGESTION.md) para guia completo.**

#### Filtragem por Versão

Busque documentos por versão (extraída automaticamente de nomes de arquivo/caminhos):

```python
# Uso da ferramenta MCP
search_kb(
    query="passos de instalação",
    product="AppServer",
    version="3.2"  # Apenas buscar docs 3.2
)
```

**Padrões de versão suportados:**
- Numérico: `22.3`, `23.1.5`
- Prefixo CE: `CE 24.4`
- Prefixo v: `v2.5`
- Palavra-chave version: `version 16.2`

**Veja [VERSION_FILTERING.md](docs/VERSION_FILTERING.md) para guia completo.**

#### Sobrescrita de Metadados

Sobrescreva a classificação automática com arquivos `_meta.json`:

```json
{
  "product": "AppServer",
  "doc_type": "admin_guide",
  "files": {
    "install.pdf": {
      "doc_type": "installation_guide"
    }
  }
}
```

**Veja [METADATA_OVERRIDES.md](docs/METADATA_OVERRIDES.md) para guia completo.**

#### Reclassificação de Documentos

Quando as regras de classificação melhoram (ex.: melhores padrões de detecção de fornecedor), você pode atualizar metadados de documentos já ingeridos sem reprocessar ou re-embeber:

##### Uso Básico

```bash
# Reclassificar arquivos específicos
kb-ingest reclassify "docs/OpenText/*.pdf"

# Reclassificar por filtro de metadados
kb-ingest reclassify "**/*.pdf" --filter 'vendor=""'

# Combinar padrão e filtro
kb-ingest reclassify "docs/OT*.pdf" --filter 'subsystem=""'

# Pular confirmação (automação)
kb-ingest reclassify "docs/**/*" --yes
```

##### Fluxo de Verificação

Antes de reclassificar, verifique o que mudaria:

```bash
# Verificar incompatibilidades
kb-ingest reclassify verify "docs/**/*.pdf"

# Mostra:
# - Documentos com incompatibilidades de metadados
# - Valores atuais vs. esperados
# - Detalhes por documento
```

Após reclassificar, verifique se as mudanças foram aplicadas:

```bash
kb-ingest reclassify verify "docs/**/*.pdf"
# Deve mostrar: "Todos os documentos correspondem às classificações esperadas"
```

##### Reversão

Se a reclassificação produzir resultados inesperados, reverta para os metadados anteriores:

```bash
# Listar sessões de backup
kb-ingest reclassify sessions

# Reverter sessão inteira
kb-ingest reclassify rollback --session 2026-05-26T15-30-00

# Reversão seletiva (padrão + timestamp)
kb-ingest reclassify rollback "docs/OT*.pdf" --before 2026-05-26T16-00-00
```

Backups são mantidos por 30 dias por padrão (configurável via `RECLASSIFY_BACKUP_RETENTION_DAYS`).

##### Como Funciona

1. **Detectar Mudanças:** Executa `classify()` nos documentos correspondentes, compara com metadados atuais do Qdrant
2. **Visualização:** Mostra resumo agregado por campo (ex.: "vendor: 47 docs ('' → 'OpenText')")
3. **Backup:** Grava metadados antigos no SQLite (`data/registry.db`) para reversão
4. **Atualizar:** Atualiza campos de payload do Qdrant in-place (preserva vetores)
5. **Auditoria:** Registra mudanças na tabela `reclassify_history` para rastreamento

##### Opções

| Flag | Descrição |
|------|-----------|
| `--collection <nome>` | Direcionar coleção Qdrant específica |
| `--filter <expr>` | Filtro de metadados (ex.: `vendor=""`) |
| `--yes` / `-y` | Pular prompt de confirmação |
| `--allow-missing` | Processar documentos mesmo se arquivo fonte ausente |
| `--include-custom` | Atualizar campos personalizados além dos campos de classificação |
| `--no-progress` | Desabilitar barra de progresso (para scripts) |

##### Recursos de Segurança

- **Confirmação interativa:** Mostra visualização antes de fazer mudanças (use `--yes` para pular)
- **Backup automático:** Metadados antigos salvos no SQLite antes das atualizações
- **Rastreamento de sessão:** Todos os backups vinculados ao timestamp da sessão para reversão completa
- **Log de auditoria:** Todas as mudanças registradas na tabela `reclassify_history`
- **Retenção de 30 dias:** Backups limpos automaticamente após 30 dias (configurável)

##### Fluxos de Trabalho Comuns

**Cenário 1: Detecção de fornecedor melhorada**

A Fase 11 foi lançada com inferência básica de fornecedor, deixando muitos documentos com o campo `vendor` vazio. Após melhorar os padrões do `VENDOR_MAP`:

```bash
# Verificar o que mudaria
kb-ingest reclassify verify "**/*" --filter 'vendor=""'

# Mostra 47 documentos que mudariam vendor → "OpenText"

# Aplicar mudanças
kb-ingest reclassify "**/*" --filter 'vendor=""' --yes
```

**Cenário 2: Corrigir documentos classificados incorretamente**

Alguns PDFs foram incorretamente classificados como `doc_type="overview"` quando deveriam ser `"admin_guide"`:

```bash
# Verificar estado atual
kb-ingest reclassify verify "docs/admin/*.pdf"

# Reclassificar (após atualizar regras de doc_type em classifier.py)
kb-ingest reclassify "docs/admin/*.pdf"

# Verificar correção
kb-ingest reclassify verify "docs/admin/*.pdf"
```

**Cenário 3: Reversão após regressão de classificação**

Mudança de regra de classificação introduziu valores incorretos de subsystem:

```bash
# Verificar sessões recentes
kb-ingest reclassify sessions

# Mostra sessão 2026-05-26T15-30-00 com 50 docs alterados

# Reverter sessão inteira
kb-ingest reclassify rollback --session 2026-05-26T15-30-00
```

##### Solução de Problemas

**"Nenhuma mudança de classificação detectada"**

Possíveis causas:
- Regras de classificação não mudaram desde a última ingestão
- Padrão não corresponde a nenhum documento no Qdrant
- Filtro de metadados muito restritivo

Solução: Execute `verify` para ver valores atuais vs. esperados

**"Arquivo fonte não encontrado no disco"**

Por padrão, reclassify pula documentos onde o arquivo fonte está ausente (arquivo fonte necessário para executar `classify()`). Se arquivos foram movidos ou você quer reclassificar usando apenas metadados do Qdrant:

```bash
kb-ingest reclassify "**/*" --allow-missing
```

**Sessão de reversão não encontrada**

Sessões com mais de 30 dias são limpas automaticamente. Ajuste a retenção:

```bash
export RECLASSIFY_BACKUP_RETENTION_DAYS=90
kb-ingest reclassify "**/*"
```

---

### 🏥 Verificações de Saúde

KB-RAG inclui um sistema abrangente de health check que monitora todos os componentes.

#### Endpoints de Saúde

O servidor de saúde roda na porta 8000 (configurável via `HEALTH_PORT`) e fornece:

```bash
# Saúde básica - para load balancers
GET /health
→ {"status": "ok", "service": "kb-rag"}

# Saúde detalhada - para dashboards de monitoramento
GET /health/detailed
→ {
  "status": "ok",
  "healthy": true,
  "timestamp": "2026-05-15T12:00:00Z",
  "components": {
    "embedding": {"healthy": true, "latency_ms": 45.2, ...},
    "vector_store": {"healthy": true, "latency_ms": 12.5, ...},
    "cache": {"healthy": true, "latency_ms": 0.1, ...},
    "database": {"healthy": true, "latency_ms": 2.3, ...},
    "filesystem": {"healthy": true, "latency_ms": 1.5, ...}
  }
}

# Probe de readiness - estilo Kubernetes
GET /ready
→ {"ready": true}  # 200 se pronto, 503 se não

# Probe de liveness - estilo Kubernetes
GET /alive
→ {"alive": true}  # Sempre 200 se respondendo
```

#### Verificações de Componentes

| Componente | Verificações | Crítico | Detalhes |
|-----------|--------|----------|---------|
| **embedding** | Serviço alcançável, embedding de teste | Sim | Backend, modelo, dimensões |
| **vector_store** | Conexão Qdrant, coleção existe | Sim | Total de chunks, documentos |
| **cache** | Estatísticas disponíveis | Não | Backend, entradas, hit rate |
| **database** | SQLite acessível, queries funcionam | Sim | Contagem de jobs, arquivos |
| **filesystem** | Acesso leitura/escrita, espaço em disco | Não | Espaço livre (aviso < 10%) |

**Nota:** Modelo cross-encoder de reranking é lazy-loaded (não verificado no probe de saúde) — carrega na primeira query de reranking (~10s mais rápido na inicialização).

#### Scripts de Health Check

```bash
# Verificar todos os serviços
./deployment/scripts/health-check.sh all

# Verificar serviço específico
./deployment/scripts/health-check.sh server
./deployment/scripts/health-check.sh health
./deployment/scripts/health-check.sh scheduler

# Códigos de saída: 0=saudável, 1=não saudável, 2=erro
```

#### Servidor de Saúde Manual

Para desenvolvimento sem systemd:

```bash
# Iniciar servidor de saúde
python -m kb_server.health_server

# Ou use a CLI
kb-rag check health

# Em outro terminal, verifique a saúde
curl http://localhost:8000/health/detailed | jq
```

---

### ⚙️ Gerenciamento de Serviços

> **Nota:** Gerenciamento de serviços requer deployment em produção com systemd. Veja [Deploy em Produção](#deploy-em-produção).

#### Comandos Básicos

```bash
# Iniciar todos os serviços KB-RAG
sudo systemctl start kb-rag.target

# Parar todos os serviços KB-RAG
sudo systemctl stop kb-rag.target

# Reiniciar todos os serviços KB-RAG
sudo systemctl restart kb-rag.target

# Verificar status geral
sudo systemctl status kb-rag.target
```

#### Serviços Individuais

```bash
# Servidor MCP (serviço principal)
sudo systemctl status kb-rag-server
sudo systemctl restart kb-rag-server

# Servidor de Health Check
sudo systemctl status kb-rag-health
sudo systemctl restart kb-rag-health

# File Watcher (auto-ingestão)
sudo systemctl status kb-rag-watcher
sudo systemctl restart kb-rag-watcher

# Agendador de Jobs
sudo systemctl status kb-rag-scheduler
sudo systemctl restart kb-rag-scheduler
```

#### Visualizando Logs

```bash
# Seguir todos os logs
sudo journalctl -u kb-rag-server -u kb-rag-health -f

# Apenas logs do servidor MCP
sudo journalctl -u kb-rag-server -f

# Últimas 100 linhas
sudo journalctl -u kb-rag-server -n 100

# Desde horário específico
sudo journalctl -u kb-rag-server --since "1 hour ago"

# Com filtro de nível de log
sudo journalctl -u kb-rag-server -p err  # Apenas erros
sudo journalctl -u kb-rag-server -p warning  # Warnings e acima
```

#### Verificações de Status de Serviço

```bash
# Verificar se serviço está rodando
systemctl is-active kb-rag-server  # active ou inactive

# Verificar se serviço está habilitado (auto-start)
systemctl is-enabled kb-rag-server  # enabled ou disabled

# Status completo com logs recentes
sudo systemctl status kb-rag.target --no-pager

# Uso de recursos
systemd-cgtop -1 | grep kb-rag
```

#### Configuração de Auto-Restart

Serviços reiniciam automaticamente em caso de falha com estas configurações:

- **Política de Restart**: `always` (reinicia em qualquer saída)
- **Atraso de Restart**: 10 segundos entre tentativas
- **Limite de Burst**: 3 tentativas em 5 minutos
- **Recuperação**: Após 5 minutos, reseta contador de falhas

Ver histórico de restarts:

```bash
# Verificar contagem de restarts
systemctl show kb-rag-server -p NRestarts

# Ver falhas de serviço
systemctl list-units --failed | grep kb-rag
```

---

### 🔧 Ferramentas MCP

#### `search_kb`

Busca semântica na base de conhecimento.

**Parâmetros:**
- `query` (obrigatório): Query de busca
- `top_k` (opcional): Número de resultados (1-20, padrão: 5)
- `product` (opcional): Filtrar por produto
- `vendor` (opcional): Filtrar por vendor (auto-classificado de nomes de arquivo)
- `subsystem` (opcional): Filtrar por subsistema (auto-classificado de nomes de arquivo)
- `doc_type` (opcional): Filtrar por tipo de documento
- `filter_type` (opcional): Filtrar por formato de arquivo (pdf, docx, xlsx, pptx, txt, code)
- `version` (opcional): Filtrar por versão de documento

**Retorna:** Lista de chunks com `chunk_id`, `score`, `text`, `source_file`,
`product`, `vendor`, `subsystem`, `doc_type`, `file_type`, `page`, `version`.

#### `list_documents`

Lista documentos indexados com filtros opcionais.

**Parâmetros:**
- `product` (opcional): Filtrar por produto
- `vendor` (opcional): Filtrar por vendor
- `subsystem` (opcional): Filtrar por subsistema
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
kb_server/server.py ←→ MCP (stdio ou SSE)
    ↓
Claude Code / OpenCode
```

**Componentes:**

- **Gerenciamento de Jobs**: Fila de jobs baseada em SQLite com agendamento por prioridade
- **Pool de Workers**: Pool de workers assíncronos com rate limiting
- **Observabilidade**: Métricas Prometheus, logging estruturado, rastreamento de progresso
- **Sistema de Cache**: Cache LRU com auto-ajuste de RAM ou backend Redis
- **Extratores de Documentos**: Suporte multi-formato (PDF via PyMuPDF/docling)
- **Classificador**: Detecção automática de produto e doc_type via regex
- **Auto-classificação**: Inferência de vendor, subsistema, versão a partir de nomes de arquivo e caminhos
- **Cross-encoder reranker**: Lazy-loaded na primeira query de reranking (~10s mais rápido na inicialização)

---

### 👨‍💻 Desenvolvimento

#### Requisitos

Veja `requirements.in` para dependências legíveis por humanos.

#### Executando Testes

```bash
pytest tests/ -v

# Com cobertura
pytest tests/ --cov=kb_server --cov=ingest --cov=observability --cov-branch --cov-report=term-missing

# Cobertura com validação de threshold (90% cobertura branch necessária)
pytest tests/ --cov=kb_server --cov=ingest --cov-branch --cov-fail-under=90

# Arquivo de teste específico
pytest tests/test_job_system.py -v
```

**Baseline de testes:** 585 testes core (excluindo handler SSE e testes e2e)

#### Qualidade de Código

```bash
# Formatar código
black kb_server/ ingest/ scripts/ tests/
isort kb_server/ ingest/ scripts/ tests/

# Lint
flake8 kb_server/ ingest/ scripts/ tests/

# Type check
mypy kb_server/ ingest/ scripts/

# Auditoria de logging (garantir que todos os métodos públicos têm chamadas de log)
python scripts/logging-audit.py

# Auditoria de inglês (validar zero português nos arquivos-fonte)
python scripts/docstring-audit.py --check-inline
```

#### Adicionando Dependências

```bash
# Edite requirements.in
vim requirements.in

# Compile e instale
pip-compile requirements.in
pip-sync requirements.txt
```

---

### 📚 Documentação

**Guias do Usuário:**
- [AUTO_INGESTION.md](docs/AUTO_INGESTION.md) - File watching automático e ingestão
- [METADATA_OVERRIDES.md](docs/METADATA_OVERRIDES.md) - Sobrescrever classificação com _meta.json
- [VERSION_FILTERING.md](docs/VERSION_FILTERING.md) - Busca por versão de documento
- [SEARCH_QUALITY.md](docs/SEARCH_QUALITY.md) - Busca híbrida e reranking
- [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Problemas comuns e soluções

**Documentação Técnica:**
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Arquitetura e design do sistema
- [OPERATIONS.md](docs/OPERATIONS.md) - Deployment e operações em produção
- [TESTING.md](docs/TESTING.md) - Estratégia de testes
- [INDEX.md](docs/INDEX.md) - Índice de documentação
- [REFERENCE.md](docs/REFERENCE.md) - Referência de API
- [KUBERNETES.md](docs/KUBERNETES.md) - Guia de deployment Kubernetes

---

### 📊 Monitoramento

KB-RAG fornece monitoramento abrangente através de métricas Prometheus, health checks e logging estruturado.

#### Métricas Prometheus

Métricas são expostas em `http://localhost:8000/metrics` (servidor de saúde).

**Métricas Disponíveis (28 total):**

```bash
# Gerenciamento de Jobs (4 métricas)
kb_rag_jobs_created_total          # Contador de jobs criados
kb_rag_jobs_completed_total        # Contador de jobs completados
kb_rag_jobs_active                 # Gauge de jobs atualmente ativos
kb_rag_job_duration_seconds        # Histograma de duração de job

# Processamento de Arquivos (3 métricas)
kb_rag_files_processed_total      # Contador de arquivos processados
kb_rag_files_processing_time_seconds  # Histograma de processamento de arquivo
kb_rag_chunks_generated_total     # Contador de chunks gerados

# Pool de Workers (6 métricas)
kb_rag_worker_pool_size            # Gauge de tamanho do pool de workers
kb_rag_worker_pool_queue_size     # Gauge de tamanho da fila
kb_rag_worker_pool_utilization    # Gauge de utilização do pool
kb_rag_rate_limiter_tokens        # Gauge de tokens disponíveis
kb_rag_rate_limiter_waits_total   # Contador de esperas por rate limit
kb_rag_rate_limiter_wait_time_seconds  # Histograma de tempo de espera

# Requisições de API (2 métricas)
kb_rag_api_requests_total         # Contador de requisições de API
kb_rag_api_latency_seconds        # Histograma de latência de API

# Performance de Cache (5 métricas)
kb_rag_cache_hits_total           # Contador de cache hits
kb_rag_cache_misses_total         # Contador de cache misses
kb_rag_cache_evictions_total      # Contador de evictions de cache
kb_rag_cache_size_bytes           # Gauge de tamanho do cache
kb_rag_cache_entries              # Gauge de contagem de entradas do cache

# Processamento em Lote (8 métricas)
kb_rag_batch_embeddings_total          # Operações de embedding em lote
kb_rag_batch_embedding_texts_total     # Textos embedded em lotes
kb_rag_batch_embedding_duration_seconds  # Duração de embedding em lote
kb_rag_batch_upserts_total            # Operações de upsert em lote
kb_rag_batch_upsert_points_total      # Points upserted em lotes
kb_rag_batch_upsert_duration_seconds  # Duração de upsert em lote
kb_rag_http_pool_connections          # Tamanho do pool de conexões HTTP
kb_rag_batch_processing_throughput    # Gauge de throughput de processamento
```

#### Configuração do Prometheus

```yaml
# Adicione a prometheus.yml
scrape_configs:
  - job_name: 'kb-rag'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s
```

Ou use a configuração fornecida:

```bash
# Copie para diretório de config do Prometheus
sudo cp deployment/config/prometheus.yml /etc/prometheus/
sudo cp deployment/config/kb-rag-alerts.yml /etc/prometheus/

# Recarregue o Prometheus
sudo systemctl reload prometheus
```

#### Regras de Alerta

11 regras de alerta pré-configuradas em `deployment/config/kb-rag-alerts.yml`:

**Alertas de Saúde (Crítico):**
- Servidor down por 2+ minutos
- Alta taxa de erro (>10 erros/seg por 5 min)
- Serviço de embedding não saudável (3+ min)
- Vector store não saudável (3+ min)

**Alertas de Performance (Warning):**
- Alta latência (P95 > 5s por 10 min)
- Baixa taxa de hit de cache (<50% por 15 min)

**Alertas de Recursos:**
- Alto uso de memória (>90% por 10 min)
- Pouco espaço em disco (<10% por 5 min)

**Alertas de Jobs:**
- Jobs travados (rodando mas sem progresso por 30 min)
- Alta taxa de falha de jobs (>0.1/seg por 10 min)

#### Dashboard Grafana

Importe dashboard de `deployment/config/grafana-dashboard.json` (em breve).

Painéis principais:
- Status de saúde do serviço
- Taxa de requisições e latência
- Taxa de hit e tamanho do cache
- Fila de jobs e throughput
- Uso de recursos (CPU, memória, disco)
- Taxas de erro

#### Logging Estruturado

Logs são escritos em formato JSON para fácil parsing:

```bash
# Ver logs estruturados
sudo journalctl -u kb-rag-server -o json-pretty

# Extrair campos específicos
sudo journalctl -u kb-rag-server -o json | \
  jq -r 'select(.PRIORITY=="3") | .MESSAGE'  # Apenas erros

# Buscar por componente
sudo journalctl -u kb-rag-server | grep '"component":"cache"'
```

#### Rotação de Logs

Rotação automática de logs configurada via `/etc/logrotate.d/kb-rag`:

- **Frequência**: Diária
- **Retenção**: 14 dias
- **Compressão**: gzip (atrasada 1 dia)
- **Tamanho máximo**: 100MB por arquivo
- **Logs de acesso**: 7 dias, 500MB máximo

Rotação manual:

```bash
# Forçar rotação
sudo logrotate -f /etc/logrotate.d/kb-rag

# Testar configuração
sudo logrotate -d /etc/logrotate.d/kb-rag
```

---

### 🛠️ Operações

#### Backup e Restore

**Criar Backup:**

```bash
# Backup com nome automático
./deployment/scripts/backup.sh

# Caminho customizado
./deployment/scripts/backup.sh /backups/kb-rag-20260515.tar.gz
```

Backup inclui:
- Bancos de dados SQLite (metadados de job, registro de arquivos)
- Arquivos de configuração
- Logs recentes (últimos 7 dias)

**Restaurar de Backup:**

```bash
sudo ./deployment/scripts/restore.sh /caminho/para/backup.tar.gz
```

Recursos de segurança:
- Backup automático pré-restore
- Orquestração de parada/inicialização de serviços
- Restauração de permissões
- Verificação de saúde

**Backups Agendados:**

```bash
# Adicione a /etc/cron.daily/kb-rag-backup
#!/bin/bash
/opt/kb-rag/deployment/scripts/backup.sh \
  /backups/kb-rag-$(date +%Y%m%d).tar.gz

# Limpeza de backups antigos (manter 30 dias)
find /backups -name "kb-rag-*.tar.gz" -mtime +30 -delete
```

#### Atualizações

**Atualizar para Versão Mais Recente:**

```bash
sudo ./deployment/scripts/update.sh
```

Processo de atualização:
1. Criar backup pré-atualização
2. Parar serviços
3. Git pull das mudanças mais recentes
4. Atualizar dependências
5. Atualizar serviços systemd
6. Reiniciar serviços
7. Verificar saúde
8. Rollback em caso de falha (automático)

**Atualizar para Versão Específica:**

```bash
sudo ./deployment/scripts/update.sh v1.3
```

#### Tarefas de Manutenção

**Limpar Jobs Antigos:**

```bash
# Limpar jobs completados com mais de 30 dias
python3 -m ingest.cli job clean --days 30

# Dry run (apenas visualização)
python3 -m ingest.cli job clean --days 30 --dry-run
```

**Reconstruir Índice:**

```bash
# Reingerir todos os documentos (lento)
python3 -m ingest.ingest --docs /caminho/para/docs --clean
```

**Gerenciamento de Cache:**

```bash
# Limpar cache (reiniciar serviço)
sudo systemctl restart kb-rag-server

# Verificar estatísticas de cache
curl http://localhost:8000/health/detailed | jq '.components.cache'
```

#### Tuning de Performance

**Processamento em Lote:**

Ajuste via variáveis de ambiente em `/opt/kb-rag/config/kb-rag.env`:

```bash
# Tamanho do lote de embedding (25-64 recomendado)
EMBED_BATCH_SIZE=32

# Lote de processamento de arquivo (50-100 recomendado)
FILE_BATCH_SIZE=50

# Lote de upsert no Qdrant (80-200 recomendado)
QDRANT_BATCH_SIZE=100

# Conexões HTTP (20-50 recomendado)
HTTP_POOL_CONNECTIONS=20

# Uploads concorrentes (1-5 recomendado)
MAX_CONCURRENT_UPLOADS=3
```

**Pool de Workers:**

```bash
# Aumentar workers para ingestão mais rápida
WORKER_POOL_SIZE=8  # Padrão: 4

# Ajustar rate limit (requisições/seg por worker)
WORKER_RATE_LIMIT=20  # Padrão: 10
```

**Cache:**

```bash
# Aumentar tamanho do cache
CACHE_MAX_SIZE_MB=1024  # Padrão: auto (10% RAM)

# Usar Redis para cache distribuído
CACHE_BACKEND=redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

#### Solução de Problemas

**Serviço Não Inicia:**

```bash
# Verificar status do serviço
sudo systemctl status kb-rag-server

# Ver logs recentes
sudo journalctl -u kb-rag-server -n 100

# Verificar configuração
sudo cat /opt/kb-rag/config/kb-rag.env | grep -v "^#"

# Verificar dependências
/opt/kb-rag/venv/bin/python3 -m pip check
```

**Alto Uso de Memória:**

```bash
# Verificar uso atual
systemctl show kb-rag-server -p MemoryCurrent

# Reduzir tamanho do cache
sudo nano /opt/kb-rag/config/kb-rag.env
# Defina: CACHE_MAX_SIZE_MB=256

sudo systemctl restart kb-rag-server
```

**Performance Lenta:**

```bash
# Verificar saúde e latência dos componentes
curl http://localhost:8000/health/detailed | jq

# Monitorar uso de recursos
systemd-cgtop | grep kb-rag

# Verificar taxa de hit do cache (deve ser >80%)
curl http://localhost:8000/health/detailed | \
  jq '.components.cache.details.hit_rate'
```

**Para guia completo de solução de problemas com 40+ cenários, veja [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).**

---

### 🛠️ Solução de Problemas

> **📖 Veja [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) para o guia completo de solução de problemas com 40+ cenários, comandos de diagnóstico e soluções.**

**Correções Rápidas:**

**API de embedding não responde:**
```bash
# Verificar se LM Studio está rodando e modelo carregado
curl http://localhost:1234/v1/models

# Verificar Ollama
curl http://localhost:11434/api/tags
```

**Erro de conexão com Qdrant:**
```bash
# Verificar se Qdrant está rodando
docker ps | grep qdrant
curl http://localhost:6333/healthz
```

**Sem resultados de busca:**
- Verificar `SCORE_THRESHOLD` (abaixe se muito rigoroso)
- Verificar se documentos estão indexados: `kb-rag status` ou `python ingest/ingest.py --status`
- Verificar se query está no idioma correto

**Ingestão lenta:**
- Reduzir `--workers` se CPU-bound
- Verificar se API de embedding não está sobrecarregada
- Considerar usar GPU para LM Studio

---

### 📝 Licença

Licença MIT

Copyright (c) 2026 Contribuidores do Servidor MCP KB-RAG

A permissão é concedida, gratuitamente, a qualquer pessoa que obtenha uma cópia
deste software e arquivos de documentação associados (o "Software"), para lidar
com o Software sem restrições, incluindo, sem limitação, os direitos de usar,
copiar, modificar, mesclar, publicar, distribuir, sublicenciar e/ou vender
cópias do Software, e permitir que as pessoas a quem o Software é fornecido o
façam, sujeitas às seguintes condições:

O aviso de copyright acima e este aviso de permissão devem ser incluídos em todas
as cópias ou partes substanciais do Software.

O SOFTWARE É FORNECIDO "COMO ESTÁ", SEM GARANTIA DE QUALQUER TIPO, EXPRESSA OU
IMPLÍCITA, INCLUINDO, MAS NÃO SE LIMITANDO ÀS GARANTIAS DE COMERCIALIZAÇÃO,
ADEQUAÇÃO A UM FIM ESPECÍFICO E NÃO VIOLAÇÃO. EM NENHUM CASO OS AUTORES OU
TITULARES DE DIREITOS AUTORAIS SERÃO RESPONSÁVEIS POR QUALQUER REIVINDICAÇÃO,
DANOS OU OUTRA RESPONSABILIDADE, SEJA EM AÇÃO DE CONTRATO, DELITO OU OUTRA FORMA,
DECORRENTE DE, FORA DE OU EM CONEXÃO COM O SOFTWARE OU O USO OU OUTRAS NEGOCIAÇÕES
NO SOFTWARE.

---

### 🤝 Contribuindo

Contribuições são bem-vindas! Por favor, leia [CONTRIBUTING.md](CONTRIBUTING.md) primeiro.
