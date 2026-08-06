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
