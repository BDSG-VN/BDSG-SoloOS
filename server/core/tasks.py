"""Persistent Kanban board. Execution adapters can claim queued work in later releases."""

import sqlite3
import time
import uuid

STATES = ("todo", "doing", "done")


class TaskQueue:
    def __init__(self, path):
        self.path = path
        with sqlite3.connect(path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS tasks "
                "(id TEXT PRIMARY KEY,title TEXT,state TEXT,created REAL)"
            )

    def list(self):
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute("SELECT * FROM tasks ORDER BY created DESC")]

    def create(self, title):
        task_id = str(uuid.uuid4())
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO tasks VALUES (?,?,?,?)", (task_id, title, "todo", time.time()))
        return {"id": task_id, "title": title, "state": "todo"}

    def move(self, task_id, state):
        if state not in STATES:
            raise ValueError("Invalid Kanban state")
        with sqlite3.connect(self.path) as db:
            if db.execute("UPDATE tasks SET state=? WHERE id=?", (state, task_id)).rowcount != 1:
                raise ValueError("Task not found")
        return {"id": task_id, "state": state}
