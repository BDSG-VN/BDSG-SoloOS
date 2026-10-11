"""Explicit, expiring conversation snapshots, revocable without changing the original chat."""

import hashlib
import json
import secrets
import sqlite3
import time
import uuid
from pathlib import Path


class Shares:
    def __init__(self, path: Path):
        self.path = path
        with sqlite3.connect(path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS shares(id TEXT PRIMARY KEY,digest TEXT NOT NULL UNIQUE,title TEXT NOT NULL,snapshot TEXT NOT NULL,expires REAL NOT NULL,revoked INTEGER NOT NULL DEFAULT 0)"
            )

    def create(self, title, messages, days):
        token = secrets.token_urlsafe(32)
        identifier = uuid.uuid4().hex
        expires = time.time() + days * 86400
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT INTO shares(id,digest,title,snapshot,expires) VALUES(?,?,?,?,?)",
                (
                    identifier,
                    hashlib.sha256(token.encode()).hexdigest(),
                    title,
                    json.dumps(messages, ensure_ascii=False),
                    expires,
                ),
            )
        return {"id": identifier, "url": "/share/" + token, "expires": expires}

    def get(self, token):
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute(
                "SELECT title,snapshot,expires FROM shares WHERE digest=? AND revoked=0 AND expires>?",
                (hashlib.sha256(token.encode()).hexdigest(), time.time()),
            ).fetchone()
        if not row:
            raise ValueError("Liên kết không tồn tại, đã hết hạn hoặc được thu hồi.")
        return {
            "title": row["title"],
            "messages": json.loads(row["snapshot"]),
            "expires": row["expires"],
        }

    def list(self):
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            return [
                dict(row)
                for row in db.execute(
                    "SELECT id,title,expires,revoked FROM shares ORDER BY expires DESC"
                )
            ]

    def revoke(self, identifier):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE shares SET revoked=1 WHERE id=?", (identifier,))
        return {"revoked": True}
