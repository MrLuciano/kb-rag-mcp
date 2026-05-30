"""Custom RAG-style evaluation metrics using LLM-as-judge.

Implements the 4 core RAGAS metrics without requiring the ragas library:
  - faithfulness        : Is the answer supported by the context?
  - answer_relevancy    : Does the answer address the question?
  - context_precision   : Fraction of retrieved contexts that are relevant
  - context_recall      : Fraction of ground-truth facts present in contexts

Each metric sends one or more prompts to an LLM judge and parses a 0-1 score.
"""
from __future__ import annotations

import logging
import re
from typing import Any

log = logging.getLogger("kb-mcp.eval")

# ── Prompt templates ─────────────────────────────────────────────────────

_FAITHFULNESS_PROMPT = """You are an expert evaluator. Your task is to rate how well the provided answer is supported by the given context.

Context:
{contexts}

Answer:
{answer}

Rate from 0.0 to 1.0 where:
- 1.0 = the answer is fully and directly supported by the context
- 0.0 = the answer is completely unsupported or contradicts the context
- 0.5 = partially supported

Respond with ONLY a decimal number between 0.0 and 1.0.
"""

_ANSWER_RELEVANCY_PROMPT = """You are an expert evaluator. Your task is to rate how well the answer addresses the question.

Question:
{question}

Answer:
{answer}

Rate from 0.0 to 1.0 where:
- 1.0 = the answer directly and completely addresses the question
- 0.0 = the answer is completely irrelevant
- 0.5 = partially relevant

Respond with ONLY a decimal number between 0.0 and 1.0.
"""

_CONTEXT_PRECISION_PROMPT = """You are an expert evaluator. Your task is to rate what fraction of the provided contexts are relevant to the question.

Question:
{question}

Contexts:
{contexts}

Rate from 0.0 to 1.0 where:
- 1.0 = every context is relevant
- 0.0 = none of the contexts are relevant
- 0.5 = about half are relevant

Respond with ONLY a decimal number between 0.0 and 1.0.
"""

_CONTEXT_RECALL_PROMPT = """You are an expert evaluator. Your task is to rate what fraction of facts in the expected answer are present in the provided contexts.

Question:
{question}

Expected Answer (ground truth):
{ground_truth}

Retrieved Contexts:
{contexts}

Rate from 0.0 to 1.0 where:
- 1.0 = all facts from the expected answer are present in the contexts
- 0.0 = none of the facts are present
- 0.5 = about half are present

Respond with ONLY a decimal number between 0.0 and 1.0.
"""


# ── Score parsing ─────────────────────────────────────────────────────────


def _parse_score(text: str) -> float:
    """Extract a 0-1 float from free-form LLM output.

    Handles formats:
        - Decimal: "0.85", ".85"
        - Percentage: "85%" → 0.85
        - Keywords: "yes" → 1.0, "no" → 0.0, "high" → 0.8, "low" → 0.2
        - First number in text if nothing else matches

    Args:
        text: Raw LLM response string.

    Returns:
        Float between 0.0 and 1.0 (clamped).
    """
    text_lower = text.lower().strip()

    # Keyword mapping
    keyword_map = {
        "yes": 1.0,
        "true": 1.0,
        "correct": 1.0,
        "supported": 1.0,
        "no": 0.0,
        "false": 0.0,
        "incorrect": 0.0,
        "unsupported": 0.0,
        "high": 0.8,
        "medium": 0.5,
        "low": 0.2,
        "partial": 0.5,
    }
    for keyword, score in keyword_map.items():
        if keyword in text_lower.split():
            return score

    # Percentage pattern
    pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if pct_match:
        return min(1.0, max(0.0, float(pct_match.group(1)) / 100.0))

    # Decimal pattern (0.85 or .85)
    dec_match = re.search(r"\b(\d?\.\d+)\b", text)
    if dec_match:
        val = float(dec_match.group(1))
        if 0.0 <= val <= 1.0:
            return val
        if val > 1.0 and val <= 100.0:
            return val / 100.0

    # Integer pattern
    int_match = re.search(r"\b(\d+)\b", text)
    if int_match:
        val = int(int_match.group(1))
        if val == 0 or val == 1:
            return float(val)
        if 0 < val <= 10:
            return val / 10.0
        if val <= 100:
            return val / 100.0

    log.warning("Could not parse score from: %r", text)
    return 0.5  # Neutral default


# ── Metric functions ───────────────────────────────────────────────────────


async def faithfulness(answer: str, contexts: list[str], llm: Any) -> float:
    """Rate how well the answer is supported by the retrieved contexts.

    Args:
        answer: Generated answer text.
        contexts: List of retrieved context strings.
        llm: LLM judge with async ``invoke(prompt) -> str`` method.

    Returns:
        Float between 0.0 and 1.0.
    """
    prompt = _FAITHFULNESS_PROMPT.format(
        contexts="\n---\n".join(contexts),
        answer=answer,
    )
    response = await llm.invoke(prompt)
    return _parse_score(response)


async def answer_relevancy(question: str, answer: str, llm: Any) -> float:
    """Rate how well the answer addresses the question.

    Args:
        question: User query.
        answer: Generated answer text.
        llm: LLM judge with async ``invoke(prompt) -> str`` method.

    Returns:
        Float between 0.0 and 1.0.
    """
    prompt = _ANSWER_RELEVANCY_PROMPT.format(
        question=question,
        answer=answer,
    )
    response = await llm.invoke(prompt)
    return _parse_score(response)


async def context_precision(question: str, contexts: list[str], llm: Any) -> float:
    """Rate what fraction of retrieved contexts are relevant to the question.

    Args:
        question: User query.
        contexts: List of retrieved context strings.
        llm: LLM judge with async ``invoke(prompt) -> str`` method.

    Returns:
        Float between 0.0 and 1.0.
    """
    prompt = _CONTEXT_PRECISION_PROMPT.format(
        question=question,
        contexts="\n---\n".join(f"[{i+1}] {ctx}" for i, ctx in enumerate(contexts)),
    )
    response = await llm.invoke(prompt)
    return _parse_score(response)


async def context_recall(
    question: str,
    ground_truth: str,
    contexts: list[str],
    llm: Any,
) -> float:
    """Rate what fraction of ground-truth facts are present in contexts.

    Args:
        question: User query.
        ground_truth: Expected correct answer.
        contexts: List of retrieved context strings.
        llm: LLM judge with async ``invoke(prompt) -> str`` method.

    Returns:
        Float between 0.0 and 1.0.
    """
    prompt = _CONTEXT_RECALL_PROMPT.format(
        question=question,
        ground_truth=ground_truth,
        contexts="\n---\n".join(f"[{i+1}] {ctx}" for i, ctx in enumerate(contexts)),
    )
    response = await llm.invoke(prompt)
    return _parse_score(response)
