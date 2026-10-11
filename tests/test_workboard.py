import sqlite3

from server.core.tasks import TaskInput, TaskQueue


def test_legacy_task_storage_remains_compatible_and_metadata_survives_move(tmp_path):
    path = tmp_path / "tasks.db"
    store = TaskQueue(path)
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO tasks VALUES('legacy','Old task','todo',1)")
    assert store.list()[0]["priority"] == "normal"
    store.update(
        "legacy",
        TaskInput(title="Revised", priority="urgent", due="2026-12-01", description="Notes"),
    )
    store.move("legacy", "done")
    row = store.list()[0]
    assert row["priority"] == "urgent" and row["state"] == "done" and row["description"] == "Notes"
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO tasks VALUES('rollback','Previous version works','todo',2)")
    assert len(store.list()) == 2
