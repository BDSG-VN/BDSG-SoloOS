import pytest

from server.core.brain import Brain
from server.core.workspace import ProjectInput, SessionInput, Workspace


def test_sessions_isolate_history_and_project_context(tmp_path):
    brain = Brain(tmp_path / "brain")
    brain.add("default", "user", "legacy message")
    workspace = Workspace(tmp_path / "workspace.db", brain)
    project = workspace.save(
        "projects", ProjectInput(title="Project one", context="private context")
    )
    first = workspace.save("sessions", SessionInput(title="First", project_id=project["id"]))
    second = workspace.save("sessions", SessionInput(title="Second"))
    brain.add(first["id"], "user", "special phrase")
    assert brain.messages(second["id"]) == []
    assert "private context" in workspace.context(first["id"])
    assert workspace.context(second["id"]) == ""
    assert [s["id"] for s in workspace.list("sessions", "special phrase")] == [first["id"]]
    workspace.save("sessions", SessionInput(title="First", archived=True), first["id"])
    with pytest.raises(ValueError, match="Khôi phục"):
        workspace.context(first["id"])
    assert len(workspace.list("sessions", archived=True)) == 1
    assert brain.messages("default")[0]["content"] == "legacy message"


def test_unknown_project_and_session_rejected(tmp_path):
    workspace = Workspace(tmp_path / "workspace.db", Brain(tmp_path / "brain"))
    with pytest.raises(ValueError):
        workspace.save("sessions", SessionInput(project_id="nonexistent"))
    with pytest.raises(ValueError):
        workspace.context("unknown")
