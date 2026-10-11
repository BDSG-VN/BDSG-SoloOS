"""Single-owner Customer 360, inbox, campaigns, sales, support and operations.

Real provider APIs are connected via MCP. This database records local business
state and never labels a configured connector as connected until it has been tested.
Amounts are integer VND, with idempotent sales receipt entries (not bank verification).
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from cryptography.fernet import Fernet

CHANNELS = [
    {"id": "zalo", "name": "Zalo OA", "kind": "messaging", "capabilities": "Tin nhắn · Khách hàng"},
    {"id": "facebook", "name": "Facebook", "kind": "social", "capabilities": "Inbox · Bình luận"},
    {
        "id": "instagram",
        "name": "Instagram",
        "kind": "social",
        "capabilities": "Tin nhắn · Khách hàng",
    },
    {"id": "tiktok", "name": "TikTok", "kind": "social", "capabilities": "Nội dung · Khách hàng"},
    {
        "id": "google_ads",
        "name": "Google Ads",
        "kind": "advertising",
        "capabilities": "Quảng cáo · Lead",
    },
    {"id": "email", "name": "Email", "kind": "email", "capabilities": "Email · Marketing"},
    {
        "id": "hotline",
        "name": "Hotline / Call Center",
        "kind": "voice",
        "capabilities": "Cuộc gọi · Tổng đài",
    },
    {"id": "website", "name": "Website", "kind": "web", "capabilities": "Livechat · Form đăng ký"},
    {"id": "sms", "name": "SMS / ZNS", "kind": "messaging", "capabilities": "Thông báo · Chăm sóc"},
]
CHANNEL_IDS = {c["id"] for c in CHANNELS}


def new_id():
    return str(uuid.uuid4())


def render_arguments(template, recipient: str, content: str):
    """JSON template substitution, never code evaluation or string interpolation."""
    if isinstance(template, dict):
        return {k: render_arguments(v, recipient, content) for k, v in template.items()}
    if isinstance(template, list):
        return [render_arguments(v, recipient, content) for v in template]
    if template == "$recipient":
        return recipient
    if template == "$content":
        return content
    return template


class BusinessStore:
    def __init__(self, path: Path, key: str):
        self.path = path
        self.cipher = Fernet(key.encode())
        with self.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS customers (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT, phone TEXT,
                    stage TEXT NOT NULL DEFAULT 'lead', notes TEXT NOT NULL DEFAULT '', created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS identities (
                    channel TEXT NOT NULL, external_id TEXT NOT NULL,
                    customer_id TEXT NOT NULL REFERENCES customers(id), PRIMARY KEY(channel,external_id));
                CREATE TABLE IF NOT EXISTS channel_config (
                    id TEXT PRIMARY KEY, connector TEXT, read_tool TEXT, send_tool TEXT,
                    argument_template TEXT NOT NULL, webhook_secret BLOB, enabled INTEGER NOT NULL,
                    last_test REAL, test_ok INTEGER);
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY, channel TEXT NOT NULL, external_id TEXT,
                    sender_id TEXT NOT NULL, customer_id TEXT REFERENCES customers(id),
                    direction TEXT NOT NULL, status TEXT NOT NULL, content TEXT NOT NULL,
                    created REAL NOT NULL, confirmation_id TEXT, UNIQUE(channel,external_id));
                CREATE TABLE IF NOT EXISTS campaigns (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, objective TEXT NOT NULL,
                    channels TEXT NOT NULL, budget INTEGER NOT NULL, status TEXT NOT NULL,
                    plan TEXT NOT NULL DEFAULT '', created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS sales (
                    id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES customers(id),
                    title TEXT NOT NULL, items TEXT NOT NULL, total INTEGER NOT NULL,
                    status TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS tickets (
                    id TEXT PRIMARY KEY, customer_id TEXT REFERENCES customers(id), title TEXT NOT NULL,
                    description TEXT NOT NULL, priority TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS ledger (
                    id TEXT PRIMARY KEY, direction TEXT NOT NULL, amount INTEGER NOT NULL,
                    description TEXT NOT NULL, source_ref TEXT UNIQUE, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS staff (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL, email TEXT,
                    status TEXT NOT NULL, created REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS message_customer ON messages(customer_id,created);
            """)
        self.path.chmod(0o600)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        except sqlite3.IntegrityError as exc:
            raise ValueError("Invalid or conflicting business record") from exc
        finally:
            db.close()

    def channels(self):
        with self.db() as db:
            configs = {row["id"]: dict(row) for row in db.execute("SELECT * FROM channel_config")}
        result = []
        for channel in CHANNELS:
            config = configs.get(channel["id"], {})
            secret = config.pop("webhook_secret", None)
            config["argument_template"] = json.loads(config.get("argument_template", "{}"))
            result.append(
                channel
                | config
                | {
                    "webhook_configured": bool(secret),
                    "status": "tested"
                    if config.get("test_ok") and config.get("enabled")
                    else "configured"
                    if config.get("enabled")
                    else "not_connected",
                }
            )
        return result

    def configure_channel(
        self,
        channel: str,
        connector: str | None,
        read_tool: str | None,
        send_tool: str | None,
        argument_template: dict,
        enabled: bool,
        webhook_secret: str | None = None,
    ):
        if channel not in CHANNEL_IDS:
            raise ValueError("Unknown channel")
        with self.db() as db:
            old = db.execute(
                "SELECT webhook_secret FROM channel_config WHERE id=?", (channel,)
            ).fetchone()
            secret = (
                (self.cipher.encrypt(webhook_secret.encode()) if webhook_secret else None)
                if webhook_secret is not None
                else (old[0] if old else None)
            )
            db.execute(
                "INSERT OR REPLACE INTO channel_config VALUES (?,?,?,?,?,?,?,NULL,NULL)",
                (
                    channel,
                    connector,
                    read_tool,
                    send_tool,
                    json.dumps(argument_template),
                    secret,
                    int(enabled),
                ),
            )

    def channel(self, channel: str):
        with self.db() as db:
            row = db.execute("SELECT * FROM channel_config WHERE id=?", (channel,)).fetchone()
        if not row or not row["enabled"]:
            raise ValueError("Channel is not configured/enabled")
        data = dict(row)
        data["argument_template"] = json.loads(data["argument_template"])
        return data

    def webhook_key(self, channel):
        data = self.channel(channel)
        if not data["webhook_secret"]:
            raise ValueError("Webhook secret missing")
        return self.cipher.decrypt(data["webhook_secret"])

    def record_test(self, channel, okay):
        with self.db() as db:
            db.execute(
                "UPDATE channel_config SET last_test=?,test_ok=? WHERE id=?",
                (time.time(), int(okay), channel),
            )

    def create_customer(self, name, email=None, phone=None, stage="lead", notes=""):
        customer_id = new_id()
        with self.db() as db:
            db.execute(
                "INSERT INTO customers VALUES (?,?,?,?,?,?,?)",
                (customer_id, name, email, phone, stage, notes, time.time()),
            )
        return {"id": customer_id, "name": name}

    def customers(self):
        with self.db() as db:
            rows = db.execute(
                "SELECT c.*, (SELECT COUNT(*) FROM messages m WHERE m.customer_id=c.id) AS message_count, "
                "(SELECT COALESCE(SUM(total),0) FROM sales s WHERE s.customer_id=c.id AND status='paid') AS revenue "
                "FROM customers c ORDER BY created DESC"
            ).fetchall()
            identities = [dict(r) for r in db.execute("SELECT * FROM identities")]
        return [
            dict(row) | {"identities": [i for i in identities if i["customer_id"] == row["id"]]}
            for row in rows
        ]

    def customer(self, customer_id):
        with self.db() as db:
            row = db.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone()
            if not row:
                raise ValueError("Customer not found")
            result = dict(row)
            for table in ("messages", "sales", "tickets"):
                result[table] = [
                    dict(r)
                    for r in db.execute(
                        f"SELECT * FROM {table} WHERE customer_id=? ORDER BY created DESC",
                        (customer_id,),
                    )
                ]
        return result

    def update_customer(self, customer_id, stage, notes):
        with self.db() as db:
            if (
                db.execute(
                    "UPDATE customers SET stage=?,notes=? WHERE id=?", (stage, notes, customer_id)
                ).rowcount
                != 1
            ):
                raise ValueError("Customer not found")

    def link_identity(self, customer_id, channel, external_id):
        if channel not in CHANNEL_IDS:
            raise ValueError("Unknown channel")
        with self.db() as db:
            db.execute(
                "INSERT INTO identities VALUES (?,?,?) ON CONFLICT(channel,external_id) DO UPDATE SET customer_id=excluded.customer_id",
                (channel, external_id, customer_id),
            )
            db.execute(
                "UPDATE messages SET customer_id=? WHERE channel=? AND sender_id=?",
                (customer_id, channel, external_id),
            )

    def receive(self, channel, external_id, sender_id, sender_name, content):
        if channel not in CHANNEL_IDS:
            raise ValueError("Unknown channel")
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute(
                "SELECT id FROM messages WHERE channel=? AND external_id=?", (channel, external_id)
            ).fetchone()
            if old:
                return {"id": old["id"], "duplicate": True}
            identity = db.execute(
                "SELECT customer_id FROM identities WHERE channel=? AND external_id=?",
                (channel, sender_id),
            ).fetchone()
            customer_id = identity["customer_id"] if identity else new_id()
            if not identity:
                db.execute(
                    "INSERT INTO customers VALUES (?,?,NULL,NULL,'lead','',?)",
                    (customer_id, sender_name, time.time()),
                )
                db.execute(
                    "INSERT INTO identities VALUES (?,?,?)", (channel, sender_id, customer_id)
                )
            message_id = new_id()
            db.execute(
                "INSERT INTO messages VALUES (?,?,?,?,?,'inbound','received',?,?,NULL)",
                (message_id, channel, external_id, sender_id, customer_id, content, time.time()),
            )
            return {"id": message_id, "customer_id": customer_id, "duplicate": False}

    def messages(self, customer_id=None):
        with self.db() as db:
            sql = "SELECT m.*, c.name AS customer_name FROM messages m LEFT JOIN customers c ON c.id=m.customer_id"
            params = ()
            if customer_id:
                sql += " WHERE customer_id=?"
                params = (customer_id,)
            return [dict(r) for r in db.execute(sql + " ORDER BY m.created DESC LIMIT 500", params)]

    def draft_message(self, channel, recipient, content, customer_id=None):
        if channel not in CHANNEL_IDS:
            raise ValueError("Unknown channel")
        message_id = new_id()
        with self.db() as db:
            db.execute(
                "INSERT INTO messages VALUES (?,?,NULL,?,?,'outbound','draft',?,?,NULL)",
                (message_id, channel, recipient, customer_id, content, time.time()),
            )
        return {"id": message_id, "status": "draft"}

    def claim_message(self, message_id):
        # Claim before external dispatch; repeated clicks cannot send the same draft twice.
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
            if not row or row["status"] != "draft":
                raise ValueError("Message unavailable or already dispatched")
            db.execute("UPDATE messages SET status='dispatching' WHERE id=?", (message_id,))
            return dict(row)

    def message_result(self, message_id, result):
        status = {
            "completed": "accepted_by_tool",
            "requires_confirmation": "awaiting_confirmation",
            "tool_error": "failed",
            "rejected": "rejected",
        }.get(result["status"], "uncertain")
        with self.db() as db:
            db.execute(
                "UPDATE messages SET status=?,confirmation_id=? WHERE id=?",
                (status, result.get("confirmation_id"), message_id),
            )

    def settle_confirmation(self, confirmation_id, result):
        with self.db() as db:
            row = db.execute(
                "SELECT id FROM messages WHERE confirmation_id=?", (confirmation_id,)
            ).fetchone()
        if row:
            self.message_result(row["id"], result)

    def campaigns(self):
        with self.db() as db:
            return [
                dict(row) | {"channels": json.loads(row["channels"])}
                for row in db.execute("SELECT * FROM campaigns ORDER BY created DESC")
            ]

    def create_campaign(self, title, objective, channels, budget):
        if not channels or any(c not in CHANNEL_IDS for c in channels):
            raise ValueError("Valid campaign channels required")
        campaign_id = new_id()
        with self.db() as db:
            db.execute(
                "INSERT INTO campaigns VALUES (?,?,?,?,?,'draft','',?)",
                (campaign_id, title, objective, json.dumps(channels), budget, time.time()),
            )
        return {"id": campaign_id}

    def update_campaign(self, campaign_id, status, plan):
        with self.db() as db:
            if (
                db.execute(
                    "UPDATE campaigns SET status=?,plan=? WHERE id=?", (status, plan, campaign_id)
                ).rowcount
                != 1
            ):
                raise ValueError("Campaign not found")

    def sales(self):
        with self.db() as db:
            return [
                dict(row) | {"items": json.loads(row["items"])}
                for row in db.execute(
                    "SELECT s.*,c.name AS customer_name FROM sales s JOIN customers c ON c.id=s.customer_id ORDER BY s.created DESC"
                )
            ]

    def create_sale(self, customer_id, title, items):
        sale_id = new_id()
        total = sum(item["quantity"] * item["unit_price"] for item in items)
        if total > 10**15:
            raise ValueError("Sales total exceeds supported VND limit")
        with self.db() as db:
            db.execute(
                "INSERT INTO sales VALUES (?,?,?,?,?,'quote',?)",
                (sale_id, customer_id, title, json.dumps(items), total, time.time()),
            )
        return {"id": sale_id, "total": total}

    def sale_status(self, sale_id, status):
        transitions = {
            "quote": {"quote", "order", "cancelled"},
            "order": {"order", "paid", "cancelled"},
            "paid": {"paid"},
            "cancelled": {"cancelled"},
        }
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            sale = db.execute("SELECT * FROM sales WHERE id=?", (sale_id,)).fetchone()
            if not sale or status not in transitions[sale["status"]]:
                raise ValueError("Invalid sales state transition")
            db.execute("UPDATE sales SET status=? WHERE id=?", (status, sale_id))
            if status == "paid":
                db.execute(
                    "INSERT OR IGNORE INTO ledger VALUES (?,'income',?,?,?,?)",
                    (
                        new_id(),
                        sale["total"],
                        "Đơn hàng: " + sale["title"],
                        "sale:" + sale_id,
                        time.time(),
                    ),
                )

    def list_records(self, table):
        if table not in {"tickets", "ledger", "staff"}:
            raise ValueError("Invalid table")
        with self.db() as db:
            return [dict(r) for r in db.execute(f"SELECT * FROM {table} ORDER BY created DESC")]

    def create_ticket(self, customer_id, title, description, priority):
        ticket_id = new_id()
        with self.db() as db:
            db.execute(
                "INSERT INTO tickets VALUES (?,?,?,?,?,'open',?)",
                (ticket_id, customer_id, title, description, priority, time.time()),
            )
        return {"id": ticket_id}

    def ticket_status(self, ticket_id, status):
        with self.db() as db:
            if (
                db.execute("UPDATE tickets SET status=? WHERE id=?", (status, ticket_id)).rowcount
                != 1
            ):
                raise ValueError("Ticket not found")

    def create_ledger(self, direction, amount, description):
        record_id = new_id()
        with self.db() as db:
            db.execute(
                "INSERT INTO ledger VALUES (?,?,?,?,NULL,?)",
                (record_id, direction, amount, description, time.time()),
            )
        return {"id": record_id}

    def create_staff(self, name, role, email):
        record_id = new_id()
        with self.db() as db:
            db.execute(
                "INSERT INTO staff VALUES (?,?,?,?,'active',?)",
                (record_id, name, role, email, time.time()),
            )
        return {"id": record_id}

    def staff_status(self, staff_id, status):
        with self.db() as db:
            if db.execute("UPDATE staff SET status=? WHERE id=?", (status, staff_id)).rowcount != 1:
                raise ValueError("Staff member not found")

    def analytics(self):
        with self.db() as db:
            income = db.execute(
                "SELECT COALESCE(SUM(amount),0) FROM ledger WHERE direction='income'"
            ).fetchone()[0]
            expense = db.execute(
                "SELECT COALESCE(SUM(amount),0) FROM ledger WHERE direction='expense'"
            ).fetchone()[0]
            channel_rows = [
                dict(r)
                for r in db.execute(
                    "SELECT channel,COUNT(*) AS messages FROM messages WHERE direction='inbound' GROUP BY channel"
                )
            ]
            stages = [
                dict(r)
                for r in db.execute("SELECT stage,COUNT(*) AS count FROM customers GROUP BY stage")
            ]
            tickets = db.execute(
                "SELECT COUNT(*) FROM tickets WHERE status!='resolved'"
            ).fetchone()[0]
            total = db.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
            orders = db.execute("SELECT COUNT(*) FROM sales WHERE status='paid'").fetchone()[0]
        return {
            "income": income,
            "expense": expense,
            "balance": income - expense,
            "customers": total,
            "paid_orders": orders,
            "open_tickets": tickets,
            "channels": channel_rows,
            "stages": stages,
            "currency": "VND",
            "bank_verified": False,
        }
