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

- [ ] Recipe ingredient table rows have `even:bg-muted/50` zebra striping
- [ ] Meal selection table rows have `even:bg-muted/50` zebra striping
- [ ] Navigation Sheet has proper left padding on text
- [ ] No horizontal overflow on any screen at mobile widths
- [ ] Consistent card/content padding across all screens
- [ ] Touch targets are adequately sized on mobile

## Tasks

- [ ] Add `even:bg-muted/50` to recipe ingredient table rows in `RecipeEditPage.jsx`
- [ ] Add `even:bg-muted/50` to meal selection table rows
- [ ] Fix navigation Sheet padding in `App.jsx` SheetContent
- [ ] Audit trip planner screen for mobile issues and fix
- [ ] Audit snack selection screen for mobile issues and fix
- [ ] Audit meal selection screen for mobile issues and fix
- [ ] Audit recipe library and recipe edit screens for mobile issues and fix
- [ ] Audit ingredient database screen for mobile issues and fix
- [ ] Audit packing screen and trip summary for mobile issues and fix
