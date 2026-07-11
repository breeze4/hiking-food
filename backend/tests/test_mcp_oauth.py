import base64
import hashlib
import sqlite3
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_oauth.app import create_router
from mcp_oauth.auth import BearerAuthMiddleware
from mcp_oauth.tokens import TokenError, TokenStore


def _challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class _FakeClock:
    """Deterministic, advanceable clock for throttle-window tests."""

    def __init__(self, start: float = 1_000.0) -> None:
        self.value = start

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def _throttle_app(tmp_path, monkeypatch, clock):
    issuer = "https://food.example.test/hiking-food"
    monkeypatch.setenv("HIKING_FOOD_OAUTH_ISSUER", issuer)
    monkeypatch.setenv("HIKING_FOOD_AUTH_PASSWORD", "correct horse")
    monkeypatch.setenv("HIKING_FOOD_JWT_KEY", "0123456789abcdef0123456789abcdef")
    app = FastAPI()
    app.include_router(
        create_router(db_path=str(tmp_path / "auth.db"), issuer=issuer, now=clock)
    )
    redirect_uri = "https://claude.ai/api/mcp/auth_callback"
    registration = TestClient(app).post("/register", json={"redirect_uris": [redirect_uri]})
    client_id = registration.json()["client_id"]
    base = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": _challenge("a" * 48),
        "scope": "hiking-food offline_access",
        "state": "",
    }
    good = {**base, "password": "correct horse"}
    bad = {**base, "password": "wrong"}
    return app, good, bad


def test_password_failures_are_throttled_per_address(tmp_path, monkeypatch):
    clock = _FakeClock()
    app, good, bad = _throttle_app(tmp_path, monkeypatch, clock)
    attacker = TestClient(app, client=("10.0.0.9", 5555))

    for _ in range(5):
        rejected = attacker.post("/authorize", data=bad, follow_redirects=False)
        assert rejected.status_code == 401

    throttled = attacker.post("/authorize", data=bad, follow_redirects=False)
    assert throttled.status_code == 429
    # Even a correct password is refused while the address is locked out.
    still_locked = attacker.post("/authorize", data=good, follow_redirects=False)
    assert still_locked.status_code == 429

    # A different client address is unaffected by the lockout.
    other = TestClient(app, client=("10.0.0.10", 6666))
    unaffected = other.post("/authorize", data=good, follow_redirects=False)
    assert unaffected.status_code == 302

    # The window expires after five minutes on the injected clock.
    clock.advance(300)
    recovered = attacker.post("/authorize", data=good, follow_redirects=False)
    assert recovered.status_code == 302


def test_successful_authorization_resets_failure_counter(tmp_path, monkeypatch):
    clock = _FakeClock()
    app, good, bad = _throttle_app(tmp_path, monkeypatch, clock)
    client = TestClient(app, client=("10.0.0.11", 7777))

    for _ in range(4):
        assert client.post("/authorize", data=bad, follow_redirects=False).status_code == 401

    # A success clears the four accumulated failures.
    assert client.post("/authorize", data=good, follow_redirects=False).status_code == 302

    # Four fresh failures are still below the threshold, so no lockout yet.
    for _ in range(4):
        assert client.post("/authorize", data=bad, follow_redirects=False).status_code == 401
    assert client.post("/authorize", data=good, follow_redirects=False).status_code == 302


def test_discovery_drops_oidc_and_jwks_and_advertises_only_supported(tmp_path, monkeypatch):
    issuer = "https://food.example.test/hiking-food"
    monkeypatch.setenv("HIKING_FOOD_OAUTH_ISSUER", issuer)
    app = FastAPI()
    app.include_router(create_router(db_path=str(tmp_path / "auth.db"), issuer=issuer))
    client = TestClient(app)

    assert client.get("/.well-known/openid-configuration").status_code == 404
    assert client.get("/jwks").status_code == 404

    metadata = client.get("/.well-known/oauth-authorization-server").json()
    assert metadata["response_types_supported"] == ["code"]
    assert metadata["grant_types_supported"] == ["authorization_code", "refresh_token"]
    assert metadata["code_challenge_methods_supported"] == ["S256"]
    assert metadata["token_endpoint_auth_methods_supported"] == ["none"]
    assert set(metadata["scopes_supported"]) == {"hiking-food", "offline_access"}
    assert "jwks_uri" not in metadata
    assert "id_token_signing_alg_values_supported" not in metadata


