"""Local encrypted connector credentials, owner policies, and single-use approvals.

Only trusted application setup / owner routes may update this store. MCP annotations
and model output are never policy inputs. SQLite transactions protect approval use
even when multiple workers share the database.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlsplit

from cryptography.fernet import Fernet


class Permission(StrEnum):
    READ_ONLY = "read_only"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    FULL_ACCESS = "full_access"


class PolicyError(Exception):
    """Denied by local policy; safe to surface without credential data."""


def canonical(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class Connector:
    id: str
    transport: str = "stdio"
    command: str | None = None
    args: list[str] = field(default_factory=list)
    url: str | None = None
    permission: Permission = Permission.READ_ONLY
    # Explicit owner-reviewed allowlist. Missing tools are denied at every level.
    tools: dict[str, bool] = field(default_factory=dict)  # name -> verified read-only
    enabled: bool = True
    revision: int = 1

    def validate(self) -> None:
        if not self.id or len(self.id) > 128:
            raise ValueError("Connector id must be 1..128 characters")
        Permission(self.permission)
        if self.transport == "stdio":
            if not self.command or self.url:
                raise ValueError("stdio requires a command and no URL")
        elif self.transport == "streamable_http":
            url = urlsplit(self.url or "")
            local = url.hostname in {"localhost", "127.0.0.1", "::1"}
            if url.scheme != "https" and not (url.scheme == "http" and local):
                raise ValueError("Use HTTPS (HTTP allowed only on loopback)")
            if not url.hostname or url.username or url.password or self.command:
                raise ValueError("Invalid MCP URL")
        else:
            raise ValueError("Unsupported MCP transport")
        if any(not name or type(read) is not bool for name, read in self.tools.items()):
            raise ValueError("Tools require explicit boolean owner classifications")


class MCPStore:
    def __init__(self, path: Path | str, key: str | bytes):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS connectors (
                    id TEXT PRIMARY KEY, config TEXT NOT NULL, secrets BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS confirmations (
                    id TEXT PRIMARY KEY, payload TEXT NOT NULL, expires REAL NOT NULL,
                    status TEXT NOT NULL, decided_by TEXT);
                CREATE TABLE IF NOT EXISTS audit (
                    id INTEGER PRIMARY KEY, at REAL NOT NULL, event TEXT NOT NULL,
                    connector TEXT NOT NULL, tool TEXT NOT NULL, actor TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS rate_limits (
                    bucket TEXT PRIMARY KEY, window INTEGER NOT NULL, count INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY, expires REAL NOT NULL);
            """)
        os.chmod(self.path, 0o600)

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def put_connector(
        self, config: Connector, credentials: dict[str, dict[str, str]] | None = None
    ):
        """Trusted setup only. Credentials are {env: {...}, headers: {...}}."""
        config.validate()
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT * FROM connectors WHERE id=?", (config.id,)).fetchone()
            data = dict(vars(config))
            data["revision"] = json.loads(old["config"])["revision"] + 1 if old else 1
            encrypted = (
                self.cipher.encrypt(canonical(credentials or {}).encode())
                if credentials is not None or not old
                else old["secrets"]
            )
            db.execute(
                "INSERT OR REPLACE INTO connectors VALUES (?,?,?)",
                (config.id, canonical(data), encrypted),
            )

    def connector(self, connector_id: str) -> Connector:
        with self._db() as db:
            row = db.execute("SELECT config FROM connectors WHERE id=?", (connector_id,)).fetchone()
        if not row:
            raise PolicyError("Unknown connector")
        data = json.loads(row["config"])
        data["permission"] = Permission(data["permission"])
        return Connector(**data)

    def credentials(self, connector_id: str) -> dict:
        with self._db() as db:
            row = db.execute(
                "SELECT secrets FROM connectors WHERE id=?", (connector_id,)
            ).fetchone()
        if not row:
            raise PolicyError("Unknown connector")
        return json.loads(self.cipher.decrypt(row["secrets"]))

    def connectors(self) -> list[dict]:
        with self._db() as db:
            return [
                json.loads(row["config"]) for row in db.execute("SELECT config FROM connectors")
            ]

    def request_confirmation(self, payload: dict, ttl: int = 300) -> str:
        confirmation_id = secrets.token_urlsafe(32)
        with self._db() as db:
            db.execute(
                "INSERT INTO confirmations VALUES (?,?,?,'pending',NULL)",
                (confirmation_id, canonical(payload), time.time() + ttl),
            )
        return confirmation_id

    def confirmations(self) -> list[dict]:
        with self._db() as db:
            rows = db.execute(
                "SELECT * FROM confirmations WHERE status='pending' AND expires>?", (time.time(),)
            ).fetchall()
        return [dict(row) | {"payload": json.loads(row["payload"])} for row in rows]

    def decide(self, confirmation_id: str, approved: bool, owner: str):
        with self._db() as db:
            changed = db.execute(
                "UPDATE confirmations SET status=?,decided_by=? "
                "WHERE id=? AND status='pending' AND expires>?",
                ("approved" if approved else "rejected", owner, confirmation_id, time.time()),
            ).rowcount
        if changed != 1:
            raise PolicyError("Confirmation unavailable, expired, or already decided")

    def claim(self, confirmation_id: str, actor: str) -> dict:
        """Consume before external dispatch: uncertain failures must never auto-retry."""
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM confirmations WHERE id=?", (confirmation_id,)
            ).fetchone()
            if not row or row["status"] != "approved" or row["expires"] <= time.time():
                raise PolicyError("Confirmation not approved, expired, or already used")
            payload = json.loads(row["payload"])
            if payload["actor"] != actor:
                raise PolicyError("Confirmation belongs to a different requester")
            db.execute("UPDATE confirmations SET status='consumed' WHERE id=?", (confirmation_id,))
        return payload

    def audit(self, event: str, connector: str, tool: str, actor: str):
        # Do not log arguments, results, tokens or connector credentials.
        with self._db() as db:
            db.execute(
                "INSERT INTO audit(at,event,connector,tool,actor) VALUES (?,?,?,?,?)",
                (time.time(), event, connector, tool, actor),
            )

    def rate_limit(self, bucket: str, limit: int, seconds: int = 60) -> bool:
        window = int(time.time()) // seconds
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM rate_limits WHERE window < ?", (window - 2,))
            db.execute(
                "INSERT INTO rate_limits VALUES (?,?,1) ON CONFLICT(bucket) DO UPDATE SET "
                "count=CASE WHEN window=excluded.window THEN count+1 ELSE 1 END, "
                "window=excluded.window",
                (bucket, window),
            )
            row = db.execute("SELECT count FROM rate_limits WHERE bucket=?", (bucket,)).fetchone()
            return row["count"] <= limit

    def register_session(self, token_hash: str, expires: float):
        with self._db() as db:
            db.execute("DELETE FROM sessions WHERE expires<=?", (time.time(),))
            db.execute("INSERT INTO sessions VALUES (?,?)", (token_hash, expires))

    def session_valid(self, token_hash: str) -> bool:
        with self._db() as db:
            return (
                db.execute(
                    "SELECT 1 FROM sessions WHERE token_hash=? AND expires>?",
                    (token_hash, time.time()),
                ).fetchone()
                is not None
            )

    def revoke_session(self, token_hash: str):
        with self._db() as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))
