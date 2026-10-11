"""Local business MCP tools. Hub policies enforce reviewed writes before dispatch."""

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from server.api.business import CampaignInput, CustomerInput, TicketInput
from server.core.business import BusinessStore

mcp = FastMCP("BDSG Business")
store = BusinessStore(Path(os.environ["BDSG_BUSINESS_DB"]), os.environ["BDSG_STORE_KEY"])


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def list_customers() -> list[dict]:
    """Read Customer 360 records."""
    return store.customers()


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def list_inbox() -> list[dict]:
    """Read normalized local inbox messages."""
    return store.messages()


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def business_analytics() -> dict:
    """Read local income, expense, customer and support metrics."""
    return store.analytics()


@mcp.tool()
def create_customer(name: str, email: str | None = None, phone: str | None = None) -> dict:
    """Create a local customer after owner approval through Hub."""
    return store.create_customer(**CustomerInput(name=name, email=email, phone=phone).model_dump())


@mcp.tool()
def create_campaign(title: str, objective: str, channels: list[str], budget: int = 0) -> dict:
    """Save a local campaign draft; does not publish external content."""
    return store.create_campaign(
        **CampaignInput(
            title=title, objective=objective, channels=channels, budget=budget
        ).model_dump()
    )


@mcp.tool()
def create_ticket(title: str, description: str = "", customer_id: str | None = None) -> dict:
    """Create a local support ticket after owner approval."""
    return store.create_ticket(
        **TicketInput(title=title, description=description, customer_id=customer_id).model_dump()
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
