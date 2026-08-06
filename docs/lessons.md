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

- date: 2026-08-06
  context: hiking-food step 5 (shopping + packing units); legacy invariance snapshots
  category: approach
  body: A "legacy output is unchanged" criterion is only worth as much as the
    snapshot's provenance. Capturing the dict from the tree you just edited proves
    nothing. Building the fixture in a script, running it against a git worktree of
    the pre-change commit with the project venv on the worktree's backend path, and
    hard-coding that JSON took about ten minutes and made the assertion real.
  fix: For any invariance claim, capture the baseline from a worktree of the
    pre-change commit before touching the file, and say in the test's comment which
    commit it came from.

- date: 2026-08-06
  context: hiking-food step 5; three copies of the same aggregation block
  category: approach
  body: `shopping_view` had the same seven-line `totals.setdefault(...)` block for
    recipe ingredients and catalog servings, and the new bag expansion would have
    been a third. The acceptance criterion "on_hand / essentials / packing_method
    behave the same for expanded bag ingredients" is then a property you assert
    rather than one the code guarantees.
  fix: When a new source has to merge into an existing aggregation, extract the
    line-creation into one helper first, so the shared behavior holds by
    construction and the new source cannot drift from the old ones.

- date: 2026-08-06
  context: hiking-food structured-snack-units orchestration run; browser gates
  category: friction
  body: The Vite dev proxy rewrites `/hiking-food/api/...` to `/api/...` before
    forwarding to :8000, but `backend/main.py` mounts the whole app under
    `/hiking-food`, so every proxied API call 404s and the dev page renders "No
    trips". Pre-existing mismatch, discovered by the step-1 verifier. All five
    browser gates ran against the production-served dist at
    `http://localhost:8000/hiking-food/` instead (each step's build gate had just
    rebuilt it, so the served bundle matched the diff under test).
  fix: Drop the `rewrite` from the `/hiking-food/api` proxy entry in
    `frontend/vite.config.js` (the backend expects the prefixed path). One-line
    change, separate commit; until then `pnpm dev` is not usable for API-backed
    pages.

- date: 2026-08-06
  context: structured-snack-units run; six plans executed by six implementer agents
  category: doc-gap
  body: Every implementer legitimately touched files outside its plan's Owns list,
    and it was the same shared infrastructure each time - tests/conftest.py
    (dependency_overrides for a new router), frontend/src/test/apiMock.js (shared
    fixtures), docs/architecture.md (self-healing counts/enumerations that go
    stale on any new module). Each deviation cost handoff space to justify and
    orchestrator time to audit.
  fix: spec-to-plans should emit a standing "shared surfaces, expected to touch"
    list (conftest, shared test fixtures, architecture.md, lessons.md) in every
    plan, so Owns stays about domain code and deviations mean something.

- date: 2026-08-06
  context: structured-snack-units run; step-5 verifier browser cleanup
  category: friction
  body: A verifier ended its browser work with `agent-browser close --all`, which
    closed two unrelated named sessions ("hiking-trip-docs", "ia") that other
    work had open. Nothing was lost beyond the open contexts, but an agent
    should never tear down sessions it did not create.
  fix: Verifier briefings (and the agent-browser skill docs) should say: close
    only the session you opened, by name; never `--all` in a shared environment.
