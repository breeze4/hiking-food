# Implementation Plans Index

## Completed

| # | Plan | Description |
|---|------|-------------|
| 01 | [Scaffolding](01-scaffolding.md) | Project scaffolding: FastAPI + React + Vite |
| 02 | [Ingredients](02-ingredients.md) | Ingredient database CRUD API + management UI |
| 03 | [Snack Catalog](03-snack-catalog.md) | Snack catalog CRUD API + management UI |
| 04 | [Recipe Library](04-recipe-library.md) | Recipe library CRUD API + browse/edit UI |
| 05 | [Seed Data](05-seed-data.md) | Skurka recipes + Utah 2026 snack selections |
| 06 | [Trip Planner](06-trip-planner.md) | Trip CRUD, calculator, snack/meal selection, summary |
| 07 | [Packing Screen](07-packing-screen.md) | Packing checklist with actual weights + shopping list |
| 08 | [Deployment](08-beebaby-deployment.md) | Deploy to beebaby via rsync + systemd |
| 09 | [Frontend Redesign](09-frontend-redesign-shadcn.md) | shadcn/ui + Tailwind CSS v4 redesign |
| 10 | [Snack Categories](10-snack-categories.md) | Add category column to snack catalog (5 types) |
| 11 | [Meal Slots](11-meal-slots.md) | Assign trip snacks to time-of-day slots |
| 12 | [Drink Mix Config](12-drink-mix-config.md) | Configurable drink mixes per day on trips |
| 13 | [Slot Calorie Meters](13-slot-calorie-meters.md) | Per-slot calorie meters + days covered in summary |
| 15 | [Ratings](15-ratings.md) | 1-5 ratings on snacks and recipes |
| 16 | [Slot Simplification](16-slot-simplification.md) | Collapse 3 snack slots to 2 (lunch + snacks) with 40/60 split |
| 14 | [Food Planning Agent](14-food-planning-agent.md) | CLI agent that plans trip food via API |
| 17 | [Drink Mix Manual Control](17-drink-mix-manual-control.md) | Manual drink mix servings with budget meter |
| 18 | [Progress Bar Meters](18-progress-bar-meters.md) | Replace badges with color-coded progress bars for cal/weight |
| 19 | [Zebra Striping + Mobile Audit](19-zebra-striping-mobile-audit.md) | Table striping + mobile layout fixes across all screens |
| 20 | [Per-Section Meters](20-per-section-meters.md) | Per-section meters + summary relayout |
| 21 | [Collapsible Category Grid](21-collapsible-category-grid.md) | Collapse 5-category grid by default in trip summary |
| 22 | [Shopping List Enhancements](22-shopping-list-enhancements.md) | On-hand toggle, essentials, packing method for ingredients |
| 23 | [Drink Mix Subcategories](23-drink-mix-subcategories.md) | Add drink_mix_type field (breakfast/dinner/all_day) to snack catalog |
| 24 | [Daily Plan — Auto-Fill](24-daily-plan-autofill.md) | Day assignments table, auto-fill algorithm, read-only UI |
| 25 | [Daily Plan — Manual Editing](25-daily-plan-manual-editing.md) | CRUD endpoints for assignments, unallocated pool, reset |
| 26 | [Daily Plan — Bar Chart & Layout](26-daily-plan-bar-chart.md) | Stacked bar chart, target lines, responsive day grid |
| 27 | [Ingredient Macro Fields](27-ingredient-macro-fields.md) | Macro columns on ingredients + calorie derivation |
| 28 | [Recipe Macro Totals](28-recipe-macro-totals.md) | Macro grams in recipe totals |
| 29 | [Snack Macro Per-Serving](29-snack-macro-per-serving.md) | Macro grams per serving on snack catalog |
| 30 | [Trip Summary Macros](30-trip-summary-macros.md) | Macro percentage breakdown in trip summary |
| 31 | [App Settings + Macro Targets](31-app-settings-macro-targets.md) | Global macro target percentages + actual vs target |
| 32 | [Daily Plan Macros](32-daily-plan-macros.md) | Per-day macro breakdown on daily plan |

## In Progress

| # | Plan | Description | Blocked by |
|---|------|-------------|------------|

## Not Started

| # | Plan | Description | Blocked by |
|---|------|-------------|------------|

## Specs

- [Macronutrient Tracking](../specs/10-macronutrient-tracking.md) — covers plans 27-32

## PRDs

- [Meal Slots, Snack Categories, and Food Planning Agent](../specs/03-prd-meal-slots-and-planning-agent.md) — covers plans 10-15
- [Utility Audit](../specs/04-utility-audit.md) — covers plans 16-19

## Design Sessions

- [2026-04-01: Food Planning Agent Design](../sessions/2026-04-01-food-planning-agent-design.md)
