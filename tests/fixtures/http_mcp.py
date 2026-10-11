import sys

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("HTTP integration test", host="127.0.0.1", port=int(sys.argv[1]), stateless_http=True)


@mcp.tool()
def echo(message: str) -> str:
    """Echo for a real Streamable HTTP transport test."""
    return message


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
