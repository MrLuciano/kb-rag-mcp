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

import logging
import re
from pathlib import Path

log = logging.getLogger("kb-ingest")

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
            r"\blgpd\b",
            r"lei.geral",
            r"\bgdpr\b",
            r"\bnist\b",  # word boundary to prevent matching "administrator"
            r"\bcompliance\b",
            r"\bregulation\b",
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

# ── Vendor Mapping (Phase 11) ───────────────────────────────────────────────
# Maps product names to their parent vendors

VENDOR_MAP: dict[str, str] = {
    # OTCS Products → OpenText
    "WebReports": "OpenText",
    "xECM": "OpenText",
    "Workflow": "OpenText",
    "CSIDE": "OpenText",
    "ContentServer": "OpenText",
    "Brava": "OpenText",
    "OT2": "OpenText",
    "DocumentViewer": "OpenText",
    "APIGateway": "OpenText",
    "ArchiveCenter": "OpenText",
    "AppServer": "OpenText",
    "DataSync": "OpenText",
    "AdminPortal": "OpenText",
    "RecordsManagement": "OpenText",
    # Standards bodies
    "ISO": "ISO",
}

# Patterns to detect vendor directly from filename
FILENAME_VENDOR_PATTERNS: list[tuple[str, list[str]]] = [
    ("OpenText", [r"\bopentext\b"]),
    # OT-WebReport, OT_Admin patterns (after normalization: space replaces -/_)
    ("OpenText", [r"\bot\s+\w"]),
]

# ── Subsystem Patterns (Phase 11) ───────────────────────────────────────────
# Patterns to detect functional subsystem from filename

SUBSYSTEM_PATTERNS: list[tuple[str, list[str]]] = [
    ("API", [r"\bapi\b", r"\bsdk\b", r"\brest\b", r"\bsoap\b", r"\bwebservice"]),
    ("Security", [r"\bsecurity\b", r"\bauth\b", r"\bpermission\b", r"\bacl\b"]),
    ("Admin", [r"\badmin\b", r"\badministration\b", r"\boperator\b"]),
    ("Integration", [r"\bintegration\b", r"\bconnector\b"]),
    ("Migration", [r"\bmigration\b", r"\bupgrade\b", r"\bupgrad"]),
    ("Install", [r"\binstall\b", r"\bsetup\b", r"\bdeploy"]),
    ("Reporting", [r"\breport\b", r"\bdashboard\b"]),
    ("Performance", [r"\bperformance\b", r"\btuning\b", r"\bscalab"]),
]

# Skip-list directories for subsystem inference
SKIP_SUBSYSTEM_DIRS = {"varios", "templates", "archive"}


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES PÚBLICAS
# ─────────────────────────────────────────────────────────────────────────────


