# Remote Chatbot MCP

## Goal

Expose Hiking Food as one OAuth-protected Streamable HTTP MCP server on BeeBaby
that supports trip creation, cloning, refinement, day allocation, and validation
from Codex, ChatGPT, and Claude.

## Deliverables

- [x] Define a compact, stable, domain-level tool surface rather than raw REST CRUD.
- [x] Add exact-path FastMCP Streamable HTTP transport under `/hiking-food/mcp`.
- [x] Add OAuth discovery, dynamic client registration, PKCE authorization,
  refresh tokens, and bearer-token enforcement.
- [x] Advertise `offline_access` for long-lived ChatGPT connectivity.
- [x] Reject duplicate destination trip names and insecure non-loopback HTTP redirects.
- [x] Invalidate stale daily assignments after duration or inventory changes.
- [x] Add OAuth-flow and end-to-end tool-workflow tests.
- [x] Document Codex, ChatGPT, and Claude setup and the canonical planning workflow.
- [ ] Publish the route through BeeBaby's HTTPS Funnel.
- [ ] Verify live OAuth discovery, authorization, `tools/list`, and a read-only tool call.
- [ ] Register and authenticate the live server in Codex.

## Verification

- `cd backend && venv/bin/pytest`
- `cd frontend && pnpm lint && pnpm build`
- Unauthenticated live `GET` and `POST` return JSON `401` plus OAuth discovery.
- Browser OAuth completes against the public path-prefixed issuer.
- A real MCP client lists the exact expected tools and calls `list_trips`.
