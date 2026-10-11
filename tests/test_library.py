import io
import zipfile

import pytest

from server.core.library import Library


def test_brains_proposals_conflict_and_revisions(tmp_path):
    library = Library(tmp_path)
    second = library.create("Separate")
    proposal = library.propose("default", "memory/FACTS.md", "confirmed")
    assert library.brain("default").notes() == []
    library.decide(proposal["id"], True)
    assert library.brain(second["id"]).notes() == []
    stale = library.propose("default", "memory/FACTS.md", "old proposal")
    library.brain("default").write_note("memory/FACTS.md", "new owner edit")
    with pytest.raises(ValueError, match="đã thay đổi"):
        library.decide(stale["id"], True)
    assert library.revisions("default", "memory/FACTS.md")[0]["content"] == "confirmed"
    library.decide(stale["id"], False)
    assert library.proposals("default") == []
    with zipfile.ZipFile(io.BytesIO(library.export("default"))) as archive:
        assert archive.read("memory/FACTS.md") == b"new owner edit"
        assert not any(name.endswith(".db") for name in archive.namelist())


@pytest.mark.parametrize(
    "path", ["../secret.md", "wiki/../../secret.md", "/tmp/secret.md", "memory/x.json"]
)
def test_library_rejects_unsafe_paths(tmp_path, path):
    with pytest.raises(ValueError):
        Library(tmp_path).propose("default", path, "bad")
