"""Owner-controlled workboard. Assigning an assistant does not execute it."""

import json
import sqlite3
import time
import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

STATES = ("todo", "doing", "done")


class TaskInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=20000)
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    due: date | None = None
    project_id: str | None = None
    agent_id: str | None = None


class TaskQueue:
    def __init__(self, path):
        self.path = path
        with sqlite3.connect(path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY,title TEXT,state TEXT,created REAL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS task_metadata(task_id TEXT PRIMARY KEY,data TEXT NOT NULL)"
            )

    def list(self):
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            result = []
            for row in db.execute(
                "SELECT tasks.*, COALESCE(task_metadata.data, '{}') AS metadata FROM tasks LEFT JOIN task_metadata ON task_metadata.task_id=tasks.id ORDER BY created DESC"
            ):
                item = dict(row)
                metadata = json.loads(item.pop("metadata"))
                result.append(
                    {**TaskInput(title=item["title"]).model_dump(mode="json"), **metadata, **item}
                )
            return result

    def create(self, title, **metadata):
        body = TaskInput(title=title, **metadata)
        task_id = str(uuid.uuid4())
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT INTO tasks(id,title,state,created) VALUES (?,?,?,?)",
                (task_id, title, "todo", time.time()),
            )
            db.execute(
                "INSERT INTO task_metadata VALUES(?,?)",
                (task_id, body.model_dump_json(exclude={"title"})),
            )
        return next(t for t in self.list() if t["id"] == task_id)

    def update(self, task_id, body):
        with sqlite3.connect(self.path) as db:
            if (
                db.execute("UPDATE tasks SET title=? WHERE id=?", (body.title, task_id)).rowcount
                != 1
            ):
                raise ValueError("Task not found")
            db.execute(
                "INSERT OR REPLACE INTO task_metadata VALUES(?,?)",
                (task_id, body.model_dump_json(exclude={"title"})),
            )
        return next(t for t in self.list() if t["id"] == task_id)

    def move(self, task_id, state):
        if state not in STATES:
            raise ValueError("Invalid Kanban state")
        with sqlite3.connect(self.path) as db:
            if db.execute("UPDATE tasks SET state=? WHERE id=?", (state, task_id)).rowcount != 1:
                raise ValueError("Task not found")
        return {"id": task_id, "state": state}
