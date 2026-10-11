"""Customer identities are deliberately separate from owner authorization."""

import hashlib
import hmac
import secrets
import time
import uuid

COOKIE = "bdsg_member"


def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()


class Members:
    def __init__(self, cms):
        self.cms = cms
        with cms.db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS members(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,salt TEXT NOT NULL,password TEXT NOT NULL,created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS member_sessions(hash TEXT PRIMARY KEY,member_id TEXT NOT NULL REFERENCES members(id),csrf TEXT NOT NULL,expires REAL NOT NULL);
            """)

    def register(self, email, name, password):
        salt = secrets.token_hex(16)
        digest = password_hash(password, salt)
        with self.cms.db() as db:
            db.execute(
                "INSERT INTO members VALUES(?,?,?,?,?,?)",
                (uuid.uuid4().hex, email, name, salt, digest, time.time()),
            )

    def login(self, email, password):
        with self.cms.db() as db:
            row = db.execute("SELECT * FROM members WHERE email=?", (email,)).fetchone()
        digest = password_hash(password, row["salt"] if row else "00" * 16)
        if not row or not hmac.compare_digest(digest, row["password"]):
            return None
        token = secrets.token_urlsafe(40)
        with self.cms.db() as db:
            db.execute("DELETE FROM member_sessions WHERE expires<?", (time.time(),))
            db.execute(
                "INSERT INTO member_sessions VALUES(?,?,?,?)",
                (
                    hashlib.sha256(token.encode()).hexdigest(),
                    row["id"],
                    secrets.token_urlsafe(32),
                    time.time() + 43200,
                ),
            )
        return token

    def session(self, token):
        with self.cms.db() as db:
            row = db.execute(
                "SELECT m.id,m.email,m.name,s.csrf FROM member_sessions s JOIN members m ON m.id=s.member_id WHERE s.hash=? AND s.expires>?",
                (hashlib.sha256(token.encode()).hexdigest(), time.time()),
            ).fetchone()
        return dict(row) if row else None

    def logout(self, token):
        with self.cms.db() as db:
            db.execute(
                "DELETE FROM member_sessions WHERE hash=?",
                (hashlib.sha256(token.encode()).hexdigest(),),
            )
