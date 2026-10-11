"""Owner-operated business modules; outbound integrations always call MCP Hub."""

import hashlib
import hmac
import json
import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from server.api.security import owner
from server.core.business import render_arguments
from server.core.mcp_store import PolicyError

router = APIRouter(prefix="/api/business", dependencies=[Depends(owner)])
webhooks = APIRouter(prefix="/api/business")


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CustomerInput(Input):
    name: str = Field(min_length=1, max_length=256)
    email: str | None = Field(default=None, max_length=256)
    phone: str | None = Field(default=None, max_length=64)
    stage: Literal["lead", "prospect", "customer", "loyal"] = "lead"
    notes: str = Field(default="", max_length=20000)


class CustomerUpdate(Input):
    stage: Literal["lead", "prospect", "customer", "loyal"]
    notes: str = Field(default="", max_length=20000)


class IdentityInput(Input):
    channel: str
    external_id: str = Field(min_length=1, max_length=256)


class ChannelInput(Input):
    connector: str | None = None
    read_tool: str | None = None
    send_tool: str | None = None
    argument_template: dict = Field(
        default_factory=lambda: {"recipient": "$recipient", "content": "$content"}
    )
    enabled: bool = True
    webhook_secret: str | None = Field(default=None, max_length=256)


class InvokeInput(Input):
    arguments: dict = Field(default_factory=dict)


class InboundInput(Input):
    external_id: str = Field(min_length=1, max_length=256)
    sender_id: str = Field(min_length=1, max_length=256)
    sender_name: str = Field(min_length=1, max_length=256)
    content: str = Field(min_length=1, max_length=20000)


class DraftInput(Input):
    channel: str
    recipient: str = Field(min_length=1, max_length=256)
    content: str = Field(min_length=1, max_length=20000)
    customer_id: str | None = None


class CampaignInput(Input):
    title: str = Field(min_length=1, max_length=256)
    objective: str = Field(min_length=1, max_length=4000)
    channels: list[str] = Field(min_length=1, max_length=9)
    budget: int = Field(default=0, ge=0, le=10**15, strict=True)


class CampaignUpdate(Input):
    status: Literal["draft", "planned", "done"]
    plan: str = Field(default="", max_length=50000)


class SaleItem(Input):
    name: str = Field(min_length=1, max_length=256)
    quantity: int = Field(ge=1, le=100000, strict=True)
    unit_price: int = Field(ge=0, le=10**12, strict=True)


class SaleInput(Input):
    customer_id: str
    title: str = Field(min_length=1, max_length=256)
    items: list[SaleItem] = Field(min_length=1, max_length=100)


class SaleUpdate(Input):
    status: Literal["quote", "order", "paid", "cancelled"]


class TicketInput(Input):
    customer_id: str | None = None
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(default="", max_length=20000)
    priority: Literal["normal", "high"] = "normal"


class TicketUpdate(Input):
    status: Literal["open", "doing", "resolved"]


class LedgerInput(Input):
    direction: Literal["income", "expense"]
    amount: int = Field(gt=0, le=10**15, strict=True)
    description: str = Field(min_length=1, max_length=1000)


class StaffInput(Input):
    name: str = Field(min_length=1, max_length=256)
    role: str = Field(min_length=1, max_length=256)
    email: str | None = Field(default=None, max_length=256)


class StaffUpdate(Input):
    status: Literal["active", "leave", "inactive"]


@router.get("/customers")
def customers(request: Request):
    return request.app.state.business.customers()


@router.post("/customers")
def create_customer(body: CustomerInput, request: Request):
    return request.app.state.business.create_customer(**body.model_dump())


@router.get("/customers/{customer_id}")
def customer(customer_id: str, request: Request):
    return request.app.state.business.customer(customer_id)


@router.patch("/customers/{customer_id}")
def update_customer(customer_id: str, body: CustomerUpdate, request: Request):
    request.app.state.business.update_customer(customer_id, **body.model_dump())
    return {"updated": True}


@router.post("/customers/{customer_id}/identities")
def link_identity(customer_id: str, body: IdentityInput, request: Request):
    request.app.state.business.link_identity(customer_id, **body.model_dump())
    return {"linked": True}


@router.get("/channels")
def channels(request: Request):
    from server.integrations.catalog import CATALOG

    return {"channels": request.app.state.business.channels(), "official_catalog": CATALOG}


@router.put("/channels/{channel}")
def configure_channel(channel: str, body: ChannelInput, request: Request):
    if body.connector:
        request.app.state.store.connector(body.connector)
    if body.webhook_secret and len(body.webhook_secret) < 32:
        raise ValueError("Webhook secret must contain at least 32 characters")
    request.app.state.business.configure_channel(channel, **body.model_dump())
    return {"configured": True}


@router.post("/channels/{channel}/test")
async def test_channel(channel: str, request: Request):
    config = request.app.state.business.channel(channel)
    if not config["connector"]:
        raise ValueError("Configure an MCP connector first")
    try:
        tools = await request.app.state.hub.list_tools(config["connector"])
        names = {tool["name"] for tool in tools}
        expected = {name for name in (config["read_tool"], config["send_tool"]) if name}
        okay = bool(expected) and expected <= names
        request.app.state.business.record_test(channel, okay)
        return {"mcp_reachable": okay, "tools": sorted(names), "account_access_verified": False}
    except Exception as exc:
        request.app.state.business.record_test(channel, False)
        raise HTTPException(502, "MCP discovery failed; check configuration") from exc


