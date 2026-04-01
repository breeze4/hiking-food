# Issue #6: Seed Data — Skurka Recipes + Utah 2026 Snack Selections

## Context
The app needs pre-loaded data to be useful from day one. The user is migrating from a Google Sheet for the Utah 2026 trip, so the seed script must reproduce that sheet's snack catalog and serving selections exactly. The 12 Skurka recipes (already extracted to `data/skurka-recipes.json`) provide the recipe library starting point. All ingredients from both sources feed into the shared ingredient table.

This is a backend-only change. No UI work. The seed script must be idempotent — running it twice produces the same database state with no duplicates.

## Prerequisites
- Issues #3 (ingredients), #4 (snack catalog), #5 (recipe library) are complete — all CRUD endpoints and DB models exist
- `data/skurka-recipes.json` exists with all 12 recipes, ingredients, and amounts
- **Utah 2026 snack data must be extracted** to `data/utah-2026-snacks.json` (or similar) before implementation. The PRD says this was "captured as CSV and analyzed" but no file exists in the repo yet. This data needs: ingredient name, calories_per_oz, weight_per_serving, calories_per_serving, servings for the trip. Without this file, only the Skurka recipe seeding can proceed.

## Verification Targets (from issue acceptance criteria)
- Quickstart Cereal: 4.5 oz, ~617 cal, ~137 cal/oz
- Cheesy Potatoes: 4.5 oz, ~537 cal, ~119 cal/oz
- Utah 2026 snacks: ~103 oz total weight, ~11,745 total calories, ~114 cal/oz average
- Idempotent: second run produces no duplicates, no errors

## Plan

### Step 1: Extract and commit Utah 2026 snack data to JSON
The Google Sheet data needs to land in `data/utah-2026-snacks.json` as a structured file that the seed script can consume. The file should contain an array of snack items, each with: ingredient name, calories_per_oz, weight_per_serving, calories_per_serving, and servings (the trip-level serving count). Also include the trip metadata (name, day fractions if known).

Manually create this file from the spreadsheet data. Include a top-level verification block with the known totals (~103 oz, ~11,745 cal, ~114 cal/oz) so the seed script can sanity-check itself.

**Files**: `data/utah-2026-snacks.json`
**Verify**: JSON is valid. Manually confirm the totals from the items match the verification targets.

### Step 2: Create seed script skeleton with DB session and idempotency pattern
Create `backend/seed.py` that:
- Imports the SQLAlchemy models and database session
- Establishes the idempotency pattern: look up by unique natural key (name for ingredients/recipes, ingredient_id for snack catalog items) before inserting
- Defines helper functions: `get_or_create_ingredient(session, name, cal_per_oz, notes)` and similar for other entities
- Runs as `python -m seed` from the backend directory (or `python backend/seed.py` from project root)
- On completion, prints a summary of what was created vs. already existed

**Files**: `backend/seed.py`
**Verify**: Script runs without error against an empty database, prints summary. Run again — prints "already exists" for everything, no duplicates in DB.

### Step 3: Seed all ingredients from Skurka recipes
Load `data/skurka-recipes.json`, collect all unique ingredients across all 12 recipes (dedup by name), and insert them using the get-or-create pattern. Each ingredient gets its name, calories_per_oz, and notes from the JSON.

Deduplication note: the same ingredient appears in multiple recipes (e.g., "Butter", "Salt", "Rolled oats"). The JSON has the same name string for shared ingredients, so dedup by exact name match. Some ingredients have different calories_per_oz in different recipe contexts (e.g., "Green chiles" is 23 cal/oz in Cheesy Potatoes but 9 cal/oz in Southwest Egg Burrito) — use the first occurrence or the most common value and note the discrepancy in a comment.

**Files**: `backend/seed.py`
**Verify**: Run script. Query ingredients table — all unique Skurka ingredients present with correct cal/oz values. Count matches expected unique ingredient count from JSON.

