# 07 — Shopping List Enhancements

## Problem Statement

The shopping list is currently a flat, read-only list of ingredient names and total ounces. There's no way to record what's already on hand, no way to mark pantry essentials that don't need purchasing, and no guidance on how each ingredient should be packed. The user wants to use the shopping list as a prep-session tool — checking stock, identifying what to buy, and knowing how to pack each item.

## Solution

Add three new fields to ingredients: on-hand status, essentials flag, and packing method. The shopping list sorts by purchase need, hides essentials by default, and shows packing method. Recipe assembly on the packing screen shows essentials so the user can verify they have their basics.

## User Stories

1. As a trip planner doing a prep session, I want to toggle ingredients as on-hand directly on the shopping list, so that I can track what I've already got without leaving the page.
2. As a trip planner, I want to mark staple ingredients (salt, pepper, oil) as essentials, so that they don't clutter the shopping list with things I always have.
3. As a trip planner, I want essentials shown in recipe assembly, so that I can verify I actually have the basics before packing day.
4. As a trip planner, I want the shopping list sorted by what I need to buy first, then what I have on hand, so that the list doubles as a stock check and purchase list.
5. As a trip planner, I want to see the packing method for each ingredient, so that I know how to handle it on packing day (weigh it out, count packets, bring the whole container, etc.).
6. As a trip planner, I want to set packing method and essentials flag on the ingredient database screen, so that these defaults apply across all trips.
7. As a trip planner, I want a visible section where I can review all essentials, so that I can double-check my assumptions about what I've always got.

## Implementation Decisions

- Three new columns on the `ingredients` table:
  - `on_hand` — BOOLEAN, default FALSE. Simple flag, no quantity tracking.
  - `essentials` — BOOLEAN, default FALSE. Essentials are assumed always available.
  - `packing_method` — TEXT, nullable. Enum values: `by_weight`, `by_count`, `single_serving`, `baggies`, `full_item`.
- Shopping list endpoint returns these fields and sorts results: need-to-buy (not on-hand, not essential) first, then on-hand, alphabetical within each group.
- Essentials are hidden from the main shopping list. A collapsed section at the bottom shows essentials for verification.
- The on-hand toggle is interactive directly on the shopping list — hits an endpoint to update the ingredient's on_hand flag.
- Recipe assembly view on the packing screen shows essentials ingredients used by the recipe, so the user can verify they have basics.
- Ingredient database screen gets UI for editing essentials and packing_method fields.
- Packing method is displayed on the packing screen next to each item to guide assembly.
- On-hand state persists across trips (it's on the ingredient, not the trip).

## Testing Decisions

- Backend tests for the shopping list endpoint: verify sort order (need-to-buy before on-hand), verify essentials filtering, verify packing_method is returned.
- Backend tests for the on_hand toggle endpoint.
- Existing test patterns in the backend test suite serve as prior art.

## Out of Scope

- Quantity tracking for on-hand ingredients (just a boolean).
- Per-trip packing method overrides (ingredient-level only).
- Auto-detection of essentials (user marks them manually).
