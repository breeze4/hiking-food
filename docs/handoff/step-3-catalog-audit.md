# Step 3 handoff — shared catalog projections + completion audit (plan 45)

Test-first backend refactor plus documentation. No commit/push/deploy performed
(the orchestrator handles git and BeeBaby verification after a separate
verifier passes).

## Result summary

- `backend/mcp_server.py` now imports nothing from any `routers.*` module.
- Recipe and snack catalog projections live in one place
  (`backend/services/catalog_queries.py`); REST routers and the MCP
  `list_food_options` tool both call it, so REST payloads are byte-for-byte
  unchanged.
- `docs/architecture.md` corrected to match the system after plans 43, 44, 45.
- Gates: backend `173 passed`; frontend `39 tests` pass, lint clean, build
  clean (no large-bundle warning).

## Gate output

- `cd backend && venv/bin/pytest -q` → `173 passed` (168 before + 5 new catalog
  tests). All pre-existing REST tests stay green.
- `cd frontend && pnpm test` → 8 files / 39 tests pass (frontend untouched).
- `cd frontend && pnpm lint` → clean.
- `cd frontend && pnpm build` → clean; entry chunk 306.44 kB (gzip 98.18 kB),
  no chunk-size warning.
- `grep -n "routers\." backend/mcp_server.py` → no matches (exit 1). Zero
  `routers.*` references of any kind remain.

## Changes per file

- `backend/services/catalog_queries.py` (new) — shared catalog projection
  module following the `services/trip_queries.py` pattern (`db: Session` first
  arg, `<noun>_view` / `<noun>_list_view` naming, plain dicts, no FastAPI
  imports). Contains `recipe_ingredients(db, recipe_id)` (moved verbatim from
  `routers/recipes.py::_get_recipe_ingredients`), `recipe_list_view(db,
  category=None)` (moved verbatim from `routers/recipes.py::list_recipes`
  body), `snack_view(item, ingredient)` (moved verbatim from
  `routers/snacks.py::_to_response`), and `snack_list_view(db, category=None)`
  (moved verbatim from `routers/snacks.py::list_snacks` join). Result dicts are
  identical to the originals.

- `backend/routers/recipes.py` — imports `catalog_queries` and re-exports its
  `recipe_ingredients` under the old private name
  (`recipe_ingredients as _get_recipe_ingredients`) so `get_recipe`,
  `create_recipe`, and `update_recipe` keep working unchanged. The local
  `_get_recipe_ingredients` definition is deleted (single source now in the
  service). `list_recipes` is a thin wrapper: `return
  catalog_queries.recipe_list_view(db, category)`. Decorator and signature
  unchanged, so REST output is identical.

- `backend/routers/snacks.py` — imports `catalog_queries`; deletes the local
  `_to_response`. `list_snacks` becomes `return
  catalog_queries.snack_list_view(db, category)`; `create_snack` and
  `update_snack` now return `catalog_queries.snack_view(item, ingredient)`, so
  there is a single snack projection across all snack routes.

- `backend/mcp_server.py` — deleted the two router imports (`from
  routers.recipes import list_recipes as build_recipe_list` and `from
  routers.snacks import _to_response as build_snack`) and the now-unused `from
  models import Ingredient, SnackCatalogItem`; added `from services import
  catalog_queries`. `list_food_options` now calls
  `catalog_queries.recipe_list_view(db, category)` and
  `catalog_queries.snack_list_view(db, category)` instead of the router handler
  and the duplicated snack join. The `needle`/`query` filtering and `kind`
  branching are unchanged.

- `backend/tests/test_mcp_tools.py` — added five behavior tests for
  `list_food_options` (pinned against the pre-refactor implementation first,
  then kept green after): `test_list_food_options_returns_recipes_and_snacks`,
  `test_list_food_options_kind_selects_one_catalog`,
  `test_list_food_options_category_filters_each_catalog`,
  `test_list_food_options_query_filters_by_name`, and the REST-vs-MCP parity
  cross-check `test_list_food_options_matches_rest_catalog` (asserts MCP
  recipes == `/api/recipes` and MCP snacks == `/api/snacks`).

- `docs/architecture.md` — corrected Database, Migrations, Routing, Session
  management, Schemas, Services, Configuration, Dependencies, CORS/Auth, MCP,
  Frontend, and Testing sections (details below).

- `docs/plans/45-catalog-projections-audit.md` — checked off completed tasks
  and satisfied acceptance criteria; the commit/deploy task and the
  deployed-healthy acceptance bullet are left unchecked for the orchestrator.

