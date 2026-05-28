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
- ✅ **585+ testes** — Isolamento total via mocks, sem dependências externas
- ✅ **Pipeline CI/CD** — Gate de cobertura (90% branch), lint Helm
- ✅ **Auto-classificação** — Vendor, produto, subsistema, versão
- ✅ **Kubernetes/Helm** — Helm chart para deployment multi-réplica
- 📊 **Monitoramento em tempo real** — Grafana + Prometheus (6 abas)
- 🔄 **Sistema de cache** — LRU com auto-ajuste de RAM ou Redis (80%+ hit rate)
- 🔧 **Multi-backend** — LM Studio, Ollama ou APIs compatíveis com OpenAI
- 🛠️ **Operações** — Instalação automatizada, backup/restore, atualizações

---

### 🚀 Início Rápido

Escolha seu modo de implantação:

| Modo | Ideal para | Comece aqui |
|------|-----------|-------------|
| Docker Compose | Desenvolvimento local / equipes pequenas | `docker compose up -d` → [docs/INSTRUCTIONS.md → Docker Compose](docs/INSTRUCTIONS.md#docker-compose) |
| Helm (Kubernetes) | Clusters de produção | `helm install` → [docs/KUBERNETES.md](docs/KUBERNETES.md) |
| Systemd | Servidores bare metal / VMs | `sudo ./deployment/scripts/install.sh` → [docs/INSTRUCTIONS.md → Systemd](docs/INSTRUCTIONS.md#systemd) |
| Manual (Source) | Desenvolvimento / customização | `python -m kb_server.server` → [docs/INSTRUCTIONS.md → Manual](docs/INSTRUCTIONS.md#manual) |

**Pré-requisitos:** Python 3.11+, Docker (para Qdrant), backend de embedding (LM Studio, Ollama ou OpenAI).

**Documentação completa por modo de implantação:** [docs/INDEX.md](docs/INDEX.md)

---

### 📚 Documentação Detalhada

| Tópico | Documento |
|--------|-----------|
| Arquitetura | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Operações (backup, monitoramento) | [docs/OPERATIONS.md](docs/OPERATIONS.md) |
| Solução de problemas | [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) |
| Instruções técnicas | [docs/INSTRUCTIONS.md](docs/INSTRUCTIONS.md) |
| Referência técnica | [docs/REFERENCE.md](docs/REFERENCE.md) |
| Implantação Kubernetes | [docs/KUBERNETES.md](docs/KUBERNETES.md) |
| Qualidade de busca | [docs/SEARCH_QUALITY.md](docs/SEARCH_QUALITY.md) |
| Filtragem por versão | [docs/VERSION_FILTERING.md](docs/VERSION_FILTERING.md) |
| Web UI | [docs/WEB_UI.md](docs/WEB_UI.md) |
| Segurança | [docs/SECURITY.md](docs/SECURITY.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |

### 📝 Licença

Distribuído sob licença MIT.
