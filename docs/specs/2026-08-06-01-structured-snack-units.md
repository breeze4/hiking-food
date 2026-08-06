# Structured Snack Units (4 × 2 oz per day)

## Problem Statement

Snack planning today is free-form: pick catalog items, set serving counts, and steer by a calorie band (60% of daytime calories after drink mixes). In practice this produced large miscellaneous bags of snacks and fiddly planning. The user wants a simpler mental and packing model: four snacks per day, two ounces each, in addition to breakfast, lunch, and dinner. Past trips must stay exactly as packed — they are a historical record — but new trips, starting with Olympics 2026, should get the structured model.

## Solution

Introduce a per-trip snack model. Legacy trips keep today's behavior untouched. Structured trips plan snacks as **units**: a unit is either one packaged catalog item (an RX bar, a fig bar — nominally 2 oz) or a **bag** — a reusable composition of bulk ingredients portioned to ~2 oz (e.g., 1 oz nuts + 1 oz M&Ms). The trip has a unit quota (snacks per day × days, scaled and rounded on partial days). The planner fills the quota with unit types × quantity and shows a units-filled meter as the primary gauge. Lunch and drink mixes are unchanged. Shopping, packing, daily plan, and the planning agent all understand units on structured trips.

## User Stories

1. As a trip planner, I want new trips to use a 4 × 2 oz/day snack structure, so that snack planning is a simple count instead of a calorie budget.
2. As a trip planner, I want my old trips to remain exactly as packed, so that my historical record stays truthful.
3. As a trip planner, I want to define reusable bag compositions (e.g., trail mix bag = 1 oz nuts + 1 oz M&Ms), so that I define a bag once and use it on every trip.
4. As a trip planner, I want packaged snacks (bars) to count as one unit without any bag definition, so that simple things stay simple.
5. As a trip planner, I want a unit quota computed from trip days (partial days scaled by fraction, rounded to whole units), so that I never pack a fraction of a bag.
6. As a trip planner, I want to fill the quota by choosing unit types and quantities, so that batching identical bags is one row, not many clicks.
7. As a trip planner, I want a units-filled meter (e.g., 12 of 14) as the snacks section's primary gauge, so that "am I done?" is a glance.
8. As a trip planner, I want calories and weight still shown as secondary info on the snacks section, so that I keep the nutritional gut-check.
9. As a trip planner, I want a warning when a unit type's real weight is outside a tolerance band around 2 oz, so that drifty bags are visible but not blocked.
10. As a trip planner, I want snacks per day and ounces per snack configurable per trip (defaults 4 and 2), so that a winter trip can run heavier without a code change.
11. As a trip planner, I want cloning a trip to copy its snack model and its unit selections, so that clones behave like their source.
12. As a trip planner, I want the daily plan to auto-fill 2 units in morning snacks and 2 in afternoon snacks (scaled on partial days), so that the day view matches the structure.
13. As a trip planner, I want the shopping list to expand bag units into bulk-ingredient ounces, so that shopping stays accurate.
14. As a trip planner, I want the packing list to say "make 6 × trail mix bag @ 2.0 oz", so that packing day is an assembly checklist.
15. As a trip planner, I want the planning agent (MCP tools) to plan structured trips with units, so that agent-driven planning keeps working.
16. As a trip planner, I want lunch planning unchanged on structured trips, so that only the snack portion gains structure.
17. As a trip planner, I want to mark unit selections as packed with actual weights, like snacks today, so that pack-day workflow is familiar.

## Data Flow

- The trip record gains `snack_model` (`legacy` | `structured`), `snacks_per_day` (default 4), and `oz_per_snack` (default 2). Existing rows backfill to `legacy`; newly created trips default to `structured`.
- A **snack unit type library** stores bag compositions: a unit type has a name, notes, and composition rows (ingredient + ounces), mirroring the recipe/recipe-ingredient pattern. Packaged units need no library entry — they reference a snack catalog item directly.
- A **trip snack unit selection** links a trip to either a catalog item (packaged) or a unit type (bag), with a quantity, packed flag, actual weight, and trip notes. Legacy `TripSnack` rows continue to serve lunch and drink mixes on all trips, and everything on legacy trips.
- The trip summary computes: unit quota = per-day sum of round(snacks_per_day × day fraction); units filled = sum of selection quantities; per-unit-type weight/calories/macros derived from ingredient per-oz data (bags) or catalog serving data (packaged). On structured trips the snacks slot subtotal reports the unit meter instead of the 60% calorie band; lunch's 40% band is computed as today.
- The daily plan auto-fill, on structured trips, distributes unit selections into `morning_snacks` / `afternoon_snacks` (2 + 2 per full day, scaled on partial days) via a new assignment source type; lunch and drink mix distribution unchanged.
- Shopping list expands bag selections into ingredient ounces and merges with the rest; packaged selections aggregate as catalog servings. Packing detail groups unit selections by unit type with counts and target weight.
- MCP tools gain unit-type library CRUD and trip-unit selection CRUD plus quota readout; the plan-food agent instructions gain the structured flow.

## Behavior

