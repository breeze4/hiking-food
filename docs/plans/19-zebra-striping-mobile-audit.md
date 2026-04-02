# Zebra Striping + Mobile Audit

## Parent spec

`docs/specs/04-utility-audit.md`

## What to build

Add zebra striping to recipe ingredient and meal selection tables to match existing snack tables. Fix mobile navigation padding and audit all screens for mobile usability issues (overflow, padding, touch targets, text truncation).

## Type

AFK

## Blocked by

None - can start immediately

## User stories addressed

- User story 14: Zebra-striped rows in recipe ingredient tables
- User story 15: Proper padding in navigation menu
- User story 16: Consistent mobile layout across all screens

## Acceptance criteria

- [x] Recipe ingredient table rows have `even:bg-muted/50` zebra striping
- [x] Meal selection table rows have `even:bg-muted/50` zebra striping
- [x] Navigation Sheet has proper left padding on text
- [x] No horizontal overflow on any screen at mobile widths
- [x] Consistent card/content padding across all screens
- [x] Touch targets are adequately sized on mobile

## Tasks

- [x] Add `even:bg-muted/50` to recipe ingredient table rows in `RecipeEditPage.jsx`
- [x] Add `even:bg-muted/50` to meal selection table rows
- [x] Fix navigation Sheet padding in `App.jsx` SheetContent
- [x] Audit trip planner screen for mobile issues and fix
- [x] Audit snack selection screen for mobile issues and fix
- [x] Audit meal selection screen for mobile issues and fix
- [x] Audit recipe library and recipe edit screens for mobile issues and fix
- [x] Audit ingredient database screen for mobile issues and fix
- [x] Audit packing screen and trip summary for mobile issues and fix
