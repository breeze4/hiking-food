# Drink Mix Subcategories

## Parent spec

[docs/specs/08-drink-mix-subcategories.md](../specs/08-drink-mix-subcategories.md)

## What to build

Add a drink_mix_type field to the snack catalog that classifies drink mixes as breakfast, dinner, or all_day. This enables time-of-day-aware distribution in the daily meal plan (plan 24). Includes a data migration to classify existing drink mix items and a UI selector when editing drink mix catalog entries.

## Type

AFK

## Blocked by

None — can start immediately

## User stories addressed

- User story 1 — drink mixes categorized by time of day
- User story 2 — set drink_mix_type when editing catalog items

## Acceptance criteria

- [x] New drink_mix_type column on snack_catalog (TEXT, nullable; values: breakfast, dinner, all_day)
- [x] Existing drink mix items migrated to correct drink_mix_type values
- [x] Snack catalog API returns and accepts drink_mix_type
- [x] Snack catalog edit UI shows drink_mix_type selector when category is drink_mix
- [x] Selector hidden for non-drink-mix categories

## Tasks

- [x] Add drink_mix_type column to snack_catalog table (migration)
- [x] Write data migration to classify existing drink mixes (coffee/carnation/greens → breakfast, tea → dinner, electrolytes → all_day)
- [x] Update snack catalog CRUD endpoints to handle drink_mix_type
- [x] Update snack catalog edit UI: conditional drink_mix_type selector for drink_mix items
- [x] Verify existing snack catalog functionality is unaffected for non-drink-mix items
