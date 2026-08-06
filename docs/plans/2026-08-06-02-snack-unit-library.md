# Snack Unit Type Library

## Parent spec

[Structured Snack Units](../specs/2026-08-06-01-structured-snack-units.md)

## What to build

The reusable bag-composition library (spec: Modules — "Snack unit type library"). CRUD for unit types (name, notes) and their composition rows (ingredient + ounces), a derived-values query (weight = sum of composition oz; calories/macros from per-oz ingredient data), delete protection while any trip references the type, and a library UI where the user builds bags and sees derived weight/calories with a tolerance badge when weight is outside ±25% of the 2 oz default. This module owns all composition math — every consumer reads derived values through its views.

## Goal

The user can define "trail mix bag = 1 oz nuts + 1 oz M&Ms" once in a library UI, see its true weight/calories/macros and a drift warning, and trust that no other part of the app recomputes that math.

## Type

AFK

## Blocked by

- Blocked by `2026-08-06-01-trip-snack-mode-schema.md` (tables + models)

## User stories addressed

- User story 3 (reusable bag compositions)
- User story 9 (tolerance warning, library side)

## Acceptance criteria

- [ ] `venv/bin/pytest` passes with a new backend test module covering: CRUD round-trip; derived weight equals sum of composition oz; derived calories equal Σ(amount_oz × ingredient calories_per_oz); macros likewise; `weight_warning` true at 1.4 oz and 2.6 oz, false at 1.5–2.5 oz.
- [ ] DELETE on a unit type referenced by any `trip_snack_units` row returns 409 with a clear message; unreferenced types delete with 204.
- [ ] `GET /api/snack-unit-types` lists types with composition and derived values in one response.
- [ ] Library UI: create a bag with two ingredients, see derived weight/calories update, see the warning badge on an off-weight bag; `pnpm lint && pnpm build && pnpm test` pass with a component test for the builder.

## Owns

- `backend/routers/snack_units.py` — new router (CRUD for unit types + composition)
- `backend/main.py` — router registration line only
- `backend/schemas.py` — unit type schemas only
- `backend/services/catalog_queries.py` — new `snack_unit_type_view` / `snack_unit_type_list_view` (derived values)
- `backend/tests/test_snack_unit_library.py` — new
- `frontend/src/pages/SnackUnitLibraryPage.jsx` (+ test) — new page
- `frontend/src/api.js` — library API helpers
- `frontend/src/App.jsx` — nav/route entry for the library page

## Must not touch

- `backend/models.py`, `backend/migrations.py` — owned by plan `2026-08-06-01` (schema is frozen for this slice)
- `backend/services/trip_queries.py`, `backend/routers/trips.py` — owned by plans `2026-08-06-01/03/05`
- `backend/services/autofill.py`, `backend/services/daily_plan_queries.py` — owned by plan `2026-08-06-04`
- `backend/mcp_server.py` — owned by plan `2026-08-06-06`
- `frontend/src/components/SnackSelection.jsx` — owned by plan `2026-08-06-03`

## Defines interfaces

- `snack_unit_type_view` (dict with `id`, `name`, `notes`, `composition[]`, `weight_oz`, `calories`, `protein_g/fat_g/carb_g`, `weight_warning`) in `backend/services/catalog_queries.py` — consumed by plans `2026-08-06-03`, `04`, `05`, `06`
- `/api/snack-unit-types` REST shape — consumed by plans `2026-08-06-03` (frontend), `06` (MCP)

## Pattern exemplar

- **MUST follow the pattern in**: `backend/routers/snacks.py` — router structure, `get_db`, response models, status codes
- Follow the pattern in: `backend/services/catalog_queries.py` — `recipe_ingredients` / `snack_view` for derived-value view functions; `frontend/src/pages/SnackCatalogPage.jsx` for the library page layout; `frontend/src/pages/RecipeEditPage.jsx` for composition editing (ingredient + amount rows)

## Tasks

- [ ] View functions in `catalog_queries.py` with all composition math (weight, calories, macros, `weight_warning` vs ±25% of 2 oz).
- [ ] Router: list/create/update/delete unit types, composition managed as nested payload on create/update (like recipe ingredients); 409 delete protection.
- [ ] Schemas + router registration.
- [ ] Backend tests per acceptance criteria.
- [ ] Library page: list with derived values + warning badge, bag builder (name, notes, ingredient rows with oz), delete with error surfacing; component test; nav entry.

## Implementation notes

The tolerance badge here uses the global default of 2 oz (`weight_warning`), because a library entry is trip-independent. Plan 03 re-evaluates the warning against the specific trip's `oz_per_snack` on the planner side. Ingredients missing per-oz calorie/macro data contribute 0 and the view sets a `has_full_data: false` flag — same posture as macro handling in `trip_summary_view`.
