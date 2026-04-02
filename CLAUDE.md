Dev: `cd backend && uvicorn main:app --reload` + `cd frontend && npm run dev` (Vite proxies /api to :8000)
Test: `cd backend && venv/bin/pytest`
Deploy: `./deploy/deploy.sh` (rsyncs to beebaby, builds, restarts service) — ask before deploying
Access: `http://beebaby:8000`

## Plans

All implementation plans live in `docs/plans/` with an index at `docs/plans/INDEX.md`.

When you complete a plan or change its status, update `docs/plans/INDEX.md`:
- Move the plan between the Completed / In Progress / Not Started sections
- Keep the table format consistent
- Do this in the same commit as the plan file changes
