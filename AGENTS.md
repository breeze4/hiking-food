Dev: `cd backend && uvicorn main:app --reload` + `cd frontend && pnpm dev` (Vite proxies /api to :8000)
Test: `cd backend && venv/bin/pytest`
Frontend checks: `cd frontend && pnpm lint && pnpm build`
Deploy: commit to `main`. Woodpecker checks the exact commit, publishes its
container image, and deploys that image to BeeBaby.
The `.woodpecker/` workflows are the active contract.
The check workflow runs `scripts/ci-gates.sh` as the project gate.
Read `docs/deployment.md` for the deploy, rollback, and verification path.
Do not use a direct deployment script.
Access: `http://beebaby:8000/hiking-food/`
Chatbot MCP: read `docs/agents/hiking-food-mcp.md` before planning trips through MCP.

## Plans

All implementation plans live in `docs/plans/` with an index at `docs/plans/INDEX.md`.

When you complete a plan or change its status, update `docs/plans/INDEX.md`:
- Move the plan between the Completed / In Progress / Not Started sections
- Keep the table format consistent
- Do this in the same commit as the plan file changes
