# Lessons

Structured session feedback. Each entry: date, context, category
(`friction` | `correction` | `worked-well` | `missing-tool` | `doc-gap`), body,
and a proposed fix when obvious.

---

- date: 2026-07-12
  context: hiking-food deploy blocked; anyio 4.14.2 released upstream
  category: correction
  body: The cicd-router lock gate (`scripts/check-requirements-lock.sh`) recompiled
    requirements to a fresh temp file with no preferences, so `uv pip compile`
    always resolved the newest release of every transitive dependency and demanded
    the committed lock match it. Any upstream publish marked the lock "stale" and
    blocked ALL deploys, including unrelated feature commits. User flagged this as
    an unacceptable failure mode.
  fix: Seed the temp output with the committed lock so uv keeps pinned versions as
    preferences; the gate now fails only on genuine `.in`-vs-lock inconsistency.
    Added `scripts/update-requirements.sh` for deliberate regen/upgrades. A pinned
    lockfile should only change on intentional upgrade, never on upstream drift.

- date: 2026-08-06
  context: hiking-food step 2 (snack unit library); backend test fixtures
  category: friction
  body: Test fixtures passed `calories_per_oz` alongside macros when creating
    ingredients, and three assertions failed with numbers nobody expected. The
    ingredients router derives `calories_per_oz` from macros (4/9/4 Atwater)
    whenever macros are present and silently drops the supplied value.
  fix: Recorded in the step-2 handoff so later plans' fixtures state macros only
    and assert against the derived per-oz calories. A comment on the derivation
    branch in `routers/ingredients.py` would catch this at the source.

- date: 2026-08-06
  context: hiking-food step 2; whole-App vitest page test
  category: friction
  body: A page test clicked `getByRole('button', { name: 'Delete' })` and hit the
    TripSelector's Delete in the header instead of the table row's, deleting a
    trip and leaving the assertion to fail somewhere unrelated. Whole-App renders
    put the header's generic control names in scope for every page test.
  fix: Give repeated table row actions per-item accessible names (`Delete {name}`)
    — better for screen readers and unambiguous in tests. Also note that a Base UI
    modal hides the background from the accessibility tree, so assertions about
    the table behind an open dialog must dismiss it first.

- date: 2026-08-06
  context: hiking-food step 4 (daily plan units); legacy-model backend tests
  category: friction
  body: Flipping the `POST /api/trips` default to the structured snack model made
    older test modules quietly stop testing what they claim. Step 3 hit one module
    (`test_slots.py`); step 4 hit three more (`test_daily_plan.py`,
    `test_daily_plan_macros.py`, `test_trip_workflows.py`) with seven failures,
    each because a helper created a trip through the API and assumed the legacy
    snack behavior. The failures read as broken features, not as stale fixtures.
  fix: When a model default flips, every test helper that creates the entity
    through the API is now suspect. Pin the model explicitly in the helper and say
    in its docstring which model the module exercises, so the next default change
    fails loudly in one place instead of scattering assertion errors.

- date: 2026-08-06
  context: hiking-food step 4; whole-App vitest page test
  category: friction
  body: After a mutation re-rendered the plan, `findByText(/Fig Bar/)` resolved to
    the pre-mutation unallocated-pool node, which React had already detached, so
    `toBeVisible()` failed on an element that was not in the document. The name
    existed in two places before and after the click, and the query picked the
    stale one.
  fix: Assert on something only the post-mutation tree has — a per-item control's
    accessible name — instead of a text match that also existed before the click.
