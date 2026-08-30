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

The corrected worker-limit push again received HTTP `502` from the GitHub
webhook route and created no Woodpecker pipeline. This evidence commit triggers
the unchanged recovery tree after recording that edge failure.

The first evidence trigger also received no Woodpecker pipeline. After the
existing Funnel target was reapplied without a route change, this step creates
one empty recovery trigger for the corrected tree and verifies the delivery and
pipeline through the Woodpecker API.

## Final bridge evidence

Woodpecker pipeline `5` passes for commit
`51a49c4c799f3e047def8a2d2288a2b8abb6ea4b`. It publishes
`ghcr.io/breeze4/hiking-food@sha256:c4e3a2768e92085ac7a2b90be3911543cedab24931728febcbfe7aa2a9b4a452`.
The OCI revision label equals that commit, and the image user is `1000:1000`.

The candidate used SQLite backup operations for both databases, then mounted
only those backup files at `/data`. It passed `/hiking-food/api/health`, OAuth
authorization-server discovery with the retained HTTPS issuer, and the
path-prefixed root route. The Planner and OAuth database integrity checks both
returned `ok`. The Planner backup retained WAL mode, and the OAuth backup
retained delete journal mode. Docker inspection proves `ReadonlyRootfs=true`,
`CapDrop=[ALL]`, and only the candidate `/data` bind.

The candidate moved to loopback port `18086` only because `18080` belongs to
the existing Caddy candidate and `18081` belongs to the deployment probe. This
temporary test override does not change the committed service definition or any
production route. The source `hiking-food.service` stayed active throughout.

The normal commit hook recorded Factory compatibility deployment
`aef0c6e1-d803-43dd-82c7-4f7c9c1312be` for the trigger commit. After the
candidate stopped, the source service returned its health response and the
path-prefixed root response from port `8000`. The candidate never received
production traffic.

## Remaining verification

A fresh-context verifier must inspect this committed bridge and repeat the
repository, image, database restore, OAuth discovery, path-prefix, source
service, and rollback criteria without repairing this step.
