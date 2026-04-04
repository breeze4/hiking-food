# Recipe Macro Totals

## Parent spec

`docs/specs/10-macronutrient-tracking.md`

## What to build

Roll up ingredient-level macros into recipe totals. `compute_recipe_totals()` returns total protein, fat, and carb grams alongside existing weight and calorie totals. Recipe API responses include macro totals. Recipe edit page displays macro totals next to the existing weight/calorie summary.

## Type

AFK

## Blocked by

- Blocked by `27-ingredient-macro-fields.md`

## User stories addressed

- User story 2: See macro grams roll up on each recipe
- User story 14: Meal selection views show macro info

## Acceptance criteria

- [ ] `compute_recipe_totals()` returns `protein_g`, `fat_g`, `carb_g` (sum of each ingredient's macro_per_oz * amount_oz)
- [ ] Ingredients with null macros contribute 0 to macro totals (but still contribute calories)
- [ ] Recipe detail API response includes `protein_g`, `fat_g`, `carb_g`
- [ ] Recipe edit page shows macro totals alongside weight/calorie totals
- [ ] Recipe list/browse shows macro totals per recipe
- [ ] Tests verify macro rollup with full data, partial data (some ingredients missing macros), and no macro data

## Pattern exemplar

- Follow the pattern in: `backend/services/recipe_calc.py` — extend `compute_recipe_totals()` with same structure
- Follow the pattern in: `frontend/src/pages/RecipeEditPage.jsx` — where weight/calorie totals are displayed via useMemo

## Tasks

- [ ] Extend `compute_recipe_totals()` to sum protein, fat, carb grams from ingredients
- [ ] Update recipe-related Pydantic schemas to include macro fields
- [ ] Update recipe API responses to include macro totals
- [ ] Update RecipeEditPage to display macro totals
- [ ] Write tests for recipe macro rollup (full, partial, and no macro data)
