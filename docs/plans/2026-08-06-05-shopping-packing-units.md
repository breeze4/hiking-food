# Shopping List + Packing Screen for Snack Units

## Parent spec

[Structured Snack Units](../specs/2026-08-06-01-structured-snack-units.md)

## What to build

Structured trips' unit selections surface on the shopping list and packing screen (spec: Data Flow — shopping/packing; user stories 13–14). Shopping: bag selections expand into bulk-ingredient ounces (6 trail-mix bags = 6 oz nuts + 6 oz M&Ms) and merge with ingredient lines from meals/lunch; packaged selections aggregate as catalog-item quantities. Packing: unit selections group by unit type with counts and target weight — "make 6 × trail mix bag @ 2.0 oz" — alongside the existing meal/snack sections, with packed checkoff and actual weights flowing through the existing packed fields. Legacy trips' shopping and packing output are unchanged.

## Goal

For a structured trip, the shopping list tells the user exactly how many ounces of each bulk ingredient to buy and the packing screen reads as a bag-assembly checklist with counts and target weights — with legacy trips' outputs untouched.

## Type

AFK

## Blocked by

- Blocked by `2026-08-06-03-trip-unit-selections.md`

## User stories addressed

- User story 13 (shopping expansion)
- User story 14 (packing assembly view)
- User story 17 (packed/actual weight on units, packing side)

## Acceptance criteria

- [x] `venv/bin/pytest` passes with new tests: 6 × (1 oz nuts + 1 oz M&Ms) bag yields 6 oz of each ingredient on the shopping list, merged with ounces of the same ingredient from other sources; packaged units aggregate by catalog item; a legacy trip's `shopping_view` and `packing_view` outputs are unchanged (snapshot assertions).
- [x] `packing_view` for a structured trip includes a units section grouped by unit type: count, per-unit target weight, per-unit derived weight, packed state, actual weights.
- [x] Packing screen shows "make N × <type> @ <target> oz" rows with packed checkoff and actual-weight entry wired to the existing trip-unit update endpoint; `pnpm lint && pnpm build && pnpm test` pass.
- [x] Ingredient `on_hand` / `essentials` / `packing_method` behavior on the shopping list applies to expanded bag ingredients the same as to recipe ingredients.

## Owns

- `backend/services/trip_queries.py` — `shopping_view`, `packing_view` only
- `backend/tests/test_shopping_list.py`, `backend/tests/test_packing.py` — added cases
- `frontend/src/pages/PackingScreen.jsx` + `PackingScreen.test.jsx` — units section

## Must not touch

- `trip_summary_view`, `trip_detail_view`, `trip_snack_view` in `backend/services/trip_queries.py` — owned by plan `2026-08-06-03`
- `backend/services/snack_units.py`, `backend/routers/trips.py`, `backend/services/trip_planning.py` — owned by plan `2026-08-06-03`
- `backend/services/catalog_queries.py`, `backend/routers/snack_units.py` — owned by plan `2026-08-06-02`
- `backend/services/autofill.py`, `backend/services/daily_plan_queries.py` — owned by plan `2026-08-06-04`
- `backend/mcp_server.py` — owned by plan `2026-08-06-06`
- `backend/models.py`, `backend/migrations.py` — schema frozen

## Defines interfaces

None — consumes `snack_unit_type_view` (plan 02), selection views (plan 03), and the existing shopping/packing response shapes.

## Pattern exemplar

- **MUST follow the pattern in**: `backend/services/trip_queries.py` — the existing `shopping_view` ingredient-aggregation loop (extend its merge keying; bag expansion contributes ingredient ounces exactly like recipe ingredients do)
- Follow the pattern in: `frontend/src/pages/PackingScreen.jsx` — existing snack packing section for the units section; `backend/tests/test_shopping_list.py` for fixtures

## Tasks

- [x] Shopping expansion: for each bag selection, add quantity × amount_oz per composition ingredient into the aggregation; packaged selections keep the current catalog-item path.
- [x] Packing units section: group selections by unit type / catalog item, expose count, target weight (`oz_per_snack`), derived weight, packed, actual weights.
- [x] Legacy snapshot tests + new-case tests per criteria.
- [x] Packing screen units section + component test cases (checkoff and actual-weight entry reuse the plan-03 selection update endpoint — no new backend mutation).
