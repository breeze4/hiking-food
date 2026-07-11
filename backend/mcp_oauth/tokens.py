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


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


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
        self._schema_ready = False

    def _ensure_schema(self) -> None:
        """Create directories and tables on first use, not at construction time.

        Deferring this keeps ``import main`` free of database writes.
        """
        if self._schema_ready:
            return
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        self._schema_ready = True

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
                CREATE TABLE IF NOT EXISTS oauth_clients (
                  client_id TEXT NOT NULL,
                  redirect_uri TEXT NOT NULL,
                  scope TEXT NOT NULL,
                  client_name TEXT NOT NULL,
                  created_at INTEGER NOT NULL,
                  PRIMARY KEY (client_id, redirect_uri)
                );
                CREATE TABLE IF NOT EXISTS refresh_tokens (
                  token_hash TEXT PRIMARY KEY,
                  sub TEXT NOT NULL,
                  scope TEXT NOT NULL,
                  expires_at INTEGER NOT NULL,
                  created_at INTEGER NOT NULL
                );
                """
            )
            columns = {
                row[1] for row in conn.execute("PRAGMA table_info(refresh_tokens)")
            }
            if "token" in columns:
                rows = conn.execute(
                    "SELECT token, sub, scope, expires_at, created_at FROM refresh_tokens"
                ).fetchall()
                conn.executescript(
                    """
                    ALTER TABLE refresh_tokens RENAME TO refresh_tokens_plaintext;
                    CREATE TABLE refresh_tokens (
                      token_hash TEXT PRIMARY KEY,
                      sub TEXT NOT NULL,
                      scope TEXT NOT NULL,
                      expires_at INTEGER NOT NULL,
                      created_at INTEGER NOT NULL
                    );
                    """
                )
                conn.executemany(
                    "INSERT INTO refresh_tokens VALUES (?,?,?,?,?)",
                    [(_token_hash(token), sub, scope, expires_at, created_at)
                     for token, sub, scope, expires_at, created_at in rows],
                )
                conn.execute("DROP TABLE refresh_tokens_plaintext")

    def register_client(
        self, *, client_id: str, redirect_uris: list[str], scope: str,
        client_name: str,
    ) -> None:
        self._ensure_schema()
        now = _now()
        with self._conn() as conn:
            conn.executemany(
                "INSERT INTO oauth_clients VALUES (?,?,?,?,?)",
                [
                    (client_id, redirect_uri, scope, client_name, now)
                    for redirect_uri in redirect_uris
                ],
            )

    def client_allows(self, *, client_id: str, redirect_uri: str, scope: str) -> bool:
        self._ensure_schema()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT scope FROM oauth_clients "
                "WHERE client_id = ? AND redirect_uri = ?",
                (client_id, redirect_uri),
            ).fetchone()
        return bool(row) and set(scope.split()) <= set(row[0].split())

    def put_auth_code(
        self, *, client_id: str, redirect_uri: str, code_challenge: str,
        scope: str, sub: str,
    ) -> str:
        self._ensure_schema()
        code = _random_token()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO auth_codes VALUES (?,?,?,?,?,?,?)",
                (code, client_id, redirect_uri, code_challenge, scope, sub,
                 _now() + AUTH_CODE_TTL_SECONDS),
            )
        return code

    def consume_auth_code(self, code: str) -> AuthCodeRecord:
        self._ensure_schema()
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
        self._ensure_schema()
        token = _random_token()
        now = _now()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO refresh_tokens VALUES (?,?,?,?,?)",
                (_token_hash(token), sub, scope,
                 now + REFRESH_TOKEN_TTL_SECONDS, now),
            )
        return token

    def rotate_refresh_token(self, token: str) -> tuple[str, str, str]:
        self._ensure_schema()
        token_hash = _token_hash(token)
        replacement = _random_token()
        now = _now()
        with self._conn() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT sub, scope, expires_at FROM refresh_tokens "
                "WHERE token_hash = ?", (token_hash,),
            ).fetchone()
            if row is None:
                raise TokenError("unknown refresh token")
            conn.execute(
                "DELETE FROM refresh_tokens WHERE token_hash = ?", (token_hash,)
            )
            sub, scope, expires_at = row
            if expires_at < now:
                raise TokenError("refresh token expired")
            conn.execute(
                "INSERT INTO refresh_tokens VALUES (?,?,?,?,?)",
                (_token_hash(replacement), sub, scope,
                 now + REFRESH_TOKEN_TTL_SECONDS, now),
            )
        return sub, scope, replacement


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
