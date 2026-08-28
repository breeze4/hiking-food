Dev: `cd backend && uvicorn main:app --reload` + `cd frontend && pnpm dev` (Vite proxies /api to :8000)
Test: `cd backend && venv/bin/pytest`
Frontend checks: `cd frontend && pnpm lint && pnpm build`
Deploy: commit to `main`. The Factory runner publishes the exact commit and
records its deployment.
The `factory.project.yml` file is the active contract.
Factory runs `scripts/cicd-router-gates.sh` as the project gate.
The `cicd-router.project.yml` file is audit data only.
Do not use a direct deployment script.
Access: `http://beebaby:8000/hiking-food/`
Chatbot MCP: read `docs/agents/hiking-food-mcp.md` before planning trips through MCP.

## Plans

All implementation plans live in `docs/plans/` with an index at `docs/plans/INDEX.md`.

When you complete a plan or change its status, update `docs/plans/INDEX.md`:
- Move the plan between the Completed / In Progress / Not Started sections
- Keep the table format consistent
- Do this in the same commit as the plan file changes
