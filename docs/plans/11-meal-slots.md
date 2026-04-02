# Meal Slots on Trip Snacks

## Parent PRD

`docs/prd-meal-slots-and-planning-agent.md` — User stories 3-5, 7

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

- [ ] `trip_snacks` table has a `slot` TEXT column with values: morning_snack, lunch, afternoon_snack
- [ ] Adding a snack to a trip auto-assigns a default slot based on category
- [ ] `GET /api/trips/:id` response includes `slot` on each snack
- [ ] `PUT /api/trips/:id/snacks/:id` accepts `slot` field for reassignment
- [ ] Trip planner groups snacks by slot with section headers
- [ ] Each slot section has its own add-snack button
- [ ] Summary endpoint returns per-slot weight/calorie subtotals

## Tasks

- [ ] Add `slot` column to `TripSnack` model (TEXT, nullable initially)
- [ ] Write migration to populate slot for existing trip_snacks based on catalog category
- [ ] Define category-to-slot default mapping (drink_mix→morning_snack, lunch→lunch, salty→afternoon_snack, sweet→afternoon_snack, bars_energy→morning_snack)
- [ ] Update `POST /api/trips/:id/snacks` to auto-assign slot from category, allow override
- [ ] Update `PUT /api/trips/:id/snacks/:id` to accept slot changes
- [ ] Update `GET /api/trips/:id` to include slot on snack objects
- [ ] Update summary endpoint to return per-slot subtotals (weight, calories per slot)
- [ ] Refactor SnackSelection component: render three slot sections instead of one flat table
- [ ] Each slot section gets its own add-snack panel, filtered to relevant categories by default
- [ ] Allow changing a snack's slot via dropdown or drag
