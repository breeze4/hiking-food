# Ingredient Macro Fields + Calorie Derivation

## Parent spec

`docs/specs/10-macronutrient-tracking.md`

## What to build

Add protein, fat, and carb fields (grams per oz) to the ingredient model. When all three macros are set, calories_per_oz is derived (p*4 + f*9 + c*4). When calories_per_oz is set directly, macros are nulled. The ingredient API accepts and returns the new fields, and the ingredients table UI gets three new inline-editable columns. Ingredients missing macro data should be visually distinguishable.

## Type

AFK

## Blocked by

None - can start immediately

## User stories addressed

- User story 1: See protein/fat/carb grams per oz on each ingredient
- User story 8: Calories automatically derived from macros
- User story 9: Enter calories directly without macros for simple items
- User story 10: Edit macro fields inline on ingredients table
- User story 11: External agent can populate macro data via API
- User story 12: See which ingredients are missing macro data

## Acceptance criteria

- [ ] Ingredient table has `protein_per_oz`, `fat_per_oz`, `carb_per_oz` columns (nullable REAL)
- [ ] PUT/POST ingredient with all three macros set → `calories_per_oz` is computed as `p*4 + f*9 + c*4`
- [ ] PUT/POST ingredient with `calories_per_oz` set and no macros → macros are null, calories stored directly
- [ ] PUT/POST ingredient with all three macros AND calories_per_oz → macros win, calories derived
- [ ] GET ingredient returns all three macro fields (null when not set)
- [ ] Ingredients page shows protein, fat, carb columns with inline editing
- [ ] Ingredients missing macro data are visually distinguishable (e.g., empty cells, muted text)
- [ ] Migration adds columns without losing existing data
- [ ] Tests cover derivation rules: macros→calories, direct calories, and the transition between them

## Pattern exemplar

- Follow the pattern in: `backend/routers/ingredients.py` — same CRUD endpoint shape, same Pydantic schema pattern in `schemas.py`
- Follow the pattern in: `frontend/src/pages/IngredientsPage.jsx` — same inline editing pattern for new columns
- Follow the pattern in: `backend/migrations/` — most recent migration script for column addition format

## Tasks

- [ ] Add migration script to add `protein_per_oz`, `fat_per_oz`, `carb_per_oz` to ingredients table
- [ ] Update `models.py` with new columns, update `schemas.py` with new fields
- [ ] Add calorie derivation logic to ingredient create/update endpoints
- [ ] Update ingredients router to accept and return macro fields
- [ ] Add protein, fat, carb columns to IngredientsPage with inline editing
- [ ] Add visual indicator for ingredients missing macro data
- [ ] Write tests for calorie derivation rules (macros→calories, direct calories, transitions)
