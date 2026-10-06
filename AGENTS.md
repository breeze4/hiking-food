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

<!-- cos:managed-project:start -->
## Reading copy

This section applies only when the file `.cos/reading-copy` exists in this checkout. If that file doesn't exist, ignore this section.

When `.cos/reading-copy` exists:

- This checkout is a reading copy of the project `hiking-food`, which the chief of staff owns on beebaby.
- The git hooks in this checkout reject every commit and push.
- To change the project, ask the chief of staff. Or run `cos eject hiking-food` here, make the change, and run `cos migrate hiking-food` when you finish.
<!-- cos:managed-project:end -->
