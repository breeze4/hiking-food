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