def infer_doc_type(file_path: Path) -> str:
    """
    Infer document type from the file name and full path.

    Evaluates classification rules by priority order and returns the
    highest-priority matching doc_type, or 'document' if none match.

    Args:
        file_path: Path to the file to classify.

    Returns:
        Document type string (e.g., 'admin_guide', 'standard', 'training').
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


def infer_vendor(file_path: Path, product: str = "") -> str:
    """
    Infer vendor from filename patterns or product-to-vendor mapping.

    Priority order:
    1. Filename patterns (FILENAME_VENDOR_PATTERNS)
    2. Parent directory name patterns
    3. Product-to-vendor mapping (VENDOR_MAP)

    Args:
        file_path: Path to the file.
        product: Optional inferred product name for VENDOR_MAP lookup.

    Returns:
        Vendor string (e.g., 'OpenText', 'ISO') or empty string if unknown.
    """
    # Normalize filename + full path text
    text = (file_path.stem + " " + str(file_path)).lower()
    text = re.sub(r"[_\-/\\]", " ", text)

    # Check filename patterns first
    for vendor, patterns in FILENAME_VENDOR_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return vendor

    # Check parent directory names
    for parent in file_path.parents:
        parent_name = parent.stem.lower()
        parent_text = re.sub(r"[_\-/]", " ", parent_name)
        for vendor, patterns in FILENAME_VENDOR_PATTERNS:
            for pattern in patterns:
                if re.search(pattern, parent_text, re.IGNORECASE):
                    return vendor

    # Check VENDOR_MAP with product
    if product:
        # Exact match first
        if product in VENDOR_MAP:
            return VENDOR_MAP[product]
        # Check if product contains "ISO" (e.g., "ISO 9001")
        if "ISO" in product:
            return "ISO"

    return ""


def infer_subsystem(file_path: Path, docs_root: Path) -> str:
    """
    Infer subsystem from directory hierarchy or filename patterns.

    Subsystem is a sub-categorization below the product level.
    Example: "docs/WebReports/Designer/Guide.pdf" → subsystem="Designer"

    Priority order:
    1. Intermediate directories between docs_root and filename
    2. Filename patterns (SUBSYSTEM_PATTERNS)

    Args:
        file_path: Path to the file.
        docs_root: Root documents directory.

    Returns:
        Subsystem string or empty string if unknown.
    """
    # Try directory-based inference first
    try:
        relative = file_path.relative_to(docs_root)
        parts = list(relative.parts)

        # If there are at least 3 parts: [product_dir, subsystem_dir, ..., filename]
        # OR at least 2 parts where the first is not a skip-dir and not the file
        if len(parts) >= 2:
            # Find the first real directory (skip "varios", "templates", "archive")
            candidate_idx = 0
            while (
                candidate_idx < len(parts) - 1
                and parts[candidate_idx].lower() in SKIP_SUBSYSTEM_DIRS
            ):
                candidate_idx += 1

            # Now look for a subsystem AFTER the product level
            # If we have parts[candidate_idx] and parts[candidate_idx + 1]
            # (where the second to last is a directory, not the filename)
            # The subsystem is the first directory after the product root
            # or the intermediate directory between root and file

            # Simple approach: get all directories between docs_root and file
            dir_parts = parts[:-1]  # exclude filename

            if len(dir_parts) >= 2:
                # Skip skip-list directories at any level
                filtered = [
                    d for d in dir_parts if d.lower() not in SKIP_SUBSYSTEM_DIRS
                ]
                # If there are 2+ filtered dirs, the 2nd one is the subsystem
                # e.g., [WebReports, Designer, ...] → Designer
                if len(filtered) >= 2:
                    return filtered[1]
            elif len(dir_parts) == 1:
                # Single directory between docs_root and file → no subsystem
                # (that's the product directory itself)
                pass
    except ValueError:
        # Not relative to docs_root - skip directory inference
        pass

    # Fall back to filename pattern matching
    name_lower = re.sub(r"[_\-/]", " ", file_path.stem.lower())
    for subsystem, patterns in SUBSYSTEM_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, name_lower, re.IGNORECASE):
                return subsystem

    return ""


def infer_product(
    file_path: Path, docs_root: Path, product_override: str | None = None
) -> str:
    """
    Infer product name from the file path or explicit override.

    Priority order:
    1. Explicit product_override parameter
    2. Root directory name relative to docs_root
    3. File name patterns (PRODUCT_FROM_NAME)
    4. Fallback: 'geral'

    Args:
        file_path: Path to the file.
        docs_root: Root documents directory.
        product_override: Explicit product name (takes precedence).

    Returns:
        Product name string.
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


# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENT METADATA EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────


def extract_document_metadata(file_path: Path) -> dict[str, str]:
    """
    Extract metadata fields from PDF/DOCX documents for gap-filling classification.

    Uses PyMuPDF for PDFs and python-docx for DOCX files. Returns empty dict
    for unsupported formats or on any error (always degrades gracefully).

    Args:
        file_path: Path to the document file.

    Returns:
        Dict with text metadata fields (may be empty).
    """
    ext = file_path.suffix.lower()

    if ext == ".pdf":
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(file_path))
            try:
                md = doc.metadata
                return {
                    "title": md.get("title") or "",
                    "author": md.get("author") or "",
                    "subject": md.get("subject") or "",
                    "keywords": md.get("keywords") or "",
                }
            finally:
                doc.close()
        except ImportError:
            log.warning("fitz (PyMuPDF) not available for PDF metadata extraction")
            return {}
        except Exception:
            log.warning(f"Failed to extract PDF metadata from {file_path}")
            return {}

    elif ext == ".docx":
        try:
            from docx import Document

            doc = Document(str(file_path))
            cp = doc.core_properties
            return {
                "title": cp.title or "",
                "author": cp.author or "",
                "subject": cp.subject or "",
                "keywords": cp.keywords or "",
            }
        except ImportError:
            log.warning("python-docx not available for DOCX metadata extraction")
            return {}
        except Exception:
            log.warning(f"Failed to extract DOCX metadata from {file_path}")
            return {}

    return {}


def _build_metadata_text(metadata: dict[str, str]) -> str:
    """Build a searchable text string from metadata fields."""
    parts = []
    for key in ("title", "subject", "author", "keywords"):
        val = metadata.get(key, "")
        if val:
            parts.append(val)
    text = " ".join(parts)
    # Normalize separators (same as infer_product does for filenames)
    text = re.sub(r"[_\-/\\]", " ", text)
    return text


def _classify_from_metadata_text(
    metadata_text: str,
    docs_root: Path,
    product_override: str | None = None,
) -> dict[str, str]:
    """Run classification heuristics on a metadata text string.

    Creates a synthetic Path so we can reuse existing inference functions
    without modifying their signatures (CLASSIFY-03).

    Args:
        metadata_text: Concatenated metadata text to classify.
        docs_root: Root documents directory.
        product_override: Optional product name for vendor inference.

    Returns:
        Dict with 'vendor', 'product', 'doc_type' keys (may be empty).
    """
    if not metadata_text.strip():
        return {}

    synthetic = Path(metadata_text)

    return {
        "vendor": infer_vendor(synthetic, product_override or ""),
        "product": infer_product(synthetic, docs_root, product_override),
        "doc_type": infer_doc_type(synthetic),
    }


