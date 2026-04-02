# Snack Categories

## Parent PRD

`docs/specs/03-prd-meal-slots-and-planning-agent.md` — User stories 1-2

## What to build

Add a `category` column to the `snack_catalog` table with five values: `drink_mix`, `lunch`, `salty`, `sweet`, `bars_energy`. Migrate all existing catalog items to their correct category. Expose category in the API responses and allow filtering by category. Show category in the snack catalog page and the trip planner's add-snack search panel.

## Type

AFK

## Blocked by

None - can start immediately

## User stories addressed

- As a user, I can see which category each snack belongs to (drink mix, lunch, salty, sweet, bars/energy)
- As a user, I can filter snacks by category when browsing the catalog or adding to a trip
- As the planning agent, I can read snack categories from the API to build balanced plans

## Acceptance criteria

- [x] `snack_catalog` table has a `category` TEXT column with allowed values: drink_mix, lunch, salty, sweet, bars_energy
- [x] All existing catalog items are migrated to the correct category
- [x] `GET /api/snacks` response includes `category` field
- [x] `POST /api/snacks` and `PUT /api/snacks/:id` accept `category` field
- [x] Snack Catalog page shows category for each item, allows editing
- [x] Add-snack search panel in trip planner shows category and can filter by it
- [x] Seed script assigns categories to all seeded items

## Tasks

- [x] Add `category` column to `SnackCatalogItem` model (TEXT, nullable initially for migration)
- [x] Write migration to add column and populate existing items with correct categories
- [x] Update seed script to assign categories to all seeded snack items
- [x] Update snack API schemas to include `category` in request/response
- [x] Update `GET /api/snacks` to support optional `?category=` query filter
- [x] Update Snack Catalog page: show category column, editable via dropdown in edit mode
- [x] Update add-snack search panel in SnackSelection: show category badge, add filter tabs/buttons
- [x] Run seed script on existing DB to populate categories