def test_oauth_metadata_registration_code_and_refresh_flow(tmp_path, monkeypatch):
    issuer = "https://food.example.test/hiking-food"
    monkeypatch.setenv("HIKING_FOOD_OAUTH_ISSUER", issuer)
    monkeypatch.setenv("HIKING_FOOD_AUTH_PASSWORD", "correct horse")
    monkeypatch.setenv("HIKING_FOOD_JWT_KEY", "0123456789abcdef0123456789abcdef")
    app = FastAPI()
    app.include_router(create_router(db_path=str(tmp_path / "auth.db"), issuer=issuer))
    client = TestClient(app)

    metadata = client.get("/.well-known/oauth-authorization-server").json()
    assert metadata["issuer"] == issuer
    assert metadata["registration_endpoint"] == f"{issuer}/register"
    assert "offline_access" in metadata["scopes_supported"]
    protected = client.get("/.well-known/oauth-protected-resource").json()
    assert protected["resource"] == f"{issuer}/mcp"

    registration = client.post("/register", json={
        "client_name": "Claude",
        "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"],
        "scope": "hiking-food offline_access",
    })
    assert registration.status_code == 201
    client_id = registration.json()["client_id"]

    verifier = "a" * 48
    params = {
        "response_type": "code", "client_id": client_id,
        "redirect_uri": "https://claude.ai/api/mcp/auth_callback",
        "code_challenge": _challenge(verifier), "code_challenge_method": "S256",
        "scope": "hiking-food offline_access", "state": "state-1",
    }
    form = client.get("/authorize", params=params)
    assert form.status_code == 200
    assert f'action="{issuer}/authorize"' in form.text

    authorized = client.post("/authorize", data={
        **params, "password": "correct horse",
    }, follow_redirects=False)
    assert authorized.status_code == 302
    query = parse_qs(urlparse(authorized.headers["location"]).query)
    assert query["state"] == ["state-1"]

    tokens = client.post("/token", data={
        "grant_type": "authorization_code", "code": query["code"][0],
        "redirect_uri": params["redirect_uri"], "client_id": client_id,
        "code_verifier": verifier,
    })
    assert tokens.status_code == 200
    assert tokens.json()["scope"] == "hiking-food offline_access"
    refresh = tokens.json()["refresh_token"]

    refreshed = client.post("/token", data={
        "grant_type": "refresh_token", "refresh_token": refresh,
    })
    assert refreshed.status_code == 200
    rotated_refresh = refreshed.json()["refresh_token"]
    assert rotated_refresh != refresh

    replay = client.post("/token", data={
        "grant_type": "refresh_token", "refresh_token": refresh,
    })
    assert replay.status_code == 400
    assert replay.json()["error"] == "invalid_grant"


def test_registration_rejects_insecure_non_loopback_redirect(tmp_path):
    app = FastAPI()
    app.include_router(create_router(db_path=str(tmp_path / "auth.db")))
    response = TestClient(app).post("/register", json={
        "redirect_uris": ["http://attacker.example/callback"],
    })
    assert response.status_code == 400


def test_authorization_rejects_unknown_client(tmp_path):
    app = FastAPI()
    app.include_router(create_router(db_path=str(tmp_path / "auth.db")))

    response = TestClient(app).get("/authorize", params={
        "response_type": "code",
        "client_id": "not-registered",
        "redirect_uri": "https://example.test/callback",
        "code_challenge": _challenge("a" * 48),
        "code_challenge_method": "S256",
        "scope": "hiking-food offline_access",
    })

    assert response.status_code == 400
    assert response.json()["detail"] == "unknown client or unregistered redirect_uri"


def test_registered_client_survives_restart_and_only_uses_exact_redirect(tmp_path):
    db_path = str(tmp_path / "auth.db")
    registration_app = FastAPI()
    registration_app.include_router(create_router(db_path=db_path))
    registration = TestClient(registration_app).post("/register", json={
        "redirect_uris": ["https://example.test/callback"],
    })
    client_id = registration.json()["client_id"]

    restarted_app = FastAPI()
    restarted_app.include_router(create_router(db_path=db_path))
    restarted = TestClient(restarted_app)
    base_params = {
        "response_type": "code",
        "client_id": client_id,
        "code_challenge": _challenge("a" * 48),
        "code_challenge_method": "S256",
        "scope": "hiking-food offline_access",
    }

    allowed = restarted.get("/authorize", params={
        **base_params, "redirect_uri": "https://example.test/callback",
    })
    rejected = restarted.get("/authorize", params={
        **base_params, "redirect_uri": "https://example.test/other",
    })

    assert allowed.status_code == 200
    assert rejected.status_code == 400


def test_refresh_token_bearer_secret_is_never_persisted(tmp_path):
    db_path = tmp_path / "auth.db"
    store = TokenStore(db_path)

    refresh = store.put_refresh_token(
        sub="owner", scope="hiking-food offline_access"
    )

    with sqlite3.connect(db_path) as conn:
        columns = [row[1] for row in conn.execute(
            "PRAGMA table_info(refresh_tokens)"
        )]
        persisted = conn.execute(
            "SELECT token_hash FROM refresh_tokens"
        ).fetchone()[0]
    assert columns[0] == "token_hash"
    assert persisted == hashlib.sha256(refresh.encode("ascii")).hexdigest()
    assert persisted != refresh


def test_existing_refresh_token_survives_plaintext_storage_upgrade(tmp_path):
    db_path = tmp_path / "auth.db"
    legacy_refresh = "legacy-refresh-secret"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """CREATE TABLE refresh_tokens (
                token TEXT PRIMARY KEY,
                sub TEXT NOT NULL,
                scope TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )"""
        )
        conn.execute(
            "INSERT INTO refresh_tokens VALUES (?,?,?,?,?)",
            (legacy_refresh, "owner", "hiking-food offline_access", 4_102_444_800, 1),
        )

    store = TokenStore(db_path)
    sub, scope, replacement = store.rotate_refresh_token(legacy_refresh)

    assert (sub, scope) == ("owner", "hiking-food offline_access")
    assert replacement != legacy_refresh
    with pytest.raises(TokenError, match="unknown refresh token"):
        store.rotate_refresh_token(legacy_refresh)


def test_unauthorized_mcp_response_has_discovery_challenge(monkeypatch):
    monkeypatch.setenv("HIKING_FOOD_OAUTH_ISSUER", "https://food.example/hiking-food")

    async def inner(scope, receive, send):  # pragma: no cover - must not be called
        raise AssertionError("unauthorized request reached MCP")

    app = FastAPI()
    app.mount("/mcp", BearerAuthMiddleware(inner))
    response = TestClient(app).get("/mcp")
    assert response.status_code == 401
    assert "resource_metadata=" in response.headers["www-authenticate"]
    assert "hiking-food/.well-known/oauth-protected-resource" in response.headers["www-authenticate"]
