"""Owned Markdown memory and SQLite conversation history with FTS5."""

import fcntl
import hashlib
import sqlite3
import time
import uuid
from pathlib import Path


class Brain:
    def __init__(self, root: Path):
        self.root = root
        for name in ("memory", "wiki"):
            (root / name).mkdir(parents=True, exist_ok=True)
        self.db_path = root / "conversations.db"
        with sqlite3.connect(self.db_path) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY, conversation TEXT NOT NULL, role TEXT NOT NULL,
                    content TEXT NOT NULL, at REAL NOT NULL);
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(content, id UNINDEXED);
                CREATE TABLE IF NOT EXISTS note_revisions(id TEXT PRIMARY KEY,path TEXT NOT NULL,content TEXT NOT NULL,created REAL NOT NULL);
            """)

    def add(self, conversation: str, role: str, content: str):
        message_id = str(uuid.uuid4())
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "INSERT INTO messages VALUES (?,?,?,?,?)",
                (message_id, conversation, role, content, time.time()),
            )
            db.execute("INSERT INTO messages_fts VALUES (?,?)", (content, message_id))

    def messages(self, conversation: str = "default", limit: int = 50) -> list[dict]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT * FROM (SELECT * FROM messages WHERE conversation=? "
                "ORDER BY at DESC LIMIT ?) ORDER BY at",
                (conversation, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def notes(self) -> list[dict]:
        return [
            {"path": str(p.relative_to(self.root)), "content": p.read_text()}
            for folder in ("memory", "wiki")
            for p in sorted((self.root / folder).glob("*.md"))
        ]

    def note_path(self, name: str) -> Path:
        path = (self.root / name).resolve()
        if path.parent not in {(self.root / "memory").resolve(), (self.root / "wiki").resolve()}:
            raise ValueError("Notes must be directly inside memory/ or wiki/")
        if path.suffix != ".md":
            raise ValueError("Markdown notes only")
        return path

    def write_note(self, name: str, content: str, expected_hash=None):
        path = self.note_path(name)
        with (self.root / ".notes.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            current = path.read_text() if path.exists() else ""
            if (
                expected_hash is not None
                and hashlib.sha256(current.encode()).hexdigest() != expected_hash
            ):
                raise ValueError("Nội dung đã thay đổi sau khi đề xuất được tạo. Tạo đề xuất mới.")
            with sqlite3.connect(self.db_path) as db:
                db.execute(
                    "INSERT INTO note_revisions VALUES(?,?,?,?)",
                    (str(uuid.uuid4()), name, current, time.time()),
                )
            temporary = path.with_suffix(".md.tmp")
            temporary.write_text(content, encoding="utf-8")
            temporary.replace(path)
        return {"path": name, "saved": True}

    def revisions(self, name):
        self.note_path(name)
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM note_revisions WHERE path=? ORDER BY created DESC", (name,)
                )
            ]
