"""
Classificador de conteúdo da KB.

Infere dimensões a partir do nome do arquivo e caminho:
  - product  : produto/sistema ao qual o documento pertence
  - doc_type : tipo de conteúdo (admin_guide, standard, training, etc.)
  - version  : versão extraída do nome do arquivo/diretório (FASE 13)

FASE 13: Suporta metadata overrides via _meta.json em diretórios.

Nenhuma reorganização de pastas é necessária — tudo é inferido
por padrões no nome do arquivo e estrutura de diretórios existente.
"""

import re
from pathlib import Path

# ── Taxonomia de doc_type ──────────────
# --------------------------------------
# Cada entrada: (prioridade, doc_type, [padrões regex no nome do arquivo])
# Maior prioridade = verificado primeiro.

DOC_TYPE_RULES: list[tuple[int, str, list[str]]] = [
    # Padrões ISO / normas / regulamentos
    (
        100,
        "standard",
        [
            r"\biso\b",
            r"\biso[-_]\d+",
            r"15489",
            r"lgpd",
            r"lei.geral",
            r"gdpr",
            r"nist",
            r"compliance",
            r"regulation",
        ],
    ),
    # Release notes
    (
        90,
        "release_notes",
        [
            r"release.?notes?",
            r"relnotes?",
            r"what.?s.?new",
            r"patch.?notes?",
            r"changelog",
        ],
    ),
    # Guias de upgrade / migração
    (
        85,
        "upgrade_guide",
        [
            r"upgrad",
            r"migrat",
            r"update.instal",
            r"migration",
        ],
    ),
    # Guias de instalação
    (
        80,
        "install_guide",
        [
            r"install",
            r"installation",
            r"setup.guide",
            r"deploy",
            r"getting.started",
            r"\bigi\b",
            r"\bigu\b",
            r"\biasw\b",
            r"\bigw\b",
            r"\bigd\b",
        ],
    ),
    # Guias de administração
    (
        75,
        "admin_guide",
        [
            r"admin",
            r"administration",
            r"system.admin",
            r"sysadmin",
            r"\bacn\b",
            r"\bagd\b",
            r"operator",
        ],
    ),
    # Guias de configuração / cenários
    (
        70,
        "config_guide",
        [
            r"config",
            r"configuration",
            r"scenario",
            r"setup",
            r"\bcgd\b",
            r"\bist\b",
            r"storm.config",
            r"cookbook",
            r"how.to",
            r"howto",
        ],
    ),
    # Guias de usuário
    (
        65,
        "user_guide",
        [
            r"user.?guide",
            r"user.?manual",
            r"\bugd\b",
            r"end.user",
            r"manual.do.usu",
            r"guia.do.usu",
        ],
    ),
    # Guias de API / SDK / programação
    (
        60,
        "api_guide",
        [
            r"\bapi\b",
            r"\bsdk\b",
            r"programm",
            r"developer",
            r"integration",
            r"web.service",
            r"\brest\b",
            r"\bsoap\b",
            r"\bpsa\b",
            r"interface",
            r"endpoints?",
        ],
    ),
    # Case studies / howto / troubleshooting
    (
        55,
        "howto",
        [
            r"case.study",
            r"how.to",
            r"howto",
            r"troubleshoot",
            r"cookbook",
            r"recipe",
            r"tip",
            r"trick",
            r"best.practice",
            r"reverse.proxy",
            r"ha.proxy",
            r"\bkb\d{5,}",
            r"knowledge.base",
        ],
    ),
    # Treinamentos / apresentações educacionais
    (
        50,
        "training",
        [
            r"training",
            r"vilt",
            r"webinar",
            r"workshop",
            r"course",
            r"module\s*\d",
            r"day\s*\d",
            r"lab",
            r"study.guide",
            r"learn",
            r"tutorial",
            r"enablement",
            r"certification",
            r"certificate",
        ],
    ),
    # Apresentações / visão geral
    (
        45,
        "overview",
        [
            r"overview",
            r"introduction",
            r"intro\b",
            r"what.is",
            r"understanding",
            r"fundamentals?",
            r"concepts?",
            r"architecture",
            r"whitepaper",
            r"datasheet",
            r"presentation",
            r"comprehensive",
            r"portfolio",
        ],
    ),
    # Documentos de referência técnica / terminologia
    (
        40,
        "reference",
        [
            r"technical.paper",
            r"terminolog",
            r"glossar",
            r"reference",
            r"spec",
            r"specification",
            r"technical.note",
            r"technote",
        ],
    ),
    # Notas de reunião / sessões gravadas
    (
        35,
        "meeting",
        [
            r"meeting.recording",
            r"recording",
            r"session",
            r"clickthrough",
            r"knowledge.sharing",
        ],
    ),
    # Artefatos binários / pacotes
    (
        10,
        "release_artifact",
        [
            r"\.zip$",
            r"\.patch$",
            r"pat\d{9,}",
            r"p-ar-center",
            r"schema.and.pre.upgrade",
        ],
    ),
]

