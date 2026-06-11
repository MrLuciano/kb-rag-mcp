"""Tests for optimization modules."""
from kb_server.optimization.chunking_experiments import (
    ChunkingStrategy,
    FixedStrategy,
    RecursiveStrategy,
    SemanticStrategy,
    create_strategy,
)
from kb_server.optimization.scoring_experiments import (
    DenseOnlyVariant,
    HybridVariant,
    RerankedVariant,
    ScoringVariant,
    create_variant,
)


def test_chunking_strategies_importable():
    """All chunking classes are importable."""
    assert issubclass(FixedStrategy, ChunkingStrategy)
    assert issubclass(RecursiveStrategy, ChunkingStrategy)
    assert issubclass(SemanticStrategy, ChunkingStrategy)


def test_scoring_variants_importable():
    """All scoring classes are importable."""
    assert issubclass(DenseOnlyVariant, ScoringVariant)
    assert issubclass(HybridVariant, ScoringVariant)
    assert issubclass(RerankedVariant, ScoringVariant)


def test_create_strategy_factory():
    """Factory returns correct strategy types."""
    assert isinstance(create_strategy("fixed"), FixedStrategy)
    assert isinstance(create_strategy("recursive"), RecursiveStrategy)
    assert isinstance(create_strategy("semantic"), SemanticStrategy)


def test_create_variant_factory():
    """Factory returns correct variant types."""
    assert isinstance(create_variant("dense_only"), DenseOnlyVariant)
    assert isinstance(create_variant("hybrid"), HybridVariant)
    assert isinstance(create_variant("reranked"), RerankedVariant)
