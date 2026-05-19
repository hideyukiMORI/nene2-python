"""LocalMcpServer — thin wrapper around FastMCP with NENE2 defaults.

Provides the framework scaffolding; tool registration is done in the
application layer (example/mcp.py) using the .tool() decorator.
"""

from collections.abc import Callable
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP


class LocalMcpServer:
    """MCP server with sensible defaults for local / stdio transport."""

    def __init__(self, name: str, instructions: str = "") -> None:
        self._mcp = FastMCP(name, instructions=instructions)

    def tool(self, description: str = "") -> Callable[[Any], Any]:
        """Register a function as an MCP tool."""
        return self._mcp.tool(description=description)

    def run(self, transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None:
        """Start the MCP server. Blocks until the client disconnects."""
        self._mcp.run(transport=transport)
