from datetime import datetime, timezone

import pytest

from server.core.automation import Automation, Step, Workflow
from server.core.scheduling import Schedule


def test_timezone_and_weekday_preview():
    base = datetime(2026, 10, 9, 3, tzinfo=timezone.utc).timestamp()  # Friday 10am Vietnam
    schedule = Schedule(workflow_id="w", kind="cron", cron="0 9 * * 1-5")
    assert schedule.next_after(base) == datetime(2026, 10, 12, 2, tzinfo=timezone.utc).timestamp()


@pytest.mark.parametrize(
    "fields",
    [
        {"kind": "cron", "cron": "* * * * * *"},
        {"timezone": "Fake/Zone"},
        {"kind": "once", "at": "2026-12-01T09:00:00"},
        {"kind": "cron", "cron": "0 0 31 2 *"},
    ],
)
def test_invalid_schedules_fail_closed(fields):
    with pytest.raises(ValueError):
        Schedule(workflow_id="w", **fields)


def test_once_is_not_replayed_and_overlap_is_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr("server.core.automation.time.time", lambda: 1000)
    queue = Automation(tmp_path / "jobs.db")
    flow = queue.save(
        "workflows", Workflow(title="Reminder", steps=[Step(kind="note", prompt="hi")])
    )
    queue.schedule(
        Schedule(
            workflow_id=flow["id"],
            kind="once",
            at=datetime.fromtimestamp(1100, timezone.utc),
            enabled=True,
        )
    )
    monkeypatch.setattr("server.core.automation.time.time", lambda: 1200)
    queue.tick()
    queue.tick()
    assert len(queue.runs()) == 1
    assert not queue.schedules()[0]["enabled"]
    schedule = queue.schedule(Schedule(workflow_id=flow["id"], interval_minutes=15, enabled=True))
    monkeypatch.setattr("server.core.automation.time.time", lambda: 2200)
    queue.tick()
    assert len(queue.runs()) == 1
    queue.cancel(queue.runs()[0]["id"])
    monkeypatch.setattr("server.core.automation.time.time", lambda: 3200)
    queue.tick()
    assert len(queue.runs()) == 2
    queue.delete_schedule(schedule["id"])
    assert len(queue.schedules()) == 1


def test_disabled_dependency_does_not_prevent_pausing_schedule(tmp_path):
    queue = Automation(tmp_path / "jobs.db")
    flow = queue.save("workflows", Workflow(title="Reminder", steps=[Step(kind="note")]))
    schedule = queue.schedule(Schedule(workflow_id=flow["id"], enabled=True))
    queue.save(
        "workflows",
        Workflow(title="Reminder", steps=[Step(kind="note")], enabled=False),
        flow["id"],
    )
    queue.schedule(Schedule(workflow_id=flow["id"], enabled=False), schedule["id"])
    assert not queue.schedules()[0]["enabled"]