def enrich_classification(
    file_path: Path,
    docs_root: Path,
    current: dict[str, str],
) -> dict[str, str]:
    """Fill classification gaps using document metadata.

    When filename-based classification produces default/empty values
    for vendor, product, or doc_type, this function extracts PDF/DOCX
    metadata (title, subject, author, keywords) and reruns the
    classification heuristics on the metadata text. Only replaces fields
    that have default/empty values — never overrides explicit classification.

    Precedence (highest to lowest):
    1. _meta.json overrides (already applied before this function)
    2. Filename/directory heuristics (current classification)
    3. Document metadata heuristics (this function — gap-fill only)

    Args:
        file_path: Path to the document file.
        docs_root: Root documents directory.
        current: Current classification dict from classify().

    Returns:
        Updated classification dict (new copy, original unchanged).
    """
    result = dict(current)

    # Determine which fields need gap-filling
    defaults = {"", "geral", "document"}
    gaps = {
        k for k in ("vendor", "product", "doc_type")
        if result.get(k) in defaults or not result.get(k)
    }

    if not gaps:
        return result

    metadata = extract_document_metadata(file_path)
    if not metadata or not any(metadata.values()):
        return result

    metadata_text = _build_metadata_text(metadata)
    if not metadata_text.strip():
        return result

    # Only pass product_override if it's a concrete value (not a default/gap)
    # to avoid short-circuiting infer_product() in the metadata classification.
    product_for_override = (
        result.get("product")
        if result.get("product") not in {"", "geral"}
        else None
    )
    meta_classification = _classify_from_metadata_text(
        metadata_text, docs_root, product_for_override
    )

    # Only fill gaps — never override non-default values
    if "vendor" in gaps and meta_classification.get("vendor"):
        result["vendor"] = meta_classification["vendor"]
    if "product" in gaps and meta_classification.get("product"):
        result["product"] = meta_classification["product"]
    if "doc_type" in gaps and meta_classification.get("doc_type"):
        result["doc_type"] = meta_classification["doc_type"]

    return result


def classify(
    file_path: Path,
    docs_root: Path,
    product_override: str | None = None,
) -> dict[str, str]:
    """
    Classify a file and return inferred product, doc_type, vendor, subsystem,
    and version.

    Single entry point used by ingest.py. Applies the following precedence:
    1. _meta.json file-specific overrides
    2. _meta.json directory-level overrides
    3. product_override parameter (CLI)
    4. Auto-classification

    FASE 11: Adds vendor and subsystem inference.
    FASE 13: Integrates version extractor and meta loader.

    Args:
        file_path: Path to file being classified.
        docs_root: Root docs directory.
        product_override: Optional product override from CLI.

    Returns:
        Dict with 'product', 'doc_type', 'vendor', 'subsystem', and
        optionally 'version'.
    """
    # FASE 13: Load metadata overrides from _meta.json
    try:
        from ingest.core.meta_loader import MetaLoader

        loader = MetaLoader()
        meta = loader.load_meta(file_path.parent)
        overrides = loader.get_metadata(file_path, meta)
    except Exception:
        # If meta loader fails, use empty overrides
        overrides = {
            "product": None,
            "doc_type": None,
            "vendor": None,
            "subsystem": None,
        }

    # Auto-classify (will be overridden if _meta.json specifies)
    auto_product = infer_product(file_path, docs_root, product_override)
    auto_doc_type = infer_doc_type(file_path)
    # FASE 11: Auto-infer vendor and subsystem
    auto_vendor = infer_vendor(
        file_path, product_override or auto_product
    )
    auto_subsystem = infer_subsystem(file_path, docs_root)

    # Apply precedence: _meta.json > product_override > auto
    product = overrides.get("product") or auto_product
    doc_type = overrides.get("doc_type") or auto_doc_type
    # FASE 11: Apply same precedence to vendor/subsystem
    vendor = overrides.get("vendor") or auto_vendor
    subsystem = overrides.get("subsystem") or auto_subsystem

    result = {
        "product": product,
        "doc_type": doc_type,
        "vendor": vendor,
        "subsystem": subsystem,
    }

    # FASE 11-02: Apply enrichment from document metadata (gap-fill only,
    # lowest precedence — never overrides _meta.json or auto-classification)
    defaults = {"", "geral", "document"}
    enriched = enrich_classification(file_path, docs_root, result)
    for key in ("vendor", "product", "doc_type"):
        if result[key] in defaults and enriched[key] not in defaults:
            result[key] = enriched[key]

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
