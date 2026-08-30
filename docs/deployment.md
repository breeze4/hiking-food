# Hiking Food deployment

Hiking Food runs from an immutable GitHub Container Registry image. The image
contains the built client and the Python API. It reads its Planner and OAuth
SQLite databases and MCP environment file at runtime.

## Runtime data and OAuth

The Compose service mounts `HIKING_FOOD_DATA_DIR` at `/data`. The directory
contains `hiking_food.db`, `hiking_food_auth.db`, their SQLite journal files,
and migration backups. The service reads `HIKING_FOOD_ENV_FILE`. Keep OAuth and
MCP secrets in that protected file, outside the image and repository.

Before a candidate starts, back up both databases with SQLite:

```sh
sqlite3 /srv/beebaby/data/hiking-food/hiking_food.db ".backup '/srv/beebaby/backups/hiking-food/hiking_food.db'"
sqlite3 /srv/beebaby/data/hiking-food/hiking_food_auth.db ".backup '/srv/beebaby/backups/hiking-food/hiking_food_auth.db'"
```

The mounted directory must have UID and GID `1000`. The retained OAuth issuer
and path prefix remain in `HIKING_FOOD_ENV_FILE`.

## Build and verify an image

Set these values before rendering `compose.beebaby.yaml`:

```sh
IMAGE_DIGEST=ghcr.io/breeze4/hiking-food@sha256:IMAGE_SHA256
HIKING_FOOD_DATA_DIR=/srv/beebaby/data/hiking-food
HIKING_FOOD_ENV_FILE=/srv/beebaby/secrets/hiking-food/mcp.env
```

The candidate listens on loopback port `18080`. Confirm
`/hiking-food/api/health`, OAuth discovery, a retained route, and reload after
the container becomes healthy.

## Roll back a candidate

While Factory owns the source deployment, stop the candidate Compose service.
The bridge does not move traffic, remove Factory contracts, or change the
source deployment service.
