# OAuth and Server Boundary Hardening

## Goal

Close the remaining confirmed security weaknesses in the OAuth and server
boundaries: throttle password failures, stop advertising OIDC flows the server
does not implement, remove wildcard CORS, enable MCP DNS-rebinding protection,
and make the OAuth database path absolute and lazy. Preserve the working
authorization-code + PKCE flow for existing chatbot clients.

Blocked by: none.

## Context

Facts confirmed in code (2026-07-11):

- Password check: `verify_password` at `backend/mcp_oauth/tokens.py:247-251`,
  called from `authorize_post` at `backend/mcp_oauth/app.py:156`. Failure
  re-renders `authorize.html` with 401. No throttling, lockout, or attempt
  counting exists anywhere; no rate-limit library is installed.
- Metadata: `metadata()` at `backend/mcp_oauth/app.py:51-62` advertises only
  `response_types_supported: ["code"]`, but
  `GET /.well-known/openid-configuration` (`app.py:68-75`) adds `jwks_uri`,
  `subject_types_supported`, and `id_token_signing_alg_values_supported` even
  though the token endpoint (`app.py:172-209`) never issues an ID token and
  `GET /jwks` (`app.py:86-88`) returns an empty key set.
- CORS: `backend/main.py:45-51` adds `CORSMiddleware` with
  `allow_origins=["*"]` and `allow_credentials=True`, hardcoded. Prod serves
  the SPA same-origin from the same uvicorn process; dev uses the Vite proxy
  (`frontend/vite.config.js:17-24`), so no legitimate cross-origin browser
  caller exists.
- MCP transport: `build_mcp_server()` at `backend/mcp_server.py:36-49` sets
  `TransportSecuritySettings(enable_dns_rebinding_protection=False)`.
- OAuth DB path: `create_router` defaults to relative `./hiking_food_auth.db`
  (`backend/mcp_oauth/app.py:46`, env override `HIKING_FOOD_AUTH_DB_PATH`), and
  `TokenStore.__init__` (`tokens.py:56-60`) creates directories and runs
  `_init_schema()` immediately — which happens at import time of `main.py`
  because `create_oauth_router()` is called at module level (`main.py:60`).
  The main app DB does this right: absolute default anchored to
  `Path(__file__)` with env override (`backend/database.py:7-11`) and deferred
  table creation in the lifespan.
- Prod `WorkingDirectory` is `backend/` (`deploy/hiking-food.service:6`), so
  the current relative default already resolves to
  `backend/hiking_food_auth.db` — an absolute default anchored there points at
  the same file and needs no data migration.
- Test pattern to follow: `backend/tests/test_mcp_oauth.py` builds a fresh
  `FastAPI()` + `create_router(db_path=str(tmp_path / "auth.db"), issuer=...)`
  per test, sets env via `monkeypatch.setenv`, and uses the `_challenge()`
  PKCE helper.

## Decisions (made, not open)

- Throttling is in-process and in-memory, keyed by client address, with an
  injectable clock for tests. After 5 consecutive failures, further attempts
  from that address are rejected for 5 minutes (HTTP 429 on the re-rendered
  form). Any successful authorization resets the counter. No new dependency.
- `/.well-known/openid-configuration` and `/jwks` are removed entirely. The
  RFC 8414 `/.well-known/oauth-authorization-server` and
  `/.well-known/oauth-protected-resource` endpoints remain — MCP-spec clients
  use OAuth discovery, not OIDC. If a previously connected client cached the
  OIDC document, a one-time reconnect is the documented remedy.
- The `CORSMiddleware` block is deleted with no replacement env var.
- DNS-rebinding protection is enabled with allowed hosts/origins from
  `HIKING_FOOD_MCP_ALLOWED_HOSTS` / `HIKING_FOOD_MCP_ALLOWED_ORIGINS` env vars,
  defaulting to `localhost:8000`, `127.0.0.1:8000`, `beebaby:8000`, plus the
  host of `HIKING_FOOD_OAUTH_ISSUER` so the HTTPS Funnel hostname is accepted
  in production without extra configuration.
- OAuth DB default becomes an absolute path anchored beside the backend
  package (same file the relative default resolves to in prod); the
  `HIKING_FOOD_AUTH_DB_PATH` override stays. Schema creation moves out of
  `TokenStore.__init__` to first use, so importing `main` never creates or
  migrates a database file.

## Tasks

Test-first: each behavior gets a failing test in
`backend/tests/test_mcp_oauth.py` (or `test_runtime_config.py` where noted)
before the change, following the existing per-test `tmp_path` isolation.

- [x] Throttle repeated password failures: 5 consecutive failures from one
  client address → 429 with the error rendered on the form; a success resets
  the counter; the window expires after 5 minutes via the injectable clock;
  a different client address is unaffected.
- [x] Remove `/.well-known/openid-configuration` and `/jwks`; test that they
  return 404 and that `/.well-known/oauth-authorization-server` still
  advertises exactly the implemented capabilities (`code`,
  `authorization_code`/`refresh_token`, `S256`, `none`, both scopes).
- [x] Remove the `CORSMiddleware` block from `backend/main.py`; test that API
  responses carry no `access-control-allow-origin` header for a cross-origin
  request.
- [x] Enable DNS-rebinding protection in `build_mcp_server()` with the env-var
  host/origin policy above; test that a request with a disallowed Host is
  rejected and the default allowed hosts (including the issuer host) are
  honored.
- [x] Make the OAuth DB path absolute-by-default with env override, and defer
  schema creation to first use; test that importing `main` (fresh module
  state) creates no database file and that the default path is CWD-independent.
- [x] Run the full backend suite: `cd backend && venv/bin/pytest -q` — all
  tests pass, none skipped that ran before.

## Acceptance criteria

- [x] Repeated wrong-password attempts are throttled per client address and
  recover after the window; successful local use is not made brittle.
- [x] Discovery metadata describes only flows the service implements; OIDC
  discovery and the empty JWKS endpoint are gone.
- [x] No wildcard CORS: the API grants no cross-origin browser access.
- [x] MCP transport rejects requests with unexpected Host/Origin values while
  accepting localhost, beebaby, and the production issuer host.
- [x] The OAuth database path is absolute or explicitly configured, and
  importing the application performs no database writes.
- [x] The authorization-code + PKCE flow, refresh rotation, and existing
  registered clients keep working (existing OAuth tests remain green).

## Done when

`cd backend && venv/bin/pytest -q` passes with new coverage for all five
behaviors, and after the deployed commit the live BeeBaby discovery endpoints
serve the trimmed metadata, the authorize page renders, and the MCP endpoint
still returns its 401 discovery challenge through the funnel hostname.
