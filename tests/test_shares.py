import sqlite3
import time

import pytest

from server.core.shares import Shares


def test_share_is_snapshot_expires_and_revokes(tmp_path):
    store = Shares(tmp_path / "shares.db")
    messages = [{"role": "user", "content": "original"}]
    created = store.create("Chat", messages, 7)
    token = created["url"].split("/")[-1]
    messages[0]["content"] = "later private message"
    assert store.get(token)["messages"][0]["content"] == "original"
    assert token not in repr(store.list())
    store.revoke(created["id"])
    with pytest.raises(ValueError):
        store.get(token)
    other = store.create("Chat", messages, 1)
    with sqlite3.connect(store.path) as db:
        db.execute("UPDATE shares SET expires=?", (time.time() - 1,))
    with pytest.raises(ValueError):
        store.get(other["url"].split("/")[-1])
