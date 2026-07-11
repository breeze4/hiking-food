# Shared Catalog Projections and Completion Audit

## Goal

Remove the last MCP imports from REST routers by introducing shared catalog
projections, bring `docs/architecture.md` back in line with reality, and run
the full completion audit: gates, deploy verification, and an explicit
accounting of the spec's compatibility/correctness/security/operations
behaviors.

Blocked by: 43-oauth-server-hardening, 44-frontend-mutation-ux.

## Context

Facts confirmed in code (2026-07-11):

- `backend/mcp_server.py:14-15` imports `routers.recipes.list_recipes` (a
  route handler called with `db=` to bypass `Depends`) and
  `routers.snacks._to_response` (a private projection helper). Both are used
  only in the `list_food_options` tool (`mcp_server.py:76-103`), which also
  duplicates the snack join query from `routers/snacks.py:49-54`. No other
  `routers.*` imports remain in `mcp_server.py`.
- Service pattern to follow: `services/trip_queries.py` /
  `services/daily_plan_queries.py` — pure projection modules, `db: Session`
  first arg, `<noun>_view` / `<noun>_list_view` naming, plain dicts, no
  FastAPI. There is no catalog-scoped module yet.
- Test coverage gap: no test exercises `list_food_options` behavior (only its
  presence in the tool surface, `test_mcp_tools.py:51`). The
  `test_mcp_overview_matches_rest_trip_and_summary` pattern
  (`test_mcp_tools.py:126-135`) cross-checks MCP vs REST and can be extended
  to catalog parity.
- `docs/architecture.md` stale claims: Migrations described as inline
  `_add_column_if_missing` with "no Alembic" (now versioned migrations with
  pre-migration backups in `backend/migrations.py`); Database section omits
  the `HIKING_FOOD_DATABASE_URL` override and the SQLite FK listener;
  Services section omits `TripPlanningService`/`trip_queries`/
  `daily_plan_queries` and still claims business logic lives in routers;
  Dependencies claims "four unpinned packages" (now hash-locked
  `requirements.txt` + `requirements-dev.txt`); router list omits
  `food_intake` and says tests override six `get_db` modules (now seven).
  The MCP and CORS/Auth sections must also reflect plan 43's changes.

## Decisions (made, not open)

- New module `backend/services/catalog_queries.py` with
  `recipe_list_view(db, category=None)` (logic moved from
  `routers.recipes.list_recipes`) and `snack_view(item, ingredient)` plus
  `snack_list_view(db, category=None)` (moved from `routers/snacks.py`
  `_to_response` and the list join). REST routers and
  `mcp_server.list_food_options` both call the service; response shapes are
  byte-for-byte unchanged.
- The spec has no literal checkbox matrix; the audit deliverable is a table in
  this step's handoff file mapping every bullet under the spec's
  "Compatibility behaviors to preserve", "Correctness behaviors to add",
  "Security behaviors to add", and "Operational behaviors to add" to the test
  or commit that covers it, with any uncovered row called out explicitly.

## Tasks

- [x] Add behavior tests for `list_food_options` (recipes and snacks returned,
  category and query filters work) and a REST-vs-MCP catalog parity
  cross-check, following the existing `test_mcp_tools.py` patterns. These
  pass against the current implementation before the refactor.
- [x] Create `services/catalog_queries.py` per the decision above; point
  `routers/recipes.py`, `routers/snacks.py`, and `mcp_server.py` at it;
  delete the `routers.*` imports from `mcp_server.py` and the duplicated
  snack join. REST response shapes unchanged (existing REST tests stay
  green).
- [x] Update `docs/architecture.md`: service boundary (trip planning and
  catalog projections), versioned migrations with backups, database
  configuration (env overrides, absolute paths, FK enforcement), dependency
  locks, MCP/OAuth topology including plan 43's CORS/metadata/transport
  changes, and the corrected router/test-fixture counts.
- [x] Run the full gates: `cd backend && venv/bin/pytest -q` and
  `cd frontend && pnpm test && pnpm lint && pnpm build`.
- [x] Commit, push, and inspect the exact-SHA cicd-router result for this
  commit; verify BeeBaby health at `http://beebaby:8000/hiking-food/` plus
  representative REST reads and MCP discovery/tool reads.
- [x] Write the spec-behavior accounting table into this step's handoff file;
  every bullet in the spec's four behavior lists is mapped to covering
  evidence or explicitly flagged as uncovered.

## Acceptance criteria

- [x] `mcp_server.py` imports nothing from any `routers.*` module.
- [x] REST recipe/snack list responses are byte-identical to before the
  refactor; MCP `list_food_options` behavior is covered by tests.
- [x] `docs/architecture.md` accurately describes the service boundary,
  migrations, database configuration, dependency locks, and MCP/OAuth
  topology as they exist after plans 43 and 44.
- [x] All backend and frontend gates pass; the deployed commit is verified
  healthy on BeeBaby with working REST and MCP reads.
- [x] Every spec behavior bullet is explicitly accounted for.

## Done when

The full backend and frontend gates are green, the deployed exact-SHA commit
serves healthy REST and MCP reads on BeeBaby, and the handoff file contains
the complete spec-behavior accounting with no unexplained rows.
