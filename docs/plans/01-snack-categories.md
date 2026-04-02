# Snack Categories

## Parent PRD

`docs/prd-meal-slots-and-planning-agent.md` — User stories 1-2

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

- [ ] `snack_catalog` table has a `category` TEXT column with allowed values: drink_mix, lunch, salty, sweet, bars_energy
- [ ] All existing catalog items are migrated to the correct category
- [ ] `GET /api/snacks` response includes `category` field
- [ ] `POST /api/snacks` and `PUT /api/snacks/:id` accept `category` field
- [ ] Snack Catalog page shows category for each item, allows editing
- [ ] Add-snack search panel in trip planner shows category and can filter by it
- [ ] Seed script assigns categories to all seeded items

## Tasks

- [ ] Add `category` column to `SnackCatalogItem` model (TEXT, nullable initially for migration)
- [ ] Write migration to add column and populate existing items with correct categories
- [ ] Update seed script to assign categories to all seeded snack items
- [ ] Update snack API schemas to include `category` in request/response
- [ ] Update `GET /api/snacks` to support optional `?category=` query filter
- [ ] Update Snack Catalog page: show category column, editable via dropdown in edit mode
- [ ] Update add-snack search panel in SnackSelection: show category badge, add filter tabs/buttons
- [ ] Run seed script on existing DB to populate categories
