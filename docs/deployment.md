# Deploy Hiking Food

Woodpecker on BeeBaby builds, publishes, and deploys this repository. Factory no
longer participates.

## What happens on a pull request and on main

The workflows come from the BeeBaby CI template. To stamp them again, run
`scripts/stamp-ci.py hiking-food . --image hiking-food,Dockerfile` from
`beebaby-infra`. The command doesn't overwrite a file that exists.

Pull requests and pushes to `main` run the same two workflows:

1. `.woodpecker/check.yaml` runs `scripts/ci-gates.sh all` in the shared CI
   image. The gate checks that no non-plugin step reads `ghcr_token`, then runs
   the backend pytest suite and the frontend tests, lint, and build.
2. `.woodpecker/build-image.yaml` builds the runtime image with no secret and
   pushes nothing, so a broken image build fails the pull request.

A push to `main` then runs two more workflows:

1. `.woodpecker/publish.yaml` waits for `check` and `build-image`, builds the
   image again, and pushes it to `ghcr.io/breeze4/hiking-food` with the commit
   SHA as its tag. Its `publish-image` step is the only step that reads
   `ghcr_token`.
2. `.woodpecker/deploy.yaml` follows `publish` and calls the restricted
   deployment command on BeeBaby with that tag. The host resolves the tag to
   its immutable digest with its own registry credentials.

Deployment secrets stay out of pull request pipelines.

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
HIKING_FOOD_ENV_FILE=/srv/beebaby/secrets/runtime/hiking-food.env
```

The data directory holds `hiking_food.db`, `hiking_food_auth.db`, their SQLite
journal files, and migration backups. It must have UID and GID `1000`. Keep the
data directory and the environment file outside the image and this repository.

`secret-names.yaml` at the repository root lists the names that the environment
file holds. The file holds names only. The values live in the BeeBaby store at
`/srv/beebaby/secrets/store/hiking-food/`. The list names these variables:

- `HIKING_FOOD_AUTH_PASSWORD`: the single-user authorization password.
- `HIKING_FOOD_JWT_KEY`: the access-token signing key, at least 32 bytes.
- `HIKING_FOOD_OAUTH_ISSUER`: the public OAuth issuer and path prefix. This
  value isn't secret, but it stays on the list so that the environment file
  keeps it when `beebaby-deploy` writes that file from the store.

When you add a variable that the deployed service needs, add its name to
`secret-names.yaml` and its value to the store with `cos secrets` in the same
change.

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
