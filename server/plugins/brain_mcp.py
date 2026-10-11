"""Real MCP server; the Hub supplies the local data directory through subprocess env."""

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from server.core.brain import Brain

mcp = FastMCP("BDSG Second Brain")
brain = Brain(Path(os.environ["BDSG_BRAIN_DIR"]))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def list_notes() -> list[dict]:
    """List the owner's Markdown notes."""
    return brain.notes()


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def read_note(path: str) -> str:
    """Read a note from memory/ or wiki/."""
    return brain.note_path(path).read_text(encoding="utf-8")


@mcp.tool()
def write_note(path: str, content: str) -> dict:
    """Save reviewed Markdown knowledge. Requires owner confirmation by default."""
    if len(content) > 100_000:
        raise ValueError("Note too large")
    return brain.write_note(path, content)


if __name__ == "__main__":
    mcp.run(transport="stdio")
