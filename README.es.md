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
- ✅ **585 pruebas** — Aislamiento total con mocks, sin dependencias externas para pruebas unitarias
- ✅ **Pipeline CI/CD** — Cobertura mínima (90% branch), auditoría de logging, Helm lint
- ✅ **Transporte SSE** — Starlette 1.0.0 con manejo estable de desconexión
- ✅ **Python 3.13** — Matriz CI prueba 3.11, 3.12, 3.13
- ✅ **Auto-clasificación** — Inferencia de vendor, producto, subsistema y versión desde nombres de archivo y metadatos
- ✅ **Cross-encoder lazy** — ~10s más rápido en inicio del servidor, modelo carga en primera consulta con reranking
- ✅ **Kubernetes/Helm** — Helm chart para despliegue multi-réplica
- 🎯 **Clasificación inteligente**: detección automática de producto y tipo de documento
- 🚀 **Listo para producción**: servicios systemd, health checks, auto-restart
- 💾 **Ingesta incremental**: procesa solo archivos nuevos/modificados
- 📊 **Monitoreo**: métricas Prometheus, reglas de alerta, endpoints de health
- 🔄 **Sistema de caché**: LRU con auto-ajuste de RAM o Redis (80%+ hit rate)
- 🔧 **Multi-backend**: LM Studio, Ollama o APIs compatibles con OpenAI
- ⚡ **Procesamiento por lotes**: ingesta 3-5x más rápida con connection pooling
- 🛠️ **Operaciones**: instalación automatizada, backup/restore, actualizaciones
- 👁️ **Auto-ingesta**: file watcher para actualizaciones automáticas de documentos
- 🏷️ **Filtrado por versión**: búsqueda por versión de documento (22.3, CE 24.4)
- 📝 **Sobrescritura de metadatos**: control de clasificación por directorio/archivo

---

### 📋 Índice

