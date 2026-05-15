"""
Classificador de conteúdo da KB.

Infere duas dimensões a partir do nome do arquivo e caminho:
  - product  : produto/sistema ao qual o documento pertence
  - doc_type : tipo de conteúdo (admin_guide, standard, training, etc.)

Nenhuma reorganização de pastas é necessária — tudo é inferido
por padrões no nome do arquivo e estrutura de diretórios existente.
"""

import re
from pathlib import Path

# ── Taxonomia de doc_type ─────────────────────────────────────────────────────
# Cada entrada: (prioridade, doc_type, [padrões regex no nome do arquivo])
# Maior prioridade = verificado primeiro.

DOC_TYPE_RULES: list[tuple[int, str, list[str]]] = [
    # Padrões ISO / normas / regulamentos
    (100, "standard", [
        r"\biso\b", r"\biso[-_]\d+", r"15489", r"lgpd", r"lei.geral",
        r"gdpr", r"nist", r"compliance", r"regulation",
    ]),

    # Release notes
    (90, "release_notes", [
        r"release.?notes?", r"relnotes?", r"what.?s.?new",
        r"patch.?notes?", r"changelog",
    ]),

    # Guias de upgrade / migração
    (85, "upgrade_guide", [
        r"upgrad", r"migrat", r"update.instal", r"migration",
    ]),

    # Guias de instalação
    (80, "install_guide", [
        r"install", r"installation", r"setup.guide", r"deploy",
        r"getting.started", r"\bigi\b", r"\bigu\b", r"\biasw\b",
        r"\bigw\b", r"\bigd\b",
    ]),

    # Guias de administração
    (75, "admin_guide", [
        r"admin", r"administration", r"system.admin", r"sysadmin",
        r"\bacn\b", r"\bagd\b", r"operator",
    ]),

    # Guias de configuração / cenários
    (70, "config_guide", [
        r"config", r"configuration", r"scenario", r"setup",
        r"\bcgd\b", r"\bist\b", r"storm.config", r"cookbook",
        r"how.to", r"howto",
    ]),

    # Guias de usuário
    (65, "user_guide", [
        r"user.?guide", r"user.?manual", r"\bugd\b", r"end.user",
        r"manual.do.usu", r"guia.do.usu",
    ]),

    # Guias de API / SDK / programação
    (60, "api_guide", [
        r"\bapi\b", r"\bsdk\b", r"programm", r"developer",
        r"integration", r"web.service", r"\brest\b", r"\bsoap\b",
        r"\bpsa\b", r"interface", r"endpoints?",
    ]),

    # Case studies / howto / troubleshooting
    (55, "howto", [
        r"case.study", r"how.to", r"howto", r"troubleshoot",
        r"cookbook", r"recipe", r"tip", r"trick", r"best.practice",
        r"reverse.proxy", r"ha.proxy", r"\bkb\d{5,}", r"knowledge.base",
    ]),

    # Treinamentos / apresentações educacionais
    (50, "training", [
        r"training", r"vilt", r"webinar", r"workshop",
        r"course", r"module\s*\d", r"day\s*\d", r"lab",
        r"study.guide", r"learn", r"tutorial", r"enablement",
        r"certification", r"certificate",
    ]),

    # Apresentações / visão geral
    (45, "overview", [
        r"overview", r"introduction", r"intro\b", r"what.is",
        r"understanding", r"fundamentals?", r"concepts?",
        r"architecture", r"whitepaper", r"datasheet",
        r"presentation", r"comprehensive", r"portfolio",
    ]),

    # Documentos de referência técnica / terminologia
    (40, "reference", [
        r"technical.paper", r"terminolog", r"glossar",
        r"reference", r"spec", r"specification",
        r"technical.note", r"technote",
    ]),

    # Notas de reunião / sessões gravadas
    (35, "meeting", [
        r"meeting.recording", r"recording", r"session",
        r"clickthrough", r"knowledge.sharing",
    ]),

    # Artefatos binários / pacotes
    (10, "release_artifact", [
        r"\.zip$", r"\.patch$", r"pat\d{9,}", r"p-ar-center",
        r"schema.and.pre.upgrade",
    ]),
]

# ── Mapeamento de pasta raiz → produto ───────────────────────────────────────
# Complementa a detecção automática por pasta com aliases

PRODUCT_ALIASES: dict[str, str] = {
    "archive":            "ArchiveCenter",
    "contentserver":      "ContentServer",
    "content server":     "ContentServer",
    "xecm":               "xECM",
    "extended ecm":       "xECM",
    "otds":               "OTDS",
    "directory services": "OTDS",
    "wem":                "WEM",
    "adobe":              "Adobe",
    "reccordsmanagement": "RecordsManagement",
    "records management": "RecordsManagement",
    "varios":             "geral",
    "templates":          "geral",
}

# Padrões de produto inferíveis do próprio nome do arquivo
PRODUCT_FROM_NAME: list[tuple[str, list[str]]] = [
    ("ArchiveCenter",      [r"archive.center", r"\bar\d{6}", r"archive.server"]),
    ("ContentServer",      [r"content.server", r"lles", r"\bcs\d{2}\b"]),
    ("xECM",               [r"extended.ecm", r"\bxecm\b", r"powerdocs", r"exstream"]),
    ("OTDS",               [r"directory.services", r"\botds\b"]),
    ("WEM",                [r"web.experience", r"\bwem\b", r"\bwcm\b"]),
    ("AppWorks",           [r"appworks"]),
    ("ProcessSuite",       [r"process.suite", r"process.platform", r"appworks.platform"]),
    ("DocumentFilters",    [r"document.filters"]),
    ("TeleForm",           [r"teleform"]),
    ("Adobe",              [r"\badobe\b", r"adobe.sign", r"docusign"]),
    ("SAP",                [r"\bsap\b", r"successfactors", r"archiving.and.document.access"]),
    ("ISO",                [r"\biso[-_]\d+", r"15489", r"irish.version"]),
    ("RecordsManagement",  [r"records?.management", r"file.plan", r"lgpd", r"lei.geral"]),
    ("Apache",             [r"\bapache\b"]),
    ("Gradle",             [r"\bgradle\b"]),
    ("CMIS",               [r"\bcmis\b"]),
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
    if file_path.suffix.lower() in (".zip", ".patch", ".mp4", ".avi", ".jpg", ".png"):
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


def infer_product(file_path: Path, docs_root: Path, product_override: str | None = None) -> str:
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
        root_folder = relative.parts[0].lower() if len(relative.parts) > 1 else ""
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
    Retorna dict com product e doc_type inferidos.
    Ponto de entrada único usado pelo ingest.py.
    """
    return {
        "product":  infer_product(file_path, docs_root, product_override),
        "doc_type": infer_doc_type(file_path),
    }
