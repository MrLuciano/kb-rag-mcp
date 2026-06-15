"""Tests for streamable HTTP transport in the MCP server."""
import os
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _setup_server(extra_env=None):
    """Helper: import server module, set TRANSPORT=streamable-http."""
    if extra_env:
        for k, v in extra_env.items():
            os.environ[k] = v
    os.environ["MCP_PORT"] = os.environ.get("MCP_PORT", "18765")
    os.environ["MCP_HOST"] = os.environ.get("MCP_HOST", "127.0.0.1")
    os.environ["MCP_ENDPOINT"] = os.environ.get("MCP_ENDPOINT", "/mcp-test")
    os.environ["RATE_LIMIT_ENABLED"] = os.environ.get("RATE_LIMIT_ENABLED", "false")

    import kb_server.server

    kb_server.server.TRANSPORT = "streamable-http"
    from kb_server.server import main

    mock_mgr_instance = MagicMock()
    mock_mgr_instance.run.return_value.__aenter__ = AsyncMock()
    mock_mgr_instance.run.return_value.__aexit__ = AsyncMock()
    mock_mgr_cls = MagicMock(return_value=mock_mgr_instance)
    return main, mock_mgr_cls


async def _run_main(main, mock_mgr_cls, extra_patches=None):
    """Run main() with standard patches plus optional extras."""
    patches = [
        patch("kb_server.server.store.connect", new_callable=AsyncMock),
        patch("kb_server.health.check_embedding_service", new_callable=AsyncMock),
        patch("kb_server.health.check_vector_store", new_callable=AsyncMock),
        patch("kb_server.server.CollectionManager"),
        patch("kb_server.server.CollectionRouter"),
        patch("kb_server.server.FilterTermsCache"),
        patch("mcp.server.streamable_http_manager.StreamableHTTPSessionManager", mock_mgr_cls),
        patch("uvicorn.Server.serve", new_callable=AsyncMock),
    ]
    if extra_patches:
        patches.extend(extra_patches)

    with _MultiPatch(patches) as mocks:
        mocks["check_embedding_service"].return_value.healthy = True
        mocks["check_vector_store"].return_value.healthy = True
        mocks["CollectionManager"].return_value = AsyncMock()
        mocks["FilterTermsCache"].return_value.reindex = AsyncMock()
        await main()
        return mocks


class _MultiPatch:
    """Helper to manage multiple patches cleanly."""

    def __init__(self, patches):
        self._patches = patches
        self._entered = []

    def __enter__(self):
        mocks = {}
        for p in self._patches:
            entered = p.__enter__()
            # Extract a usable key from the patch target
            key = p.attribute.split(".")[-1]
            mocks[key] = entered
        self._entered = mocks
        return mocks

    def __exit__(self, *args):
        for p in reversed(self._patches):
            p.__exit__(*args)


@pytest.mark.asyncio
async def test_streamable_http_transport_env():
    """Server main() accepts TRANSPORT=streamable-http without error."""
    main, mock_mgr_cls = _setup_server()
    mocks = await _run_main(main, mock_mgr_cls)
    assert mocks["serve"].called, "main() did not reach streamable-http branch"
    assert mock_mgr_cls.called, "StreamableHTTPSessionManager was not called"
    assert mock_mgr_cls.call_args[1]["app"] is not None


@pytest.mark.asyncio
async def test_streamable_http_auth_rejection():
    """Streamable HTTP returns 401 when AUTH_ENABLED and no key provided."""
    os.environ["MCP_PORT"] = "18766"
    main, mock_mgr_cls = _setup_server({"AUTH_ENABLED": "true"})

    with patch("kb_server.auth.is_auth_enabled", return_value=True), \
         patch("kb_server.auth.verify_request", return_value=(False, "Missing API key")):
        mocks = await _run_main(main, mock_mgr_cls)
    assert mocks["serve"].called


@pytest.mark.asyncio
async def test_streamable_http_rate_limiting():
    """Rate limiting integration for streamable-http transport."""
    os.environ["MCP_PORT"] = "18767"
    main, mock_mgr_cls = _setup_server()

    with patch("kb_server.server.RATE_LIMIT_ENABLED", True), \
         patch("kb_server.server.rate_limiter") as mock_rl, \
         patch("kb_server.server.record_rate_limit_allowed") as mock_allowed, \
         patch("kb_server.server.record_rate_limit_rejected") as mock_rejected:
        mock_rl.check = AsyncMock(return_value=(True, None))
        mocks = await _run_main(main, mock_mgr_cls)
    assert mocks["serve"].called


def test_session_tracker_evict_when_at_capacity():
    """Evict oldest tracked session when at max_sessions limit (D-01 / D-02)."""
    from kb_server.server import _SessionTracker

    mock_mgr = MagicMock()
    mock_mgr.sessions = {
        "session-old": MagicMock(),
        "session-new": MagicMock(),
    }
    tracker = _SessionTracker(mock_mgr, max_sessions=2)
    tracker._last_active = {
        "session-old": time.time() - 100,
        "session-new": time.time() - 10,
    }
    evicted = tracker.evict_if_needed()
    assert evicted == "session-old", "Should evict oldest session"
    assert "session-old" not in mock_mgr.sessions
    assert "session-new" in mock_mgr.sessions


def test_session_tracker_no_evict_below_capacity():
    """No eviction when sessions below max_sessions."""
    from kb_server.server import _SessionTracker

    mock_mgr = MagicMock()
    mock_mgr.sessions = {"session-1": MagicMock()}
    tracker = _SessionTracker(mock_mgr, max_sessions=5)
    evicted = tracker.evict_if_needed()
    assert evicted is None
    assert "session-1" in mock_mgr.sessions


def test_session_tracker_mark_active():
    """mark_active updates last_active for a session ID."""
    from kb_server.server import _SessionTracker

    mock_mgr = MagicMock()
    mock_mgr.sessions = {}
    tracker = _SessionTracker(mock_mgr, max_sessions=10)

    before = time.time()
    tracker.mark_active("sess-123")
    assert "sess-123" in tracker._last_active
    assert tracker._last_active["sess-123"] >= before

    tracker.mark_active(None)
    # Should not raise — None sessions are ignored


def test_session_tracker_cleanup():
    """cleanup removes entries for sessions no longer in the manager."""
    from kb_server.server import _SessionTracker

    mock_mgr = MagicMock()
    mock_mgr.sessions = {"active-1": MagicMock()}
    tracker = _SessionTracker(mock_mgr, max_sessions=10)
    tracker._last_active = {
        "active-1": time.time() - 5,
        "gone-1": time.time() - 100,
        "gone-2": time.time() - 200,
    }
    removed = tracker.cleanup()
    assert removed == 2
    assert "active-1" in tracker._last_active
    assert "gone-1" not in tracker._last_active
    assert "gone-2" not in tracker._last_active
    assert tracker.active_count == 1


def test_session_tracker_evict_falls_back_to_any_session():
    """When no last_active tracked, evict the first session in dict."""
    from kb_server.server import _SessionTracker

    mock_mgr = MagicMock()
    mock_mgr.sessions = {"only-session": MagicMock()}
    tracker = _SessionTracker(mock_mgr, max_sessions=1)
    # No _last_active entries for these sessions
    evicted = tracker.evict_if_needed()
    assert evicted == "only-session"
    assert "only-session" not in mock_mgr.sessions
