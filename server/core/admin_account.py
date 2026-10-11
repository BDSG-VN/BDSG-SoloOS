"""One owner account, initialized only with the server's bootstrap credential."""

import hmac
import json
import secrets

from server.core.members import password_hash


def configured(cms):
    with cms.db() as db:
        return db.execute("SELECT 1 FROM settings WHERE key='admin_account'").fetchone() is not None


def initialize(cms, username, password):
    salt = secrets.token_hex(16)
    value = json.dumps(
        {"username": username, "salt": salt, "password": password_hash(password, salt)}
    )
    with cms.db() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM settings WHERE key='admin_account'").fetchone():
            raise ValueError("Already installed")
        db.execute("INSERT INTO settings VALUES('admin_account',?)", (value,))


def authenticate(cms, username, password):
    with cms.db() as db:
        row = db.execute("SELECT value FROM settings WHERE key='admin_account'").fetchone()
    value = json.loads(row["value"]) if row else {"salt": "00" * 16, "password": "", "username": ""}
    digest = password_hash(password, value["salt"])
    return (
        bool(row)
        and hmac.compare_digest(digest, value["password"])
        and hmac.compare_digest(username.encode(), value["username"].encode())
    )
