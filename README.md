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
- **Hosting**: Self-hosted on a Linux mini PC, accessed via Tailscale
- **Auth**: None (Tailscale network handles access)

## Development

Start the backend:

```sh
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Start the frontend (Vite proxies `/api` to `:8000`):

```sh
cd frontend
npm install
npm run dev
```

Run tests:

```sh
cd backend
venv/bin/pytest
```

## Deploy

```sh
./deploy/deploy.sh
```

Rsyncs to the host, builds the frontend, and restarts the service.
