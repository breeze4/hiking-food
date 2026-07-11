"""Bearer-token gate for the Hiking Food MCP transport."""
from __future__ import annotations

import os
from typing import Any, Awaitable, Callable

from mcp_oauth.tokens import TokenError, validate_access_token

DEFAULT_SCOPE = "hiking-food"


class UnauthorizedError(Exception):
    pass


def validate_bearer(header: str | None) -> dict:
    if not header:
        raise UnauthorizedError("missing bearer token")
    parts = header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        raise UnauthorizedError("malformed authorization header")
    try:
        claims = validate_access_token(parts[1])
    except TokenError as exc:
        raise UnauthorizedError("invalid or expired token") from exc
    if DEFAULT_SCOPE not in str(claims.get("scope", "")).split():
        raise UnauthorizedError("required scope missing")
    return claims


Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]


class BearerAuthMiddleware:
    def __init__(self, app: Callable[[Scope, Receive, Send], Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        try:
            scope["auth_claims"] = validate_bearer(headers.get("authorization"))
        except UnauthorizedError as exc:
            await _send_401(send, str(exc))
            return
        await self.app(scope, receive, send)


async def _send_401(send: Send, description: str) -> None:
    issuer = os.environ.get(
        "HIKING_FOOD_OAUTH_ISSUER", "http://localhost:8000/hiking-food"
    ).rstrip("/")
    safe = description.replace("\\", "\\\\").replace('"', '\\"')
    body = f'{{"error":"invalid_token","error_description":"{safe}"}}'.encode()
    challenge = (
        f'Bearer error="invalid_token", error_description="{safe}", '
        f'resource_metadata="{issuer}/.well-known/oauth-protected-resource", '
        f'scope="{DEFAULT_SCOPE}"'
    )
    await send({
        "type": "http.response.start", "status": 401,
        "headers": [
            (b"content-type", b"application/json"),
            (b"www-authenticate", challenge.encode("latin-1")),
            (b"content-length", str(len(body)).encode("ascii")),
        ],
    })
    await send({"type": "http.response.body", "body": body})
