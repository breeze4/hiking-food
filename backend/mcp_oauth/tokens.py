"""Single-user OAuth token issuance and persistent refresh-token storage."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

import jwt

ACCESS_TOKEN_TTL_SECONDS = 3600
REFRESH_TOKEN_TTL_SECONDS = 90 * 24 * 3600
AUTH_CODE_TTL_SECONDS = 300
JWT_ALGORITHM = "HS256"


class TokenError(Exception):
    """Raised when an OAuth token or authorization code is invalid."""


def _now() -> int:
    return int(time.time())


def _random_token() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("ascii")


def verify_pkce_s256(code_verifier: str, code_challenge: str) -> bool:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return hmac.compare_digest(expected, code_challenge)


@dataclass(frozen=True)
class AuthCodeRecord:
    code: str
    client_id: str
    redirect_uri: str
    code_challenge: str
    scope: str
    sub: str
    expires_at: int


class TokenStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, isolation_level=None, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS auth_codes (
                  code TEXT PRIMARY KEY,
                  client_id TEXT NOT NULL,
                  redirect_uri TEXT NOT NULL,
                  code_challenge TEXT NOT NULL,
                  scope TEXT NOT NULL,
                  sub TEXT NOT NULL,
                  expires_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS refresh_tokens (
                  token TEXT PRIMARY KEY,
                  sub TEXT NOT NULL,
                  scope TEXT NOT NULL,
                  expires_at INTEGER NOT NULL,
                  created_at INTEGER NOT NULL
                );
                """
            )

    def put_auth_code(
        self, *, client_id: str, redirect_uri: str, code_challenge: str,
        scope: str, sub: str,
    ) -> str:
        code = _random_token()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO auth_codes VALUES (?,?,?,?,?,?,?)",
                (code, client_id, redirect_uri, code_challenge, scope, sub,
                 _now() + AUTH_CODE_TTL_SECONDS),
            )
        return code

    def consume_auth_code(self, code: str) -> AuthCodeRecord:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT code, client_id, redirect_uri, code_challenge, scope, sub, expires_at "
                "FROM auth_codes WHERE code = ?", (code,),
            ).fetchone()
            if row is None:
                raise TokenError("unknown authorization code")
            conn.execute("DELETE FROM auth_codes WHERE code = ?", (code,))
        record = AuthCodeRecord(*row)
        if record.expires_at < _now():
            raise TokenError("authorization code expired")
        return record

    def put_refresh_token(self, *, sub: str, scope: str) -> str:
        token = _random_token()
        now = _now()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO refresh_tokens VALUES (?,?,?,?,?)",
                (token, sub, scope, now + REFRESH_TOKEN_TTL_SECONDS, now),
            )
        return token

    def lookup_refresh_token(self, token: str) -> tuple[str, str]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT sub, scope, expires_at FROM refresh_tokens WHERE token = ?", (token,),
            ).fetchone()
        if row is None:
            raise TokenError("unknown refresh token")
        sub, scope, expires_at = row
        if expires_at < _now():
            raise TokenError("refresh token expired")
        return sub, scope


def _jwt_key() -> str:
    key = os.environ.get("HIKING_FOOD_JWT_KEY", "")
    if len(key) < 32:
        raise RuntimeError("HIKING_FOOD_JWT_KEY must be at least 32 bytes")
    return key


def _issuer() -> str:
    return os.environ.get(
        "HIKING_FOOD_OAUTH_ISSUER", "http://localhost:8000/hiking-food"
    ).rstrip("/")


def issue_access_token(*, sub: str, scope: str, refresh_id: str = "") -> str:
    now = _now()
    issuer = _issuer()
    return jwt.encode(
        {
            "sub": sub, "iat": now, "exp": now + ACCESS_TOKEN_TTL_SECONDS,
            "scope": scope, "refresh_id": refresh_id,
            "iss": issuer, "aud": f"{issuer}/mcp",
        },
        _jwt_key(), algorithm=JWT_ALGORITHM,
    )


def validate_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token, _jwt_key(), algorithms=[JWT_ALGORITHM],
            issuer=_issuer(), audience=f"{_issuer()}/mcp",
        )
    except jwt.PyJWTError as exc:
        raise TokenError("invalid or expired access token") from exc


def verify_password(provided: str) -> bool:
    expected = os.environ.get("HIKING_FOOD_AUTH_PASSWORD", "")
    return bool(expected) and hmac.compare_digest(
        provided.encode("utf-8"), expected.encode("utf-8")
    )
