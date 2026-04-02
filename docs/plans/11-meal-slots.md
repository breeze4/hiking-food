# Meal Slots on Trip Snacks

## Parent PRD

`docs/specs/03-prd-meal-slots-and-planning-agent.md` — User stories 3-5, 7

## What to build

Add a `slot` column to `trip_snacks` with values: `morning_snack`, `lunch`, `afternoon_snack`. When a snack is added to a trip, default the slot based on the snack's category (e.g. bars_energy → morning_snack, lunch → lunch, sweet → afternoon_snack). Group snacks by slot in the trip planner UI instead of showing one flat list.

## Type

AFK

## Blocked by

- Blocked by `10-snack-categories.md` (category drives default slot assignment)

## User stories addressed

- As a user, I can assign snacks to time-of-day slots (morning snack, lunch, afternoon snack)
- As a user, I can see my snacks organized by slot in the trip planner
- As a user, I can drag/reassign a snack to a different slot

## Acceptance criteria

- [x] `trip_snacks` table has a `slot` TEXT column with values: morning_snack, lunch, afternoon_snack
- [x] Adding a snack to a trip auto-assigns a default slot based on category
- [x] `GET /api/trips/:id` response includes `slot` on each snack
- [x] `PUT /api/trips/:id/snacks/:id` accepts `slot` field for reassignment
- [x] Trip planner groups snacks by slot with section headers
- [x] Each slot section has its own add-snack button
- [x] Summary endpoint returns per-slot weight/calorie subtotals

## Tasks

- [x] Add `slot` column to `TripSnack` model (TEXT, nullable initially)
- [x] Write migration to populate slot for existing trip_snacks based on catalog category
- [x] Define category-to-slot default mapping (drink_mix→morning_snack, lunch→lunch, salty→afternoon_snack, sweet→afternoon_snack, bars_energy→morning_snack)
- [x] Update `POST /api/trips/:id/snacks` to auto-assign slot from category, allow override
- [x] Update `PUT /api/trips/:id/snacks/:id` to accept slot changes
- [x] Update `GET /api/trips/:id` to include slot on snack objects
- [x] Update summary endpoint to return per-slot subtotals (weight, calories per slot)
- [x] Refactor SnackSelection component: render three slot sections instead of one flat table
- [x] Each slot section gets its own add-snack panel, filtered to relevant categories by default
- [x] Allow changing a snack's slot via dropdown (drag deferred)
