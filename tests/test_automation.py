from types import SimpleNamespace

import pytest

from server.core.automation import Agent, Automation, Schedule, Skill, Step, Workflow
from server.engines.automation import execute


@pytest.fixture
def queue(tmp_path):
    return Automation(tmp_path / "jobs.db")


@pytest.mark.asyncio
async def test_snapshot_and_waiting_does_not_replay_tool(queue):
    skill = queue.save("skills", Skill(title="Facts", instruction="Use verified facts"))
    agent = queue.save("agents", Agent(title="Writer", skills=[skill["id"]]))
    flow = queue.save(
        "workflows",
        Workflow(
            title="Flow",
            agent_id=agent["id"],
            steps=[
                Step(kind="mcp", connector="write", tool="save", arguments={"x": 1}),
                Step(kind="note", prompt="after"),
            ],
        ),
    )
    queue.enqueue(flow["id"])
    queue.save("skills", Skill(title="Facts", instruction="Changed"), skill["id"])
    run = queue.claim()
    assert run["definition"]["instructions"] == "\n\nUse verified facts"
    calls = []

    async def call(connector, tool, arguments, actor, run_id, agent_id=None):
        calls.append((connector, tool, arguments, actor))
        return {"status": "requires_confirmation", "confirmation_id": "approval"}

    state = SimpleNamespace(automation=queue, hub=SimpleNamespace(call_tool=call))
    await execute(state, run)
    assert queue.runs()[0]["status"] == "waiting"
    assert queue.claim() is None
    queue.settle("approval", {"status": "completed", "result": {"ok": True}})
    await execute(state, queue.claim())
    assert queue.runs()[0]["status"] == "completed"
    assert len(calls) == 1 and calls[0][-1] == "agent"
    queue.settle("approval", {"status": "completed"})
    assert queue.claim() is None


@pytest.mark.asyncio
async def test_uncertain_failure_is_not_retried(queue):
    flow = queue.save(
        "workflows", Workflow(title="Write", steps=[Step(kind="mcp", connector="x", tool="y")])
    )
    queue.enqueue(flow["id"])

    async def call(*args, **kw):
        raise ConnectionError("possibly delivered")

    await execute(
        SimpleNamespace(automation=queue, hub=SimpleNamespace(call_tool=call)), queue.claim()
    )
    assert queue.runs()[0]["status"] == "uncertain"
    assert queue.claim() is None


def test_claim_schedule_recovery_and_cancel(queue):
    flow = queue.save(
        "workflows", Workflow(title="Reminder", steps=[Step(kind="note", prompt="hello")])
    )
    scheduled = queue.schedule(Schedule(workflow_id=flow["id"], interval_minutes=15, enabled=True))
    with queue.db() as db:
        db.execute("UPDATE schedules SET next_run=0 WHERE id=?", (scheduled["id"],))
    queue.tick()
    queue.tick()
    assert len(queue.runs()) == 1
    run = queue.claim()
    assert queue.claim() is None
    queue.recover()
    assert queue.runs()[0]["status"] == "uncertain"
    new = queue.enqueue(flow["id"])
    queue.cancel(new["id"])
    assert queue.claim() is None
    assert not queue.checkpoint(run["id"], 1, [], "completed")


@pytest.mark.asyncio
async def test_cancel_while_confirmation_is_being_created_revokes_it(queue):
    flow = queue.save(
        "workflows", Workflow(title="Write", steps=[Step(kind="mcp", connector="x", tool="y")])
    )
    queue.enqueue(flow["id"])
    run = queue.claim()
    decisions = []

    async def call(*args, **kw):
        queue.cancel(run["id"])
        return {"status": "requires_confirmation", "confirmation_id": "late"}

    state = SimpleNamespace(
        automation=queue,
        hub=SimpleNamespace(call_tool=call),
        store=SimpleNamespace(decide=lambda *args: decisions.append(args)),
    )
    await execute(state, run)
    assert decisions == [("late", False, "owner")]
    assert queue.runs()[0]["status"] == "cancelled"
