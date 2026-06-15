"""
Graph metadata derivation for cross-document knowledge relationships.

Derives deterministic graph-ready metadata from document content and
existing classification fields without requiring heavy external NLP
dependencies. Designed to be called during ingest payload assembly.

Phase 30 foundation — provides ``document_id``, ``graph_entities``,
``graph_topics``, and ``graph_related`` fields for each chunk payload.
"""

import hashlib
import logging
import re
from collections import Counter
from typing import Any

log = logging.getLogger("kb-ingest.graph_builder")

_MIN_TERM_LENGTH = 3
_MAX_ENTITIES = 8
_TOP_N_TERMS = 5

_STOP_WORDS: set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can",
    "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above",
    "below", "between", "out", "off", "over", "under", "again",
    "further", "then", "once", "here", "there", "when", "where",
    "why", "how", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "just", "because",
    "but", "and", "or", "if", "while", "about", "up", "this",
    "that", "these", "those", "it", "its", "which", "who", "whom",
    "what", "i", "me", "my", "we", "our", "you", "your", "he",
    "she", "they", "them", "their", "his", "her", "itself",
    "themselves", "please", "see", "also", "use", "using", "used",
    "set", "get", "make", "made", "via", "per", "e.g.", "i.e.",
    "etc", "etc.", "note", "important", "steps", "step", "click",
    "select", "choose", "enter", "type", "press", "configure",
}


def _normalize(text: str) -> str:
    text = text.lower()
    text = text.replace("_", " ").replace("-", " ")
    return text


def _tokenize(text: str) -> list[str]:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", _normalize(text))
    return [
        t for t in cleaned.split()
        if len(t) >= _MIN_TERM_LENGTH
        and t not in _STOP_WORDS
        and not t.isdigit()
    ]


def extract_entities(text: str) -> list[str]:
    """Extract lightweight key terms from text using frequency heuristics.

    Returns the top-N content words sorted by frequency, filtered for
    meaningful terms. Acts as a lightweight stand-in for named entity
    recognition without external dependencies.
    """
    tokens = _tokenize(text)
    if not tokens:
        return []
    counts = Counter(tokens)
    return [word for word, _ in counts.most_common(_MAX_ENTITIES)]


def extract_topics(meta: dict[str, Any]) -> list[str]:
    """Derive topic labels from existing classification metadata.

    Uses product, doc_type, vendor, subsystem, and module fields to
    produce topic-like labels that describe the document's domain.
    """
    topics: list[str] = []
    product = meta.get("product", "").strip()
    doc_type = meta.get("doc_type", "").strip()
    vendor = meta.get("vendor", "").strip()
    subsystem = meta.get("subsystem", "").strip()
    module = meta.get("module", "").strip()

    if product:
        topics.append(product)
    if module:
        topics.append(module)
    elif subsystem:
        topics.append(subsystem)
    if doc_type:
        label = doc_type.replace("_", " ").title()
        if label not in topics:
            topics.append(label)
    if vendor and vendor != product:
        topics.append(vendor)
    return topics


def compute_document_id(source_file: str, product: str) -> str:
    """Compute a stable, deterministic document identifier.

    Uses SHA-256 of ``source_file + product`` so the same file always
    produces the same document_id, even across re-ingests.
    """
    raw = f"{source_file}::{product}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def compute_related_hints(meta: dict[str, Any]) -> list[str]:
    """Compute related-document hint labels for grouping.

    Produces labels like ``product:doc_type``, ``product:subsystem``,
    and similar combinations that can be used to find related documents
    sharing the same attribute values.
    """
    hints: list[str] = []
    product = meta.get("product", "").strip()
    doc_type = meta.get("doc_type", "").strip()
    vendor = meta.get("vendor", "").strip()
    subsystem = meta.get("subsystem", "").strip()
    module = meta.get("module", "").strip()

    if product and doc_type:
        hints.append(f"product:{product}:doc_type:{doc_type}")
    if product and subsystem:
        hints.append(f"product:{product}:subsystem:{subsystem}")
    if product and module:
        hints.append(f"product:{product}:module:{module}")
    if vendor and vendor != product:
        hints.append(f"vendor:{vendor}")
    if subsystem and module:
        hints.append(f"subsystem:{subsystem}:module:{module}")

    return hints


def build_graph_metadata(
    text: str,
    source_file: str,
    meta: dict[str, Any],
) -> dict[str, Any]:
    """Build graph metadata payload fields for a chunk.

    Args:
        text: Chunk text content.
        source_file: Relative file path of the source document.
        meta: Classification metadata dict with keys like product,
            doc_type, vendor, subsystem, module.

    Returns:
        A dict with keys ``doc_graph_id``, ``graph_entities``,
        ``graph_topics``, and ``graph_related`` suitable for adding
        to chunk payloads.
    """
    product = meta.get("product", "")
    entities = extract_entities(text)
    topics = extract_topics(meta)
    related = compute_related_hints(meta)
    doc_id = compute_document_id(source_file, product)

    return {
        "doc_graph_id": doc_id,
        "graph_entities": entities,
        "graph_topics": topics,
        "graph_related": related,
    }