- [Inicio Rápido](#inicio-rápido)
- [Despliegue en Producción](#despliegue-en-producción)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [Verificaciones de Salud](#verificaciones-de-salud)
- [Gestión de Servicios](#gestión-de-servicios)
- [Herramientas MCP](#herramientas-mcp)
- [Arquitectura](#arquitectura)
- [Monitoreo](#monitoreo)
- [Operaciones](#operaciones)
- [Desarrollo](#desarrollo)
- [Documentación](#documentación)
- [Licencia](#licencia)

---

### 🚀 Inicio Rápido

> **Requisitos previos:** Python 3.11+, 3.12, 3.13 soportados, Docker (para Qdrant), y un backend de embedding
> (LM Studio, Ollama o cualquier servidor compatible con OpenAI).

#### Opción 1: Configuración con un comando (recomendado)

```bash
git clone https://github.com/MrLuciano/kb-rag-mcp
cd kb-rag-mcp

# Inicia Qdrant, instala dependencias, lanza el servidor MCP
bash scripts/quickstart.sh --docs /ruta/a/sus/docs
```

El script:
1. Copia `config/.env.template` → `.env` (edite `EMBED_URL`, `EMBED_MODEL` antes de ejecutar nuevamente)
2. Crea `.venv/` e instala todas las dependencias Python
3. Inicia Qdrant via Docker Compose
4. Lanza el servidor MCP en segundo plano (`logs/kb-rag-mcp.log`)
5. Ingiere documentos de la ruta proporcionada

#### Opción 2: Docker Compose (stack completo)

```bash
cp config/.env.template .env   # complete EMBED_URL y EMBED_MODEL
docker compose up -d
```

#### Opción 3: Configuración manual

```bash
# 1. Inicie Qdrant
docker compose up -d qdrant

# 2. Instale dependencias Python
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .

# 3. Configure
cp config/.env.template .env
#    → edite .env: defina EMBED_URL, EMBED_MODEL, DOCS_PATH

# 4. Inicie el servidor MCP
python -m kb_server.server

# 5. Ingiera sus documentos
python ingest/ingest.py --docs /ruta/a/sus/docs
```

#### Conecte su asistente de IA

Agregue a la configuración de su cliente MCP (Claude, OpenCode, Cursor, Copilot):

```json
{
  "mcpServers": {
    "kb-rag": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

Para **modo stdio** (sin SSE, predeterminado para Claude Code):

```json
{
  "mcpServers": {
    "kb-rag": {
      "command": "python",
      "args": ["-m", "kb_server.server"],
      "cwd": "/ruta/a/kb-rag-mcp",
      "env": { "MCP_TRANSPORT": "stdio" }
    }
  }
}
```

#### Verifique que todo funciona

```bash
# Qdrant
curl http://localhost:6333/healthz

# Salud del servidor MCP
curl http://localhost:8080/health

# O use el health check via CLI
kb-rag check health

# Pregunte a su asistente de IA:
# "Busque en la base de conocimiento por <tema en sus docs>"
```

#### Habilitando Acceso por LAN (Windows)

Por defecto, los servicios de kb-rag-mcp son accesibles solo desde `localhost` (127.0.0.1) en el host Windows. Para habilitar el acceso desde otras máquinas en la red:

**1. Ejecute el script de inicio con la opción `-ConfigureFirewall`:**

```powershell
.\scripts\start-kb-rag.ps1 -ConfigureFirewall
```

**Nota:** Requiere privilegios de Administrador. Si no está ejecutando como admin, el script le pedirá permiso para reiniciar elevado.

**2. Se crearán reglas de firewall para:**

| Puerto | Servicio | Propósito |
|--------|----------|-----------|
| 6333 | Qdrant REST API | Consultas a la base de datos vectorial |
| 6334 | Qdrant gRPC | Base de datos vectorial (protocolo gRPC) |
| 8765 | MCP SSE | Endpoint del Model Context Protocol |
| 8080 | Health/Metrics | Health checks y métricas Prometheus |
| 9090 | Prometheus | Recopilación de métricas y PromQL |
| 3000 | Grafana | Panel de monitoreo |

**3. Acceda a los servicios mediante la dirección IP de Windows:**

```bash
# Encuentre su IP de Windows
ipconfig  # Busque la dirección IPv4 del adaptador Ethernet/Wi-Fi (ej: 192.168.1.100)

# Desde otra máquina en la red:
curl http://192.168.1.100:8080/health          # Health check
curl http://192.168.1.100:3000                 # Interfaz Grafana
curl http://192.168.1.100:6333/collections     # API Qdrant
```

**Idempotencia:** Ejecutar con `-ConfigureFirewall` múltiples veces es seguro — las reglas existentes son detectadas y omitidas.

**Eliminando Reglas de Firewall:**

Si ya no necesita acceso por LAN:

```powershell
Get-NetFirewallRule -Group "KB-RAG-MCP" | Remove-NetFirewallRule
```

O deshabilite manualmente las reglas en **Firewall de Windows Defender con Seguridad Avanzada** (busque el grupo "KB-RAG-MCP").

---

### 🏭 Despliegue en Producción

**Instalación automatizada para servidores Debian/Ubuntu de producción con servicios systemd, health checks y monitoreo.**

#### Instalación Rápida para Producción

```bash
# 1. Clone el repositorio
git clone https://github.com/MrLuciano/kb-rag-mcp
cd kb-rag-mcp

# 2. Execute el instalador automatizado (requiere root)
sudo ./deployment/scripts/install.sh

# 3. Configure (edite según necesidad)
sudo nano /opt/kb-rag/config/kb-rag.env

# 4. Reinicie los servicios
sudo systemctl restart kb-rag.target

# 5. Verifique la salud
curl http://localhost:8000/health/detailed
```

#### Qué Se Instala

El instalador automatizado (`deployment/scripts/install.sh`) realiza:

- ✅ Dependencias del sistema (Python 3.11+, SQLite, logrotate)
- ✅ Creación de usuario (`kb-rag` usuario del sistema)
- ✅ Estructura de directorios (`/opt/kb-rag/{data,logs,config}`)
- ✅ Entorno virtual Python con dependencias
- ✅ Generación de archivo de configuración
- ✅ Instalación de servicios systemd:
  - `kb-rag-server.service` - Servidor MCP (stdio/SSE)
  - `kb-rag-health.service` - Servidor HTTP de health check (puerto 8000)
  - `kb-rag-scheduler.service` - Agendador de jobs
  - `kb-rag-watcher.service` - File watcher
  - `kb-rag.target` - Gestión unificada de servicios
- ✅ Rotación de logs (retención de 14 días, tamaño máximo 100MB)
- ✅ Hardening de seguridad (aislamiento de usuario, protección de filesystem)
- ✅ Inicio automático de servicios y verificación de salud

#### Gestión de Servicios

```bash
# Iniciar todos los servicios
sudo systemctl start kb-rag.target

# Detener todos los servicios
sudo systemctl stop kb-rag.target

# Reiniciar todos los servicios
sudo systemctl restart kb-rag.target

# Verificar estado
sudo systemctl status kb-rag.target

# Ver logs
sudo journalctl -u kb-rag-server -f
sudo journalctl -u kb-rag-health -f
sudo journalctl -u kb-rag-watcher -f  # Logs del file watcher

# Habilitar auto-start en boot
sudo systemctl enable kb-rag.target
```

#### Verificaciones de Salud

El servidor de salud (puerto 8000) proporciona 4 endpoints:

```bash
# Salud básica (load balancers)
curl http://localhost:8000/health

# Salud detallada de componentes (monitoreo)
curl http://localhost:8000/health/detailed

# Readiness estilo Kubernetes
curl http://localhost:8000/ready

# Liveness estilo Kubernetes
curl http://localhost:8000/alive

# Métricas Prometheus
curl http://localhost:8000/metrics
```

#### Backup y Restore

```bash
# Crear backup
./deployment/scripts/backup.sh

# Restaurar desde backup
sudo ./deployment/scripts/restore.sh /ruta/a/backup.tar.gz

# Backups programados (cron)
# Agregue a /etc/cron.daily/kb-rag-backup:
#!/bin/bash
/opt/kb-rag/deployment/scripts/backup.sh /backups/kb-rag-$(date +%Y%m%d).tar.gz
```

#### Actualizaciones

```bash
# Actualizar a versión más reciente
sudo ./deployment/scripts/update.sh

# Actualizar a versión específica
sudo ./deployment/scripts/update.sh v1.3

# Rollback en caso de fallo (automático)
# Si los servicios fallan al iniciar, el script de update restaura automáticamente desde backup
```

#### Desinstalación

```bash
# Eliminar todo (incluyendo datos)
sudo ./deployment/scripts/uninstall.sh

# Eliminar pero mantener datos
sudo ./deployment/scripts/uninstall.sh --keep-data
```

#### Requisitos de Recursos

| Componente | Memoria | CPU | Disco | Notas |
|-----------|---------|-----|------|-------|
| Servidor MCP | 200-500MB | 50-100% | - | Uso baseline (v1.3) |
| Servidor de Salud | 30-50MB | 5-10% | - | Monitoreo ligero |
| Agendador | 50-100MB | 10-20% | - | Gestión de jobs |
| File Watcher | 50-100MB | 5-15% | - | Daemon de auto-ingesta |
| Qdrant | 500MB-2GB | 50-100% | Variable | Almacenamiento de vectores |
| **Total** | **~1-3.5GB** | **150-250%** | **10GB+** | Recomendado: 4GB RAM, 4 vCPU |

#### Características de Seguridad

- **Aislamiento de Usuario**: Servicios ejecutan como usuario no-root `kb-rag`
- **Protección de Filesystem**: `ProtectSystem=strict`, `ProtectHome=true`
- **Límites de Recursos**: Cuotas de memoria y CPU previenen agotamiento de recursos
- **No New Privileges**: `NoNewPrivileges=true` previene escalación
- **/tmp Privado**: `PrivateTmp=true` aísla archivos temporales
- **Permisos Mínimos**: Solo directorios de datos y logs escribibles

#### Checklist de Producción

- [ ] Qdrant ejecutándose y accesible
- [ ] Servicio de embedding (LM Studio/Ollama) accesible
- [ ] Configuración personalizada (`/opt/kb-rag/config/kb-rag.env`)
- [ ] Servicios habilitados y ejecutándose
- [ ] Health checks pasando (`curl localhost:8000/health/detailed`)
- [ ] Monitoreo Prometheus configurado (opcional)
- [ ] Reglas de alerta desplegadas (opcional)
- [ ] Backup programado (cron)
- [ ] Firewall configurado (si acceso externo necesario)
- [ ] SSL/TLS via reverse proxy (si acceso externo necesario)

Vea [docs/OPERATIONS.md](docs/OPERATIONS.md) para documentación completa de despliegue.

---

### 💻 Instalación

> **Para despliegue en producción**, vea la sección [Despliegue en Producción](#despliegue-en-producción) arriba para instalación automatizada con servicios systemd.

Esta sección cubre instalación manual para desarrollo.

#### Requisitos Previos

- Python 3.11, 3.12, 3.13 soportados
- Docker (para Qdrant) o Qdrant embedded
- LM Studio / Ollama / API de embedding compatible con OpenAI
- 8+ GB RAM (16+ GB recomendado)

#### Instalación para Desarrollo

**1. Clone el repositorio**

```bash
git clone https://github.com/MrLuciano/kb-rag-mcp
cd kb-rag-mcp
```

**2. Cree el entorno virtual**

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

**3. Instale dependencias**

```bash
# Usando pip-tools (recomendado)
pip install pip-tools
pip-sync requirements.txt

# O directamente con pip
pip install -r requirements.txt
```

**4. Configure el entorno**

```bash
# Copie el template
cp deployment/config/kb-rag.env.template .env

# Edite con sus configuraciones
vim .env
```

**5. Inicie Qdrant**

```bash
# Usando Docker
docker run -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/data/qdrant:/qdrant/storage \
  qdrant/qdrant

# O con Docker Compose
docker compose up -d
```

**6. Verifique la instalación**

```bash
# Inicie el servidor MCP
python -m kb_server.server

# En otro terminal, verifique la salud
kb-rag check health
curl http://localhost:8000/health/detailed
```

---

### ⚙️ Configuración

#### Variables de Entorno

Cree el archivo `.env` en la raíz del proyecto:

```bash
# Backend de Embedding
EMBED_BACKEND=openai-compat  # lmstudio-sdk, lmstudio-rest, openai-compat, ollama
EMBED_MODEL=text-embedding-nomic-embed-text-v1.5-embedding
LMS_BASE_URL=http://localhost:1234  # URL de LM Studio (sin /v1)
OLLAMA_HOST=http://localhost:11434

# Vector Store
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_PATH=  # Deje vacío para Docker, defina ruta para modo embedded
QDRANT_COLLECTION=kb_docs

# Configuraciones de Búsqueda
SCORE_THRESHOLD=0.35  # Score mínimo de relevancia (0.0-1.0)
DEFAULT_TOP_K=5       # Resultados predeterminados de búsqueda

# Transporte MCP
MCP_TRANSPORT=stdio   # stdio o sse
SSE_HOST=0.0.0.0      # Para modo SSE
SSE_PORT=8765

# Configuraciones de Caché
CACHE_BACKEND=lru     # lru o redis
CACHE_MAX_SIZE_MB=512 # Tamaño del caché LRU (auto si no definido)
CACHE_TTL=3600        # TTL del caché en segundos

# Procesamiento por Lotes
EMBED_BATCH_SIZE=32        # Tamaño del lote de embedding (25-64)
FILE_BATCH_SIZE=50         # Lote de procesamiento de archivos (50-100)
QDRANT_BATCH_SIZE=100      # Lote de upsert en Qdrant (80-200)
HTTP_POOL_CONNECTIONS=20   # Tamaño del pool de conexiones HTTP
MAX_CONCURRENT_UPLOADS=3   # Uploads concurrentes (1-5)

# Pool de Workers
WORKER_POOL_SIZE=4         # Cantidad de workers (predeterminado: 4)
WORKER_RATE_LIMIT=10       # Solicitudes/seg por worker (predeterminado: 10)

# Auto-Ingesta (File Watcher)
WATCH_PATH=                # Directorio para monitorear cambios
WATCH_DEBOUNCE_SECONDS=30  # Intervalo de debounce en segundos
WATCH_RECURSIVE=true       # Monitorear subdirectorios
WATCH_IGNORE_PATTERNS=     # Patrones glob separados por coma para ignorar

# Servidor de Salud
HEALTH_PORT=8000           # Puerto del servidor HTTP de health check

# General
LOG_LEVEL=INFO             # Nivel de logging (DEBUG, INFO, WARNING, ERROR)
```

#### Configuración del Cliente MCP

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
        "/home/SU_USUARIO/kb-rag-mcp/.venv/bin/python",
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
        "/ruta/a/kb-rag-mcp/.venv/bin/python",
        "-m", "kb_server.server"
      ]
    }
  }
}
```

---

### 📖 Uso

#### Ingesta de Documentos

```bash
# Usando la CLI kb-rag (recomendado)
kb-rag ingest --docs /ruta/a/docs

# O directamente con Python
source .venv/bin/activate
python ingest/ingest.py --docs /ruta/a/docs

# Con producto y vendor explícitos
python ingest/ingest.py --docs /ruta/a/docs --product MiProducto --vendor Acme

# Archivo único
python ingest/ingest.py --file /ruta/a/documento.pdf

# Limpiar y reingerir todo
python ingest/ingest.py --docs /ruta/a/docs --clean

# Más workers (use con GPU)
python ingest/ingest.py --docs /ruta/a/docs --workers 4

# Verificar estado de la ingesta via CLI
kb-rag status
kb-rag status --source /ruta/a/docs

# O los comandos de estado legacy
python ingest/ingest.py --status
python ingest/ingest.py --status --list    # Listar todos los archivos
python ingest/ingest.py --status --errors  # Solo errores
```

#### Estructura de Directorios Recomendada

```
docs/
├── producto-a/
│   ├── referencia-api.pdf
│   ├── primeros-pasos.docx
│   └── ejemplos/
│       └── ejemplo.py
├── producto-b/
│   ├── manual.pdf
│   └── config.xlsx
└── general/
    └── arquitectura.pptx
```

El producto se infiere automáticamente del nombre del directorio. Los documentos también se
auto-clasifican con metadatos de **vendor**, **subsistema** y **versión**
extraídos de nombres de archivo y estructura de directorios (vea características de Fase 11).

#### Auto-Ingesta

Monitoree directorios para cambios y dispare ingesta automáticamente:

```bash
# Iniciar servicio de file watcher
sudo systemctl start kb-rag-watcher

# O ejecutar standalone
python -m ingest.watcher.file_watcher

# Configure en .env
WATCH_PATH=/ruta/a/docs
WATCH_DEBOUNCE_SECONDS=30
```

**Vea [AUTO_INGESTION.md](docs/AUTO_INGESTION.md) para guía completa.**

#### Filtrado por Versión

Busque documentos por versión (extraída automáticamente de nombres de archivo/rutas):

```python
# Uso de la herramienta MCP
search_kb(
    query="pasos de instalación",
    product="AppServer",
    version="3.2"  # Solo buscar docs 3.2
)
```

**Patrones de versión soportados:**
- Numérico: `22.3`, `23.1.5`
- Prefijo CE: `CE 24.4`
- Prefijo v: `v2.5`
- Palabra clave version: `version 16.2`

**Vea [VERSION_FILTERING.md](docs/VERSION_FILTERING.md) para guía completa.**

#### Sobrescritura de Metadatos

Sobrescriba la clasificación automática con archivos `_meta.json`:

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

**Vea [METADATA_OVERRIDES.md](docs/METADATA_OVERRIDES.md) para guía completa.**

#### Reclasificación de Documentos

Cuando las reglas de clasificación mejoran (ej.: mejores patrones de detección de proveedor), puede actualizar metadatos de documentos ya ingeridos sin reprocesar o re-embeber:

##### Uso Básico

```bash
# Reclasificar archivos específicos
kb-ingest reclassify "docs/OpenText/*.pdf"

# Reclasificar por filtro de metadatos
kb-ingest reclassify "**/*.pdf" --filter 'vendor=""'

# Combinar patrón y filtro
kb-ingest reclassify "docs/OT*.pdf" --filter 'subsystem=""'

# Saltar confirmación (automatización)
kb-ingest reclassify "docs/**/*" --yes
```

##### Flujo de Verificación

Antes de reclasificar, verifique qué cambiaría:

```bash
# Verificar incompatibilidades
kb-ingest reclassify verify "docs/**/*.pdf"

# Muestra:
# - Documentos con incompatibilidades de metadatos
# - Valores actuales vs. esperados
# - Detalle por documento
```

Después de reclasificar, verifique si los cambios se aplicaron:

```bash
kb-ingest reclassify verify "docs/**/*.pdf"
# Debería mostrar: "Todos los documentos coinciden con las clasificaciones esperadas"
```

##### Reversión

Si la reclasificación produce resultados inesperados, revierta a los metadatos anteriores:

```bash
# Listar sesiones de respaldo
kb-ingest reclassify sessions

# Revertir sesión completa
kb-ingest reclassify rollback --session 2026-05-26T15-30-00

# Reversión selectiva (patrón + timestamp)
kb-ingest reclassify rollback "docs/OT*.pdf" --before 2026-05-26T16-00-00
```

Los respaldos se mantienen por 30 días de forma predeterminada (configurable mediante `RECLASSIFY_BACKUP_RETENTION_DAYS`).

##### Cómo Funciona

1. **Detectar Cambios:** Ejecuta `classify()` en los documentos coincidentes, compara con metadatos actuales de Qdrant
2. **Vista Previa:** Muestra resumen agregado por campo (ej.: "vendor: 47 docs ('' → 'OpenText')")
3. **Respaldo:** Escribe metadatos antiguos en SQLite (`data/registry.db`) para reversión
4. **Actualizar:** Actualiza campos de payload de Qdrant in-place (preserva vectores)
5. **Auditoría:** Registra cambios en la tabla `reclassify_history` para seguimiento

##### Opciones

| Flag | Descripción |
|------|-------------|
| `--collection <nombre>` | Dirigir a una colección Qdrant específica |
| `--filter <expr>` | Filtro de metadatos (ej.: `vendor=""`) |
| `--yes` / `-y` | Saltar prompt de confirmación |
| `--allow-missing` | Procesar documentos incluso si falta el archivo fuente |
| `--include-custom` | Actualizar campos personalizados además de campos de clasificación |
| `--no-progress` | Deshabilitar barra de progreso (para scripts) |

##### Características de Seguridad

- **Confirmación interactiva:** Muestra vista previa antes de hacer cambios (use `--yes` para saltar)
- **Respaldo automático:** Metadatos antiguos guardados en SQLite antes de las actualizaciones
- **Seguimiento de sesión:** Todos los respaldos vinculados al timestamp de sesión para reversión completa
- **Registro de auditoría:** Todos los cambios registrados en tabla `reclassify_history`
- **Retención de 30 días:** Respaldos limpiados automáticamente después de 30 días (configurable)

##### Flujos de Trabajo Comunes

**Escenario 1: Detección de proveedor mejorada**

La Fase 11 se lanzó con inferencia básica de proveedor, dejando muchos documentos con el campo `vendor` vacío. Después de mejorar los patrones de `VENDOR_MAP`:

```bash
# Verificar qué cambiaría
kb-ingest reclassify verify "**/*" --filter 'vendor=""'

# Muestra 47 documentos que cambiarían vendor → "OpenText"

# Aplicar cambios
kb-ingest reclassify "**/*" --filter 'vendor=""' --yes
```

**Escenario 2: Corregir documentos clasificados incorrectamente**

Algunos PDFs fueron incorrectamente clasificados como `doc_type="overview"` cuando deberían ser `"admin_guide"`:

```bash
# Verificar estado actual
kb-ingest reclassify verify "docs/admin/*.pdf"

# Reclasificar (después de actualizar reglas de doc_type en classifier.py)
kb-ingest reclassify "docs/admin/*.pdf"

# Verificar corrección
kb-ingest reclassify verify "docs/admin/*.pdf"
```

**Escenario 3: Reversión después de regresión de clasificación**

El cambio de regla de clasificación introdujo valores incorrectos de subsystem:

```bash
# Verificar sesiones recientes
kb-ingest reclassify sessions

# Muestra sesión 2026-05-26T15-30-00 con 50 docs modificados

# Revertir sesión completa
kb-ingest reclassify rollback --session 2026-05-26T15-30-00
```

##### Solución de Problemas

**"No se detectaron cambios de clasificación"**

Posibles causas:
- Las reglas de clasificación no han cambiado desde la última ingestión
- El patrón no coincide con ningún documento en Qdrant
- Filtro de metadatos demasiado restrictivo

Solución: Ejecute `verify` para ver valores actuales vs. esperados

**"Archivo fuente no encontrado en disco"**

Por defecto, reclassify omite documentos donde falta el archivo fuente (archivo fuente necesario para ejecutar `classify()`). Si los archivos se movieron o quiere reclasificar usando solo metadatos de Qdrant:

```bash
kb-ingest reclassify "**/*" --allow-missing
```

**Sesión de reversión no encontrada**

Las sesiones con más de 30 días se limpian automáticamente. Ajuste la retención:

```bash
export RECLASSIFY_BACKUP_RETENTION_DAYS=90
kb-ingest reclassify "**/*"
```

---

### 🏥 Verificaciones de Salud

KB-RAG incluye un sistema integral de health check que monitorea todos los componentes.

#### Endpoints de Salud

El servidor de salud ejecuta en puerto 8000 (configurable via `HEALTH_PORT`) y proporciona:

```bash
# Salud básica - para load balancers
GET /health
→ {"status": "ok", "service": "kb-rag"}

# Salud detallada - para dashboards de monitoreo
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
→ {"ready": true}  # 200 si listo, 503 si no

# Probe de liveness - estilo Kubernetes
GET /alive
→ {"alive": true}  # Siempre 200 si responde
```

#### Verificaciones de Componentes

| Componente | Verificaciones | Crítico | Detalles |
|-----------|--------|----------|---------|
| **embedding** | Servicio alcanzable, embedding de prueba | Sí | Backend, modelo, dimensiones |
| **vector_store** | Conexión Qdrant, colección existe | Sí | Total de fragmentos, documentos |
| **cache** | Estadísticas disponibles | No | Backend, entradas, hit rate |
| **database** | SQLite accesible, queries funcionan | Sí | Conteo de jobs, archivos |
| **filesystem** | Acceso lectura/escritura, espacio en disco | No | Espacio libre (aviso < 10%) |

**Nota:** Modelo cross-encoder de reranking es lazy-loaded (no verificado en probe de salud) — carga en primera query de reranking (~10s más rápido en inicio).

#### Scripts de Health Check

```bash
# Verificar todos los servicios
./deployment/scripts/health-check.sh all

# Verificar servicio específico
./deployment/scripts/health-check.sh server
./deployment/scripts/health-check.sh health
./deployment/scripts/health-check.sh scheduler

# Códigos de salida: 0=saludable, 1=no saludable, 2=error
```

#### Servidor de Salud Manual

Para desarrollo sin systemd:

```bash
# Iniciar servidor de salud
python -m kb_server.health_server

# O use la CLI
kb-rag check health

# En otro terminal, verifique la salud
curl http://localhost:8000/health/detailed | jq
```

---

### ⚙️ Gestión de Servicios

> **Nota:** Gestión de servicios requiere despliegue en producción con systemd. Vea [Despliegue en Producción](#despliegue-en-producción).

#### Comandos Básicos

```bash
# Iniciar todos los servicios KB-RAG
sudo systemctl start kb-rag.target

# Detener todos los servicios KB-RAG
sudo systemctl stop kb-rag.target

# Reiniciar todos los servicios KB-RAG
sudo systemctl restart kb-rag.target

# Verificar estado general
sudo systemctl status kb-rag.target
```

#### Servicios Individuales

```bash
# Servidor MCP (servicio principal)
sudo systemctl status kb-rag-server
sudo systemctl restart kb-rag-server

# Servidor de Health Check
sudo systemctl status kb-rag-health
sudo systemctl restart kb-rag-health

# File Watcher (auto-ingesta)
sudo systemctl status kb-rag-watcher
sudo systemctl restart kb-rag-watcher

# Agendador de Jobs
sudo systemctl status kb-rag-scheduler
sudo systemctl restart kb-rag-scheduler
```

#### Visualizando Logs

```bash
# Seguir todos los logs
sudo journalctl -u kb-rag-server -u kb-rag-health -f

# Solo logs del servidor MCP
sudo journalctl -u kb-rag-server -f

# Últimas 100 líneas
sudo journalctl -u kb-rag-server -n 100

# Desde horario específico
sudo journalctl -u kb-rag-server --since "1 hour ago"

# Con filtro de nivel de log
sudo journalctl -u kb-rag-server -p err  # Solo errores
sudo journalctl -u kb-rag-server -p warning  # Warnings y superiores
```

#### Verificaciones de Estado de Servicio

```bash
# Verificar si servicio está ejecutándose
systemctl is-active kb-rag-server  # active o inactive

# Verificar si servicio está habilitado (auto-start)
systemctl is-enabled kb-rag-server  # enabled o disabled

# Estado completo con logs recientes
sudo systemctl status kb-rag.target --no-pager

# Uso de recursos
systemd-cgtop -1 | grep kb-rag
```

#### Configuración de Auto-Restart

Servicios reinician automáticamente en caso de fallo con estas configuraciones:

- **Política de Restart**: `always` (reinicia en cualquier salida)
- **Retraso de Restart**: 10 segundos entre intentos
- **Límite de Burst**: 3 intentos en 5 minutos
- **Recuperación**: Después de 5 minutos, resetea contador de fallos

Ver historial de restarts:

```bash
# Verificar conteo de restarts
systemctl show kb-rag-server -p NRestarts

# Ver fallos de servicio
systemctl list-units --failed | grep kb-rag
```

---

### 🔧 Herramientas MCP

#### `search_kb`

Búsqueda semántica en la base de conocimiento.

**Parámetros:**
- `query` (requerido): Query de búsqueda
- `top_k` (opcional): Número de resultados (1-20, predeterminado: 5)
- `product` (opcional): Filtrar por producto
- `vendor` (opcional): Filtrar por vendor (auto-clasificado de nombres de archivo)
- `subsystem` (opcional): Filtrar por subsistema (auto-clasificado de nombres de archivo)
- `doc_type` (opcional): Filtrar por tipo de documento
- `filter_type` (opcional): Filtrar por formato de archivo (pdf, docx, xlsx, pptx, txt, code)
- `version` (opcional): Filtrar por versión de documento

**Retorna:** Lista de fragmentos con `chunk_id`, `score`, `text`, `source_file`,
`product`, `vendor`, `subsystem`, `doc_type`, `file_type`, `page`, `version`.

#### `list_documents`

Lista documentos indexados con filtros opcionales.

**Parámetros:**
- `product` (opcional): Filtrar por producto
- `vendor` (opcional): Filtrar por vendor
- `subsystem` (opcional): Filtrar por subsistema
- `doc_type` (opcional): Filtrar por tipo de documento
- `filter_type` (opcional): Filtrar por formato de archivo

**Retorna:** Documentos agrupados por `doc_type`.

#### `get_chunk`

Recupera fragmento completo con contexto alrededor.

**Parámetros:**
- `chunk_id` (requerido): ID del fragmento de resultados de búsqueda
- `context_window` (opcional): Número de fragmentos vecinos (0-3, predeterminado: 1)

**Retorna:** Fragmento con contexto.

#### `kb_stats`

Estadísticas de la base de conocimiento.

**Retorna:** Total de documentos, fragmentos, breakdown por doc_type y formato de archivo.

---

### 🏗️ Arquitectura

```
Documentos (PDF, DOCX, XLSX, PPTX, TXT, código)
    ↓  ingest/ingest.py
Extracción de Texto → Chunking → Embedding (LM Studio / Ollama)
    ↓
Qdrant (almacén de vectores)
    ↓
kb_server/server.py ←→ MCP (stdio o SSE)
    ↓
Claude Code / OpenCode
```

**Componentes:**

- **Gestión de Jobs**: Cola de jobs basada en SQLite con programación por prioridad
- **Pool de Workers**: Pool de workers asíncronos con rate limiting
- **Observabilidad**: Métricas Prometheus, logging estructurado, seguimiento de progreso
- **Sistema de Caché**: Caché LRU con auto-ajuste de RAM o backend Redis
- **Extractores de Documentos**: Soporte multi-formato (PDF via PyMuPDF/docling)
- **Clasificador**: Detección automática de producto y doc_type via regex
- **Clasificación automática**: Inferencia de vendor, subsistema, versión desde nombres de archivo y rutas
- **Cross-encoder reranker**: Lazy-loaded en primera query de reranking (~10s más rápido en inicio)

---

### 👨‍💻 Desarrollo

#### Requisitos

Vea `requirements.in` para dependencias legibles por humanos.

#### Ejecutando Pruebas

```bash
pytest tests/ -v

# Con cobertura
pytest tests/ --cov=kb_server --cov=ingest --cov=observability --cov-branch --cov-report=term-missing

# Cobertura con validación de umbral (90% cobertura branch necesaria)
pytest tests/ --cov=kb_server --cov=ingest --cov-branch --cov-fail-under=90

# Archivo de prueba específico
pytest tests/test_job_system.py -v
```

**Baseline de pruebas:** 585 pruebas core (excluyendo handler SSE y pruebas e2e)

#### Calidad de Código

```bash
# Formatear código
black kb_server/ ingest/ scripts/ tests/
isort kb_server/ ingest/ scripts/ tests/

# Lint
flake8 kb_server/ ingest/ scripts/ tests/

# Type check
mypy kb_server/ ingest/ scripts/

# Auditoría de logging (garantizar que todos los métodos públicos tienen llamadas de log)
python scripts/logging-audit.py

# Auditoría de inglés (validar cero portugués en archivos fuente)
python scripts/docstring-audit.py --check-inline
```

#### Agregando Dependencias

```bash
# Edite requirements.in
vim requirements.in

# Compile e instale
pip-compile requirements.in
pip-sync requirements.txt
```

---

### 📚 Documentación

**Guías del Usuario:**
- [AUTO_INGESTION.md](docs/AUTO_INGESTION.md) - File watching automático e ingesta
- [METADATA_OVERRIDES.md](docs/METADATA_OVERRIDES.md) - Sobrescribir clasificación con _meta.json
- [VERSION_FILTERING.md](docs/VERSION_FILTERING.md) - Búsqueda por versión de documento
- [SEARCH_QUALITY.md](docs/SEARCH_QUALITY.md) - Búsqueda híbrida y reranking
- [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Problemas comunes y soluciones

**Documentación Técnica:**
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Arquitectura y diseño del sistema
- [OPERATIONS.md](docs/OPERATIONS.md) - Despliegue y operaciones en producción
- [TESTING.md](docs/TESTING.md) - Estrategia de pruebas
- [INDEX.md](docs/INDEX.md) - Índice de documentación
- [REFERENCE.md](docs/REFERENCE.md) - Referencia de API
- [KUBERNETES.md](docs/KUBERNETES.md) - Guía de despliegue Kubernetes

---

### 📊 Monitoreo

KB-RAG proporciona monitoreo integral a través de métricas Prometheus, health checks y logging estructurado.

#### Métricas Prometheus

Las métricas se exponen en `http://localhost:8000/metrics` (servidor de salud).

**Métricas Disponibles (28 total):**

```bash
# Gestión de Jobs (4 métricas)
kb_rag_jobs_created_total          # Contador de jobs creados
kb_rag_jobs_completed_total        # Contador de jobs completados
kb_rag_jobs_active                 # Gauge de jobs actualmente activos
kb_rag_job_duration_seconds        # Histograma de duración de job

# Procesamiento de Archivos (3 métricas)
kb_rag_files_processed_total      # Contador de archivos procesados
kb_rag_files_processing_time_seconds  # Histograma de procesamiento de archivo
kb_rag_chunks_generated_total     # Contador de fragmentos generados

# Pool de Workers (6 métricas)
kb_rag_worker_pool_size            # Gauge de tamaño del pool de workers
kb_rag_worker_pool_queue_size     # Gauge de tamaño de la cola
kb_rag_worker_pool_utilization    # Gauge de utilización del pool
kb_rag_rate_limiter_tokens        # Gauge de tokens disponibles
kb_rag_rate_limiter_waits_total   # Contador de esperas por rate limit
kb_rag_rate_limiter_wait_time_seconds  # Histograma de tiempo de espera

# Solicitudes de API (2 métricas)
kb_rag_api_requests_total         # Contador de solicitudes de API
kb_rag_api_latency_seconds        # Histograma de latencia de API

# Rendimiento de Caché (5 métricas)
kb_rag_cache_hits_total           # Contador de cache hits
kb_rag_cache_misses_total         # Contador de cache misses
kb_rag_cache_evictions_total      # Contador de evictions de caché
kb_rag_cache_size_bytes           # Gauge de tamaño del caché
kb_rag_cache_entries              # Gauge de conteo de entradas del caché

# Procesamiento por Lotes (8 métricas)
kb_rag_batch_embeddings_total          # Operaciones de embedding por lotes
kb_rag_batch_embedding_texts_total     # Textos embedded en lotes
kb_rag_batch_embedding_duration_seconds  # Duración de embedding por lotes
kb_rag_batch_upserts_total            # Operaciones de upsert por lotes
kb_rag_batch_upsert_points_total      # Points upserted en lotes
kb_rag_batch_upsert_duration_seconds  # Duración de upsert por lotes
kb_rag_http_pool_connections          # Tamaño del pool de conexiones HTTP
kb_rag_batch_processing_throughput    # Gauge de throughput de procesamiento
```

#### Configuración de Prometheus

```yaml
# Agregue a prometheus.yml
scrape_configs:
  - job_name: 'kb-rag'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s
```

O use la configuración proporcionada:

```bash
# Copie a directorio de config de Prometheus
sudo cp deployment/config/prometheus.yml /etc/prometheus/
sudo cp deployment/config/kb-rag-alerts.yml /etc/prometheus/

# Recargue Prometheus
sudo systemctl reload prometheus
```

#### Reglas de Alerta

11 reglas de alerta preconfiguradas en `deployment/config/kb-rag-alerts.yml`:

**Alertas de Salud (Crítico):**
- Servidor caído por 2+ minutos
- Alta tasa de error (>10 errores/seg por 5 min)
- Servicio de embedding no saludable (3+ min)
- Almacén de vectores no saludable (3+ min)

**Alertas de Rendimiento (Warning):**
- Alta latencia (P95 > 5s por 10 min)
- Baja tasa de hit de caché (<50% por 15 min)

**Alertas de Recursos:**
- Alto uso de memoria (>90% por 10 min)
- Poco espacio en disco (<10% por 5 min)

**Alertas de Jobs:**
- Jobs atascados (ejecutándose pero sin progreso por 30 min)
- Alta tasa de fallo de jobs (>0.1/seg por 10 min)

#### Dashboard Grafana

Importe dashboard desde `deployment/config/grafana-dashboard.json` (próximamente).

Paneles principales:
- Estado de salud del servicio
- Tasa de solicitudes y latencia
- Tasa de hit y tamaño del caché
- Cola de jobs y throughput
- Uso de recursos (CPU, memoria, disco)
- Tasas de error

#### Logging Estructurado

Los logs se escriben en formato JSON para parsing fácil:

```bash
# Ver logs estructurados
sudo journalctl -u kb-rag-server -o json-pretty

# Extraer campos específicos
sudo journalctl -u kb-rag-server -o json | \
  jq -r 'select(.PRIORITY=="3") | .MESSAGE'  # Solo errores

# Buscar por componente
sudo journalctl -u kb-rag-server | grep '"component":"cache"'
```

#### Rotación de Logs

Rotación automática de logs configurada via `/etc/logrotate.d/kb-rag`:

- **Frecuencia**: Diaria
- **Retención**: 14 días
- **Compresión**: gzip (retrasada 1 día)
- **Tamaño máximo**: 100MB por archivo
- **Logs de acceso**: 7 días, 500MB máximo

Rotación manual:

```bash
# Forzar rotación
sudo logrotate -f /etc/logrotate.d/kb-rag

# Probar configuración
sudo logrotate -d /etc/logrotate.d/kb-rag
```

---

### 🛠️ Operaciones

#### Backup y Restore

**Crear Backup:**

```bash
# Backup con nombre automático
./deployment/scripts/backup.sh

# Ruta personalizada
./deployment/scripts/backup.sh /backups/kb-rag-20260515.tar.gz
```

El backup incluye:
- Bases de datos SQLite (metadatos de job, registro de archivos)
- Archivos de configuración
- Logs recientes (últimos 7 días)

**Restaurar desde Backup:**

```bash
sudo ./deployment/scripts/restore.sh /ruta/a/backup.tar.gz
```

Características de seguridad:
- Backup automático pre-restauración
- Orquestación de detención/inicio de servicios
- Restauración de permisos
- Verificación de salud

**Backups Programados:**

```bash
# Agregue a /etc/cron.daily/kb-rag-backup
#!/bin/bash
/opt/kb-rag/deployment/scripts/backup.sh \
  /backups/kb-rag-$(date +%Y%m%d).tar.gz

# Limpieza de backups antiguos (mantener 30 días)
find /backups -name "kb-rag-*.tar.gz" -mtime +30 -delete
```

#### Actualizaciones

**Actualizar a Versión Más Reciente:**

```bash
sudo ./deployment/scripts/update.sh
```

Proceso de actualización:
1. Crear backup pre-actualización
2. Detener servicios
3. Git pull de cambios más recientes
4. Actualizar dependencias
5. Actualizar servicios systemd
6. Reiniciar servicios
7. Verificar salud
8. Rollback en caso de fallo (automático)

**Actualizar a Versión Específica:**

```bash
sudo ./deployment/scripts/update.sh v1.3
```

#### Tareas de Mantenimiento

**Limpiar Jobs Antiguos:**

```bash
# Limpiar jobs completados con más de 30 días
python3 -m ingest.cli job clean --days 30

# Dry run (solo visualización)
python3 -m ingest.cli job clean --days 30 --dry-run
```

**Reconstruir Índice:**

```bash
# Reingerir todos los documentos (lento)
python3 -m ingest.ingest --docs /ruta/a/docs --clean
```

**Gestión de Caché:**

```bash
# Limpiar caché (reiniciar servicio)
sudo systemctl restart kb-rag-server

# Verificar estadísticas de caché
curl http://localhost:8000/health/detailed | jq '.components.cache'
```

#### Optimización de Rendimiento

**Procesamiento por Lotes:**

Ajuste via variables de entorno en `/opt/kb-rag/config/kb-rag.env`:

```bash
# Tamaño del lote de embedding (25-64 recomendado)
EMBED_BATCH_SIZE=32

# Lote de procesamiento de archivo (50-100 recomendado)
FILE_BATCH_SIZE=50

# Lote de upsert en Qdrant (80-200 recomendado)
QDRANT_BATCH_SIZE=100

# Conexiones HTTP (20-50 recomendado)
HTTP_POOL_CONNECTIONS=20

# Uploads concurrentes (1-5 recomendado)
MAX_CONCURRENT_UPLOADS=3
```

**Pool de Workers:**

```bash
# Aumentar workers para ingesta más rápida
WORKER_POOL_SIZE=8  # Predeterminado: 4

# Ajustar rate limit (solicitudes/seg por worker)
WORKER_RATE_LIMIT=20  # Predeterminado: 10
```

**Caché:**

```bash
# Aumentar tamaño del caché
CACHE_MAX_SIZE_MB=1024  # Predeterminado: auto (10% RAM)

# Usar Redis para caché distribuido
CACHE_BACKEND=redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

#### Solución de Problemas

**Servicio No Inicia:**

```bash
# Verificar estado del servicio
sudo systemctl status kb-rag-server

# Ver logs recientes
sudo journalctl -u kb-rag-server -n 100

# Verificar configuración
sudo cat /opt/kb-rag/config/kb-rag.env | grep -v "^#"

# Verificar dependencias
/opt/kb-rag/venv/bin/python3 -m pip check
```

**Alto Uso de Memoria:**

```bash
# Verificar uso actual
systemctl show kb-rag-server -p MemoryCurrent

# Reducir tamaño del caché
sudo nano /opt/kb-rag/config/kb-rag.env
# Defina: CACHE_MAX_SIZE_MB=256

sudo systemctl restart kb-rag-server
```

**Rendimiento Lento:**

```bash
# Verificar salud y latencia de componentes
curl http://localhost:8000/health/detailed | jq

# Monitorear uso de recursos
systemd-cgtop | grep kb-rag

# Verificar tasa de hit del caché (debe ser >80%)
curl http://localhost:8000/health/detailed | \
  jq '.components.cache.details.hit_rate'
```

**Para guía completa de solución de problemas con 40+ escenarios, vea [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).**

---

### 🛠️ Solución de Problemas

> **📖 Vea [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) para la guía completa de solución de problemas con 40+ escenarios, comandos de diagnóstico y soluciones.**

**Soluciones Rápidas:**

**API de embedding no responde:**
```bash
# Verificar si LM Studio está ejecutándose y modelo cargado
curl http://localhost:1234/v1/models

# Verificar Ollama
curl http://localhost:11434/api/tags
```

**Error de conexión con Qdrant:**
```bash
# Verificar si Qdrant está ejecutándose
docker ps | grep qdrant
curl http://localhost:6333/healthz
```

**Sin resultados de búsqueda:**
- Verificar `SCORE_THRESHOLD` (reduzca si es muy estricto)
- Verificar si documentos están indexados: `kb-rag status` o `python ingest/ingest.py --status`
- Verificar si query está en idioma correcto

**Ingesta lenta:**
- Reducir `--workers` si está limitado por CPU
- Verificar si API de embedding no está sobrecargada
- Considerar usar GPU para LM Studio

---

### 📝 Licencia

Licencia MIT

Copyright (c) 2026 Contribuidores del Servidor MCP KB-RAG

Se concede permiso, de forma gratuita, a cualquier persona que obtenga una copia
de este software y archivos de documentación asociados (el "Software"), para tratar
con el Software sin restricciones, incluyendo sin limitación los derechos de usar,
copiar, modificar, fusionar, publicar, distribuir, sublicenciar y/o vender
copias del Software, y permitir que las personas a quienes se les proporcione el Software
lo hagan, sujeto a las siguientes condiciones:

El aviso de copyright anterior y este aviso de permiso deben incluirse en todas
las copias o porciones sustanciales del Software.

EL SOFTWARE SE PROPORCIONA "TAL CUAL", SIN GARANTÍA DE NINGÚN TIPO, EXPRESA O
IMPLÍCITA, INCLUYENDO PERO NO LIMITÁNDOSE A LAS GARANTÍAS DE COMERCIABILIDAD,
IDONEIDAD PARA UN PROPÓSITO PARTICULAR Y NO INFRACCIÓN. EN NINGÚN CASO LOS AUTORES O
TITULARES DE DERECHOS DE AUTOR SERÁN RESPONSABLES DE NINGUNA RECLAMACIÓN, DAÑOS U OTRA
RESPONSABILIDAD, YA SEA EN UNA ACCIÓN DE CONTRATO, AGRAVIO O DE OTRA MANERA, QUE SURJA
DE, FUERA DE O EN CONEXIÓN CON EL SOFTWARE O EL USO U OTRAS NEGOCIACIONES EN EL
SOFTWARE.

---

### 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Por favor, lea [CONTRIBUTING.md](CONTRIBUTING.md) primero.
