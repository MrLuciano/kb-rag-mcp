# Servidor MCP KB-RAG

**[English](#english) | [Português (Brasil)](#português-brasil) | [Español](#español)**

---

<a name="español"></a>
## 🇪🇸 Español

Servidor MCP (Model Context Protocol) listo para producción para búsqueda
semántica en bases de conocimiento locales. Soporta PDF, DOCX, XLSX, PPTX,
TXT, Markdown y código fuente. Compatible con **Claude Code**,
**OpenCode** y cualquier cliente MCP.

### ✨ Características

- 🔍 **Búsqueda semántica** en documentación técnica
- 📚 **Soporte multi-formato**: PDF, DOCX, XLSX, PPTX, TXT, código
- ✅ **1541+ pruebas** — Aislamiento total con mocks, sin dependencias externas
- ✅ **Pipeline CI/CD** — Gate de cobertura (90% branch), lint Helm
- ✅ **Auto-clasificación** — Vendor, producto, subsistema, versión
- ✅ **Kubernetes/Helm** — Helm chart para despliegue multi-réplica
- 📊 **Monitoreo en tiempo real** — Grafana + Prometheus (6 paneles)
- 🔄 **Sistema de caché** — LRU con auto-ajuste de RAM o Redis (80%+ hit rate)
- 🔧 **Multi-backend** — LM Studio, Ollama o APIs compatibles con OpenAI
- 🛠️ **Operaciones** — Instalación automatizada, backup/restore, actualizaciones
- 🔐 **Autenticación y control de acceso** — Login con contraseña, claves API, sesiones JWT, admin SPA
- 📋 **Panel Admin SPA** — Interfaz web para navegación, búsqueda, monitoreo y configuración
- ⏰ **Programación de ingesta** — Gestión de schedules CRON con scheduler en segundo plano
- 🏷️ **Etiquetas de documentos** — Edición y filtrado de etiquetas por documento
- 📊 **Panel de analytics** — Volumen de consultas, queries lentas, análisis de cero resultados
- 🔌 **Conectores empresariales** — Confluence, JIRA y Git como fuentes de documentos
- 🔒 **Rate limiting de inicio de sesión** — 5 intentos por ventana de 60s
- 🚀 **Optimizaciones de rendimiento** — Caché de config con TTL, croniter para schedules O(1), JOIN optimizado
- ✅ **14 pruebas E2E** — Flujos de autenticación, admin y programación

---

### 🚀 Inicio Rápido

Elija su modo de implementación:

| Modo | Ideal para | Empiece aquí |
|------|-----------|-------------|
| Docker Compose | Desarrollo local / equipos pequeños | `docker compose up -d` → [docs/INSTRUCTIONS.md → Docker Compose](docs/INSTRUCTIONS.md#docker-compose) |
| Helm (Kubernetes) | Clústers de producción | `helm install` → [docs/KUBERNETES.md](docs/KUBERNETES.md) |
| Systemd | Servidores bare metal / VMs | `sudo ./deployment/scripts/install.sh` → [docs/INSTRUCTIONS.md → Systemd](docs/INSTRUCTIONS.md#systemd) |
| Manual (Source) | Desarrollo / personalización | `python -m kb_server.server` → [docs/INSTRUCTIONS.md → Manual](docs/INSTRUCTIONS.md#manual) |

**Prerrequisitos:** Python 3.11+, Docker (para Qdrant), backend de embedding (LM Studio, Ollama o OpenAI).

**Documentación completa por modo de implementación:** [docs/INDEX.md](docs/INDEX.md)

---

### 📚 Documentación Detallada

| Tópico | Documento |
|--------|-----------|
| Arquitectura | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Operaciones (backup, monitoreo) | [docs/OPERATIONS.md](docs/OPERATIONS.md) |
| Solución de problemas | [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) |
| Instrucciones técnicas | [docs/INSTRUCTIONS.md](docs/INSTRUCTIONS.md) |
| Referencia técnica | [docs/REFERENCE.md](docs/REFERENCE.md) |
| Implementación Kubernetes | [docs/KUBERNETES.md](docs/KUBERNETES.md) |
| Calidad de búsqueda | [docs/SEARCH_QUALITY.md](docs/SEARCH_QUALITY.md) |
| Filtrado por versión | [docs/VERSION_FILTERING.md](docs/VERSION_FILTERING.md) |
| Web UI | [docs/WEB_UI.md](docs/WEB_UI.md) |
| Seguridad | [docs/SECURITY.md](docs/SECURITY.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |

### 📝 Licencia

Distribuido bajo licencia MIT.