- New trips: `snack_model = structured`, `snacks_per_day = 4`, `oz_per_snack = 2`, editable in the trip calculator alongside existing targets.
- Existing trips: backfilled `legacy` in the migration; zero behavior change anywhere on legacy trips.
- Clone: copies `snack_model`, the two config fields, and unit selections (packed flags reset, consistent with current clone behavior for snacks).
- Quota rounding: per-day round-to-nearest (half up) of snacks_per_day × fraction, summed. A 0.5 + 2 + 0.5 trip at 4/day = 2 + 4 + 4 + 2 = 12 units.
- Unit weight: packaged = catalog `weight_per_serving`; bag = sum of composition ounces. Warn (badge, non-blocking) when outside ±25% of `oz_per_snack`.
- Unit calories/macros: bag = per-oz ingredient data × composition ounces; packaged = catalog per-serving values, macros via its ingredient as today.
- The snacks slot on structured trips shows units filled / quota as the meter; weight and calories are secondary text. Lunch keeps the existing calorie band. Drink mixes are untouched (outside the structure).
- Daily plan on structured trips: only unit selections fill morning/afternoon snack slots; a half day with a 2-unit quota gets 1 + 1. Existing slot names are reused — no new slot values.
- Deleting a unit type in the library is blocked while any trip references it (same posture as catalog items in use).
- The unit-type library owns composition and derived weight/calories; consumers (summary, shopping, packing, daily plan, MCP) read derived values through its queries and never recompute composition math.

## Modules

- **Trip snack mode + config**: trip columns, migration backfill, create/clone defaults.
  - Role: **defines** the gating interface every other module checks.
  - Interface: `snack_model`, `snacks_per_day`, `oz_per_snack` on trip read/write schemas.
  - Test: yes (migration backfill, create/clone defaults).
- **Snack unit type library**: unit type + composition tables, CRUD, derived weight/calories/macros, in-use delete protection.
  - Role: **defines** the unit-type interface (deep module — all composition math lives here).
  - Interface: library CRUD endpoints + a query returning derived per-unit values.
  - Test: yes (composition math, tolerance warning, delete protection).
- **Trip unit selections**: selection CRUD under trips, quantity/packed/actual-weight handling.
  - Role: **defines** the selection interface; consumes the library.
  - Interface: trip unit selection endpoints, included in trip detail.
  - Test: yes (CRUD, structured-only guard).
- **Quota + summary integration**: quota computation, unit meter, secondary calories/weight, legacy passthrough.
  - Role: consumes trip config + selections.
  - Test: yes (partial-day rounding, meter values, legacy trips unchanged).
- **Daily plan integration**: auto-fill distribution of units 2+2, new source type, scaling on partial days.
  - Role: consumes selections; extends existing assignment interface.
  - Test: yes (distribution, partial days, legacy autofill unchanged).
- **Shopping + packing integration**: bag expansion to ingredient ounces; packing grouped by unit type.
  - Role: consumes the library and selections.
  - Test: yes (expansion math, merge with legacy lunch/drink-mix items).
- **Frontend planner UI**: structured snacks section (unit types × quantity, meter, warnings), trip calculator fields, legacy rendering unchanged.
  - Role: consumes everything above.
  - Test: yes (vitest component tests, following the existing snack selection tests), plus build + lint and an agent-browser screenshot smoke pass.
- **MCP / plan-food agent**: unit tools + agent instruction updates.
  - Role: consumes the same service layer.
  - Test: yes (MCP tool tests, prior art in existing MCP test suite).

## Resolved Decisions

- **Unit semantics**: packaged catalog items count as one nominal 2 oz unit as-is; bulk items are packed as bags with explicit ~2 oz compositions — matches how food is actually packed; a pure weight-conversion model was rejected as keeping the old fiddliness.
- **Bags can mix items**: compositions hold multiple ingredients with ounces — chosen for packing reality (nuts + M&Ms) over single-item simplicity.
- **Lunch stays as-is**: the structure covers only the snacks slot — lunch's 40% calorie band was judged to work fine.
- **Partial days scale**: round(snacks_per_day × fraction) per day — never pack a fractional bag; full-count-every-day rejected as overpacking travel days.
- **Per-trip mode field**: `snack_model` column, backfill legacy, default structured for new trips, clone copies — chosen over creation-date gating so the record is explicit and reversible.
- **Unit types × quantity UX**: batch rows with a filled/total meter — chosen over per-slot filling (too clicky) and over free-form with a converter meter (too little structure).
- **Reusable library**: bag compositions defined once, used across trips — mirrors the recipe pattern; per-trip-only was rejected as re-entering the same bag every trip.
- **2 oz is a soft target**: warn outside ±25% of `oz_per_snack`, never block — real food weights drift.
- **Unit meter primary, calories secondary**: on structured trips the 60% snack calorie band is replaced by the unit meter; both-meters was rejected as gauge clutter.
- **Daily slots reuse morning/afternoon**: 2 + 2 per full day into existing slot names — no schema churn for slot values.
- **Config over constants**: `snacks_per_day` / `oz_per_snack` trip fields with defaults 4 / 2, following the existing configurable-targets pattern.
- **Drink mixes untouched**: they remain their own category and distribution logic, outside the unit structure (decided post-interview; nothing in the request implicated them).
- **Composition references ingredients, not catalog items**: bags are mini-recipes over per-oz ingredient data, mirroring recipe ingredients — cleaner math than deriving per-oz from catalog serving weights (decided post-interview).

## Testing Decisions

- Backend modules all get pytest coverage (see Modules); prior art: existing suites for slots, snack macros, daily plan, shopping list, migrations, and MCP tools.
- Migration test proves legacy backfill and that a legacy trip's summary output is byte-identical before/after.
- Frontend: vitest component tests exist (snack selection, trip calculator, daily plan, packing screen all have them) — the structured snacks UI gets component tests following those, plus lint + build gates and an agent-browser screenshot smoke pass.

## Out of Scope

- Migrating or reinterpreting any existing trip's snack data (they stay legacy forever unless manually flipped).
- Changes to lunch or drink mix planning, targets, or distribution.
- Auto-suggesting bag compositions or auto-balancing units by calories.
- Per-unit flavor/variety constraints (e.g., "no more than 2 sweet per day").
- A UI for flipping an existing trip's snack model (the column allows it; no dedicated affordance is built).
- Retiring the legacy model.
