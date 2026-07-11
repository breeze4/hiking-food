# Step 2 handoff: Frontend mutation state, accessible controls, lazy routes

Implements `docs/plans/44-frontend-mutation-ux.md`. Frontend-only. No new
dependencies, no backend or API-contract changes.

## The shared hook

`frontend/src/hooks/useMutation.js` — `useMutation(mutationFn)` returns
`{ run, pending, error }`.

- `run(...args)` sets `pending` true, clears `error`, awaits `mutationFn(...args)`.
- On success `run` resolves to the mutation's return value; on rejection it
  captures the error in `error` and resolves to `undefined` (never rethrows),
  so call sites need no try/catch.
- `error` clears at the start of the next `run` (retry).
- The hook standardizes STATE only. Each call site's function still owns its
  refresh mechanism (refreshTrip / response-body / loadData) — the hook does
  not change what triggers a refresh.
- `run` is intentionally recreated each render and closes over the current
  `mutationFn`; nothing depends on its identity. (Earlier a `useRef`+`useCallback`
  version tripped the `react-hooks/refs` lint rule — do not reintroduce it.)
- Every `useMutation` call must sit above any early `return` in its component
  (rules-of-hooks); the planner components were reordered accordingly.

## Call sites that adopted the hook

- `MealSelection.jsx` — `addMutation` (add meal), `quantityMutation` (qty +/-,
  delete at 0). Keeps `refreshTrip()`.
- `SnackSelection.jsx` — `addMutation`, `servingsMutation`, `removeMutation`,
  `notesMutation`, `slotMutation`. A combined `mutating`/`mutationError` is
  threaded into `SlotSection`, `DrinkMixSection`, and `AddPanel`. Keeps
  `refreshTrip()`.
- `TripCalculator.jsx` — `saveMutation` wraps the debounced PUT; inputs disable
  while saving; keeps `refreshTrip()`.
- `PackingScreen.jsx` — one `mutation` wraps every packed/weight setter and
  `toggleOnHand` as `run(() => apiCall())`, then `await loadData()`. Load-failure
  `error` stays a full-page message; mutation errors render inline so a failure
  never blanks the page.
- `TripContext.jsx` — one `tripMutation` shared by `createTrip`/`cloneTrip`/
  `deleteTrip`, exposed on context as `tripMutation`. `createTrip` resolves to
  the trip, `deleteTrip` to `true`, so `TripSelector` only closes its dialog on
  success and shows `tripMutation.error` otherwise; New/Clone/Delete disable
  while pending.
- `DailyPlanPage.jsx` — `autoFillMutation` and a shared `planMutation`
  (`run(apiCall)` → `setPlan(await apiCall())`) for add/increment/remove. Keeps
  the response-body refresh. Load `error` stays full-page; mutation errors
  render inline.

## Accessible-name convention (exact templates)

`aria-label`s that include the item name so a specific row is targetable:

- Quantity/servings steppers: `Increase <name> quantity` / `Decrease <name> quantity`
  (meals); `Increase <name> servings` / `Decrease <name> servings` (snacks, both
  desktop and mobile).
- Snack number input: `<name> servings`. Notes input: `<name> notes`.
  Slot select (SelectTrigger `aria-label`): `<name> slot`.
- Remove: `Remove <name>`. Catalog add rows: `Add <name>`.
- Packing (added while wiring pending state): `<name> packed`, `<name> on hand`,
  `<name> actual weight`.
- DailyPlanPage: day-assign buttons `Assign <name> to day <n>`; allocate toggle
  `Allocate <1|½> serving of <name>`; per-item `Add half serving of <name>`,
  `Add serving of <name>`, `Remove <name>` (aria-labels added alongside the
  existing `title` attrs).

Note: base-ui `Checkbox` reflects disabled via `aria-disabled="true"` (a
`<span role="checkbox">`), not a native `disabled` attribute — assert
`toHaveAttribute('aria-disabled','true')`, not `toBeDisabled()`. base-ui
`Button` uses native `disabled`, so `toBeDisabled()` works there.

## Test infrastructure

- `frontend/src/test/apiMock.js` — extracted from `App.test.jsx`. Exports
  `jsonResponse`, `defaultTrips`, `makeTripDetail`, `makeSummary`,
  `makeDailyPlan`, `createApiMock(config)`, and `apiResponse` (zero-config
  default, faithfully reproducing the original App.test behavior — all 17 stay
  green). `createApiMock` provides sane read defaults + success mutations; pass
  `handler(path, method, options) => Response | undefined` to intercept specific
  requests (return `jsonResponse(...)` to override, `undefined` to fall through).
- New whole-App-render test files: `hooks/useMutation.test.jsx`,
  `components/MealSelection.test.jsx`, `components/SnackSelection.test.jsx`,
  `components/TripCalculator.test.jsx`, `components/TripSelector.test.jsx`,
  `pages/PackingScreen.test.jsx`, `pages/DailyPlanPage.test.jsx`.
- Per-row snack controls render in BOTH desktop and mobile layouts in jsdom,
  so those tests use `getAllBy*` (length 2) for the duplicated controls.

## Lazy routes

`App.jsx`: the 8 route pages load via `React.lazy`; the `<Routes>` is wrapped in
one `<Suspense fallback={<p className="text-muted-foreground p-4">Loading...</p>}>`.
`TripSelector`, `SettingsModal`, and nav components stay eagerly imported. No
`manualChunks` tuning.

## Build size (main/entry chunk)

- Before: `dist/assets/index-*.js` = 528.89 kB (gzip 161.46 kB), tripped Vite's
  >500 kB warning.
- After: `dist/assets/index-*.js` = 306.44 kB (gzip 98.18 kB); route pages split
  into their own async chunks (e.g. TripPlannerPage ~97 kB, DailyPlanPage
  ~11 kB). No chunk-size warning emitted.

## Verification (all green, run from `frontend/`)

- `pnpm test` — 8 files, 39 tests pass (17 original + 22 new).
- `pnpm lint` — clean.
- `pnpm build` — clean, no large-bundle warning.

Not done here (separate verifier gate): live browser pass. No commit made.
