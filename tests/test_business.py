import hashlib
import hmac
import json
import time

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from server.config import Settings
from server.core.business import BusinessStore, render_arguments
from server.main import create_app


@pytest.fixture
def store(tmp_path):
    return BusinessStore(tmp_path / "business.db", Fernet.generate_key().decode())


def test_inbound_dedup_and_explicit_identity_link(store):
    first = store.receive("zalo", "m1", "z1", "An", "Xin chào")
    assert store.receive("zalo", "m1", "z1", "An", "Xin chào")["duplicate"]
    second = store.receive("facebook", "m1", "f1", "An", "Tư vấn")
    assert first["customer_id"] != second["customer_id"]
    store.link_identity(first["customer_id"], "facebook", "f1")
    third = store.receive("facebook", "m2", "f1", "An", "Báo giá")
    assert third["customer_id"] == first["customer_id"]
    assert len(store.customer(first["customer_id"])["messages"]) == 3


def test_sales_amounts_state_and_idempotent_receipt(store):
    customer = store.create_customer("An")
    sale = store.create_sale(
        customer["id"], "Dịch vụ", [{"name": "Gói", "quantity": 3, "unit_price": 125000}]
    )
    assert sale["total"] == 375000
    with pytest.raises(ValueError):
        store.sale_status(sale["id"], "paid")
    store.sale_status(sale["id"], "order")
    store.sale_status(sale["id"], "paid")
    store.sale_status(sale["id"], "paid")
    assert len(store.list_records("ledger")) == 1
    assert store.analytics()["income"] == 375000
    with pytest.raises(ValueError):
        store.sale_status(sale["id"], "cancelled")


def test_draft_claim_and_confirmation_tracking(store):
    draft = store.draft_message("email", "recipient", "Content")
    store.claim_message(draft["id"])
    with pytest.raises(ValueError):
        store.claim_message(draft["id"])
    store.message_result(draft["id"], {"status": "requires_confirmation", "confirmation_id": "c1"})
    assert store.messages()[0]["status"] == "awaiting_confirmation"
    store.settle_confirmation("c1", {"status": "completed"})
    assert store.messages()[0]["status"] == "accepted_by_tool"
    assert render_arguments({"to": "$recipient", "nested": ["$content"]}, "user", "$(evil)") == {
        "to": "user",
        "nested": ["$(evil)"],
    }


def test_webhook_signature_replay_and_owner_boundary(tmp_path):
    settings = Settings(
        "o" * 40,
        "a" * 40,
        Fernet.generate_key().decode(),
        tmp_path,
        ("http://testserver",),
        ("testserver",),
    )
    with TestClient(create_app(settings)) as client:
        owner = {"Authorization": "Bearer " + "o" * 40}
        agent = {"Authorization": "Bearer " + "a" * 40}
        assert client.get("/api/business/customers", headers=agent).status_code == 403
        assert (
            client.post("/api/business/customers", headers=owner, json={"name": "An"}).status_code
            == 200
        )
        assert (
            client.post(
                "/api/business/sales",
                headers=owner,
                json={
                    "customer_id": "missing",
                    "title": "Invalid",
                    "items": [{"name": "x", "quantity": 1, "unit_price": 1}],
                },
            ).status_code
            == 422
        )
        key = "k" * 40
        assert (
            client.put(
                "/api/business/channels/website", headers=owner, json={"webhook_secret": key}
            ).status_code
            == 200
        )
        assert key not in client.get("/api/business/channels", headers=owner).text
        raw = json.dumps(
            {"external_id": "m1", "sender_id": "u1", "sender_name": "Bình", "content": "Hello"}
        ).encode()
        stamp = str(int(time.time()))
        signature = hmac.new(key.encode(), stamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
        headers = {"x-bdsg-timestamp": stamp, "x-bdsg-signature": signature}
        assert client.post("/api/business/webhooks/website", content=raw).status_code == 401
        assert (
            client.post("/api/business/webhooks/website", content=raw, headers=headers).json()[
                "duplicate"
            ]
            is False
        )
        assert (
            client.post("/api/business/webhooks/website", content=raw, headers=headers).json()[
                "duplicate"
            ]
            is True
        )
        assert (
            client.post(
                "/api/business/webhooks/website", content=raw + b" ", headers=headers
            ).status_code
            == 401
        )
        headers["x-bdsg-timestamp"] = "1"
        headers["x-bdsg-signature"] = hmac.new(
            key.encode(), b"1." + raw, hashlib.sha256
        ).hexdigest()
        assert (
            client.post("/api/business/webhooks/website", content=raw, headers=headers).status_code
            == 401
        )


def test_business_mcp_writes_require_owner_confirmation(tmp_path):
    settings = Settings(
        "o" * 40,
        "a" * 40,
        Fernet.generate_key().decode(),
        tmp_path,
        ("http://testserver",),
        ("testserver",),
    )
    with TestClient(create_app(settings)) as client:
        agent = {"Authorization": "Bearer " + "a" * 40}
        owner = {"Authorization": "Bearer " + "o" * 40}
        pending = client.post(
            "/api/mcp/business-write/call",
            headers=agent,
            json={"tool": "create_customer", "arguments": {"name": "From AI"}},
        )
        assert pending.json()["status"] == "requires_confirmation"
        assert client.get("/api/business/customers", headers=owner).json() == []
        result = client.post(
            "/api/confirmations/" + pending.json()["confirmation_id"] + "/decision",
            headers=owner,
            json={"approved": True},
        )
        assert result.json()["status"] == "completed"
        assert client.get("/api/business/customers", headers=owner).json()[0]["name"] == "From AI"
        read = client.post(
            "/api/mcp/business-read/call",
            headers=agent,
            json={"tool": "business_analytics", "arguments": {}},
        )
        assert read.json()["status"] == "completed"


def test_outbox_uses_hub_confirmation_and_single_dispatch(tmp_path):
    settings = Settings(
        "o" * 40,
        "a" * 40,
        Fernet.generate_key().decode(),
        tmp_path,
        ("http://testserver",),
        ("testserver",),
    )
    with TestClient(create_app(settings)) as client:
        headers = {"Authorization": "Bearer " + "o" * 40}
        # A real local MCP write acts as the transport fixture, not as an email provider.
        assert (
            client.put(
                "/api/business/channels/website",
                headers=headers,
                json={
                    "connector": "business-write",
                    "send_tool": "create_customer",
                    "argument_template": {"name": "$content"},
                },
            ).status_code
            == 200
        )
        draft = client.post(
            "/api/business/inbox/drafts",
            headers=headers,
            json={"channel": "website", "recipient": "fixture", "content": "Reviewed write"},
        ).json()
        send_path = "/api/business/inbox/" + draft["id"] + "/send"
        pending = client.post(send_path, headers=headers, json={}).json()
        assert pending["status"] == "requires_confirmation"
        assert client.get("/api/business/customers", headers=headers).json() == []
        assert client.post(send_path, headers=headers, json={}).status_code == 422
        confirmation_path = "/api/confirmations/" + pending["confirmation_id"] + "/decision"
        assert (
            client.post(confirmation_path, headers=headers, json={"approved": True}).json()[
                "status"
            ]
            == "completed"
        )
        assert (
            client.get("/api/business/inbox", headers=headers).json()[0]["status"]
            == "accepted_by_tool"
        )
        assert (
            client.post(confirmation_path, headers=headers, json={"approved": True}).status_code
            == 403
        )
        assert len(client.get("/api/business/customers", headers=headers).json()) == 1
