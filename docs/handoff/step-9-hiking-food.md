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
