# Deploy Hiking Food

Woodpecker on BeeBaby builds, publishes, and deploys this repository. Factory no
longer participates.

## What happens on a push to main

Woodpecker runs three workflows for each commit on `main`:

1. `.woodpecker/check.yaml` runs `scripts/ci-gates.sh` in a pinned container.
   The gate runs the backend pytest suite, then the frontend tests, lint, and
   build.
2. `.woodpecker/publish.yaml` builds the runtime image and pushes it to
   `ghcr.io/breeze4/hiking-food` with the commit SHA as its tag.
3. `.woodpecker/deploy.yaml` calls the restricted deployment command on BeeBaby
   with that tag. The host resolves the tag to its immutable digest with its own
   registry credentials, so the registry token stays limited to the build
   plugin.

A pull request runs only the check workflow. Deployment secrets stay out of pull
request pipelines.

## What the deployment command does

The `deploy` forced command reaches `/usr/local/sbin/beebaby-deploy`, which
accepts only an allowlisted project, repository, commit, image, and action. For
each deployment it takes the host lock, confirms that the image digest belongs
to the expected GHCR repository, confirms that the image revision label equals
the pipeline commit, renders the Compose stack with the digest, waits for
container health, probes the service through the Caddy edge, and records the
digest. A failed health or route check restores the previous digest.

## Runtime data and secrets

The image carries the built client and the Python API. It holds no data. The
Compose service in `compose.beebaby.yaml` mounts `HIKING_FOOD_DATA_DIR` at
`/data` and reads `HIKING_FOOD_ENV_FILE`:

```sh
HIKING_FOOD_DATA_DIR=/srv/beebaby/data/hiking-food
HIKING_FOOD_ENV_FILE=/srv/beebaby/secrets/hiking-food/mcp.env
```

The data directory holds `hiking_food.db`, `hiking_food_auth.db`, their SQLite
journal files, and migration backups. It must have UID and GID `1000`. The
environment file holds the OAuth and MCP secrets, the OAuth issuer, and the path
prefix. Keep both outside the image and this repository.

The container starts the idempotent startup migrations against the mounted
databases, so a deployment can change the schema. Back up both databases before
you deploy a schema change:

```sh
sqlite3 /srv/beebaby/data/hiking-food/hiking_food.db ".backup '/srv/beebaby/backups/hiking-food/hiking_food.db'"
sqlite3 /srv/beebaby/data/hiking-food/hiking_food_auth.db ".backup '/srv/beebaby/backups/hiking-food/hiking_food_auth.db'"
```

## Roll back

To return to the previous digest, read the last two entries in
`/srv/beebaby/deployments/hiking-food/history.log` on BeeBaby and run the
deployment command with the digest you want:

```sh
ssh beeadmin@beebaby
sudo /usr/local/sbin/beebaby-deploy hiking-food breeze4/hiking-food \
  COMMIT_SHA ghcr.io/breeze4/hiking-food@sha256:DIGEST deploy
```

The active digest and commit stay in
`/srv/beebaby/deployments/hiking-food/active.env`.

A digest rollback returns the code, not the data. When the rolled-back commit
predates a schema change, restore the database backups you took before that
deployment.

## Verify a deployment

The service keeps its `/hiking-food` path prefix. Check the registry port and
the public route:

```sh
curl -sS -o /dev/null -w '%{http_code}\n' http://beebaby.tailc65f2f.ts.net:8000/hiking-food/api/health
curl -sS -o /dev/null -w '%{http_code}\n' https://beebaby.tailc65f2f.ts.net/hiking-food/
```

Both must return `200`. The public HTTPS hostname also serves the OAuth-protected
MCP endpoint at `https://beebaby.tailc65f2f.ts.net/hiking-food/mcp`.

## Retired source deployment

The `deploy/remote-bootstrap.sh` script and the `deploy/hiking-food.service`
unit describe the retired source-copy deployment. They stay in the tree until
the container deployment passes one BeeBaby reboot and seven days of normal
operation, because the documented rollback path still needs them. Remove them
after that window closes.
