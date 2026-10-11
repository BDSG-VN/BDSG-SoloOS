"""Named private brains and reviewed memory revisions, using local SQLite and Markdown."""

import hashlib
import io
import json
import sqlite3
import time
import uuid
import zipfile
from contextlib import contextmanager
from pathlib import Path

from server.core.brain import Brain


class Library:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "library.db"
        with self.db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS brains(id TEXT PRIMARY KEY,title TEXT NOT NULL,archived INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS revisions(id TEXT PRIMARY KEY,brain TEXT NOT NULL,path TEXT NOT NULL,content TEXT NOT NULL,created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS proposals(id TEXT PRIMARY KEY,brain TEXT NOT NULL,path TEXT NOT NULL,content TEXT NOT NULL,base_hash TEXT NOT NULL,status TEXT NOT NULL,created REAL NOT NULL);
            """)
            db.execute("INSERT OR IGNORE INTO brains(id,title) VALUES('default','Bộ nhớ chính')")

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def list(self):
        with self.db() as db:
            return [dict(row) for row in db.execute("SELECT * FROM brains ORDER BY rowid")]

    def brain(self, identifier):
        found = next((b for b in self.list() if b["id"] == identifier), None)
        if not found or found["archived"]:
            raise ValueError("Bộ nhớ không tồn tại hoặc đã lưu trữ.")
        return Brain(self.root / ("default_brain" if identifier == "default" else identifier))

    def create(self, title):
        identifier = uuid.uuid4().hex
        with self.db() as db:
            db.execute("INSERT INTO brains(id,title) VALUES(?,?)", (identifier, title))
        self.brain(identifier)
        return {"id": identifier, "title": title, "archived": 0}

    def rename(self, identifier, title):
        self.brain(identifier)
        with self.db() as db:
            db.execute("UPDATE brains SET title=? WHERE id=?", (title, identifier))
        return {"saved": True}

    def revisions(self, brain, path):
        return self.brain(brain).revisions(path)

    def propose(self, brain, path, content, expected_hash=None):
        file = self.brain(brain).note_path(path)
        current = file.read_text() if file.exists() else ""
        if (
            expected_hash is not None
            and hashlib.sha256(current.encode()).hexdigest() != expected_hash
        ):
            raise ValueError("Nội dung thay đổi trong khi AI đang đọc. Tạo lại đề xuất.")
        identifier = uuid.uuid4().hex
        with self.db() as db:
            db.execute(
                "INSERT INTO proposals VALUES(?,?,?,?,?,?,?)",
                (
                    identifier,
                    brain,
                    path,
                    content,
                    hashlib.sha256(current.encode()).hexdigest(),
                    "pending",
                    time.time(),
                ),
            )
        return {"id": identifier, "status": "pending"}

    def proposals(self, brain):
        self.brain(brain)
        with self.db() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM proposals WHERE brain=? AND status='pending' ORDER BY created DESC",
                    (brain,),
                )
            ]

    def decide(self, identifier, approved):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM proposals WHERE id=? AND status='pending'", (identifier,)
            ).fetchone()
            if not row:
                raise ValueError("Đề xuất đã được xử lý hoặc không tồn tại.")
            if approved:
                self.brain(row["brain"]).write_note(
                    row["path"], row["content"], expected_hash=row["base_hash"]
                )
            db.execute(
                "UPDATE proposals SET status=? WHERE id=?",
                ("approved" if approved else "rejected", identifier),
            )
        return {"status": "approved" if approved else "rejected"}

    def export(self, identifier):
        brain = self.brain(identifier)
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            for note in brain.notes():
                archive.writestr(note["path"], note["content"])
            archive.writestr(
                "manifest.json",
                json.dumps(
                    {"format": "soloos-brain-v1", "brain": identifier, "created": time.time()}
                ),
            )
        return stream.getvalue()