## `docs/architecture.md` corrections applied

- Migrations: replaced the "inline `main.py:_run_migrations()` /
  `_add_column_if_missing` / no Alembic / fully manual" description with the
  real mechanism — ordered versioned migrations in `backend/migrations.py`
  run from the lifespan, gated on `PRAGMA user_version`, with a pre-migration
  backup (10 kept, `HIKING_FOOD_BACKUP_DIR` override) and a refuse-if-newer
  guard.
- Database: added the `HIKING_FOOD_DATABASE_URL` override, the absolute default
  path anchored to `database.py`, and the SQLite `connect` listener issuing
  `PRAGMA foreign_keys=ON`.
- Services: replaced "business logic lives in routers" with the real boundary —
  `TripPlanningService` owns workflow; `trip_queries` / `daily_plan_queries` /
  `catalog_queries` own projections; routers and MCP are thin adapters.
- Configuration: replaced "all config hardcoded / no env vars" with the real
  env-var list (`HIKING_FOOD_DATABASE_URL`, `_OAUTH_ISSUER`, `_JWT_KEY`,
  `_AUTH_PASSWORD`, `_AUTH_DB_PATH`, `_MCP_ALLOWED_HOSTS`, `_MCP_ALLOWED_ORIGINS`,
  `_BACKUP_DIR`).
- Dependencies: replaced "four unpinned packages" with hash-locked
  `requirements.txt` + `requirements-dev.txt`.
- Routing / Session mgmt: corrected to seven routers including `food_intake`
  and the seven `get_db` overrides in conftest.
- CORS/Auth: `CORSMiddleware` removed (SPA served same-origin, no
  cross-origin grant); added per-address password throttling and the trimmed
  discovery (OIDC `/.well-known/openid-configuration` and `/jwks` removed).
- MCP: DNS-rebinding protection enabled with the env-driven host/origin policy
  and its issuer-derived defaults.
- Frontend: `React.lazy` + single `Suspense` route splitting, the shared
  `useMutation` hook (pending/error at every mutation call site), and accessible
  control names.
- Testing: replaced "No frontend tests — no test runner" with the real Vitest
  suite (8 files / 39 tests) and its coverage; noted the backend REST-vs-MCP
  catalog parity check and that backend tests never touch the real app/OAuth
  database.

## Confirmation: zero `routers.*` imports in `mcp_server.py`

```
$ grep -n "routers\." backend/mcp_server.py
$ echo $?
1
```

No matches. The only remaining cross-module imports in `mcp_server.py` are
`database.SessionLocal`, `services.catalog_queries`, and
`services.trip_planning.TripPlanningService`.

## Spec-behavior accounting

Spec: `docs/specs/2026-07-11-01-api-driven-cohesion.md`. Every bullet in the
four behavior lists is mapped below to the covering test (file::name) or
commit, with any gap flagged. Backend tests are under `backend/tests/`;
frontend tests under `frontend/src/`. Step attribution: S1 = plan 43
(commit-level), S2 = plan 44, S3 = this step.

### Compatibility behaviors to preserve

| Spec bullet | Covered by | Notes |
| --- | --- | --- |
| Existing ingredient, recipe, snack, trip, packing, shopping, macro, intake REST response shapes | `test_ingredient_macros.py`, `test_snack_macros.py`, `test_recipe_calc.py`, `test_trip_summary_macros.py`, `test_daily_plan_macros.py`, `test_shopping_list.py`, `test_food_intake.py`, `test_settings.py`, and S3 `test_mcp_tools.py::test_list_food_options_matches_rest_catalog` | Covered. Full suite green (173) after the projection move confirms recipe/snack shapes are byte-identical; the S3 parity test asserts recipe/snack payload equality REST vs MCP. |
| Deterministic auto-fill and existing meal/snack/drink distribution rules | `test_daily_plan.py::test_deterministic`, `::test_meals_distributed_to_correct_slots`, `::test_meals_heaviest_first`, `::test_snacks_distributed_evenly_not_front_loaded`, `::test_drink_mix_even_distribution`; `test_slots.py`; `test_drink_mix.py` | Covered. |
| Trip clone workflows and the compact MCP tool surface | `test_trip_workflows.py::test_rest_clone_preserves_inventory_and_uses_unique_names`; `test_mcp_tools.py::test_clone_adjust_autofill_and_read_workflow`, `::test_duplicate_destination_is_rejected`, `::test_tool_surface_is_small_and_stable` | Covered. Tool surface list is asserted stable. |
| OAuth authorization-code + PKCE access for registered public clients | `test_mcp_oauth.py::test_oauth_metadata_registration_code_and_refresh_flow`, `::test_registered_client_survives_restart_and_only_uses_exact_redirect` | Covered (S1). |
| Existing mobile planner, daily-plan, and packing workflows | Frontend `App.test.jsx` (planner/daily-plan/packing routes), `pages/DailyPlanPage.test.jsx`, `pages/PackingScreen.test.jsx`, `components/MealSelection.test.jsx`, `components/SnackSelection.test.jsx`, `components/TripCalculator.test.jsx`; backend `test_daily_plan.py`, `test_shopping_list.py` | Covered (S2 frontend + existing backend). |

