"""Editorial MCP tools intentionally cannot publish or change homepage/settings."""

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from server.core.cms import CMSStore

mcp = FastMCP("BDSG CMS")
store = CMSStore(Path(os.environ["BDSG_CMS_DB"]))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def list_content(kind: str = "post") -> list[dict]:
    """List local editorial drafts and their version numbers."""
    return store.list(kind)


@mcp.tool()
def save_content_draft(
    content: dict, content_id: str | None = None, expected_version: int | None = None
) -> dict:
    """Save a typed post/page draft after Hub approval; never publishes. Supply the exact existing version when editing."""
    return store.save(content, content_id, expected_version)


if __name__ == "__main__":
    mcp.run(transport="stdio")
