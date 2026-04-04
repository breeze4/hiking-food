# Snack Catalog Macro Per-Serving

## Parent spec

`docs/specs/10-macronutrient-tracking.md`

## What to build

Derive per-serving macro grams for snack catalog items from their linked ingredient's macros. Snack API responses include protein, fat, and carb per serving. Snack catalog page shows macro columns.

## Type

AFK

## Blocked by

- Blocked by `27-ingredient-macro-fields.md`

## User stories addressed

- User story 3: See macro grams on each snack catalog item per serving
- User story 14: Snack selection views show macro info

## Acceptance criteria

- [ ] Snack catalog API response includes `protein_per_serving`, `fat_per_serving`, `carb_per_serving`
- [ ] Values derived as `ingredient.macro_per_oz * weight_per_serving` (null if ingredient macros are null)
- [ ] Snack catalog page shows protein, fat, carb columns
- [ ] Trip snack responses (in trip detail) include macro per-serving values
- [ ] Tests verify derivation with full macro data, null macros, and zero weight_per_serving

## Pattern exemplar

- Follow the pattern in: `backend/routers/snacks.py` — same response-building pattern where ingredient data is joined
- Follow the pattern in: `frontend/src/pages/SnackCatalogPage.jsx` — same table column pattern

## Tasks

- [ ] Update snack API response building to compute and include macro per-serving
- [ ] Update trip snack response (`_build_trip_snack`) to include macro per-serving
- [ ] Update Pydantic schemas for snack responses
- [ ] Add macro columns to SnackCatalogPage
- [ ] Write tests for snack macro derivation