### Step 4: Seed all 12 Skurka recipes with ingredient lists
For each recipe in the JSON:
- Get or create the recipe record (name, category, at_home_prep, field_prep, notes)
- For each ingredient in the recipe, look up the ingredient by name, then create the recipe_ingredient join record (recipe_id, ingredient_id, amount_oz)
- Idempotency for recipe_ingredients: if recipe already exists, skip its ingredients (don't re-add them). Check by recipe name existence.

**Files**: `backend/seed.py`
**Verify**: Run script. Hit `GET /api/recipes` — all 12 recipes listed with correct categories (6 breakfast, 6 dinner). Hit `GET /api/recipes/{id}` for Quickstart Cereal — confirm 4.5 oz total, ~617 cal, ~137 cal/oz. Same check for Cheesy Potatoes (4.5 oz, ~537 cal, ~119 cal/oz). Run script again — no duplicates.

### Step 5: Seed Utah 2026 ingredients and snack catalog items
Load `data/utah-2026-snacks.json`. For each snack item:
- Get or create the ingredient (name, calories_per_oz) — some may already exist from Skurka recipes
- Get or create the snack catalog item (ingredient_id, weight_per_serving, calories_per_serving)

Snack catalog idempotency: look up by ingredient_id. One snack catalog entry per ingredient.

**Files**: `backend/seed.py`
**Verify**: Run script. Hit `GET /api/snacks` — all Utah 2026 snack items present. Ingredient table now contains union of Skurka + Utah 2026 ingredients.

### Step 6: Seed Utah 2026 trip with snack serving selections
Create the Utah 2026 trip record and attach snack selections:
- Create trip: name="Utah 2026", set day fractions if known from spreadsheet
- For each snack item with servings > 0, create a trip_snack record (trip_id, catalog_item_id, servings)

**Files**: `backend/seed.py`
**Verify**: Query trip_snacks for Utah 2026 trip. Compute totals: sum(servings * weight_per_serving) should be ~103 oz, sum(servings * calories_per_serving) should be ~11,745 cal. Print these totals at end of seed script as a sanity check.

### Step 7: Add verification assertions to seed script
At the end of the seed script, add optional verification that:
- Recipe count = 12 (6 breakfast, 6 dinner)
- Quickstart Cereal totals match (4.5 oz, ~617 cal)
- Cheesy Potatoes totals match (4.5 oz, ~537 cal)
- Utah 2026 snack totals are within tolerance of targets (~103 oz, ~11,745 cal, ~114 cal/oz)

Print PASS/FAIL for each check. These serve as a built-in smoke test.

**Files**: `backend/seed.py`
**Verify**: Run script on fresh DB — all checks PASS. Run again — all checks still PASS, no duplicates.

## Files Summary

| Action | Path |
|--------|------|
| Create | `data/utah-2026-snacks.json` |
| Create | `backend/seed.py` |

## Key Design Decisions
- **Idempotency via natural keys**: Ingredients dedup by name, recipes by name, snack catalog items by ingredient_id, trip by name. No synthetic "seed ID" tracking needed.
- **JSON data files as source of truth**: The seed script reads from `data/*.json` files rather than hardcoding values. This keeps data separate from logic and makes it easy to update.
- **Ingredient dedup across sources**: Skurka recipes and Utah 2026 snacks share some ingredients. The get-or-create pattern handles this naturally.
- **Calorie discrepancies**: Some ingredients appear with different cal/oz values in different Skurka recipes (e.g., Green chiles: 23 vs 9 cal/oz). The seed script should pick one value and log the discrepancy. The user can adjust later via the ingredient UI.

## Verification
1. Fresh DB: `python backend/seed.py` completes without errors
2. `GET /api/recipes` returns 12 recipes (6 breakfast, 6 dinner)
3. Quickstart Cereal detail: 3 ingredients, 4.5 oz, ~617 cal, ~137 cal/oz
4. Cheesy Potatoes detail: 7 ingredients, 4.5 oz, ~537 cal, ~119 cal/oz
5. `GET /api/snacks` returns all Utah 2026 snack catalog items
6. Utah 2026 trip exists with correct snack serving counts
7. Computed snack totals: ~103 oz, ~11,745 cal, ~114 cal/oz
8. Second run of seed script: no errors, no duplicate rows, same totals
9. All existing CRUD endpoints still work (no schema breakage)