# ── Mapeamento de pasta raiz → produto ───────────────────────────────────────
# Complementa a detecção automática por pasta com aliases

PRODUCT_ALIASES: dict[str, str] = {
    "appserver": "AppServer",
    "app server": "AppServer",
    "datasync": "DataSync",
    "data sync": "DataSync",
    "adminportal": "AdminPortal",
    "admin portal": "AdminPortal",
    "adobe": "Adobe",
    "reccordsmanagement": "RecordsManagement",
    "records management": "RecordsManagement",
    "varios": "geral",
    "templates": "geral",
    # ── OTCS Product Aliases (Phase 8) ──
    "contentserver": "ContentServer",
    "content server": "ContentServer",
    "webreports": "WebReports",
    "web reports": "WebReports",
    "xecm": "xECM",
    "extended ecm": "xECM",
    "extendedecm": "xECM",
    "workflow": "Workflow",
    "cside": "CSIDE",
    "content server ide": "CSIDE",
    "brava": "Brava",
    "ot2": "OT2",
    "documentviewer": "DocumentViewer",
    "document viewer": "DocumentViewer",
    "apigateway": "APIGateway",
    "api gateway": "APIGateway",
    "archivecenter": "ArchiveCenter",
    "archive center": "ArchiveCenter",
}

# Padrões de produto inferíveis do próprio nome do arquivo
PRODUCT_FROM_NAME: list[tuple[str, list[str]]] = [
    ("AppServer", [r"app.?server", r"\bappserver\b"]),
    ("DataSync", [r"data.?sync", r"\bdatasync\b"]),
    ("AdminPortal", [r"admin.?portal", r"\badminportal\b"]),
    ("DocumentFilters", [r"document.filters"]),
    ("TeleForm", [r"teleform"]),
    ("Adobe", [r"\badobe\b", r"adobe.sign", r"docusign"]),
    ("SAP", [r"\bsap\b", r"successfactors", r"archiving.and.document.access"]),
    ("ISO", [r"\biso[-_]\d+", r"15489", r"irish.version"]),
    (
        "RecordsManagement",
        [r"records?.management", r"file.plan", r"lgpd", r"lei.geral"],
    ),
    ("Apache", [r"\bapache\b"]),
    ("Gradle", [r"\bgradle\b"]),
    ("CMIS", [r"\bcmis\b"]),
    # ── OTCS Product Filename Patterns (Phase 8) ──
    ("WebReports", [r"webreport", r"web.?report"]),
    ("xECM", [r"\bxecm\b", r"extended.?ecm"]),
    ("Workflow", [r"\bworkflow\b"]),
    ("CSIDE", [r"\bcside\b", r"content.?server.?ide"]),
    ("ContentServer", [r"content.?server"]),
    ("Brava", [r"\bbrava\b"]),
    ("OT2", [r"\bot2\b"]),
    ("DocumentViewer", [r"document.?viewer", r"doc.?viewer"]),
    ("APIGateway", [r"api.?gateway", r"apigateway"]),
    ("ArchiveCenter", [r"archive.?center", r"archivecenter"]),
]


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES PÚBLICAS
# ─────────────────────────────────────────────────────────────────────────────


