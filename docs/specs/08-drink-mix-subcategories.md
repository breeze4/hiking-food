# 08 — Drink Mix Subcategories

## Problem Statement

The daily meal plan screen (spec 09) needs to distribute drink mixes differently based on time of day. Coffee and carnation instant breakfast are morning drinks, tea is an evening drink, electrolytes go all day. Currently drink mixes have no subcategory — they're all just `category = drink_mix` on the snack catalog.

## Solution

Add a `drink_mix_type` field to the snack catalog that classifies drink mixes as breakfast, dinner, or all-day. This drives distribution logic in the daily meal plan auto-fill algorithm.

## User Stories

1. As a trip planner, I want drink mixes categorized by time of day, so that the daily planner distributes coffee to mornings and tea to evenings.
2. As a trip planner, I want to set the drink mix type when editing catalog items, so that new drink mixes are correctly classified.

## Implementation Decisions

- New column on `snack_catalog`: `drink_mix_type` — TEXT, nullable. Values: `breakfast`, `dinner`, `all_day`. Only relevant when `category = drink_mix`; null for non-drink-mix items.
- Distribution rules used by the daily planner (spec 09):
  - `breakfast` drink mixes: assigned to full days and last partial day (same as breakfast meals). Includes coffee, carnation instant breakfast, athletic greens.
  - `dinner` drink mixes: assigned to first partial day and full days (same as dinner meals). Includes tea.
  - `all_day` drink mixes: assigned to all days. Includes electrolytes.
- UI: when editing a drink mix catalog item, show a selector for drink_mix_type. Hidden for non-drink-mix categories.
- Existing drink mix items need a migration to set their drink_mix_type based on current data.

## Testing Decisions

- No dedicated test suite for this spec. The drink_mix_type field is exercised heavily by the daily planner auto-fill tests (spec 09).

## Out of Scope

- Changing how drink mixes are displayed on the trip planner snack selection screen (they stay grouped together).
- Changing the drink_mixes_per_day budget system.
