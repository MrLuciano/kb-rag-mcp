# FASE 10 Gap — SECURITY.md Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write `docs/SECURITY.md` documenting the security posture, threat model, hardening checklist, and known limitations for KB-RAG-MCP.

**Architecture:** Documentation-only task. No code changes. The document covers: threat model (no-auth internal service), attack surface, hardening steps already implemented, remaining risks, and recommendations for production deployment.

**Tech Stack:** Markdown only.

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `docs/SECURITY.md` | Create | Security reference doc |
| `tests/e2e/test_deployment_workflow.py` | Modify | Add test that SECURITY.md exists |

---

## Task 1: Add existence test and write SECURITY.md

**Files:**
- Modify: `tests/e2e/test_deployment_workflow.py`
- Create: `docs/SECURITY.md`

- [ ] **Step 1: Write the failing test**

Open `tests/e2e/test_deployment_workflow.py` and add:

```python
def test_security_doc_exists(self):
    """SECURITY.md must exist and cover key topics."""
    security_path = Path("docs/SECURITY.md")
    self.assertTrue(security_path.exists(), "docs/SECURITY.md not found")
    content = security_path.read_text()
    for topic in ["threat", "authentication", "network", "hardening"]:
        self.assertIn(topic.lower(), content.lower(),
                      f"SECURITY.md should cover '{topic}'")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
PYTHONPATH=. pytest tests/e2e/test_deployment_workflow.py -k "test_security_doc_exists" -v
```
Expected: FAIL — `docs/SECURITY.md not found`

- [ ] **Step 3: Write docs/SECURITY.md**

```markdown
# KB-RAG-MCP Security Reference

> This document describes the security posture, threat model, hardening
> measures, and known limitations of KB-RAG-MCP. Last updated: 2026-05-18.

## Design Assumptions

KB-RAG-MCP is designed as an **internal, trusted-network service**:

- No authentication or authorization on any endpoint
- No user accounts or sessions
- No public internet exposure expected
- Consumers are local AI assistants (Claude Desktop, OpenCode) or internal tools
- All data (documents, embeddings) is treated as non-sensitive internal IP

If your deployment model differs from the above, see [Production Hardening](#production-hardening).

---

## Threat Model

### In-scope threats (mitigated)

| Threat | Vector | Mitigation |
|---|---|---|
| Malicious file injection | Ingest pipeline processes attacker-controlled files | Validators reject oversized, corrupt, or invalid files; file type whitelist enforced |
| Path traversal | File paths in ingest commands | All paths validated and resolved relative to `DOCS_PATH`; absolute paths rejected |
| Embedding API abuse | Rate of embedding requests to LM Studio | Token bucket rate limiter (`ingest/worker/limiter.py`) prevents overload |
| Qdrant data corruption | Bulk upsert with malformed vectors | Dimension check enforced before upsert; Qdrant rejects mismatched dims |
| Log injection | User-supplied query text logged | Queries logged as-is to SQLite (not shell/web logs); no command execution from logs |
| Backup tampering | Migration packages restored on import | SHA256 manifest validated before any file is written (`scripts/migrate/validate.py`) |

### Out-of-scope threats (accepted risks for internal use)

| Threat | Reason out of scope |
|---|---|
| Unauthorized MCP access | stdio transport; only the local AI process connects |
| Web UI unauthorized access | No auth; deploy on trusted network only |
| Health endpoint data leakage | Exposes metrics; not sensitive for internal use |
| Prompt injection via retrieved chunks | Out of scope for the RAG layer; LLM handles prompt safety |
| Qdrant direct access | Qdrant has no auth by default; restrict via network/firewall |

---

## Attack Surface

| Component | Port | Protocol | Auth | Notes |
|---|---|---|---|---|
| MCP server (stdio) | — | stdin/stdout | None | Only accessible to spawning process |
| MCP server (SSE) | 8000 | HTTP | None | Bind to `127.0.0.1` in production |
| Web UI | 8080 | HTTP | None | Internal only; disable if unused |
| Health server | 8081 | HTTP | None | Exposes `/health` and `/metrics` |
| Qdrant | 6333 (HTTP), 6334 (gRPC) | HTTP/gRPC | None | Localhost Docker; firewall from external |
| LM Studio | 1234 | HTTP | None | Embedding API; internal network only |

---

## Hardening Already Implemented

- **File type whitelist:** Only `.pdf`, `.docx`, `.xlsx`, `.pptx`, `.txt`, `.md`, `.py`, `.ts`, `.js`, `.doc`, `.xls`, `.ppt`, `.odt`, `.zip` accepted; all others skipped
- **File size limits:** Validator rejects files exceeding configured size threshold
- **Content validation:** Empty or zero-byte files rejected before embedding
- **Rate limiting:** Token bucket limits embedding API calls per minute
- **SHA256 manifests:** Migration packages verified before restore
- **Structured logging:** Logs written to file; no shell interpretation of log content
- **systemd sandboxing:** Services run as non-root with `ProtectSystem=strict`, `NoNewPrivileges=true` (see `deployment/systemd/`)
- **Qdrant local-only:** Docker binding to `localhost` by default

---

## Production Hardening

If deploying in a less-trusted environment, apply these additional measures:

### 1. Network isolation

```bash
# Bind MCP SSE server to localhost only
SSE_HOST=127.0.0.1

