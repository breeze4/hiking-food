"""OAuth 2.0 authorization server for chatbot MCP clients."""
from __future__ import annotations

import hashlib
import os
import secrets
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

from fastapi import APIRouter, Body, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from mcp_oauth.tokens import (
    ACCESS_TOKEN_TTL_SECONDS, TokenError, TokenStore, issue_access_token,
    verify_password, verify_pkce_s256,
)

RESOURCE_SCOPE = "hiking-food"
OFFLINE_SCOPE = "offline_access"
SUPPORTED_SCOPES = {RESOURCE_SCOPE, OFFLINE_SCOPE}
DEFAULT_SCOPE = f"{RESOURCE_SCOPE} {OFFLINE_SCOPE}"
TEMPLATE_DIR = Path(__file__).parent / "templates"
# Absolute default anchored beside the backend package so the path is the same
# regardless of the process working directory. In prod the WorkingDirectory is
# ``backend/``, so this resolves to the same file the old ``./`` default did.
DEFAULT_AUTH_DB_PATH = Path(__file__).resolve().parent.parent / "hiking_food_auth.db"

MAX_PASSWORD_FAILURES = 5
THROTTLE_WINDOW_SECONDS = 300


class _PasswordThrottle:
    """In-process, in-memory lockout keyed by client address.

    After ``max_failures`` consecutive failures from an address, further
    attempts are rejected until ``window`` seconds pass on the injected clock.
    A success clears that address's counter.
    """

    def __init__(
        self, now: Callable[[], float],
        max_failures: int = MAX_PASSWORD_FAILURES,
        window: int = THROTTLE_WINDOW_SECONDS,
    ) -> None:
        self._now = now
        self._max = max_failures
        self._window = window
        self._state: dict[str, tuple[int, float]] = {}

    def is_locked(self, address: str) -> bool:
        entry = self._state.get(address)
        if entry is None:
            return False
        failures, locked_at = entry
        if failures < self._max:
            return False
        if self._now() - locked_at >= self._window:
            self._state.pop(address, None)
            return False
        return True

    def record_failure(self, address: str) -> None:
        failures, locked_at = self._state.get(address, (0, 0.0))
        failures += 1
        if failures >= self._max:
            locked_at = self._now()
        self._state[address] = (failures, locked_at)

    def reset(self, address: str) -> None:
        self._state.pop(address, None)


def _valid_scope(scope: str) -> bool:
    requested = set(scope.split())
    return RESOURCE_SCOPE in requested and requested <= SUPPORTED_SCOPES


def _valid_redirect_uri(uri: str) -> bool:
    parsed = urlparse(uri)
    if parsed.scheme == "https" and parsed.netloc:
        return True
    return parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}


def authorization_server_metadata(issuer: str) -> dict[str, Any]:
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/authorize",
        "token_endpoint": f"{issuer}/token",
        "registration_endpoint": f"{issuer}/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": [RESOURCE_SCOPE, OFFLINE_SCOPE],
    }


