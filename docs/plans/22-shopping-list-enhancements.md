# Shopping List Enhancements

## Parent spec

[docs/specs/07-shopping-list-enhancements.md](../specs/07-shopping-list-enhancements.md)

## What to build

Add three new fields to ingredients (on_hand, essentials, packing_method) and use them to enhance the shopping list and packing screen. The shopping list becomes interactive: users can toggle on-hand status, essentials are hidden in a collapsed section, items sort by purchase need, and packing method is displayed. The ingredient database screen gets editing UI for essentials and packing_method. The packing screen shows essentials in recipe assembly.

## Type

AFK

## Blocked by

None — can start immediately

## User stories addressed

- User story 1 — toggle on-hand on shopping list
- User story 2 — mark ingredients as essentials
- User story 3 — essentials shown in recipe assembly
- User story 4 — shopping list sorted by purchase need
- User story 5 — packing method displayed
- User story 6 — edit essentials/packing_method on ingredient screen
- User story 7 — review essentials section

## Acceptance criteria

- [x] Three new columns on ingredients table: on_hand (bool), essentials (bool), packing_method (text enum)
- [x] Shopping list sorts: need-to-buy first, then on-hand, alphabetical within groups
- [x] Essentials hidden from main shopping list, shown in collapsed section at bottom
- [x] On-hand toggle works directly on shopping list (hits API, updates immediately)
- [x] Packing method displayed next to each item on shopping list and packing screen
- [x] Ingredient database screen has UI for editing essentials and packing_method
- [x] Packing screen recipe assembly shows essentials ingredients
- [x] Backend tests for shopping list sort order, essentials filtering, on_hand toggle endpoint

## Tasks

- [x] Add on_hand, essentials, packing_method columns to ingredients table (migration)
- [x] Update ingredient CRUD endpoints to handle new fields
- [x] Add PATCH endpoint for toggling on_hand status
- [x] Update shopping list endpoint: return new fields, sort by purchase need, separate essentials
- [x] Update ingredient database UI: add essentials toggle and packing_method selector
- [x] Update shopping list UI: on-hand toggle, sorted display, essentials section, packing method
- [x] Update packing screen: show essentials in recipe assembly, show packing method
- [x] Write backend tests for shopping list sorting, essentials filtering, on_hand toggle
