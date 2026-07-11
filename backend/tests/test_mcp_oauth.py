import base64
import hashlib
from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_oauth.app import create_router
from mcp_oauth.auth import BearerAuthMiddleware


def _challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


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
    assert refreshed.json()["refresh_token"] == refresh


def test_registration_rejects_insecure_non_loopback_redirect(tmp_path):
    app = FastAPI()
    app.include_router(create_router(db_path=str(tmp_path / "auth.db")))
    response = TestClient(app).post("/register", json={
        "redirect_uris": ["http://attacker.example/callback"],
    })
    assert response.status_code == 400


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