### Correctness behaviors to add

| Spec bullet | Covered by | Notes |
| --- | --- | --- |
| Invalid names, ranges, enum values, references, negative quantities rejected consistently by REST and MCP | REST: `test_trip_workflows.py::test_rest_rejects_blank_trip_name`, `::test_rest_rejects_out_of_range_day_fraction`, `::test_rest_rejects_negative_full_days`, `::test_rest_rejects_invalid_trip_targets`, `::test_rest_rejects_unknown_assignment_source_type`, `::test_rest_rejects_unknown_assignment_slot`, `::test_rest_rejects_negative_meal_quantity`, `::test_rest_rejects_negative_snack_servings`, `::test_rest_rejects_duplicate_trip_name`. MCP: `test_mcp_tools.py::test_duplicate_destination_is_rejected`, `::test_assignment_update_cannot_exceed_trip_inventory` | Covered. Consistency is structural: both transports enforce validation through the shared `TripPlanningService`. REST has exhaustive negative tests; MCP has representative negative tests plus the shared-service guarantee. |
| Full first/last days receive full-day eligibility and presentation | `test_daily_plan.py::test_first_day_fraction_one_is_a_full_day`, `::test_last_day_fraction_one_is_a_full_day`, `::test_first_partial_no_breakfast`, `::test_last_partial_no_dinner` | Covered. |
| Allocation-affecting trip/inventory changes invalidate daily assignments in both transports; display-only and packing-only changes do not | Positive (REST): `test_trip_workflows.py::test_rest_trip_shape_change_invalidates_daily_plan`, `::test_rest_meal_quantity_change_invalidates_daily_plan`, `::test_rest_snack_servings_change_invalidates_daily_plan`, `::test_rest_adding_meal_invalidates_daily_plan`, `::test_rest_adding_snack_invalidates_daily_plan`. Positive (MCP): `test_mcp_tools.py::test_inventory_change_clears_stale_assignments`. Negative: implemented in `services/trip_planning.py` (`_clear_assignments` guarded by `ALLOCATION_SHAPE_FIELDS` / `quantity` / `{servings, slot}`) | Positive half fully covered in both transports. The negative half ("display-only and packing-only changes do NOT invalidate") is implemented via the guarded conditional but has NO dedicated regression test asserting a packed/notes/rename edit leaves assignments intact. Adjacent-only coverage: `test_drink_mix.py::test_updating_trip_days_does_not_recalc_drink_servings`. GAP: negative-case regression test. |
| Manual assignments must reference same-trip inventory, real day+slot, positive servings, cannot over-allocate | `test_trip_workflows.py::test_rest_rejects_assignment_source_not_on_trip`, `::test_rest_rejects_assignment_to_day_outside_trip`, `::test_rest_rejects_unknown_assignment_slot`, `::test_rest_rejects_nonpositive_assignment_servings`, `::test_rest_rejects_assignment_beyond_selected_inventory`, `::test_rest_rejects_assignment_update_beyond_selected_inventory`; MCP `test_mcp_tools.py::test_assignment_update_cannot_exceed_trip_inventory` | Covered. |
| Removing inventory or a trip cannot leave dependent assignments | `test_trip_workflows.py::test_rest_removing_meal_removes_its_daily_assignments`, `::test_rest_removing_snack_removes_its_daily_assignments`, `::test_rest_deleting_trip_cannot_leak_assignments_into_reused_id`; `test_runtime_config.py::test_database_cascades_trip_assignments`; `test_migrations.py::test_legacy_trip_rows_are_preserved_and_gain_cascades` | Covered. |
| Direct trip URLs and selected trip state remain synchronized | Frontend `App.test.jsx` "trip deep links" block: `a daily-plan URL makes its trip authoritative everywhere`, `switching trips preserves the daily-plan subroute`, `a planner URL loads and links to the same trip`, `packing deep links, trip switching, and back navigation keep trip identity`, `an unknown trip deep link shows a stable not-found boundary`, `an unknown subroute is reported without losing the trip URL`, `a late response from the previous trip cannot overwrite the current route`. Commits 05376b4, f8232f3 | Covered. |

