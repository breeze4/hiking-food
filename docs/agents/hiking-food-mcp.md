# Hiking Food MCP

## Purpose

The Hiking Food MCP is the stable conversational interface for creating and
refining trip food plans from Codex, ChatGPT, Claude, or another remote MCP
client. It intentionally exposes planning operations rather than the app's raw
REST CRUD surface.

Public Streamable HTTP endpoint:

```text
https://beebaby.tailc65f2f.ts.net/hiking-food/mcp
```

Local BeeBaby endpoint for diagnostics:

```text
http://beebaby:8000/hiking-food/mcp
```

## Golden workflow

1. Call `list_trips` and check whether the destination already exists.
2. Call `get_trip_plan(section="overview")` for the intended source and any
   existing destination.
3. Prefer `clone_trip` when a relevant previous plan exists; use `create_trip`
   only for a genuinely blank plan.
4. Use `update_trip`, `set_trip_meal_quantity`, and
   `set_trip_snack_servings` for targeted changes.
5. Call `auto_fill_daily_plan` after inventory or trip-shape changes.
6. Validate with `get_trip_plan(section="overview")` and
   `get_trip_plan(section="daily_plan")`. Check targets, warnings, and the
   unallocated summary.
7. Use `update_daily_assignment` only for deliberate per-day corrections.
8. Read `packing` or `shopping` only when preparing the final handoff; those
   sections are larger.

The write tools reject duplicate trip names. Trip duration and inventory
changes clear existing daily assignments so stale allocations cannot masquerade
as a valid plan.

## Tool contract

| Tool | Effect |
|---|---|
| `list_trips` | Read trip identities and duration shapes |
| `get_trip_plan` | Read overview, daily plan, packing, shopping, or all sections |
| `list_food_options` | Read recipe and snack choices with optional filters |
| `create_trip` | Create a uniquely named empty trip |
| `clone_trip` | Copy a source trip into a uniquely named destination |
| `update_trip` | Change identity, duration, drink-mix target, or calorie/weight targets |
| `set_trip_meal_quantity` | Add, update, or remove a recipe by semantic recipe ID |
| `set_trip_snack_servings` | Add, update, or remove a snack by semantic catalog ID |
| `auto_fill_daily_plan` | Regenerate all day assignments |
| `update_daily_assignment` | Move, resize, or remove one daily assignment |

Tool names and required inputs should remain backward compatible. ChatGPT may
retain an approved snapshot of the tool schema; breaking schema changes require
refreshing or republishing the app.

## OAuth contract

The issuer is:

```text
https://beebaby.tailc65f2f.ts.net/hiking-food
```

Discovery endpoints are below that path prefix:

- `/.well-known/oauth-protected-resource`
- `/.well-known/oauth-authorization-server`
- `/.well-known/openid-configuration`

The server supports dynamic client registration, authorization code with PKCE
S256, one-hour access tokens, refresh tokens, and the `hiking-food` plus
`offline_access` scopes. HTTPS and loopback HTTP redirect URIs are accepted;
arbitrary insecure HTTP callbacks are rejected.

Production secrets live only on BeeBaby in
`~/.config/hiking-food/mcp.env`. Never commit, print, or copy that file into a
chat. The systemd unit reads it through `EnvironmentFile`.

## Connect clients

### Codex app

```sh
codex mcp add hiking-food \
  --url https://beebaby.tailc65f2f.ts.net/hiking-food/mcp \
  --oauth-resource https://beebaby.tailc65f2f.ts.net/hiking-food/mcp
codex mcp login hiking-food --scopes hiking-food
codex mcp get hiking-food --json
```

Open a fresh Codex task or refresh the app after login so the new tools are
injected into the task.

### ChatGPT

In the Plugins directory, choose **Create app** and enter:

- Name: `Hiking Food`
- Description: `Create, clone, review, and adjust backpacking trip food plans.`
- Connection: `Server URL`
- MCP Server URL: `https://beebaby.tailc65f2f.ts.net/hiking-food/mcp`
- Authentication: `OAuth`

Accept the unreviewed-server warning, create the plugin, and authorize it with
the same single-user password used by the Brain MCP. Test a read with "list my
hiking food trips" before approving a write. Write/modify MCP actions depend on
the ChatGPT plan and workspace controls.

A useful first planning prompt is:

```text
Use the Hiking Food plugin. First list my existing trips. Before making changes,
confirm the source trip and whether the destination already exists. After any
changes, regenerate the daily plan and verify unallocated food, daily calories,
total calories, and total weight. Finish by summarizing what changed.
```

### Claude

Open Settings → Connectors → Add custom connector, name it `Hiking Food`, enter
the public endpoint, then connect and complete OAuth. Claude supports
Streamable HTTP, dynamic client registration, refresh tokens, and remote write
tools. Start with `list_trips` before enabling or approving write tools.

## Local verification

Set non-production test values for the three required environment variables:

- `HIKING_FOOD_OAUTH_ISSUER`
- `HIKING_FOOD_AUTH_PASSWORD`
- `HIKING_FOOD_JWT_KEY` (at least 32 bytes)

Then run:

```sh
cd backend
venv/bin/pytest tests/test_mcp_oauth.py tests/test_mcp_tools.py
```

For protocol verification, first confirm unauthenticated `GET` and `POST`
requests to the exact MCP URL return JSON `401` responses with a
`WWW-Authenticate` discovery challenge. Complete OAuth, then verify
`initialize`, `tools/list`, and a harmless `list_trips` call through an actual
client.
