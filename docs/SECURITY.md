# KB-RAG-MCP Security Reference

> This document describes the security posture, threat model, hardening
> measures, and known limitations of KB-RAG-MCP. Last updated: 2026-06-11.

## Design Assumptions

KB-RAG-MCP is designed as an **internal, trusted-network service**:

- Authentication is **optional and opt-in** (`AUTH_ENABLED=false` by default); existing deployments are fully backward compatible
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
| Unauthorized SSE access | Network access to MCP SSE endpoint | `AUTH_ENABLED` mitigates with Bearer token (SHA-256 hashed keys via `kb-rag auth`) |
| Rate limit abuse | High-volume requests to SSE endpoint | `RATE_LIMIT_ENABLED` applies per-subject token bucket; HTTP 429 on exhaustion |
| Upload quota exhaustion | Bulk ingest saturates disk/storage | Quota check (`kb-rag quota set`) rejects oversized uploads before expensive processing |

### Out-of-scope threats (accepted risks for internal use)

| Threat | Reason out of scope |
|---|---|
| Unauthorized MCP access (stdio) | stdio transport has no auth; only the local AI process connects; SSE can be protected via `AUTH_ENABLED` |
| Web UI unauthorized access | No auth; deploy on trusted network only |
| Health endpoint data leakage | Exposes metrics; not sensitive for internal use |
| Prompt injection via retrieved chunks | Out of scope for the RAG layer; LLM handles prompt safety |
| Qdrant direct access | Qdrant has no auth by default; restrict via network/firewall |

---

## Attack Surface

| Component | Port | Protocol | Auth | Notes |
|---|---|---|---|---|
| MCP server (stdio) | — | stdin/stdout | None | Only accessible to spawning process |
| MCP server (SSE) | 8000 | HTTP | Bearer token (optional, `AUTH_ENABLED`) | Bind to `127.0.0.1` in production |
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
- **Safe archive extraction:** ZIP and tar extraction filters path traversal members (`..` and absolute paths) before writing
- **API key authentication:** Optional Bearer token auth on SSE endpoint; `AUTH_ENABLED=true` enables it; SHA-256 hashed keys managed via `kb-rag auth create/list/revoke`
- **Rate limiting:** `RATE_LIMIT_ENABLED=true` enables per-subject token bucket; returns HTTP 429 on exhaustion
- **Upload quotas:** Per-source quotas via `kb-rag quota set/show/reset`; schema migration (v3→v4) included

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

Use a reverse proxy (nginx, Caddy) with TLS and authentication if external access is needed.

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

The `_sanitize_env` function in `scripts/migrate/export.py` redacts any key containing
`password`, `secret`, `token`, or `key` in migration packages.

---

## Known Limitations

| Limitation | Impact | Workaround |
|---|---|---|
| Auth off by default (`AUTH_ENABLED=false`) | MCP SSE, UI, and health endpoints unprotected unless configured | Enable `AUTH_ENABLED=true` + create keys via `kb-rag auth create`; stdio remains unauth |
| Query log stores raw queries | Query text visible to anyone with file access | Restrict `QUERY_LOG_PATH` file permissions |
| Qdrant collection has no ACL | Any process with network access can read/write vectors | Qdrant API key (see above) |
| No TLS on any endpoint | Traffic readable on local network | TLS termination via reverse proxy |
| LM Studio has no auth | Any process can call embedding API | Network-level isolation |
| ZIP extraction follows symlinks | Malicious ZIP could read arbitrary files | Max depth enforced; run ingest as unprivileged user |

---

## Security Contact

This is an internal tool. For security issues, open a GitHub issue or contact
the project maintainer directly.
