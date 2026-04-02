# Frontend Redesign with shadcn/ui

Full UI overhaul of all screens. Replace inline styles with Tailwind + shadcn components. Fix workflow issues identified in design review.

## Phase 0: Setup shadcn/ui + Tailwind — DONE

- [x] Install Tailwind CSS v4 (`tailwindcss` + `@tailwindcss/vite`)
- [x] Run `npx shadcn@latest init` — configured aliases, CSS variables, neutral base theme
- [x] Install shadcn components (Button, Card, Table, Tabs, Select, Input, Checkbox, Badge, Separator, Sheet, Label, Dialog, DropdownMenu, Collapsible, Tooltip)
- [x] Set up custom color theme (success green + warning amber CSS variables)
- [x] Added jsconfig.json for @/ path alias

## Phase 1: App Shell & Navigation — DONE

- [x] Sticky header with nav links, trip selector pushed right
- [x] Active nav state styling (foreground vs muted-foreground)
- [x] Mobile hamburger Sheet (slide-out) with nav + trip selector
- [x] Trip selector: Dialog for new trip (replaces window.prompt), Dialog for delete (replaces window.confirm)
- [x] "Packing" nav link (hidden when no trip selected)
- [x] `/packing` route redirects to active trip's packing screen
- [x] Consistent page padding via Tailwind, max-w-7xl centered

## Phase 2: Trip Planner — Sticky Summary — DONE

- [x] Two-column layout: left (calculator + meals + snacks), right (sticky summary)
- [x] Summary stays visible while scrolling via `sticky top-20`
- [x] Mobile: summary shown below content
- [x] TripSummary restyled as Card with Badge status indicators (green/amber)
- [x] Separators between snack/meal/combined sections
- [x] Fixed TripCalculator debounce bug (`let` -> `useRef`)

## Phase 3: Collapsible Sections — DONE

- [x] Trip Calculator in Collapsible Card with summary in collapsed header
- [x] Meals in Collapsible Card with count/weight Badge
- [x] Snacks in Card (always expanded)
- [x] Calculator: labeled inputs, muted derived values
- [x] Meals: shadcn Table, outline Button +/- for quantity, category Badge

## Phase 4: Snack Table Redesign — DONE

- [x] Removed "Packed" checkbox from planning screen
- [x] Desktop: shadcn Table with zebra striping (`even:bg-muted/50`)
- [x] Columns: Name / Servings (+/-) / Wt / Cal / Cal/oz / Notes
- [x] Mobile: card layout per snack (name, stepper, stats)
- [x] Inline notes field (blur to save)

## Phase 5: Packing Screen — DONE

- [x] "Back to Planner" button
- [x] Recipe Assembly: Card per meal with Checkbox, category/quantity Badges, ingredient Table, Collapsible at-home prep
- [x] Packed meals: opacity + strikethrough
- [x] Snack Packing: shadcn Table with Checkbox, strikethrough on packed rows
- [x] Progress badges ("0/22 packed")
- [x] Shopping List: Collapsible with item count Badge

## Phase 6: Recipe Library & Edit — DONE

- [x] Recipes list: shadcn Table, category Badge, Tabs filter (All/Breakfast/Dinner)
- [x] "+ New Recipe" Button in header
- [x] Recipe edit: Card form with Labels, shadcn Table for ingredients
- [x] Delete via destructive Dialog (replaces window.confirm)
- [x] Save/Cancel/Delete Button variants

## Phase 7: Snack Catalog & Ingredients — DONE

- [x] shadcn Table with sortable headers (click to sort, arrow indicators)
- [x] Explicit Edit/Delete buttons per row (no more double-click)
- [x] Add form via Dialog (replaces inline toggle form)
- [x] Delete confirmation via Dialog (replaces window.confirm)
- [x] Zebra striping, consistent styling

## Phase 8: Polish & Mobile QA — DONE

- [x] All screens verified at 390px width
- [x] Mobile hamburger menu works with all nav links
- [x] Snack cards stack properly on mobile
- [x] Empty states present (no meals, no snacks messages)
- [x] Deployed and verified on beebaby:8000

## Review

All 7 workflow recommendations implemented:
1. Sticky summary panel — visible while adjusting servings
2. Collapsible sections — calculator and meals collapse, snacks stay open
3. Card layout for snacks on mobile — stacked cards instead of crushed table
4. Packed checkboxes removed from planner — only on packing screen
5. Packing screen in nav — plus /packing redirect
6. shadcn/ui design system — consistent buttons, cards, tables, badges, dialogs
7. Zebra-striped tables — on snacks and catalog pages

Additional fixes:
- TripCalculator debounce bug fixed (let -> useRef)
- window.confirm/prompt replaced with Dialogs everywhere
- Packing screen has progress badges (X/Y packed)
- Shopping list is collapsible
