# Step 1 handoff — OAuth & server boundary hardening (plan 43)

Test-first backend security hardening. Full suite: `168 passed` (was 159; +9 new
tests). Auth-code + PKCE and refresh-rotation flows remain green.

## What changed, per file

- `backend/mcp_oauth/tokens.py` — `TokenStore` schema creation is now lazy.
  `__init__` only stores `db_path` and sets `_schema_ready = False`; the new
  `_ensure_schema()` does the `parent.mkdir(...)` + `_init_schema()` (including
  the legacy plaintext-refresh migration) exactly once, on first data method
  call. Every public method (`register_client`, `client_allows`, `put_auth_code`,
  `consume_auth_code`, `put_refresh_token`, `rotate_refresh_token`) calls
  `_ensure_schema()` first. Net effect: constructing a `TokenStore` (which happens
  at `import main`) performs no filesystem writes.

- `backend/mcp_oauth/app.py` —
  - New absolute default `DEFAULT_AUTH_DB_PATH = Path(__file__).resolve().parent.parent / "hiking_food_auth.db"`
    (i.e. `backend/hiking_food_auth.db`, the same file the old relative `./`
    default resolved to under the prod `WorkingDirectory=backend/`). `create_router`
    now resolves `db_path or $HIKING_FOOD_AUTH_DB_PATH or str(DEFAULT_AUTH_DB_PATH)`.
  - New `_PasswordThrottle` (in-process, in-memory, keyed by client address) and
    an injectable clock: `create_router(..., now: Callable[[], float] = time.time)`.
    Tests pass a fake advanceable clock.
  - `authorize_post` now, after client validation and before password check:
    computes `address = request.client.host` (falls back to `"unknown"`), returns
    429 (re-rendered `authorize.html`) if the address is locked, records a failure
    on wrong password (401), and resets the address's counter on success.
  - Removed the `/.well-known/openid-configuration` and `/jwks` routes entirely.
    RFC 8414 `/.well-known/oauth-authorization-server` and
    `/.well-known/oauth-protected-resource` are unchanged.

- `backend/mcp_server.py` — new `build_transport_security()` returns a
  `TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=…,
  allowed_origins=…)`; `build_mcp_server()` now uses it instead of the previous
  `enable_dns_rebinding_protection=False`. Helpers `_env_list()` (comma-split) and
  `_issuer_host_and_origin()` (netloc + scheme://netloc of the issuer) support it.

- `backend/main.py` — deleted the `CORSMiddleware` block and its import. No
  replacement env var; the SPA is served same-origin.

- `backend/tests/test_mcp_oauth.py` — added `_FakeClock`, `_throttle_app` helper,
  and tests: throttle-per-address (5 fails → 429, correct password still blocked
  while locked, other address unaffected, window expires at +300s), success resets
  the counter, and discovery drops OIDC/JWKS while advertising only supported
  capabilities.

- `backend/tests/test_runtime_config.py` — added tests: no `access-control-allow-origin`
  header on API responses; MCP transport defaults reject an unexpected Host and
  honor the default hosts incl. the issuer host (exercised via the real
  `TransportSecurityMiddleware._validate_host`); env-var overrides for hosts/origins;
  `build_mcp_server()` enables protection; `import main` (subprocess, fresh
  `HIKING_FOOD_AUTH_DB_PATH`) creates no DB file; default auth-db path is
  CWD-independent (== `backend/hiking_food_auth.db`).

## New env vars (both optional; comma-separated lists)

- `HIKING_FOOD_MCP_ALLOWED_HOSTS` — bare `host:port` values. Default (when unset):
  `localhost:8000`, `127.0.0.1:8000`, `beebaby:8000`, PLUS the netloc of
  `HIKING_FOOD_OAUTH_ISSUER`. Setting it replaces the default list entirely.
- `HIKING_FOOD_MCP_ALLOWED_ORIGINS` — origins with scheme. Default (when unset):
  `http://localhost:8000`, `http://127.0.0.1:8000`, `http://beebaby:8000`, PLUS
  `{scheme}://{netloc}` of `HIKING_FOOD_OAUTH_ISSUER`. Setting it replaces the
  default list entirely.

Because the issuer host/origin is folded into the defaults, production (which
already sets `HIKING_FOOD_OAUTH_ISSUER` to the HTTPS Funnel URL) needs no extra
MCP host config.

## Throttle parameters

- Per client address (`request.client.host`), in-process, in-memory (not shared
  across processes, resets on restart).
- 5 consecutive failures → address locked; further attempts return HTTP 429 on the
  re-rendered `authorize.html` for 5 minutes (`THROTTLE_WINDOW_SECONDS = 300`).
- A successful authorization resets that address's counter.
- The window is measured from the 5th failure and expires after 5 minutes via the
  injectable clock; a different address is never affected.

## What a reconnecting OAuth client will notice

`/.well-known/openid-configuration` and `/jwks` now return 404. MCP-spec clients
use OAuth discovery (`/.well-known/oauth-authorization-server` +
`/.well-known/oauth-protected-resource`), which are unchanged, so new connections
are unaffected. Any client that cached the old OIDC document should perform a
one-time reconnect (re-run the OAuth discovery/authorization flow); no token or
registration data is lost — the auth DB is the same file as before.
