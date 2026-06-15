"""
MCP Prompt template definitions and rendering helpers.

Exposes ``extract_answer`` and ``summarize_documents`` prompts for MCP
clients (Claude, Cursor, Copilot) to request grounded, cited answers
from the KB without building their own prompt engineering.

Prompt text and argument contracts live here so ``server.py`` only
handles registration, not template content.
"""

import logging
from typing import List, Optional

import mcp.types as types

log = logging.getLogger("kb-mcp.prompts")

# ── Prompt metadata registry ─────────────────────────────────────────

PROMPT_DEFINITIONS: dict[str, types.Prompt] = {}

_extract_answer = types.Prompt(
    name="extract_answer",
    description=(
        "Given the user's question and retrieved document chunks, "
        "extract a precise answer with source citations. "
        "Use when you need a grounded answer from the knowledge base."
    ),
    arguments=[
        types.PromptArgument(
            name="question",
            description="The user's question to answer using KB content",
            required=True,
        ),
        types.PromptArgument(
            name="search_results",
            description=(
                "JSON string of search results with text, source_file, "
                "product, doc_type, and chunk_id fields"
            ),
            required=True,
        ),
    ],
)

_summarize_documents = types.Prompt(
    name="summarize_documents",
    description=(
        "Summarize the provided document chunks as a coherent overview. "
        "Highlights key themes, differences, and takeaways. "
        "Use when you need a concise summary of KB content."
    ),
    arguments=[
        types.PromptArgument(
            name="documents",
            description=(
                "JSON string of document chunks to summarize, each with "
                "text, source_file, product, and doc_type fields"
            ),
            required=True,
        ),
        types.PromptArgument(
            name="focus",
            description=(
                "Optional area of focus for the summary "
                "(e.g. 'installation steps', 'API changes', 'security')"
            ),
            required=False,
        ),
    ],
)

PROMPT_DEFINITIONS["extract_answer"] = _extract_answer
PROMPT_DEFINITIONS["summarize_documents"] = _summarize_documents


# ── Render helpers ───────────────────────────────────────────────────


def render_extract_answer(
    arguments: dict[str, str],
) -> list[types.PromptMessage]:
    """Render the extract_answer prompt with user-provided arguments.

    Args:
        arguments: Must contain ``question`` and ``search_results`` keys.

    Returns:
        List of PromptMessage (user role) with the rendered prompt text.
    """
    question = arguments.get("question", "")
    search_results = arguments.get("search_results", "")

    prompt_text = (
        "You are a precise technical documentation assistant. "
        "Answer the user's question using ONLY the provided document "
        "chunks. Follow these rules:\n"
        "\n"
        "1. Extract the answer directly from the chunks provided.\n"
        "2. Cite the source document and chunk ID for each piece of "
        "information used.\n"
        "3. If the answer cannot be fully derived from the chunks, "
        "state clearly what is unknown.\n"
        "4. Do not invent information not present in the chunks.\n"
        "5. If the chunks are empty or irrelevant, say so.\n"
        "\n"
        f"## User Question\n{question}\n"
        "\n"
        f"## Retrieved Document Chunks\n{search_results}\n"
        "\n"
        "## Expected Output Format\n"
        "**Answer:** <concise answer>\n"
        "**Sources:** [source_file:chunk_id, ...]\n"
        "**Unknown:** <anything not covered by the chunks>"
    )

    return [
        types.PromptMessage(
            role="user",
            content=types.TextContent(type="text", text=prompt_text),
        )
    ]


def render_summarize_documents(
    arguments: dict[str, str],
) -> list[types.PromptMessage]:
    """Render the summarize_documents prompt.

    Args:
        arguments: Must contain ``documents`` key, may contain ``focus``.

    Returns:
        List of PromptMessage (user role) with the rendered prompt text.
    """
    docs = arguments.get("documents", "")
    focus = arguments.get("focus", "")

    prompt_text = (
        "You are a technical documentation summarizer. "
        "Summarize the provided documents as a coherent overview. "
        "Follow these rules:\n"
        "\n"
        "1. Highlight key themes, differences, and important takeaways.\n"
        "2. Organize the summary with section headers and bullet points.\n"
        "3. Cite source document names for each major point.\n"
        "4. Identify contradictions or gaps between documents.\n"
        "5. Focus on factual, actionable information.\n"
        "\n"
        f"## Documents to Summarize\n{docs}\n"
        "\n"
    )

    if focus:
        prompt_text += (
            f"## Area of Focus\n{focus}\n"
            "\n"
            "Prioritize information relevant to this focus area.\n"
        )

    prompt_text += (
        "## Expected Output Format\n"
        "### Overview\n<2-3 sentence summary>\n"
        "### Key Themes\n- Theme 1: ...\n- Theme 2: ...\n"
        "### Key Takeaways\n- Takeaway 1: ...\n"
    )

    return [
        types.PromptMessage(
            role="user",
            content=types.TextContent(type="text", text=prompt_text),
        )
    ]


# ── Dispatcher ───────────────────────────────────────────────────────


def render_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    """Render a prompt by name with the given arguments.

    Args:
        name: Prompt name (must be registered in PROMPT_DEFINITIONS).
        arguments: String-keyed argument dict for the prompt.

    Returns:
        GetPromptResult with rendered messages and prompt description.

    Raises:
        ValueError: If the prompt name is unknown.
    """
    prompt_def = PROMPT_DEFINITIONS.get(name)
    if prompt_def is None:
        raise ValueError(f"Unknown prompt: {name}")

    safe_args = arguments or {}

    if name == "extract_answer":
        messages = render_extract_answer(safe_args)
    elif name == "summarize_documents":
        messages = render_summarize_documents(safe_args)
    else:
        raise ValueError(f"No renderer for prompt: {name}")

    return types.GetPromptResult(
        description=prompt_def.description,
        messages=messages,
    )
