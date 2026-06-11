"""Experiment configuration defaults and parameter validation.

FASE 25: Optimization Experiments
"""
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger("kb-mcp.optimization")


@dataclass
class ExperimentConfig:
    """Default parameters for optimization experiments.

    All fields can be overridden via environment variables with the
    ``OPT_`` prefix (e.g. ``OPT_CHUNK_SIZE`` overrides *chunk_size*).
    """

    chunk_size: int = field(
        default_factory=lambda: int(os.getenv("OPT_CHUNK_SIZE", "600"))
    )
    chunk_overlap: int = field(
        default_factory=lambda: int(os.getenv("OPT_CHUNK_OVERLAP", "80"))
    )
    top_k: int = field(
        default_factory=lambda: int(os.getenv("OPT_TOP_K", "5"))
    )
    dense_weight: float = field(
        default_factory=lambda: float(os.getenv("OPT_DENSE_WEIGHT", "0.7"))
    )
    sparse_weight: float = field(
        default_factory=lambda: float(os.getenv("OPT_SPARSE_WEIGHT", "0.3"))
    )
    rrf_k: int = field(
        default_factory=lambda: int(os.getenv("OPT_RRF_K", "60"))
    )
    distance_metric: str = field(
        default_factory=lambda: os.getenv("OPT_DISTANCE_METRIC", "COSINE")
    )
    reranker_enabled: bool = field(
        default_factory=lambda: os.getenv(
            "OPT_RERANKER_ENABLED", "true"
        ).lower()
        in ("true", "1", "yes")
    )

    def to_dict(self) -> Dict[str, Any]:
        """Return a serialisable dict of all fields."""
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "top_k": self.top_k,
            "dense_weight": self.dense_weight,
            "sparse_weight": self.sparse_weight,
            "rrf_k": self.rrf_k,
            "distance_metric": self.distance_metric,
            "reranker_enabled": self.reranker_enabled,
        }


# ── Chunking strategies ─────────────────────────────────────────────


def _fixed_chunker(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Fixed-size chunking with overlap (manual fallback)."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - chunk_overlap
    return chunks


def _recursive_chunker(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Recursive character text splitting via LangChain."""
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        return splitter.split_text(text)
    except Exception:
        log.warning("Recursive chunker unavailable; falling back to fixed")
        return _fixed_chunker(text, chunk_size, chunk_overlap)


def _semantic_chunker(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Semantic chunking via docling HybridChunker.

    Falls back to recursive chunking if docling is unavailable.
    """
    try:
        from docling.chunking import HybridChunker

        chunker = HybridChunker(max_tokens=chunk_size)
        chunks = chunker.chunk(text)
        return [c.text for c in chunks]
    except Exception:
        log.warning("Semantic chunker unavailable; falling back to recursive")
        return _recursive_chunker(text, chunk_size, chunk_overlap)


CHUNK_STRATEGIES: Dict[str, Callable[..., List[str]]] = {
    "fixed": _fixed_chunker,
    "recursive": _recursive_chunker,
    "semantic": _semantic_chunker,
}


# ── Scoring variants ───────────────────────────────────────────────

SCORING_VARIANTS: Dict[str, Dict[str, Any]] = {
    "dense_only": {
        "dense_weight": 1.0,
        "sparse_weight": 0.0,
        "reranker_enabled": False,
    },
    "hybrid_default": {
        "dense_weight": 0.7,
        "sparse_weight": 0.3,
        "reranker_enabled": True,
    },
    "hybrid_dense_heavy": {
        "dense_weight": 0.9,
        "sparse_weight": 0.1,
        "reranker_enabled": True,
    },
    "sparse_heavy": {
        "dense_weight": 0.3,
        "sparse_weight": 0.7,
        "reranker_enabled": False,
    },
}


# ── Validation ─────────────────────────────────────────────────────


def validate_experiment_params(params: Dict[str, Any]) -> List[str]:
    """Validate experiment parameters and return a list of error messages.

    Checks:
    * chunk_size > 0
    * chunk_overlap < chunk_size
    * dense_weight + sparse_weight <= 1.0

    Args:
        params: Dictionary of experiment parameters.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors: List[str] = []

    chunk_size = params.get("chunk_size", 600)
    if chunk_size <= 0:
        errors.append(f"chunk_size must be > 0, got {chunk_size}")

    chunk_overlap = params.get("chunk_overlap", 80)
    if chunk_overlap >= chunk_size:
        errors.append(
            f"chunk_overlap ({chunk_overlap}) must be < chunk_size "
            f"({chunk_size})"
        )

    dense_weight = params.get("dense_weight", 0.7)
    sparse_weight = params.get("sparse_weight", 0.3)
    if dense_weight + sparse_weight > 1.0:
        errors.append(
            f"dense_weight + sparse_weight must be <= 1.0, got "
            f"{dense_weight + sparse_weight:.2f}"
        )

    return errors
