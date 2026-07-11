# API-driven cohesion cleanup handoff

Checkpoint: 2026-07-11 12:28 PDT

## Start here

/goal Continue the API-driven cohesion cleanup from this verified checkpoint. Preserve the current REST and MCP response contracts, use test-driven slices, and leave each slice committed and deployable.

Read these first:

1. `AGENTS.md`
2. `docs/specs/2026-07-11-01-api-driven-cohesion.md`
3. This handoff
4. `docs/agents/hiking-food-mcp.md` before exercising MCP trip planning

Then run:

```sh
git status --short
git log -4 --oneline
cd backend && venv/bin/pytest -q
cd ../frontend && pnpm lint && pnpm build
```

The intended starting state is a clean `main` worktree whose latest commits are:

- `2d868ca` — specify the cleanup and compatibility matrix
- `f81a9ac` — unify trip, inventory, and assignment mutations across REST and MCP
- `9e0760d` — harden database paths, versioned migrations, foreign keys, test isolation, and dependency locks
- the checkpoint commit containing this handoff — move trip and daily-plan projections behind `TripPlanningService`

## What is now true

- `TripPlanningService` is the shared application boundary for trip reads and writes.
- REST trip and daily-plan routers are thin HTTP adapters.
- MCP trip overview, summary, packing, shopping, daily-plan reads, regeneration, and assignment updates use the same service behavior.
- Trip input validation, selection validation, assignment validation, allocation invalidation, clone naming, and delete cascades are covered by public behavior tests.
- SQLite uses an absolute configurable path, foreign keys are enabled, migrations are versioned, pre-migration backups are retained, and the production database was migrated from schema 0 to 2 without row-count loss.
- Backend production and development dependencies are hash-locked and checked by the deployment gate.
- At this checkpoint the focused REST/MCP/daily-plan suite passes 80 tests.

Important implementation files:

- `backend/services/trip_planning.py`
- `backend/services/trip_queries.py`
- `backend/services/daily_plan_queries.py`
- `backend/routers/trips.py`
- `backend/routers/daily_plan.py`
- `backend/mcp_server.py`
- `backend/database.py`
- `backend/migrations.py`
- `backend/verify_database.py`

## Next slice: OAuth and server boundaries

Begin with public protocol tests in `backend/tests/test_mcp_oauth.py`. The current weaknesses are confirmed in code:

- Dynamic client registration returns a client ID but does not persist the client or its exact redirect URIs.
- Authorization accepts any client ID and any syntactically valid HTTPS/loopback redirect URI.
- Refresh tokens are stored in plaintext and are reusable rather than rotated.
- Password failures are not throttled.
- OIDC metadata advertises an ID-token response that the server does not issue.
- `backend/main.py` allows CORS from `*` even though the browser client is same-origin through the Vite/prod proxy.
- MCP transport has DNS-rebinding protection disabled.
- The OAuth SQLite path should be absolute/configurable and should avoid surprising import-time state changes.

Recommended test-first order:

1. Registered clients are persisted; unknown clients and unregistered redirects are rejected.
2. Refresh exchange rotates the refresh token and invalidates the previous token.
3. Persisted refresh credentials are one-way hashes, not bearer tokens.
4. Repeated password failures are throttled without making successful local use brittle.
5. Metadata describes only flows the service implements.
6. Remove wildcard CORS and enable a safe MCP host/origin policy without breaking the deployed chatbot.

Keep backward compatibility for existing legitimate loopback and HTTPS clients where possible. If a security correction necessarily invalidates old registrations or refresh tokens, document the one-time re-login requirement.

## Following slice: frontend route and data cohesion

The confirmed browser bug is that opening `/trips/2/daily-plan` can render trip 2 while `TripContext` still selects the first fetched trip; navigation then points back to trip 1. Make the route trip ID the source of truth for trip-scoped pages.

Add a frontend test harness first using pnpm only (Vitest, Testing Library, and jsdom are the likely fit). Cover at least:

- direct deep-link selects the route trip and keeps trip-scoped navigation on that trip;
- switching trips updates the canonical URL and data once;
- stale requests cannot overwrite a newer trip selection;
- mutations expose pending/error state and refresh the correct projections;
- quantity, half-serving, add, and remove controls have accessible names.

After behavior is covered, lazy-load route pages to remove the current large-bundle warning. Use `agent-browser` for localhost and BeeBaby verification, re-snapshotting after every navigation. Localhost is agent QA; ask the user to review the committed/deployed BeeBaby URL against live data.

## Final cleanup and completion audit

Only after OAuth and frontend slices are green:

- remove the remaining MCP imports from `routers.recipes` and `routers.snacks` by adding shared catalog projections;
- update `docs/architecture.md` so it describes the service boundary, migrations, database configuration, dependency locks, and MCP/OAuth topology accurately;
- run `backend/venv/bin/pytest -q`, `frontend/pnpm lint`, and `frontend/pnpm build`;
- commit, inspect the exact-SHA cicd-router result, and verify BeeBaby health and representative REST/MCP reads;
- review the compatibility/correctness/security/operations matrix in the spec and explicitly account for any unchecked row.

Do not broaden this cleanup into a visual redesign or new planning feature. The target is one cohesive API-driven product that behaves the same whether operated from the page or through MCP.
