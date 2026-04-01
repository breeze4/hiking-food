Dev: `cd backend && uvicorn main:app --reload` + `cd frontend && npm run dev` (Vite proxies /api to :8000)
Test: `cd backend && venv/bin/pytest`
Deploy: `./deploy/deploy.sh` (rsyncs to beebaby, builds, restarts service)
Access: `http://beebaby:8000`
