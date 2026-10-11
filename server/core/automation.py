"""Bounded owner-defined workflows with durable checkpoints and no automatic side-effect replay."""

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Skill(Strict):
    title: str = Field(min_length=1, max_length=200)
    instruction: str = Field(min_length=1, max_length=20000)
    enabled: bool = True


class Agent(Strict):
    title: str = Field(min_length=1, max_length=200)
    instruction: str = Field(default="", max_length=20000)
    skills: list[str] = Field(default_factory=list, max_length=20)
    enabled: bool = True


class Step(Strict):
    kind: Literal["ai", "mcp", "note"]
    prompt: str = Field(default="", max_length=12000)
    connector: str = Field(default="", max_length=128)
    tool: str = Field(default="", max_length=128)
    arguments: dict = Field(default_factory=dict)


class Workflow(Strict):
    title: str = Field(min_length=1, max_length=200)
    agent_id: str | None = None
    steps: list[Step] = Field(min_length=1, max_length=12)
    enabled: bool = True


class Schedule(Strict):
    workflow_id: str
    interval_minutes: int = Field(ge=15, le=525600)
    enabled: bool = False


class Automation:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS definitions(id TEXT PRIMARY KEY,kind TEXT NOT NULL,data TEXT NOT NULL,updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,definition TEXT NOT NULL,status TEXT NOT NULL,step INTEGER NOT NULL DEFAULT 0,results TEXT NOT NULL DEFAULT '[]',confirmation TEXT,error TEXT,created REAL NOT NULL,updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS schedules(id TEXT PRIMARY KEY,data TEXT NOT NULL,next_run REAL NOT NULL);
            """)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def definitions(self, kind):
        with self.db() as db:
            return [
                {"id": r["id"], **json.loads(r["data"])}
                for r in db.execute(
                    "SELECT * FROM definitions WHERE kind=? ORDER BY updated DESC", (kind,)
                )
            ]

    def definition(self, kind, identifier):
        found = next((v for v in self.definitions(kind) if v["id"] == identifier), None)
        if not found:
            raise ValueError("Không tìm thấy định nghĩa.")
        return found

    def save(self, kind, body, identifier=None):
        assert kind in {"skills", "agents", "workflows"}
        if identifier:
            self.definition(kind, identifier)
        if kind == "agents":
            for skill in body.skills:
                self.definition("skills", skill)
        if kind == "workflows" and body.agent_id:
            self.definition("agents", body.agent_id)
        identifier = identifier or uuid.uuid4().hex
        with self.db() as db:
            db.execute(
                "INSERT OR REPLACE INTO definitions VALUES(?,?,?,?)",
                (identifier, kind, body.model_dump_json(), time.time()),
            )
        return self.definition(kind, identifier)

    def snapshot(self, workflow_id):
        workflow = self.definition("workflows", workflow_id)
        if not workflow["enabled"]:
            raise ValueError("Quy trình đã tắt.")
        instructions = []
        if workflow["agent_id"]:
            agent = self.definition("agents", workflow["agent_id"])
            if not agent["enabled"]:
                raise ValueError("Trợ lý đã tắt.")
            instructions.append(agent["instruction"])
            for identifier in agent["skills"]:
                skill = self.definition("skills", identifier)
                if skill["enabled"]:
                    instructions.append(skill["instruction"])
        return {**workflow, "instructions": "\n\n".join(instructions)}

    def enqueue(self, workflow_id):
        snapshot = self.snapshot(workflow_id)
        with self.db() as db:
            return self._enqueue(db, snapshot)

    def _enqueue(self, db, snapshot):
        identifier = uuid.uuid4().hex
        now = time.time()
        db.execute(
            "INSERT INTO runs(id,definition,status,created,updated) VALUES(?,?,?, ?,?)",
            (identifier, json.dumps(snapshot), "queued", now, now),
        )
        return {"id": identifier, "status": "queued"}

    def runs(self):
        with self.db() as db:
            return [
                dict(r)
                | {"definition": json.loads(r["definition"]), "results": json.loads(r["results"])}
                for r in db.execute("SELECT * FROM runs ORDER BY created DESC LIMIT 200")
            ]

    def claim(self):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM runs WHERE status='queued' ORDER BY created LIMIT 1"
            ).fetchone()
            if not row:
                return None
            db.execute(
                "UPDATE runs SET status='running',updated=? WHERE id=?", (time.time(), row["id"])
            )
            return dict(row) | {
                "definition": json.loads(row["definition"]),
                "results": json.loads(row["results"]),
            }

    def checkpoint(
        self, identifier, step, results, status="running", confirmation=None, error=None
    ):
        with self.db() as db:
            return (
                db.execute(
                    "UPDATE runs SET step=?,results=?,status=?,confirmation=?,error=?,updated=? WHERE id=? AND status='running'",
                    (
                        step,
                        json.dumps(results),
                        status,
                        confirmation,
                        error,
                        time.time(),
                        identifier,
                    ),
                ).rowcount
                == 1
            )

    def cancel(self, identifier):
        with self.db() as db:
            changed = db.execute(
                "UPDATE runs SET status='cancelled',updated=? WHERE id=? AND status IN ('queued','running','waiting')",
                (time.time(), identifier),
            ).rowcount
        if not changed:
            raise ValueError("Lượt chạy không còn có thể hủy.")
        return {"cancelled": True}

    def active(self, identifier):
        with self.db() as db:
            return bool(
                db.execute(
                    "SELECT 1 FROM runs WHERE id=? AND status IN ('running','waiting')",
                    (identifier,),
                ).fetchone()
            )

    def running(self, identifier):
        with self.db() as db:
            return bool(
                db.execute(
                    "SELECT 1 FROM runs WHERE id=? AND status='running'", (identifier,)
                ).fetchone()
            )

    def settle(self, confirmation, result):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM runs WHERE confirmation=? AND status='waiting'", (confirmation,)
            ).fetchone()
            if not row:
                return
            good = result.get("status") == "completed"
            results = json.loads(row["results"]) + [result]
            db.execute(
                "UPDATE runs SET status=?,step=step+?,results=?,confirmation=NULL,updated=? WHERE id=?",
                (
                    "queued" if good else "failed",
                    int(good),
                    json.dumps(results),
                    time.time(),
                    row["id"],
                ),
            )

    def recover(self):
        # A process crash may occur after a remote write but before checkpoint: never retry it silently.
        with self.db() as db:
            db.execute(
                "UPDATE runs SET status='uncertain',error='Tiến trình bị ngắt; cần đối chiếu kết quả trước khi chạy lại.' WHERE status='running'"
            )

    def schedules(self):
        with self.db() as db:
            return [
                {"id": r["id"], "next_run": r["next_run"], **json.loads(r["data"])}
                for r in db.execute("SELECT * FROM schedules")
            ]

    def schedule(self, body, identifier=None):
        self.snapshot(body.workflow_id)
        identifier = identifier or uuid.uuid4().hex
        with self.db() as db:
            db.execute(
                "INSERT OR REPLACE INTO schedules VALUES(?,?,?)",
                (identifier, body.model_dump_json(), time.time() + body.interval_minutes * 60),
            )
        return {"id": identifier}

    def tick(self):
        for schedule in self.schedules():
            if not schedule["enabled"] or schedule["next_run"] > time.time():
                continue
            try:
                snapshot = self.snapshot(schedule["workflow_id"])
            except ValueError:
                continue
            with self.db() as db:
                db.execute("BEGIN IMMEDIATE")
                current = db.execute(
                    "SELECT * FROM schedules WHERE id=?", (schedule["id"],)
                ).fetchone()
                if current["next_run"] != schedule["next_run"]:
                    continue
                self._enqueue(db, snapshot)
                db.execute(
                    "UPDATE schedules SET next_run=? WHERE id=?",
                    (time.time() + schedule["interval_minutes"] * 60, schedule["id"]),
                )