# Bind Web UI to localhost only
UI_HOST=127.0.0.1

# Bind health server to localhost only
HEALTH_HOST=127.0.0.1
```

Use a reverse proxy (nginx, Caddy) with TLS and auth if external access is needed.

### 2. Qdrant authentication

Qdrant 1.7+ supports API key authentication:

```yaml
# qdrant config
service:
  api_key: your-secret-key
```

Then set in `.env`:
```
QDRANT_API_KEY=your-secret-key
```

Note: `kb_server/vector_store.py` must be updated to pass `api_key` to `AsyncQdrantClient`.

### 3. Web UI basic auth (nginx example)

```nginx
location /ui {
    auth_basic "KB-RAG";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://127.0.0.1:8080;
}
```

### 4. systemd service hardening

The provided systemd units already include:
```ini
NoNewPrivileges=true
ProtectSystem=strict
PrivateTmp=true
```

Add for stricter isolation:
```ini
ProtectHome=true
CapabilityBoundingSet=
SystemCallFilter=@system-service
```

### 5. Log file permissions

```bash
chmod 640 /var/log/kb-rag/*.log
chown kb-rag:adm /var/log/kb-rag/*.log
```

### 6. Secrets management

Never commit `.env` to git. Use:
- systemd `EnvironmentFile=/etc/kb-rag/secrets.env` (mode 600, owned by service user)
- Or a secrets manager (Vault, AWS Secrets Manager, etc.)

---

## Known Limitations

| Limitation | Impact | Workaround |
|---|---|---|
| No auth on any endpoint | Any local process can query the MCP/UI/health | Network isolation + firewall |
| Query log stores raw queries | Query text visible to anyone with file access | Restrict `QUERY_LOG_PATH` file permissions |
| Qdrant collection has no ACL | Any process with network access can read/write vectors | Qdrant API key (see above) |
| No TLS on any endpoint | Traffic readable on local network | TLS termination via reverse proxy |
| LM Studio has no auth | Any process can call embedding API | Network-level isolation |
| ZIP extraction follows symlinks | Malicious ZIP could read arbitrary files | Max depth enforced; run ingest as unprivileged user |

---

## Security Contact

This is an internal tool. For security issues, open a GitHub issue or contact
the project maintainer directly.
```

- [ ] **Step 4: Run test**

```bash
PYTHONPATH=. pytest tests/e2e/test_deployment_workflow.py -k "test_security_doc_exists" -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docs/SECURITY.md tests/e2e/test_deployment_workflow.py
git commit -m "docs: add SECURITY.md with threat model, hardening checklist, and known limitations"
```
