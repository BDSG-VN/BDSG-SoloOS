"""Owner-issued one-use pairing codes and revocable scoped native-device credentials."""

import hashlib
import json
import secrets
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Pairing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    scopes: list[Literal["read", "chat", "tasks", "approvals"]] = Field(
        default_factory=lambda: ["read", "chat"], min_length=1, max_length=4
    )
    days: int = Field(default=30, ge=1, le=90)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Devices:
    def __init__(self, path: Path):
        self.path = path
        with sqlite3.connect(path) as db:
            db.executescript("""CREATE TABLE IF NOT EXISTS pairing(id TEXT PRIMARY KEY,digest TEXT UNIQUE,data TEXT,expires REAL,used INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS devices(id TEXT PRIMARY KEY,name TEXT,digest TEXT UNIQUE,scopes TEXT,expires REAL,created REAL,last_seen REAL,revoked INTEGER DEFAULT 0);""")

    def pair(self, body):
        code = secrets.token_urlsafe(24)
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT INTO pairing(id,digest,data,expires) VALUES(?,?,?,?)",
                (uuid.uuid4().hex, digest(code), body.model_dump_json(), time.time() + 300),
            )
        return {"code": code, "expires_in": 300}

    def redeem(self, code):
        now = time.time()
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM pairing WHERE digest=? AND used=0 AND expires>?", (digest(code), now)
            ).fetchone()
            if not row:
                raise ValueError("Mã ghép không hợp lệ, đã dùng hoặc hết hạn.")
            body = Pairing.model_validate_json(row["data"])
            token = "dev_" + secrets.token_urlsafe(40)
            identifier = uuid.uuid4().hex
            db.execute("UPDATE pairing SET used=1 WHERE id=?", (row["id"],))
            db.execute(
                "INSERT INTO devices(id,name,digest,scopes,expires,created,last_seen) VALUES(?,?,?,?,?,?,?)",
                (
                    identifier,
                    body.name,
                    digest(token),
                    json.dumps(body.scopes),
                    now + body.days * 86400,
                    now,
                    now,
                ),
            )
        return {
            "id": identifier,
            "token": token,
            "name": body.name,
            "scopes": body.scopes,
            "expires": now + body.days * 86400,
        }

    def authenticate(self, token):
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute(
                "SELECT id,name,scopes,expires FROM devices WHERE digest=? AND revoked=0 AND expires>?",
                (digest(token), time.time()),
            ).fetchone()
            if not row:
                return None
            db.execute("UPDATE devices SET last_seen=? WHERE id=?", (time.time(), row["id"]))
        return dict(row) | {"scopes": json.loads(row["scopes"])}

    def list(self):
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            return [
                dict(row) | {"scopes": json.loads(row["scopes"])}
                for row in db.execute(
                    "SELECT id,name,scopes,expires,created,last_seen,revoked FROM devices ORDER BY created DESC"
                )
            ]

    def revoke(self, identifier):
        with sqlite3.connect(self.path) as db:
            if not db.execute("UPDATE devices SET revoked=1 WHERE id=?", (identifier,)).rowcount:
                raise ValueError("Không tìm thấy thiết bị.")
        return {"revoked": True}


def permits(scopes, method, path):
    import re

    if method == "DELETE" and path == "/api/devices/self":
        return True
    if method == "GET" and "read" in scopes:
        allowed = path in {
            "/api/operations",
            "/api/tasks",
            "/api/workspace/sessions",
            "/api/workspace/projects",
            "/api/library",
            "/api/engines",
        } or bool(re.fullmatch(r"/api/conversations/[\w-]+", path))
        if allowed:
            return True
    if method == "GET" and "approvals" in scopes and path == "/api/confirmations":
        return True
    if method == "POST" and "chat" in scopes and path in {"/api/chat", "/api/workspace/sessions"}:
        return True
    if "tasks" in scopes and (
        (method == "POST" and path == "/api/tasks")
        or (method in {"PUT", "PATCH"} and re.fullmatch(r"/api/tasks/[\w-]+", path))
    ):
        return True
    if (
        "approvals" in scopes
        and method == "POST"
        and re.fullmatch(r"/api/confirmations/[\w-]+/decision", path)
    ):
        return True
    return False
