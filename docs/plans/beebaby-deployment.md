# Deployment Plan: Run hiking-food on beebaby

## Context
The hiking-food app (FastAPI + React + Vite + SQLite) needs to run on "beebaby", a Linux mini PC accessible via Tailscale. The app should auto-start on boot via systemd, with FastAPI serving both the API and the built React static files on a single port. Deployment is via git pull (beebaby is not internet-exposed, only reachable via Tailscale).

## Architecture
```
beebaby (Linux mini PC, Tailscale)
  └── /opt/hiking-food/              # cloned repo
       ├── backend/
       │   ├── main.py               # FastAPI serves API + static frontend
       │   └── hiking_food.db        # SQLite data
       ├── frontend/
       │   └── dist/                  # built React static files
       └── deploy/
            ├── deploy.sh             # pull + build + restart script
            ├── setup.sh              # one-time setup script
            └── hiking-food.service   # systemd unit file
```

Single process: uvicorn runs FastAPI, which serves `/api/*` routes and falls back to serving `frontend/dist/` for everything else (React SPA).

## Plan

### Step 1: Add production static file serving to FastAPI
**File: `backend/main.py`**
- After all API routers are mounted, add a `StaticFiles` mount for `../frontend/dist` at `/`
- Use a fallback to `index.html` for SPA client-side routing
- Only mount if the dist directory exists (skip in dev when Vite proxy handles it)

### Step 2: Add production build config to frontend
**File: `frontend/vite.config.js`**
- Ensure `build.outDir` is `dist` (default, just verify)
- No base path change needed (served from root)

### Step 3: Create systemd unit file
**File: `deploy/hiking-food.service`**
```
[Unit]
Description=Hiking Food Planner
After=network.target

[Service]
Type=simple
User=breeze
WorkingDirectory=/opt/hiking-food/backend
ExecStart=/opt/hiking-food/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

### Step 4: Create deploy script
**File: `deploy/deploy.sh`**
Does everything needed to update and restart the app on beebaby:
1. `cd /opt/hiking-food && git pull`
2. `cd backend && venv/bin/pip install -r requirements.txt`
3. `cd ../frontend && npm install && npm run build`
4. `sudo systemctl restart hiking-food`

### Step 5: Create initial setup script
**File: `deploy/setup.sh`**
One-time setup on beebaby:
1. Clone repo to `/opt/hiking-food`
2. Create Python venv, install deps
3. Install Node deps, build frontend
4. Copy systemd unit file to `/etc/systemd/system/`
5. Enable and start the service
6. Print the Tailscale URL

### Step 6: Add .gitignore entries
- `frontend/dist/` (build output, not committed)

### Step 7: Update SPEC.md
Add a "Deployment" section documenting how to set up, deploy, and manage the service.

## Verification
- `npm run build` in frontend/ produces `dist/` with index.html
- `uvicorn main:app --host 0.0.0.0 --port 8000` serves both API and frontend
- Hitting `http://beebaby:8000/` loads the React app
- Hitting `http://beebaby:8000/api/health` returns health check JSON
- `systemctl status hiking-food` shows active/running
- After reboot, service starts automatically
- `deploy/deploy.sh` pulls, rebuilds, and restarts cleanly

## Files to Create/Modify
- `backend/main.py` — add static file serving for production
- `deploy/hiking-food.service` — new, systemd unit
- `deploy/deploy.sh` — new, update + restart script
- `deploy/setup.sh` — new, one-time setup script
- `docs/SPEC.md` — add Deployment section
