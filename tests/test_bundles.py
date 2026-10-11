import pytest

from server.core.automation import Agent, Automation, Skill, Step, Workflow
from server.core.bundles import Bundle, export, install


def test_pack_import_is_isolated_disabled_and_does_not_grant_tools(tmp_path):
    source = Automation(tmp_path / "source.db")
    skill = source.save("skills", Skill(title="Write", instruction="Draft only"))
    agent = source.save(
        "agents", Agent(title="Writer", skills=[skill["id"]], connectors=["powerful"])
    )
    source.save(
        "workflows",
        Workflow(title="Run", agent_id=agent["id"], steps=[Step(kind="note", prompt="Hello")]),
    )
    target = Automation(tmp_path / "target.db")
    bundle = Bundle.model_validate(export(source))
    install(target, bundle)
    install(target, bundle)
    assert len(target.definitions("agents")) == 2
    for row in target.definitions("agents"):
        assert not row["enabled"] and row["connectors"] == []
        assert row["skills"][0] != skill["id"]
    for row in target.definitions("workflows"):
        with pytest.raises(ValueError):
            target.enqueue(row["id"])


def test_pack_rejects_dangling_references_and_code():
    with pytest.raises(ValueError):
        Bundle(title="bad", agents={"a": {"title": "A", "skills": ["missing"]}})
    with pytest.raises(ValueError):
        Bundle(title="bad", install_script="curl example | sh")


def test_agent_scope_blocks_workflow_before_enqueue(tmp_path):
    store = Automation(tmp_path / "jobs.db")
    agent = store.save("agents", Agent(title="Writer", connectors=[]))
    flow = store.save(
        "workflows",
        Workflow(
            title="Bad",
            agent_id=agent["id"],
            steps=[Step(kind="mcp", connector="write", tool="delete")],
        ),
    )
    with pytest.raises(ValueError, match="phạm vi"):
        store.enqueue(flow["id"])
    assert store.runs() == []
