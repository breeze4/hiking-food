# Hiking Food Planner

A mobile-friendly web app for planning backpacking trip food. Replaces a spreadsheet workflow with better UX for browsing ingredients, building recipes, selecting snacks, and tracking weight/calorie targets.

Based on [Andrew Skurka's meal planning method](https://andrewskurka.com/).

## Features

- **Ingredient database** — shared source of truth with cal/oz and macros
- **Recipe library** — breakfast/dinner recipes with at-home and field prep instructions
- **Snack catalog** — ingredients wrapped with serving sizes for trip planning
- **Trip planner** — configurable oz/day and cal/oz targets (Skurka method), meal and snack selection, weight/calorie progress tracking
- **Daily plan** — per-day food breakdown with macronutrient targets
- **Packing checklist** — track what's packed for each trip

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, SQLite
- **Frontend**: React, Vite, Tailwind CSS, shadcn/ui
- **Hosting**: Self-hosted on a Linux mini PC, with HTTPS ingress for remote chatbot clients
- **Web app auth**: Tailscale network access
- **Chatbot auth**: OAuth 2.0 authorization code + PKCE for the remote MCP endpoint

## Development

Start the backend:

```sh
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Start the frontend (Vite proxies `/api` to `:8000`):

```sh
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

Run tests:

```sh
cd backend
venv/bin/pytest
```

Python 3.10 or newer is required because the backend includes the official Python MCP SDK.

## Chatbot MCP

The deployed Streamable HTTP MCP endpoint is:

```text
https://beebaby.tailc65f2f.ts.net/hiking-food/mcp
```

It exposes a compact tool set for listing and reading trips, creating or cloning
plans, changing trip targets and food quantities, regenerating the daily plan,
and moving individual daily assignments. See
[`docs/agents/hiking-food-mcp.md`](docs/agents/hiking-food-mcp.md) for client setup,
tool semantics, and the safe planning workflow.

The live endpoint and OAuth flow have been verified with Codex and a custom
ChatGPT plugin. Claude can use the same remote MCP URL and OAuth contract.

## Deploy

Deploys run automatically through cicd-router on each commit to `main` (see `cicd-router.project.yml`); there is no manual deploy script.
