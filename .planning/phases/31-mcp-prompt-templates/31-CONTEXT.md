# Phase 31: MCP Prompt Templates

**Status:** Backlog (promoted from ROADMAP.md)
**Priority:** High
**Code:** MCPPROMPTS-01
**Competitive Reference:** [nonatofabio/local_faiss_mcp](https://github.com/nonatofabio/local_faiss_mcp) — MCP prompts for answer extraction/summarization
**Promoted from:** `.planning/ROADMAP.md` Backlog (High Priority)

## Objective

Expose `extract_answer` and `summarize_documents` prompts via MCP prompts capability. Allows AI clients (Claude, Cursor, Copilot) to request concise, cited answers from indexed content without building their own prompt engineering.

## Expected Deliverables

- MCP prompts capability registration in `server.py`
- `extract_answer` prompt: Given a question and search results, return a concise answer with document citations
- `summarize_documents` prompt: Summarize a set of documents with key takeaways
- Prompt templates stored in `kb_server/prompts/` directory
- MCP tool to invoke prompts against current search results
- Dynamic prompt selection based on query type (fact vs summary)

## MCP Prompt Spec

### extract_answer
```
Given the user's question and retrieved document chunks, extract a precise
answer. Cite the source document ID and chunk ID for each piece of information
used. If the answer cannot be fully derived from the chunks, state what is
unknown. Format as: Answer: ... | Sources: [doc_id:chunk_id, ...]
```

### summarize_documents
```
Summarize the following documents as a coherent overview. Highlight key themes,
differences, and takeaways. Format with section headers and bullet points.
```

## Key Design Decisions to Research

- **Prompt storage:** Flat files in `prompts/` or structured in a config?
- **Dynamic templates:** Support variable substitution (doc_count, date_range, filters)
- **Citation format:** Standardize `doc_id:chunk_id` format across all responses
- **Model compatibility:** Design prompts that work across embedding/LLM backends

## Implementation Scope

1. Create `kb_server/prompts/` directory with template files
2. Register prompts capability via MCP server (`server.py`)
3. Add `use_prompt(name, arguments)` handler that executes against current KB state
4. Integration: chain `search_kb` results into `extract_answer` prompt automatically

## Open Questions

1. Should prompts run through the LLM backend or be template-only (client-side rendering)?
2. How to handle conflicting information across documents in `extract_answer`?
3. Rate limits on prompt generation?

## See Also

- `local_faiss_mcp` MCP prompts (GitHub: nonatofabio/local_faiss_mcp)
- `kb_server/server.py` — existing MCP tool registration
- MCP protocol `prompts` capability (modelcontextprotocol/specification)