### Security behaviors to add

| Spec bullet | Covered by | Notes |
| --- | --- | --- |
| Authorization accepts only persisted clients and exact registered redirects | `test_mcp_oauth.py::test_authorization_rejects_unknown_client`, `::test_registered_client_survives_restart_and_only_uses_exact_redirect`, `::test_registration_rejects_insecure_non_loopback_redirect` | Covered (S1). |
| Authorization codes remain one-time and PKCE-bound | PKCE binding exercised end-to-end in `test_mcp_oauth.py::test_oauth_metadata_registration_code_and_refresh_flow` (S256 challenge/verifier required to redeem the code) and advertised via `::test_discovery_drops_oidc_and_jwks_and_advertises_only_supported` (`code_challenge_methods_supported == ["S256"]`). One-time enforced in `mcp_oauth/tokens.py::consume_auth_code` (`DELETE FROM auth_codes` on redeem) | Partially covered. Happy-path PKCE binding is exercised and one-time redemption is implemented by consume-on-use. GAP: no dedicated negative regression test for auth-code replay or PKCE-verifier mismatch (the only replay test at `test_oauth_metadata...:178` targets refresh tokens, not auth codes). |
| Refresh tokens rotate, old refresh tokens stop working, only hashes persisted | `test_mcp_oauth.py::test_oauth_metadata_registration_code_and_refresh_flow` (asserts `rotated_refresh != refresh` and old refresh replay → 400 `invalid_grant`); `::test_refresh_token_bearer_secret_is_never_persisted`; `::test_existing_refresh_token_survives_plaintext_storage_upgrade` | Covered (S1). |
| Repeated failed password attempts are throttled | `test_mcp_oauth.py::test_password_failures_are_throttled_per_address`, `::test_successful_authorization_resets_failure_counter` | Covered (S1). |
| Browser API responses do not grant arbitrary cross-origin access | `test_runtime_config.py::test_api_responses_carry_no_cors_allow_origin_header` | Covered (S1). CORS middleware removed; SPA served same-origin. |

### Operational behaviors to add

| Spec bullet | Covered by | Notes |
| --- | --- | --- |
| Tests never create or migrate the real application or OAuth database | `test_runtime_config.py::test_importing_main_creates_no_auth_database`, `::test_application_lifespan_uses_injected_engine`; OAuth `TokenStore` schema creation is lazy (S1 handoff) | Covered (S1). |
| Same configured database selected regardless of process working directory | `test_runtime_config.py::test_default_database_path_is_independent_of_working_directory`, `::test_default_auth_db_path_is_independent_of_working_directory` | Covered (S1). Default paths anchored to module files. |
| Every supported schema version upgrades to current schema and preserves user data | `test_migrations.py::test_migrations_record_current_version_and_are_idempotent`, `::test_legacy_trip_rows_are_preserved_and_gain_cascades` | Covered. |
| Production schema verification is a post-deploy check, not a skippable unit-test dependency on live BeeBaby SSH | `backend/verify_database.py::collect_database_errors`, invoked by `deploy/remote-bootstrap.sh` post-deploy; verifier logic unit-tested against temp DBs in `test_migrations.py::test_database_verifier_accepts_current_migrated_schema`, `::test_database_verifier_rejects_unversioned_schema` (no live SSH) | Covered. |

### Summary of gaps (nothing blocking this step)

1. Correctness — negative invalidation case: no dedicated test asserts that a
   display-only or packing-only edit (packed toggle, notes/trip_notes, bare
   rename) leaves daily assignments intact. Behavior is implemented via the
   guarded `_clear_assignments` conditional in `services/trip_planning.py`.
2. Security — auth-code one-time / PKCE-mismatch negatives: PKCE binding is
   exercised on the happy path and one-time redemption is implemented
   (`consume_auth_code` deletes on use), but there is no dedicated regression
   test for auth-code replay or a wrong PKCE verifier.

Both gaps are pre-existing (owned by the S1 OAuth and the trip-workflow slices),
not regressions from this step, and neither is required by this step's plan.
They are recorded here as the explicit uncovered flags the audit requires.