def create_router(
    *, db_path: str | None = None, issuer: str | None = None,
    now: Callable[[], float] = time.time,
) -> APIRouter:
    issuer = (issuer or os.environ.get(
        "HIKING_FOOD_OAUTH_ISSUER", "http://localhost:8000/hiking-food"
    )).rstrip("/")
    db_path = (
        db_path
        or os.environ.get("HIKING_FOOD_AUTH_DB_PATH")
        or str(DEFAULT_AUTH_DB_PATH)
    )
    store = TokenStore(db_path)
    throttle = _PasswordThrottle(now)
    templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
    router = APIRouter()

    def metadata() -> dict[str, Any]:
        return authorization_server_metadata(issuer)

    @router.get("/.well-known/oauth-authorization-server")
    def authorization_metadata() -> JSONResponse:
        return JSONResponse(metadata())

    @router.get("/.well-known/openid-configuration")
    def openid_configuration() -> JSONResponse:
        return JSONResponse(metadata())

    @router.get("/.well-known/oauth-protected-resource")
    def protected_resource_metadata() -> JSONResponse:
        return JSONResponse({
            "resource": f"{issuer}/mcp",
            "authorization_servers": [issuer],
            "scopes_supported": [RESOURCE_SCOPE, OFFLINE_SCOPE],
            "bearer_methods_supported": ["header"],
        })

    @router.post("/register")
    def register_client(metadata_in: dict[str, Any] = Body(default_factory=dict)) -> JSONResponse:
        redirect_uris = metadata_in.get("redirect_uris")
        if not isinstance(redirect_uris, list) or not redirect_uris or not all(
            isinstance(uri, str) and _valid_redirect_uri(uri) for uri in redirect_uris
        ):
            return _oauth_error(
                "invalid_client_metadata",
                "redirect_uris must contain HTTPS or loopback HTTP URLs", 400,
            )
        scope = str(metadata_in.get("scope") or DEFAULT_SCOPE)
        if not _valid_scope(scope):
            return _oauth_error("invalid_scope", scope, 400)
        client_id = f"hiking-food-{secrets.token_urlsafe(16)}"
        client_name = str(metadata_in.get("client_name") or "MCP client")
        issued_at = int(time.time())
        store.register_client(
            client_id=client_id,
            redirect_uris=redirect_uris,
            scope=scope,
            client_name=client_name,
        )
        return JSONResponse({
            "client_id": client_id,
            "client_id_issued_at": issued_at,
            "client_secret_expires_at": 0,
            "redirect_uris": redirect_uris,
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "client_name": client_name,
            "scope": scope,
        }, status_code=201)

    @router.get("/authorize", response_class=HTMLResponse)
    def authorize_get(
        request: Request, response_type: str, client_id: str, redirect_uri: str,
        code_challenge: str, code_challenge_method: str = "S256",
        scope: str = DEFAULT_SCOPE, state: str = "",
    ) -> HTMLResponse:
        if response_type != "code" or code_challenge_method != "S256" or not code_challenge:
            raise HTTPException(400, "authorization_code with PKCE S256 is required")
        if not _valid_redirect_uri(redirect_uri) or not _valid_scope(scope):
            raise HTTPException(400, "invalid redirect_uri or scope")
        if not store.client_allows(
            client_id=client_id, redirect_uri=redirect_uri, scope=scope
        ):
            raise HTTPException(400, "unknown client or unregistered redirect_uri")
        return templates.TemplateResponse(request, "authorize.html", {
            "client_id": client_id, "redirect_uri": redirect_uri, "scope": scope,
            "state": state, "code_challenge": code_challenge,
            "authorize_action": f"{issuer}/authorize", "error": None,
        })

    @router.post("/authorize")
    def authorize_post(
        request: Request, client_id: str = Form(...), redirect_uri: str = Form(...),
        code_challenge: str = Form(...), scope: str = Form(DEFAULT_SCOPE),
        state: str = Form(""), password: str = Form(...),
    ):
        if not _valid_redirect_uri(redirect_uri) or not _valid_scope(scope):
            raise HTTPException(400, "invalid redirect_uri or scope")
        if not store.client_allows(
            client_id=client_id, redirect_uri=redirect_uri, scope=scope
        ):
            raise HTTPException(400, "unknown client or unregistered redirect_uri")
        address = request.client.host if request.client else "unknown"
        if throttle.is_locked(address):
            return templates.TemplateResponse(request, "authorize.html", {
                "client_id": client_id, "redirect_uri": redirect_uri, "scope": scope,
                "state": state, "code_challenge": code_challenge,
                "authorize_action": f"{issuer}/authorize",
                "error": "Too many failed attempts. Try again later.",
            }, status_code=429)
        if not verify_password(password):
            throttle.record_failure(address)
            return templates.TemplateResponse(request, "authorize.html", {
                "client_id": client_id, "redirect_uri": redirect_uri, "scope": scope,
                "state": state, "code_challenge": code_challenge,
                "authorize_action": f"{issuer}/authorize", "error": "Incorrect password",
            }, status_code=401)
        throttle.reset(address)
        code = store.put_auth_code(
            client_id=client_id, redirect_uri=redirect_uri,
            code_challenge=code_challenge, scope=scope, sub="owner",
        )
        params = {"code": code}
        if state:
            params["state"] = state
        separator = "&" if "?" in redirect_uri else "?"
        return RedirectResponse(f"{redirect_uri}{separator}{urlencode(params)}", status_code=302)

    @router.post("/token")
    def token_endpoint(
        grant_type: str = Form(...), code: str | None = Form(None),
        redirect_uri: str | None = Form(None), client_id: str | None = Form(None),
        code_verifier: str | None = Form(None), refresh_token: str | None = Form(None),
    ) -> JSONResponse:
        if grant_type == "authorization_code":
            if not (code and redirect_uri and client_id and code_verifier):
                return _oauth_error("invalid_request", "missing required parameter", 400)
            try:
                record = store.consume_auth_code(code)
            except TokenError as exc:
                return _oauth_error("invalid_grant", str(exc), 400)
            if record.redirect_uri != redirect_uri or record.client_id != client_id:
                return _oauth_error("invalid_grant", "client or redirect mismatch", 400)
            if not verify_pkce_s256(code_verifier, record.code_challenge):
                return _oauth_error("invalid_grant", "PKCE verification failed", 400)
            refresh = store.put_refresh_token(sub=record.sub, scope=record.scope)
            access = issue_access_token(
                sub=record.sub,
                scope=record.scope,
                refresh_id=hashlib.sha256(refresh.encode("ascii")).hexdigest()[:8],
            )
            return _token_response(access, refresh, record.scope)
        if grant_type == "refresh_token":
            if not refresh_token:
                return _oauth_error("invalid_request", "refresh_token required", 400)
            try:
                sub, scope, replacement = store.rotate_refresh_token(refresh_token)
            except TokenError as exc:
                return _oauth_error("invalid_grant", str(exc), 400)
            access = issue_access_token(
                sub=sub,
                scope=scope,
                refresh_id=hashlib.sha256(replacement.encode("ascii")).hexdigest()[:8],
            )
            return _token_response(access, replacement, scope)
        return _oauth_error("unsupported_grant_type", grant_type, 400)

    return router


def _token_response(access: str, refresh: str, scope: str) -> JSONResponse:
    return JSONResponse({
        "access_token": access, "token_type": "Bearer",
        "expires_in": ACCESS_TOKEN_TTL_SECONDS, "refresh_token": refresh, "scope": scope,
    })


def _oauth_error(code: str, description: str, status: int) -> JSONResponse:
    return JSONResponse(
        {"error": code, "error_description": description}, status_code=status
    )