@router.post("/channels/{channel}/read")
async def read_channel(channel: str, body: InvokeInput, request: Request):
    config = request.app.state.business.channel(channel)
    if not config["connector"] or not config["read_tool"]:
        raise ValueError("Configure a read tool first")
    policy = request.app.state.store.connector(config["connector"])
    if policy.tools.get(config["read_tool"]) is not True:
        raise PolicyError("Channel read tool must be explicitly owner-reviewed as read-only")
    return await request.app.state.hub.call_tool(
        config["connector"], config["read_tool"], body.arguments, actor="owner"
    )


@router.get("/inbox")
def inbox(request: Request, customer_id: str | None = None):
    return request.app.state.business.messages(customer_id)


@router.post("/inbox/{channel}/import")
def import_message(channel: str, body: InboundInput, request: Request):
    # Explicit owner import; never presented as a live provider connection.
    return request.app.state.business.receive(channel, **body.model_dump())


@webhooks.post("/webhooks/{channel}")
async def webhook(channel: str, request: Request):
    raw = await request.body()
    if len(raw) > 100000:
        raise HTTPException(413, "Webhook too large")
    timestamp = request.headers.get("x-bdsg-timestamp", "")
    signature = request.headers.get("x-bdsg-signature", "")
    try:
        fresh = abs(time.time() - int(timestamp)) <= 300
        key = request.app.state.business.webhook_key(channel)
    except ValueError as exc:
        raise HTTPException(401, "Webhook authentication failed") from exc
    expected = hmac.new(key, timestamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
    if not fresh or not hmac.compare_digest(signature.encode(), expected.encode()):
        raise HTTPException(401, "Webhook authentication failed")
    body = InboundInput.model_validate(json.loads(raw))
    return request.app.state.business.receive(channel, **body.model_dump())


@router.post("/inbox/drafts")
def draft_message(body: DraftInput, request: Request):
    return request.app.state.business.draft_message(**body.model_dump())


@router.post("/inbox/{message_id}/send")
async def send_message(message_id: str, request: Request):
    business = request.app.state.business
    # Check configuration before claim: missing setup should leave the draft editable.
    record = next((m for m in business.messages() if m["id"] == message_id), None)
    if not record:
        raise ValueError("Message not found")
    config = business.channel(record["channel"])
    if not config["connector"] or not config["send_tool"]:
        raise ValueError("This channel has no MCP send tool configured")
    message = business.claim_message(message_id)
    arguments = render_arguments(
        config["argument_template"], message["sender_id"], message["content"]
    )
    try:
        result = await request.app.state.hub.call_tool(
            config["connector"], config["send_tool"], arguments, actor="owner"
        )
    except PolicyError:
        business.message_result(message_id, {"status": "tool_error"})
        raise
    except BaseException:
        business.message_result(message_id, {"status": "uncertain"})
        raise
    business.message_result(message_id, result)
    return result


@router.get("/campaigns")
def campaigns(request: Request):
    return request.app.state.business.campaigns()


@router.post("/campaigns")
def create_campaign(body: CampaignInput, request: Request):
    return request.app.state.business.create_campaign(**body.model_dump())


@router.patch("/campaigns/{campaign_id}")
def update_campaign(campaign_id: str, body: CampaignUpdate, request: Request):
    request.app.state.business.update_campaign(campaign_id, **body.model_dump())
    return {"updated": True}


@router.get("/sales")
def sales(request: Request):
    return request.app.state.business.sales()


@router.post("/sales")
def create_sale(body: SaleInput, request: Request):
    return request.app.state.business.create_sale(**body.model_dump())


@router.patch("/sales/{sale_id}")
def sale_status(sale_id: str, body: SaleUpdate, request: Request):
    request.app.state.business.sale_status(sale_id, body.status)
    return {"updated": True}


@router.get("/tickets")
def tickets(request: Request):
    return request.app.state.business.list_records("tickets")


@router.post("/tickets")
def create_ticket(body: TicketInput, request: Request):
    return request.app.state.business.create_ticket(**body.model_dump())


@router.patch("/tickets/{ticket_id}")
def ticket_status(ticket_id: str, body: TicketUpdate, request: Request):
    request.app.state.business.ticket_status(ticket_id, body.status)
    return {"updated": True}


@router.get("/ledger")
def ledger(request: Request):
    return request.app.state.business.list_records("ledger")


@router.post("/ledger")
def create_ledger(body: LedgerInput, request: Request):
    return request.app.state.business.create_ledger(**body.model_dump())


@router.get("/staff")
def staff(request: Request):
    return request.app.state.business.list_records("staff")


@router.post("/staff")
def create_staff(body: StaffInput, request: Request):
    return request.app.state.business.create_staff(**body.model_dump())


@router.patch("/staff/{staff_id}")
def staff_status(staff_id: str, body: StaffUpdate, request: Request):
    request.app.state.business.staff_status(staff_id, body.status)
    return {"updated": True}


@router.get("/analytics")
def analytics(request: Request):
    return request.app.state.business.analytics()
