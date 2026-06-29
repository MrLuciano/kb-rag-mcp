# API Reference

## Auth API (prefix: `/api/v1/auth`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/auth/login` | Login with username+password, get session cookie | None |
| POST | `/auth/session` | Exchange API key (Bearer) for session cookie | API Key |
| POST | `/auth/logout` | Clear session | Session cookie |

## Users API (prefix: `/api/v1`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/users` | List all users | Admin |
| POST | `/users` | Create user | Admin |
| GET | `/users/{id}` | Get user details | Admin |
| PUT | `/users/{id}` | Update user | Admin |
| DELETE | `/users/{id}` | Delete user | Admin |
| GET | `/users/me` | Current user info | Session/Key |

## API Keys API (prefix: `/api/v1`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api-keys` | List API keys | Admin |
| POST | `/api-keys` | Create API key | Admin |
| DELETE | `/api-keys/{prefix}` | Revoke API key | Admin |

## Config API (prefix: `/api/v1/config`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/config` | List all config entries | Env-config |
| GET | `/config/{key}` | Get single config value | Env-config |
| PUT | `/config/{key}` | Set/update config value | Env-config |
| DELETE | `/config/{key}` | Delete config entry | Env-config |
| POST | `/config/reset` | Reset all config to defaults | Env-config |

Request body for PUT:
```json
{"value": "...", "type": "string|int|bool|float", "group_name": "optional", "description": "optional"}
```

## Schedules API (prefix: `/api/v1/schedules`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/schedules` | List all schedules | Admin |
| POST | `/schedules` | Create schedule (returns 201) | Admin |
| GET | `/schedules/{id}` | Get schedule details | Admin |
| PUT | `/schedules/{id}` | Update schedule | Admin |
| DELETE | `/schedules/{id}` | Delete schedule | Admin |

Create schedule request body:
```json
{"name": "...", "cron_expr": "0 3 * * 1", "docs_path": "/path", "product": "AppServer", "workers": 2, "priority": "normal", "clean": false, "force": false}
```

## Erasure API (prefix: `/api/v1`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/erasure/request` | Request GDPR erasure | Session/Key |
| GET | `/erasure/status` | Check erasure status | Session/Key |
| POST | `/erasure/cancel` | Cancel erasure request | Session/Key |
| GET | `/erasure/pending` | List pending erasure requests | Admin |
| POST | `/erasure/approve/{user_id}` | Approve erasure | Admin |
| POST | `/erasure/execute/{user_id}` | Execute erasure | Admin |

## Health API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Overall health check |
| GET | `/health/embedding` | Embedding service status |
| GET | `/health/vectorstore` | Vector store status |

## Admin UI

The Admin SPA is served at `/admin/`. No REST API docs needed for the admin UI routes.
