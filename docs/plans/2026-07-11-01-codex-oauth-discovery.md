# Codex OAuth Discovery Compatibility

## Problem

Codex native MCP login for the deployed BeeBaby `hiking-food` server fails with
`Dynamic client registration not supported` even though ChatGPT OAuth setup works
and `/hiking-food/register` accepts dynamic registration.

Direct BeeBaby checks showed the path-prefixed Hiking Food metadata is valid, but
Codex also probes OpenID and root well-known discovery paths for path-mounted
issuers. The root `/.well-known/oauth-authorization-server` on the shared
BeeBaby host currently returns Brain OAuth metadata, so Codex can conclude the
Hiking Food authorization server has no registration endpoint.

## Tasks

- [x] Add regression tests for the Codex discovery paths:
  `/hiking-food/.well-known/openid-configuration`,
  `/.well-known/oauth-authorization-server/hiking-food`, and
  `/.well-known/openid-configuration/hiking-food`.
- [x] Serve Hiking Food authorization-server metadata from those compatibility
  paths while keeping `/jwks` removed and leaving authorization, token,
  registration, and MCP paths under `/hiking-food`.
- [x] Update the OAuth contract docs to explain the Codex path-mounted issuer
  discovery aliases.
- [ ] Verify backend OAuth tests and a direct BeeBaby `codex mcp login
  hiking-food --scopes hiking-food` after deployment.

## Done when

- Codex native login reaches the Hiking Food authorization page from the real
  BeeBaby URL, not localhost.
- The MCP server starts in a fresh Codex session without the OAuth startup error.
- ChatGPT-compatible OAuth endpoints remain unchanged.
