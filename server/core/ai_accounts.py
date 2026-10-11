"""Encrypted AI accounts and one-use OAuth attempts owned by this SoloOS instance."""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from cryptography.fernet import Fernet


class AIAccounts:
    def __init__(self, path: Path, key: str):
        self.path, self.cipher = path, Fernet(key.encode())
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS accounts(
                id TEXT PRIMARY KEY, provider TEXT NOT NULL, label TEXT NOT NULL,
                identity TEXT NOT NULL, client_id TEXT NOT NULL, credentials TEXT NOT NULL,
                connected INTEGER NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
                refresh_until REAL NOT NULL DEFAULT 0, created REAL NOT NULL,
                UNIQUE(provider,identity,client_id));
            CREATE TABLE IF NOT EXISTS oauth_attempts(
                state_hash TEXT PRIMARY KEY, payload TEXT NOT NULL, expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS usage(
                id TEXT PRIMARY KEY, account_id TEXT, provider TEXT NOT NULL, model TEXT NOT NULL,
                source TEXT NOT NULL, input_tokens INTEGER, output_tokens INTEGER,
                status TEXT NOT NULL, created REAL NOT NULL);
            """)
            db.execute(
                "INSERT OR IGNORE INTO settings VALUES('host_id',?)",
                ("urn:uuid:" + str(uuid.uuid4()),),
            )
        path.chmod(0o600)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def seal(self, value):
        return self.cipher.encrypt(json.dumps(value, ensure_ascii=False).encode()).decode()

    def unseal(self, value):
        return json.loads(self.cipher.decrypt(value.encode()))

    def setting(self, key, default=None):
        with self.db() as db:
            row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        with self.db() as db:
            db.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (key, value))

    def accounts(self):
        with self.db() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT id,provider,label,connected,created FROM accounts ORDER BY created"
                )
            ]

    def account(self, account_id):
        with self.db() as db:
            row = db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        if not row:
            raise ValueError("AI account not found")
        return dict(row) | {"credentials": self.unseal(row["credentials"])}

    def save_account(
        self, identity, client_id, credentials, expected_id=None, expected_revision=None
    ):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute(
                "SELECT * FROM accounts WHERE provider='chatgpt' AND identity=? AND client_id=?",
                (identity, client_id),
            ).fetchone()
            if expected_id and (not old or old["id"] != expected_id):
                raise ValueError("The signed-in account does not match the selected account")
            if expected_revision is not None and (not old or old["revision"] != expected_revision):
                raise ValueError("Account changed since sign-in started. Start again.")
            account_id = old["id"] if old else uuid.uuid4().hex
            label = credentials.get("email") or "ChatGPT"
            if old:
                db.execute(
                    "UPDATE accounts SET credentials=?,label=?,connected=1,revision=revision+1,refresh_until=0 WHERE id=?",
                    (self.seal(credentials), label, account_id),
                )
            else:
                db.execute(
                    "INSERT INTO accounts(id,provider,label,identity,client_id,credentials,connected,created) VALUES(?,?,?,?,?,?,1,?)",
                    (
                        account_id,
                        "chatgpt",
                        label,
                        identity,
                        client_id,
                        self.seal(credentials),
                        time.time(),
                    ),
                )
            db.execute("INSERT OR REPLACE INTO settings VALUES('active_account',?)", (account_id,))
        return account_id

    def activate(self, account_id):
        if (
            account_id not in {"gateway", "claude-native"}
            and not self.account(account_id)["connected"]
        ):
            raise ValueError("Reconnect this AI account first")
        self.set_setting("active_account", account_id)

    def disconnect(self, account_id):
        with self.db() as db:
            db.execute(
                "UPDATE accounts SET connected=0,credentials=?,revision=revision+1,refresh_until=0 WHERE id=?",
                (self.seal({}), account_id),
            )
            db.execute("DELETE FROM settings WHERE key='active_account' AND value=?", (account_id,))

    def pending(self, payload):
        state = secrets.token_urlsafe(32)
        with self.db() as db:
            db.execute("DELETE FROM oauth_attempts WHERE expires<?", (time.time(),))
            db.execute(
                "INSERT INTO oauth_attempts VALUES(?,?,?)",
                (hashlib.sha256(state.encode()).hexdigest(), self.seal(payload), time.time() + 600),
            )
        return state

    def consume_pending(self, state):
        digest = hashlib.sha256(state.encode()).hexdigest()
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM oauth_attempts WHERE state_hash=?", (digest,)
            ).fetchone()
            if not row or row["expires"] < time.time():
                raise ValueError("Sign-in expired or already used. Start again.")
            db.execute("DELETE FROM oauth_attempts WHERE state_hash=?", (digest,))
        return self.unseal(row["payload"])

    def usage(self, account_id, provider, model, source, counts, status):
        with self.db() as db:
            db.execute(
                "INSERT INTO usage VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    uuid.uuid4().hex,
                    account_id,
                    provider,
                    model,
                    source,
                    counts.get("input_tokens"),
                    counts.get("output_tokens"),
                    status,
                    time.time(),
                ),
            )

    def usage_summary(self):
        with self.db() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT provider,model,source,status,COUNT(*) AS requests,SUM(input_tokens) AS input_tokens,SUM(output_tokens) AS output_tokens FROM usage WHERE created>? GROUP BY provider,model,source,status",
                    (time.time() - 30 * 86400,),
                )
            ]
