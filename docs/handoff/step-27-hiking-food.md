# Step 27 Hiking Food cleanup handoff

## Scope

This step removes the retired Factory path from Hiking Food and makes Woodpecker
on BeeBaby the only deployment path. It changes deployment plumbing and
documentation. It changes no application feature, interface, business logic, or
data model.

## Baseline

Hiking Food starts at commit `bb0388d` on `main` with a clean worktree. BeeBaby
already runs the container deployment: `/srv/beebaby/deployments/hiking-food/active.env`
records digest `sha256:c4e3a2768e92085ac7a2b90be3911543cedab24931728febcbfe7aa2a9b4a452`
for commit `51a49c4`, deployed by the `cutover` action on 2026-08-31.

The repository carried two deployment contracts, `factory.project.yml` and
`cicd-router.project.yml`, and two near-identical gate scripts,
`scripts/ci-gates.sh` and `scripts/cicd-router-gates.sh`. The check workflow ran
neither script. It repeated the gate commands inline across two container steps.

## Changes

- Removed `factory.project.yml` and `cicd-router.project.yml`. Git history keeps
  both contracts.
- Merged the two gate scripts into one `scripts/ci-gates.sh` and removed
  `scripts/cicd-router-gates.sh`. The two scripts differed only in the frontend
  test invocation. The merged gate keeps `--maxWorkers=1`, which is what the
  check workflow already ran.
- Pointed `.woodpecker/check.yaml` at the merged gate. The workflow is now one
  step on the pinned `python:3.12.13-slim` image, which supplies the Python 3.12
  that the hashed `backend/requirements-dev.txt` pins target. It adds Node
  22.14.0 from the official tarball, verified against the published SHA-256
  checksum, to match the Node version that the `Dockerfile` uses for the
  frontend build.
- Added `.woodpecker/deploy.yaml`. It depends on the `publish` workflow and calls
  the restricted deployment command with the commit tag. The host resolves the
  tag to an immutable digest with its own registry credentials.
- Rewrote `docs/deployment.md` for the container path: build, deploy, data,
  secrets, rollback, and live verification.
- Updated `README.md`, `AGENTS.md`, `CLAUDE.md`, and `docs/architecture.md`. Each
  described Factory, the retired router contract, or the systemd source
  deployment as the live path. Removed the two Factory proof comments from the
  README.
- Kept `deploy/remote-bootstrap.sh` and `deploy/hiking-food.service`. The
  rollback window stays open until the container deployment passes one BeeBaby
  reboot and seven days of normal operation. `README.md` and `docs/deployment.md`
  both record that.

## Gate results

The merged gate passed on macOS against the working tree: 275 backend tests,
9 frontend test files, 73 frontend tests, lint, and a clean Vite build.

The gate also ran on BeeBaby in the pinned check image, as root, from a clean
export of the tracked tree. The backend suite returned `275 passed in 24.50s`.
The frontend suite returned `73 passed (73)` on the first run.

A second BeeBaby run of the same tree failed two `SnackSelection.test.jsx`
assertions:

```
FAIL  src/components/SnackSelection.test.jsx > SnackSelection > every per-snack control exposes an accessible name identifying the snack
TestingLibraryElementError: Unable to find role="button" and name "Increase Tuna Packet servings"
Test Files  1 failed | 8 passed (9)
```

Both failures are Testing Library `findBy` lookups that exceeded the default
1000 ms window. The slower one reported 1297 ms. The same tree passed on the same
host minutes earlier, and the Woodpecker database was locked by concurrent
pipelines during the failing run, so the host was under load. This is a
load-sensitive flake in an existing test, not a gate regression. The merged gate
runs the same frontend command the check workflow already ran.

## Remaining risks

- The two `SnackSelection.test.jsx` assertions can fail when BeeBaby is busy.
  The fix is a longer Testing Library async timeout in `frontend/src/test/setup.js`.
  This step does not change tests, so the flake stays open.
- The check workflow now downloads the Node tarball from `nodejs.org` on every
  run. The SHA-256 check makes the download tamper-evident, but the workflow
  fails if that host is unreachable.
- The retired `deploy/` files stay in the tree. Remove them after the rollback
  window closes.
