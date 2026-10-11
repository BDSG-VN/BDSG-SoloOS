"""Reviewed memory persistence; automatic extraction is deliberately not enabled."""

import subprocess


def commit_reviewed_memory(brain, name: str, content: str, *, git_commit: bool = False):
    result = brain.write_note(name, content)
    if git_commit:
        # Only the reviewed file is staged. Git is opt-in and never runs shell text.
        path = brain.note_path(name)
        subprocess.run(["git", "add", "--", str(path)], cwd=brain.root, check=True)
        subprocess.run(
            ["git", "commit", "--only", "-m", "Save reviewed Solo-OS memory", "--", str(path)],
            cwd=brain.root,
            check=True,
        )
    return result
