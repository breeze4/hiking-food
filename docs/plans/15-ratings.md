# Snack & Meal Ratings

## Parent PRD

`docs/prd-meal-slots-and-planning-agent.md` — User stories 13-14

## What to build

Add a `rating` column to both `snack_catalog` and `recipes` tables. Ratings are integers 1-5 (null = unrated). Show ratings in the catalog/recipe list views with clickable stars or a simple selector. The planning agent reads ratings as the highest-weight preference signal, above catalog notes and conversation memory.

## Type

AFK

## Blocked by

None - can start immediately

## User stories addressed

- As a user, I can rate snacks and meals so the planning agent knows what I prefer
- As a user, I can see ratings at a glance when browsing the catalog or recipe list
- As the planning agent, I can read ratings to prioritize preferred items

## Acceptance criteria

- [ ] `snack_catalog` table has `rating` INTEGER column (nullable, 1-5)
- [ ] `recipes` table has `rating` INTEGER column (nullable, 1-5)
- [ ] API responses include `rating` field on snacks and recipes
- [ ] API accepts `rating` on create/update for both snacks and recipes
- [ ] Snack Catalog page shows ratings, allows setting via click
- [ ] Recipes page shows ratings, allows setting via click
- [ ] Recipe edit page has a rating control
- [ ] Add-snack search panel shows ratings

## Tasks

- [ ] Add `rating` column to SnackCatalogItem model (INTEGER, nullable)
- [ ] Add `rating` column to Recipe model (INTEGER, nullable)
- [ ] Migration to add both columns
- [ ] Update snack and recipe API schemas to include rating
- [ ] Update snack and recipe API endpoints to accept rating on create/update
- [ ] Add star rating component (reusable, 1-5 clickable)
- [ ] Show ratings in Snack Catalog page table
- [ ] Show ratings in Recipes page table
- [ ] Show ratings in add-snack search panel results
- [ ] Show rating control in Recipe edit page
- [ ] Update planning agent prompt to document rating as top-tier preference signal
