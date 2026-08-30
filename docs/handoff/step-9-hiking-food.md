# Step 9: Hiking Food Woodpecker bridge

## Baseline

The bridge starts from `main` at `14ee68c13046764ae18ba01f9784c5c3f58f24f3`.
The source `hiking-food.service` remains active on port `8000`. It runs the
Python API from `/home/beeadmin/dev/hiking-food/backend` and reads the protected
MCP environment file.

The Planner database is `110592` bytes and the OAuth database is `20480` bytes.
Both are owned by `beeadmin:beeadmin`. SQLite reports `ok` for both integrity
checks. The Planner database uses WAL mode; the OAuth database uses delete mode.

## Bridge

The bridge adds a digest-pinned Node and Python container image, a hardened
candidate Compose service, Woodpecker checks and image publication, the common
gate, and deployment instructions. The container mounts only `/data` and reads
the protected MCP environment file. It keeps the `/hiking-food` path prefix and
OAuth issuer configuration unchanged.

## Rollback

The candidate uses isolated SQLite backups. It does not receive production
traffic or stop the Factory source service. Stopping the candidate returns the
source service as the active writer.

## Recovery

The initial GitHub push delivery received HTTP `502` with `failed to connect to
host`, so Woodpecker created no pipeline for the bridge commit. This handoff
commit records the delivery before it triggers the unchanged bridge tree again.

Woodpecker pipeline `1` passes the Python backend tests but fails the frontend
check before application tests. Its Node image selected pnpm `11.24.0`, while
the locked frontend requires `11.5.1`. The recovery explicitly activates pnpm
`11.5.1` in the check workflow and image builder before dependency installation.

Pipeline `2` passes the backend checks and image publication, but one existing
frontend interaction test times out under the CI load after 72 tests pass. The
same full 73-test suite passes locally. This transient timing failure changes
the check command to retry a failed frontend test once. It does not change test
expectations or application behavior.

The retry exposes two failures from the shared asynchronous UI test under
parallel Woodpecker workers. The final recovery runs the unchanged frontend
suite with one worker. This preserves every assertion and prevents test-file
concurrency from changing shared UI timing.

Vitest 4 rejects the initial `--minWorkers` option before it starts tests. The
final command keeps the supported `--maxWorkers=1` limit and removes the
unsupported option.
