"""Owner-managed projects and sessions; model instructions cannot change their bindings."""

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ProjectInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    context: str = Field(default="", max_length=30000)
    links: list[str] = Field(default_factory=list, max_length=50)


class SessionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(default="Cuộc trò chuyện mới", min_length=1, max_length=200)
    project_id: str | None = None
    brain_id: str = "default"
    agent_id: str | None = None
    context_summary: str = Field(default="", max_length=12000)
    context_characters: int = Field(default=48000, ge=4000, le=120000)
    pinned: bool = False
    archived: bool = False
    model: str = Field(default="solo-default", max_length=128)


class Workspace:
    def __init__(self, path: Path, brain, library=None):
        self.automation = None
        self.path, self.brain, self.library = path, brain, library
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, data TEXT NOT NULL, updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, data TEXT NOT NULL, updated REAL NOT NULL);
            """)
            # Import legacy conversation identities without altering any messages.
            with sqlite3.connect(brain.db_path) as history:
                identifiers = [
                    r[0] for r in history.execute("SELECT DISTINCT conversation FROM messages")
                ]
            for identifier in set(identifiers + ["default"]):
                data = SessionInput(
                    title="Cuộc trò chuyện chính" if identifier == "default" else identifier[:200]
                ).model_dump()
                db.execute(
                    "INSERT OR IGNORE INTO sessions VALUES(?,?,?)",
                    (identifier, json.dumps(data), time.time()),
                )

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, kind, identifier):
        assert kind in {"sessions", "projects"}
        with self.db() as db:
            row = db.execute(f"SELECT * FROM {kind} WHERE id=?", (identifier,)).fetchone()
        if not row:
            raise ValueError("Không tìm thấy mục này.")
        return {"id": row["id"], "updated": row["updated"], **json.loads(row["data"])}

    def list(self, kind, search="", archived=False):
        assert kind in {"sessions", "projects"}
        with self.db() as db:
            rows = db.execute(f"SELECT * FROM {kind} ORDER BY updated DESC").fetchall()
        result = [{"id": r["id"], "updated": r["updated"], **json.loads(r["data"])} for r in rows]
        if kind == "sessions":
            result = [r for r in result if r["archived"] == archived]
        if search:
            query = search.casefold()
            matches = set()
            if kind == "sessions":
                with sqlite3.connect(self.brain.db_path) as db:
                    # Parameterized substring search deliberately treats FTS operators as plain text.
                    matches = {
                        r[0]
                        for r in db.execute(
                            "SELECT DISTINCT conversation FROM messages WHERE instr(lower(content),lower(?)) > 0",
                            (search,),
                        )
                    }
            result = [r for r in result if query in r["title"].casefold() or r["id"] in matches]
        return sorted(result, key=lambda r: not r.get("pinned", False))

    def save(self, kind, body, identifier=None):
        assert kind in {"sessions", "projects"}
        if identifier:
            self.get(kind, identifier)
        if kind == "sessions" and body.agent_id:
            if self.automation is None:
                raise ValueError("Chưa có kho trợ lý.")
            self.automation.agent_profile(body.agent_id)
        if kind == "sessions" and self.library:
            self.library.brain(body.brain_id)
        if kind == "sessions" and body.project_id:
            self.get("projects", body.project_id)
        identifier = identifier or uuid.uuid4().hex
        with self.db() as db:
            db.execute(
                f"INSERT OR REPLACE INTO {kind} VALUES(?,?,?)",
                (identifier, body.model_dump_json(), time.time()),
            )
        return self.get(kind, identifier)

    def chat_context(self, identifier):
        from server.core.context import bounded_history

        session = self.get("sessions", identifier)
        history = self.brain.messages(identifier, limit=200)
        result = bounded_history(history, session.get("context_characters", 48000))
        return result | {
            "summary": session.get("context_summary", ""),
            "limit": session.get("context_characters", 48000),
            "sampled": len(history),
        }

    def context(self, identifier):
        session = self.get("sessions", identifier)
        if session["archived"]:
            raise ValueError("Khôi phục cuộc trò chuyện trước khi tiếp tục.")
        project = self.get("projects", session["project_id"]) if session["project_id"] else None
        reference = {
            "project": project,
            "owner_reviewed_summary": session.get("context_summary", ""),
        }
        return (
            json.dumps(reference, ensure_ascii=False)
            if project or reference["owner_reviewed_summary"]
            else ""
        )
