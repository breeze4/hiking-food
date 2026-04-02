# Drink Mix Daily Config

## Parent PRD

`docs/specs/03-prd-meal-slots-and-planning-agent.md` — User stories 10-12

## What to build

Add a `drink_mixes_per_day` integer field to the `trips` table (default 2). Show this as a configurable input alongside the trip calculator. Drink mix snacks (category=drink_mix) have their servings auto-calculated as `drink_mixes_per_day * total_days` and are displayed in their own section separate from the three snack slots.

## Type

AFK

## Blocked by

- Blocked by `11-meal-slots.md` (drink mixes need to be visually separated from slot-based snacks)

## User stories addressed

- As a user, I can set how many drink mixes I want per day and have servings auto-calculated
- As a user, I see drink mixes in their own section, not mixed in with snack slots

## Acceptance criteria

- [x] `trips` table has `drink_mixes_per_day` INTEGER column (default 2)
- [x] Trip calculator UI shows a "Drink mixes/day" input
- [x] Changing drink_mixes_per_day recalculates servings for all drink_mix snacks on the trip
- [x] Drink mix snacks shown in their own section in the trip planner, separate from slot sections
- [x] Summary includes drink mix weight/calories as a separate line item

## Tasks

- [x] Add `drink_mixes_per_day` column to Trip model (INTEGER, default 2)
- [x] Migration to add column with default value
- [x] Update `PUT /api/trips/:id` to accept `drink_mixes_per_day`
- [x] Update `GET /api/trips/:id` to return `drink_mixes_per_day`
- [x] Add logic: when drink_mixes_per_day changes, update servings for all drink_mix snacks on trip
- [x] Add drink mixes/day input to TripCalculator component
- [x] Render drink mix snacks in a separate "Drink Mixes" section in trip planner
- [x] Update summary endpoint to break out drink mix totals separately
