"""
Tests for Phase 31 MCP prompt templates (extract_answer, summarize_documents).
"""

from unittest.mock import MagicMock, patch

import pytest

from kb_server.prompts import (
    PROMPT_DEFINITIONS,
    render_extract_answer,
    render_prompt,
    render_summarize_documents,
)


class TestPromptDefinitions:
    def test_extract_answer_registered(self):
        assert "extract_answer" in PROMPT_DEFINITIONS
        p = PROMPT_DEFINITIONS["extract_answer"]
        assert p.name == "extract_answer"
        assert len(p.arguments) == 2
        arg_names = [a.name for a in p.arguments]
        assert "question" in arg_names
        assert "search_results" in arg_names

    def test_summarize_documents_registered(self):
        assert "summarize_documents" in PROMPT_DEFINITIONS
        p = PROMPT_DEFINITIONS["summarize_documents"]
        assert p.name == "summarize_documents"
        arg_names = [a.name for a in p.arguments]
        assert "documents" in arg_names
        assert "focus" in arg_names

    def test_two_prompts_total(self):
        assert len(PROMPT_DEFINITIONS) == 2


class TestRenderExtractAnswer:
    def test_renders_with_question_and_results(self):
        messages = render_extract_answer(
            {
                "question": "How to install AppServer?",
                "search_results": "[doc1: AppServer install guide]",
            }
        )
        assert len(messages) == 1
        assert messages[0].role == "user"
        text = messages[0].content.text
        assert "How to install AppServer?" in text
        assert "AppServer install guide" in text
        assert "Answer:" in text
        assert "Sources:" in text

    def test_empty_question(self):
        messages = render_extract_answer(
            {
                "question": "",
                "search_results": "some results",
            }
        )
        text = messages[0].content.text
        assert "## User Question" in text

    def test_empty_results(self):
        messages = render_extract_answer(
            {
                "question": "test",
                "search_results": "",
            }
        )
        text = messages[0].content.text
        assert "## Retrieved Document Chunks" in text


class TestRenderSummarizeDocuments:
    def test_renders_with_documents(self):
        messages = render_summarize_documents(
            {
                "documents": "[doc1, doc2, doc3]",
            }
        )
        assert len(messages) == 1
        assert messages[0].role == "user"
        text = messages[0].content.text
        assert "doc1" in text
        assert "### Overview" in text

    def test_renders_with_focus(self):
        messages = render_summarize_documents(
            {
                "documents": "[docs]",
                "focus": "security",
            }
        )
        text = messages[0].content.text
        assert "security" in text
        assert "Area of Focus" in text

    def test_empty_documents(self):
        messages = render_summarize_documents(
            {
                "documents": "",
            }
        )
        text = messages[0].content.text
        assert "## Documents to Summarize" in text


class TestRenderPrompt:
    def test_render_extract_answer(self):
        result = render_prompt(
            "extract_answer",
            {
                "question": "Q?",
                "search_results": "results",
            },
        )
        assert result.description
        assert len(result.messages) == 1
        assert "Q?" in result.messages[0].content.text

    def test_render_summarize_documents(self):
        result = render_prompt(
            "summarize_documents",
            {
                "documents": "[docs]",
            },
        )
        assert result.description
        assert len(result.messages) == 1

    def test_unknown_prompt_raises(self):
        with pytest.raises(ValueError, match="Unknown prompt"):
            render_prompt("nonexistent", {})

    def test_none_arguments(self):
        result = render_prompt("extract_answer", None)
        assert len(result.messages) == 1


class TestServerPromptRegistration:
    @pytest.mark.asyncio
    async def test_list_prompts_returns_prompts(self):
        import kb_server.server as srv

        prompts = await srv.list_prompts()
        names = [p.name for p in prompts]
        assert "extract_answer" in names
        assert "summarize_documents" in names
        assert len(prompts) == 2

    @pytest.mark.asyncio
    async def test_get_prompt_returns_content(self):
        import kb_server.server as srv

        result = await srv.get_prompt(
            "extract_answer",
            {"question": "Q?", "search_results": "docs"},
        )
        assert result.description
        assert len(result.messages) == 1
        assert "Q?" in result.messages[0].content.text

    @pytest.mark.asyncio
    async def test_get_prompt_unknown_raises(self):
        import kb_server.server as srv

        with pytest.raises(ValueError, match="Unknown prompt"):
            await srv.get_prompt("nonexistent", {})
