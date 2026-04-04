# Macro Research Agent

## Problem

The macronutrient tracking infrastructure is fully built (ingredient fields, recipe rollups, trip summary, daily plan breakdowns) but every ingredient has null macro data. Populating ~100 ingredients manually via UI is tedious. The USDA FoodData Central API is free and covers most raw hiking food ingredients, but an automated workflow is needed to look up, convert, and write the data.

## Solution

A standalone Claude Code agent (`.claude/agents/research-macros.md`) that:
1. Scans the ingredient database for items missing macro data
2. Researches each via the USDA FoodData Central API, falling back to LLM estimation when USDA doesn't have a good match
3. Presents a review table to the user for approval/corrections
4. Writes approved values via the ingredient PUT endpoint

The agent is re-runnable — it always scans for null-macro ingredients, so it handles both initial bulk population and future additions.

## Data Flow

1. Agent calls `GET /api/ingredients`, filters to items where all three macro fields are null
2. For each ingredient, agent calls USDA search endpoint (`/fdc/v1/foods/search`) with the ingredient name
3. Agent extracts protein, fat, carb per 100g from the best USDA match, converts to per-oz (multiply by 0.283495)
4. If no good USDA match, agent estimates from its own knowledge and flags as "estimated"
5. Agent presents a markdown table with all values, sources, and confidence notes
6. User reviews, approves or corrects values
7. Agent calls `PUT /api/ingredients/:id` with `protein_per_oz`, `fat_per_oz`, `carb_per_oz` for each approved item
8. Backend calorie derivation fires automatically (p*4 + f*9 + c*4 replaces existing `calories_per_oz`)
9. Recipe, snack, trip, and daily plan macro rollups compute from updated ingredient data — no further action needed

## Behavior

- Only targets ingredients with all three macro fields null — never overwrites existing data unless user explicitly asks
- Rounds macro values to 1 decimal place
- USDA match preference: exact name > most common food form > generic over branded > "Survey (FNDDS)" or "SR Legacy" data types over branded products
- For ambiguous ingredients (e.g. "Cereal (granola or grape nuts)"), picks the most representative match and explains the choice
- For items with no reasonable USDA match (brand-specific, unusual), falls back to LLM estimation and flags the source
- Tracks data source per ingredient: "USDA" with fdcId and description, or "estimated" with reasoning
- Calorie derivation is automatic — when all three macros are set, `calories_per_oz` is recomputed by the backend. This means existing calorie values will change slightly for ingredients that get macros. The review table should show both the current `calories_per_oz` and the macro-derived value so the user can spot unexpected changes.
- USDA API uses `DEMO_KEY` by default (rate-limited to 30 req/hour, 50/day). For bulk runs, user can provide their own key (free registration at https://api.data.gov/signup/).
