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
- OAuth dynamic clients and exact redirect URIs are persisted. Unknown clients and
  unregistered redirects are rejected after restart.
- Refresh tokens are stored only as SHA-256 hashes, rotate atomically on use, and
  cannot be replayed. Existing plaintext refresh-token rows migrate to hashes
  while preserving the next legitimate refresh exchange.
- At this checkpoint the full backend suite passes 159 tests; frontend lint and
  production build also pass.

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

## Next slice: remaining OAuth and server boundaries

Client registration, exact redirect validation, refresh rotation, hashed storage,
and legacy refresh-row migration are complete and covered in
`backend/tests/test_mcp_oauth.py`. Do not reimplement them.

The remaining weaknesses are confirmed in code:

- Password failures are not throttled.
- OIDC metadata advertises an ID-token response that the server does not issue.
- `backend/main.py` allows CORS from `*` even though the browser client is same-origin through the Vite/prod proxy.
- MCP transport has DNS-rebinding protection disabled.
- The OAuth SQLite path should be absolute/configurable and should avoid surprising import-time state changes.

Recommended test-first order for the remaining work:

1. Repeated password failures are throttled without making successful local use brittle.
2. Metadata describes only flows the service implements.
3. Remove wildcard CORS and enable a safe MCP host/origin policy without breaking the deployed chatbot.

Keep backward compatibility for existing legitimate loopback and HTTPS clients where possible. If a security correction necessarily invalidates old registrations or refresh tokens, document the one-time re-login requirement.

## Frontend deep-linking completed

The route/context divergence is fixed. Canonical trip URLs are:

- `/trips/:tripId` — planner
- `/trips/:tripId/daily-plan` — daily plan
- `/trips/:tripId/packing` — packing

The route trip ID controls context, the selector preserves the current trip
subroute, global pages retain selection without navigating away, legacy root and
packing URLs redirect, invalid paths have stable boundaries, and stale responses
cannot overwrite a newer route. The frontend harness covers these behaviors plus
every global page and recipe new/edit deep link.

## Remaining frontend slice

The Vitest, Testing Library, jest-dom, and jsdom harness is installed. Continue
test-first with the remaining behaviors:

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
