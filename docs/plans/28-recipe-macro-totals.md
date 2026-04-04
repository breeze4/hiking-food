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

- [x] `compute_recipe_totals()` returns `protein_g`, `fat_g`, `carb_g` (sum of each ingredient's macro_per_oz * amount_oz)
- [x] Ingredients with null macros contribute 0 to macro totals (but still contribute calories)
- [x] Recipe detail API response includes `protein_g`, `fat_g`, `carb_g`
- [x] Recipe edit page shows macro totals alongside weight/calorie totals
- [x] Recipe list/browse shows macro totals per recipe
- [x] Tests verify macro rollup with full data, partial data (some ingredients missing macros), and no macro data

## Pattern exemplar

- Follow the pattern in: `backend/services/recipe_calc.py` — extend `compute_recipe_totals()` with same structure
- Follow the pattern in: `frontend/src/pages/RecipeEditPage.jsx` — where weight/calorie totals are displayed via useMemo

## Tasks

- [x] Extend `compute_recipe_totals()` to sum protein, fat, carb grams from ingredients
- [x] Update recipe-related Pydantic schemas to include macro fields
- [x] Update recipe API responses to include macro totals
- [x] Update RecipeEditPage to display macro totals
- [x] Update RecipesPage to display macro totals in list view
- [x] Write tests for recipe macro rollup (full, partial, and no macro data)
