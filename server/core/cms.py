"""Original SoloOS CMS: versioned drafts, immutable public snapshots and typed blocks."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import unicodedata
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConflictError(ValueError):
    pass


class Block(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["hero", "heading", "paragraph", "list", "quote", "button", "image", "divider"]
    text: str = Field(default="", max_length=20000)
    detail: str = Field(default="", max_length=4000)
    items: list[str] = Field(default_factory=list, max_length=50)
    href: str = Field(default="", max_length=2000)
    src: str = Field(default="", max_length=200)
    alt: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def safe_fields(self):
        if any(len(item) > 4000 for item in self.items):
            raise ValueError("List item too long")
        if self.type == "button":
            url = urlsplit(self.href)
            relative = self.href.startswith("/") and not self.href.startswith("//")
            if not (relative or (url.scheme == "https" and url.hostname)) or any(
                c in self.href for c in ("\\", "\n", "\r")
            ):
                raise ValueError("Buttons require a local path or HTTPS URL")
        if self.type == "image" and not re.fullmatch(r"/media/[a-f0-9]{32}\.webp", self.src):
            raise ValueError("Choose an image from the media library")
        return self


class ContentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["post", "page"] = "post"
    title: str = Field(min_length=1, max_length=250)
    slug: str = Field(default="", max_length=160)
    excerpt: str = Field(default="", max_length=1000)
    blocks: list[Block] = Field(default_factory=list, max_length=100)
    categories: list[str] = Field(default_factory=list, max_length=20)
    tags: list[str] = Field(default_factory=list, max_length=30)
    seo_title: str = Field(default="", max_length=250)
    seo_description: str = Field(default="", max_length=500)
    sources: list[str] = Field(default_factory=list, max_length=20)
    ai_generated: bool = False

    @model_validator(mode="after")
    def validate_content(self):
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("A title is required")
        if not self.slug:
            slug = unicodedata.normalize("NFKD", self.title.lower().replace("đ", "d"))
            self.slug = (
                re.sub(r"[^a-z0-9]+", "-", slug.encode("ascii", "ignore").decode())
                .strip("-")[:160]
                .rstrip("-")
                or "untitled"
            )
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", self.slug):
            raise ValueError("Slug requires lowercase letters, numbers and hyphens")
        for values in (self.categories, self.tags):
            if any(not v.strip() or len(v) > 100 for v in values):
                raise ValueError("Invalid category or tag")
        self.categories = list(dict.fromkeys(v.strip() for v in self.categories))
        self.tags = list(dict.fromkeys(v.strip() for v in self.tags))
        for source in self.sources:
            url = urlsplit(source)
            if len(source) > 2000 or url.scheme != "https" or not url.hostname or url.username:
                raise ValueError("Sources must be HTTPS URLs")
        if len(self.model_dump_json()) > 200000:
            raise ValueError("Content is too large")
        return self


class CMSStore:
    def __init__(self, path: Path, key: str | None = None):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.cipher = Fernet(key.encode()) if key else None
        with self.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS content (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, slug TEXT NOT NULL,
                    draft TEXT NOT NULL, version INTEGER NOT NULL,
                    published TEXT, published_slug TEXT, published_version INTEGER,
                    published_at REAL, trashed INTEGER NOT NULL DEFAULT 0,
                    created REAL NOT NULL, updated REAL NOT NULL,
                    UNIQUE(kind,slug), UNIQUE(kind,published_slug));
                CREATE TABLE IF NOT EXISTS revisions (
                    content_id TEXT NOT NULL REFERENCES content(id), version INTEGER NOT NULL,
                    data TEXT NOT NULL, action TEXT NOT NULL, created REAL NOT NULL,
                    PRIMARY KEY(content_id,version));
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS media (
                    filename TEXT PRIMARY KEY, original_name TEXT NOT NULL, size INTEGER NOT NULL,
                    width INTEGER NOT NULL,height INTEGER NOT NULL,created REAL NOT NULL);
            """)
        path.chmod(0o600)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        except sqlite3.IntegrityError as exc:
            raise ConflictError("Slug already exists or record is invalid") from exc
        finally:
            db.close()

    @staticmethod
    def record(row):
        return json.loads(row["draft"]) | {
            "id": row["id"],
            "version": row["version"],
            "status": "trash" if row["trashed"] else "published" if row["published"] else "draft",
            "has_unpublished_changes": bool(
                row["published"] and row["version"] != row["published_version"]
            ),
            "published_at": row["published_at"],
            "updated": row["updated"],
        }

    def list(self, kind=None, search="", status=None):
        with self.db() as db:
            rows = db.execute("SELECT * FROM content ORDER BY updated DESC").fetchall()
        records = [self.record(r) for r in rows]
        return [
            r
            for r in records
            if (not kind or r["kind"] == kind)
            and (not status or r["status"] == status)
            and search.casefold() in (r["title"] + " " + r["excerpt"]).casefold()
        ]

    def get(self, content_id):
        with self.db() as db:
            row = db.execute("SELECT * FROM content WHERE id=?", (content_id,)).fetchone()
        if not row:
            raise ValueError("Content not found")
        return self.record(row)

    def save(self, content: dict, content_id=None, expected_version=None, action="save"):
        value = ContentInput.model_validate(content).model_dump()
        payload = json.dumps(value, ensure_ascii=False)
        now = time.time()
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            if content_id:
                old = db.execute("SELECT * FROM content WHERE id=?", (content_id,)).fetchone()
                self.check_version(old, expected_version)
                if old["trashed"]:
                    raise ValueError("Restore this content before editing")
                if old["kind"] != value["kind"]:
                    raise ValueError("Content type cannot change")
                if old["published_slug"] and value["slug"] != old["published_slug"]:
                    raise ValueError("Unpublish before changing a published URL")
                version = old["version"] + 1
                db.execute(
                    "UPDATE content SET slug=?,draft=?,version=?,updated=? WHERE id=?",
                    (value["slug"], payload, version, now, content_id),
                )
            else:
                content_id, version = uuid.uuid4().hex, 1
                db.execute(
                    "INSERT INTO content(id,kind,slug,draft,version,created,updated) VALUES(?,?,?,?,?,?,?)",
                    (content_id, value["kind"], value["slug"], payload, version, now, now),
                )
            db.execute(
                "INSERT INTO revisions VALUES(?,?,?,?,?)",
                (content_id, version, payload, action, now),
            )
        return self.get(content_id)

    @staticmethod
    def check_version(row, expected):
        if not row:
            raise ValueError("Content not found")
        if row["version"] != expected:
            raise ConflictError("Content changed in another window. Reload before saving.")

    def transition(self, content_id, expected_version, action):
        if action not in {"publish", "unpublish", "trash", "restore"}:
            raise ValueError("Invalid action")
        now = time.time()
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM content WHERE id=?", (content_id,)).fetchone()
            self.check_version(row, expected_version)
            if row["trashed"] and action != "restore":
                raise ValueError("Restore trashed content first")
            version = row["version"] + 1
            if action == "publish":
                value = ContentInput.model_validate_json(row["draft"])
                if not value.blocks:
                    raise ValueError("Add content before publishing")
                for block in value.blocks:
                    if (
                        block.type == "image"
                        and not db.execute(
                            "SELECT 1 FROM media WHERE filename=?", (block.src.rsplit("/", 1)[-1],)
                        ).fetchone()
                    ):
                        raise ValueError("Upload the referenced image before publishing")
                db.execute(
                    "UPDATE content SET published=draft,published_slug=slug,published_version=?,published_at=COALESCE(published_at,?) WHERE id=?",
                    (version, now, content_id),
                )
            else:
                db.execute(
                    "UPDATE content SET published=NULL,published_slug=NULL,published_version=NULL,trashed=? WHERE id=?",
                    (int(action == "trash"), content_id),
                )
                db.execute("DELETE FROM settings WHERE key='homepage' AND value=?", (content_id,))
            db.execute(
                "UPDATE content SET version=?,updated=? WHERE id=?", (version, now, content_id)
            )
            db.execute(
                "INSERT INTO revisions VALUES(?,?,?,?,?)",
                (content_id, version, row["draft"], action, now),
            )
        return self.get(content_id)

    def revisions(self, content_id):
        self.get(content_id)
        with self.db() as db:
            return [
                dict(r) | {"data": json.loads(r["data"])}
                for r in db.execute(
                    "SELECT * FROM revisions WHERE content_id=? ORDER BY version DESC LIMIT 100",
                    (content_id,),
                )
            ]

    def restore_revision(self, content_id, revision, expected_version):
        with self.db() as db:
            row = db.execute(
                "SELECT data FROM revisions WHERE content_id=? AND version=?",
                (content_id, revision),
            ).fetchone()
        if not row:
            raise ValueError("Revision not found")
        value = json.loads(row["data"])
        # Keep the canonical URL when restoring content from an older revision.
        value["slug"] = self.get(content_id)["slug"]
        return self.save(value, content_id, expected_version, action="restore_revision")

    def public(self, kind=None, slug=None):
        with self.db() as db:
            rows = db.execute(
                "SELECT id,published,published_at FROM content WHERE published IS NOT NULL AND trashed=0 ORDER BY published_at DESC"
            ).fetchall()
        result = [
            json.loads(r["published"]) | {"id": r["id"], "published_at": r["published_at"]}
            for r in rows
        ]
        return [
            r for r in result if (not kind or r["kind"] == kind) and (not slug or r["slug"] == slug)
        ]

    def homepage(self):
        with self.db() as db:
            row = db.execute("SELECT value FROM settings WHERE key='homepage'").fetchone()
        return next((r for r in self.public("page") if row and r["id"] == row["value"]), None)

    def set_homepage(self, content_id):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            if content_id:
                row = db.execute(
                    "SELECT kind,published,trashed FROM content WHERE id=?", (content_id,)
                ).fetchone()
                if not row or row["kind"] != "page" or not row["published"] or row["trashed"]:
                    raise ValueError("Homepage must be a published page")
                db.execute("INSERT OR REPLACE INTO settings VALUES('homepage',?)", (content_id,))
            else:
                db.execute("DELETE FROM settings WHERE key='homepage'")

    def gateway(self):
        with self.db() as db:
            row = db.execute("SELECT value FROM settings WHERE key='ai_gateway'").fetchone()
        if row and self.cipher:
            return json.loads(self.cipher.decrypt(row["value"].encode()))
        return {
            "base_url": os.getenv("BDSG_LLM_BASE_URL", "").rstrip("/"),
            "api_key": os.getenv("BDSG_LLM_API_KEY", ""),
            "model": os.getenv("BDSG_LLM_MODEL", "solo-default"),
        }

    def configure_gateway(self, base_url, model, api_key=None):
        url = urlsplit(base_url)
        if (
            url.scheme not in {"https", "http"}
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError("Provide an HTTP(S) gateway URL without credentials/query")
        allowed_http = {"localhost", "127.0.0.1", "::1"} | set(
            os.getenv("BDSG_LLM_ALLOW_HTTP_HOSTS", "").split(",")
        )
        if url.scheme == "http" and url.hostname not in allowed_http:
            raise ValueError("Use HTTPS for remote AI gateways")
        if not self.cipher:
            raise ValueError("Gateway configuration unavailable")
        old = self.gateway()
        if api_key is None and (
            urlsplit(old["base_url"]).scheme,
            urlsplit(old["base_url"]).netloc,
        ) != (url.scheme, url.netloc):
            api_key = ""
        value = {
            "base_url": base_url.rstrip("/"),
            "model": model,
            "api_key": self.gateway()["api_key"] if api_key is None else api_key,
        }
        encrypted = self.cipher.encrypt(json.dumps(value).encode()).decode()
        with self.db() as db:
            db.execute("INSERT OR REPLACE INTO settings VALUES('ai_gateway',?)", (encrypted,))