def infer_doc_type(file_path: Path) -> str:
    """
    Infere o doc_type a partir do nome do arquivo e do caminho completo.
    Retorna o doc_type de maior prioridade que corresponder, ou 'document'.
    """
    # Usa nome + caminho completo como texto de busca, tudo em minúsculas
    text = (file_path.stem + " " + str(file_path)).lower()
    # Substitui separadores por espaço para facilitar matching
    text = re.sub(r"[_\-/\\]", " ", text)

    # Extensão de arquivo sem conteúdo textual → artifact
    if file_path.suffix.lower() in (
        ".zip",
        ".patch",
        ".mp4",
        ".avi",
        ".jpg",
        ".png",
    ):
        return "release_artifact"

    # Avalia regras por ordem de prioridade (maior primeiro)
    best_priority = -1
    best_type = "document"

    for priority, doc_type, patterns in DOC_TYPE_RULES:
        if priority <= best_priority:
            continue
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                best_priority = priority
                best_type = doc_type
                break

    return best_type


def infer_product(
    file_path: Path, docs_root: Path, product_override: str | None = None
) -> str:
    """
    Infere o produto a partir de:
    1. Override explícito (--product na CLI)
    2. Pasta raiz relativa a docs_root
    3. Nome do arquivo (padrões conhecidos)
    4. Fallback: 'geral'
    """
    if product_override:
        return product_override

    # Pasta raiz
    try:
        relative = file_path.relative_to(docs_root)
        root_folder = (
            relative.parts[0].lower() if len(relative.parts) > 1 else ""
        )
    except ValueError:
        root_folder = ""

    if root_folder:
        # Lookup direto no alias map
        if root_folder in PRODUCT_ALIASES:
            return PRODUCT_ALIASES[root_folder]
        # Partial match
        for alias, product in PRODUCT_ALIASES.items():
            if alias in root_folder or root_folder in alias:
                return product
        # Usa o nome da pasta com capitalização se não estiver no alias
        if root_folder not in ("varios", "templates", "archive"):
            return relative.parts[0]  # preserva capitalização original

    # Tenta pelo nome do arquivo
    name_lower = re.sub(r"[_\-]", " ", file_path.stem.lower())
    for product, patterns in PRODUCT_FROM_NAME:
        for pattern in patterns:
            if re.search(pattern, name_lower, re.IGNORECASE):
                return product

    return "geral"


def classify(
    file_path: Path,
    docs_root: Path,
    product_override: str | None = None,
) -> dict[str, str]:
    """
    Retorna dict com product, doc_type e version inferidos.
    Ponto de entrada único usado pelo ingest.py.

    FASE 13: Integra version extractor e meta loader.

    Precedência para product/doc_type:
    1. Override de _meta.json file-specific
    2. Override de _meta.json directory-level
    3. product_override parameter (CLI)
    4. Auto-classification

    Args:
        file_path: Path to file being classified
        docs_root: Root docs directory
        product_override: Optional product override from CLI

    Returns:
        Dict with 'product', 'doc_type', and optionally 'version'
    """
    # FASE 13: Load metadata overrides from _meta.json
    try:
        from ingest.core.meta_loader import MetaLoader

        loader = MetaLoader()
        meta = loader.load_meta(file_path.parent)
        overrides = loader.get_metadata(file_path, meta)
    except Exception:
        # If meta loader fails, use empty overrides
        overrides = {"product": None, "doc_type": None}

    # Auto-classify (will be overridden if _meta.json specifies)
    auto_product = infer_product(file_path, docs_root, product_override)
    auto_doc_type = infer_doc_type(file_path)

    # Apply precedence: _meta.json > product_override > auto
    product = overrides.get("product") or auto_product
    doc_type = overrides.get("doc_type") or auto_doc_type

    result = {
        "product": product,
        "doc_type": doc_type,
    }

    # FASE 13: Extract version from filename/path
    try:
        from ingest.core.version_extractor import extract_version

        version = extract_version(file_path)
        if version:
            result["version"] = version
    except Exception:
        # If version extractor fails, continue without version
        pass

    return result


def classify_document(
    file_path: Path,
    product_override: str | None = None,
) -> dict[str, str]:
    """
    Convenience wrapper around classify() that uses the file's parent
    directory as docs_root. Used by batch_processor and other callers
    that do not have a separate docs_root.

    Args:
        file_path: Path to file being classified
        product_override: Optional product name override

    Returns:
        dict with product, doc_type, and optionally version keys
    """
    return classify(
        file_path,
        docs_root=file_path.parent,
        product_override=product_override,
    )
