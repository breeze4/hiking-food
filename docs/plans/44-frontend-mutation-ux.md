# Frontend Mutation State, Accessible Controls, and Lazy Routes

## Goal

Give every frontend mutation observable pending/error state with the correct
projection refresh, give the quantity/half-serving/add/remove controls real
accessible names, and lazy-load route pages to remove the Vite large-bundle
warning. Test-first with the installed Vitest + Testing Library harness.

Blocked by: none.

## Context

Facts confirmed in code (2026-07-11):

- `frontend/src/api.js` is the sole HTTP client (thin `get/post/put/patch/del`
  over fetch). No query library, no hooks layer. `TripContext.jsx` exposes
  `refreshTrip` (refetch detail + summary) and `refreshTrips`.
- Mutations are fire-and-forget: no call site exposes pending state, and only
  `DailyPlanPage.jsx` (try/catch → local `error` rendered at line 290) and
  `PackingScreen.toggleOnHand` surface errors. Call sites with no error
  handling: `MealSelection.jsx` `handleAdd`/`updateQuantity` (71-88),
  `SnackSelection.jsx` `handleAdd`/`updateServings`/`removeSnack`/
  `updateNotes`/`updateSlot` (76-108), `TripCalculator.handleChange` (35-43,
  debounced PUT), `PackingScreen` packed/weight setters (49-71), and
  `TripContext` `createTrip`/`cloneTrip`/`deleteTrip` (91-120).
- Refresh strategies already in place: planner components call
  `refreshTrip()`; `DailyPlanPage` assigns the mutation response body into
  `plan` state; `PackingScreen` refetches via its local `loadData`.
- Accessible-name gaps: `MealSelection.jsx` `-`/`+` steppers (132-140);
  `SnackSelection.jsx` `-`/`+`/`×` buttons, bare number `Input`, notes input,
  slot `Select` (267-319 desktop, 322-360 mobile, 442-499 drink mixes);
  `DailyPlanPage.jsx` day-number assign buttons (388-402) have numerals only
  (its `½`/`+`/`×` buttons already carry `title` attributes). The one good
  example: `TripSelector.jsx:37` `aria-label="Active trip"`.
- Routing: all pages statically imported in `frontend/src/App.jsx` (lines
  6-15); no `React.lazy`/`Suspense` anywhere; no `manualChunks`; everything
  lands in one chunk that trips Vite's 500 kB warning.
- Test harness: Vitest config inline in `vite.config.js` (jsdom,
  `src/test/setup.js`, `restoreMocks`). The 17 existing tests live in
  `frontend/src/App.test.jsx`: fetch stubbed via
  `vi.stubGlobal('fetch', vi.fn(apiResponse))` with a hand-written path
  switch, routes seeded via `history.replaceState`, whole `<App />` rendered,
  assertions via roles and `findBy*`.

## Decisions (made, not open)

- No query library. Add one small shared hook (e.g.
  `frontend/src/hooks/useMutation.js`) that wraps an async mutation and
  exposes run/pending/error; every mutation call site above adopts it.
  Controls are disabled while their mutation is pending; errors render with
  the existing `text-destructive` pattern from `DailyPlanPage`.
- Refresh stays per the existing strategies (refreshTrip / response-body /
  loadData) — the hook standardizes state, not the refresh mechanism.
- Accessible names are `aria-label`s that include the item name (e.g.
  "Increase <name> quantity", "Remove <name>"), so tests and assistive tech
  can target a specific row. `DailyPlanPage` day buttons get labels like
  "Assign <name> to day <n>".
- The shared fetch-mock helpers (`apiResponse`, `jsonResponse`, seeding) are
  extracted from `App.test.jsx` into `frontend/src/test/` so new test files
  reuse them; `App.test.jsx` keeps its existing tests.
- Route pages load via `React.lazy` + one `Suspense` fallback in `App.jsx`.
  No `manualChunks` tuning beyond that.

## Tasks

Write the failing test before each behavior change, following the existing
whole-App render + fetch-stub pattern.

- [x] Extract the shared fetch-mock helpers from `App.test.jsx` into
  `frontend/src/test/` with all 17 existing tests still passing.
- [x] Add the shared mutation hook with tests: pending is true during an
  in-flight mutation (resolver-controlled promise, like the existing stale-
  response test), error state is set on rejection and clears on retry.
- [x] Adopt the hook in `MealSelection` and `SnackSelection`: tests prove a
  failed add/update/remove surfaces an error message, controls disable while
  pending, and a successful mutation refreshes the trip projections
  (refetch called, updated values rendered).
- [x] Adopt the hook in `TripCalculator`, `PackingScreen`, and `TripContext`
  create/clone/delete with the same pending/error coverage.
- [x] `DailyPlanPage`: keep its response-body refresh, adopt the hook for
  pending state, and verify assignment mutations update the rendered plan.
- [x] Add accessible names to all quantity, half-serving, add, remove, notes,
  and slot controls listed in Context; tests locate each control by role and
  accessible name (e.g. `getByRole('button', { name: /increase .* quantity/i })`).
- [x] Convert route pages in `App.jsx` to `React.lazy` with a `Suspense`
  fallback; all tests still pass (async `findBy*` where needed) and
  `pnpm build` completes without the chunk-size warning.
- [x] Run `cd frontend && pnpm test && pnpm lint && pnpm build` — all green.

## Acceptance criteria

- [x] Every mutation call site exposes pending and error state to the UI;
  no fire-and-forget mutation remains.
- [x] Failed mutations show a visible error and leave the app usable;
  successful mutations refresh the correct projections.
- [x] Quantity, half-serving, add, and remove controls (desktop and mobile
  layouts) have accessible names that identify the item they act on.
- [x] Route pages are code-split; `pnpm build` emits no large-bundle warning.
- [x] Frontend suite, lint, and production build pass.

## Done when

`cd frontend && pnpm test && pnpm lint && pnpm build` is green with the new
coverage, and a live browser pass against the local app confirms: pages load
via lazy chunks, a snack add/remove and quantity change work end-to-end, and
the controls expose their accessible names in the accessibility tree.
