# Data Inventory

**Last updated:** 2026-06-29
**Purpose:** GDPR compliance — catalog all data stores managed by kb-rag-mcp.

| Data Store | Data Categories | PII? | Retention | Deletion Method |
|---|---|---|---|---|
| `users` table (auth.db) | username, role, timestamps | Pseudonymous | Indefinite → tombstone on erasure | Anonymize username, clear is_active, hard-delete API keys |
| `api_keys` table (auth.db) | key_hash (SHA-256), prefix, timestamps | None | Until user erasure | Hard DELETE on user erasure |
| `audit_logs` table (auth.db) | actor_id (UUID), action, resource_type, timestamp | None | 90 days auto-prune | Hard DELETE after TTL via `prune_audit_logs(days=90)` |
| `config` table (kb_metadata.db) | key, value, type, group | None | Indefinite | Direct DELETE via Config API |
| `files` table (kb_metadata.db) | file path, SHA-256, metadata | None (product docs) | Indefinite | DELETE via registry API |
| `jobs` / `job_progress` (kb_metadata.db) | job config, file progress | None | 30 days (planned) | Manual cleanup |
| `quota_config` / `quota_usage` (kb_metadata.db) | Quota limits and counters | None | Indefinite | Direct DELETE |
| `reclassify_backups` / `reclassify_history` | Old metadata values | None | 30 days (configurable) | Auto-cleanup per retention env var |
| `connector_state` (kb_metadata.db) | Connector sync state, remote IDs | None | Indefinite | DELETE via connector API |
| `query_logs` (query_logs.db) | Query text, filters, latency, user | None (query text only) | 90 days auto-prune | Hard DELETE after TTL |
| `api_keys` — legacy (auth.db) | key_hash (SHA-256), prefix, scope | None | Until manual revoke | DELETE via CLI or API |
| Application logs (log files) | Request paths, response codes, timestamps | None (IP stripped) | 30 days | Log rotation |
| Qdrant vector store | Document chunks, embeddings, metadata | None (product docs) | Indefinite | Collection drop via Qdrant API |

## Breach Notification

In the event of a data breach affecting any of the above stores:

1. Identify the affected store(s) using this inventory
2. Determine data categories exposed — this table shows PII classification per store
3. For pseudonymous data (usernames): notify affected users within 72 hours per GDPR Article 33
4. For non-PII data (key hashes, config values, timestamps): log internally, no user notification required
5. Revoke all exposed API keys immediately via the API key revocation endpoint
6. Rotate any config values that were exposed (API keys, secrets stored in config table)
7. Document the incident in the audit log

## Related Documents

- `kb_server/auth/models.py` — SQLAlchemy model definitions
- `kb_server/auth/service.py` — Auth service with CRUD and audit logging
- `kb_server/auth/erasure.py` — GDPR erasure workflow implementation
- `kb_server/auth/router.py` — REST API with erasure and export endpoints
