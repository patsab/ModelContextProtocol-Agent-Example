"""Example MCP client for interacting with the MCP server."""

from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client


class MCPClient:
    """A client class for interacting with the MCP (Model Control Protocol) server."""

    def __init__(self, sse_url: str = "http://localhost:8000/sse"):
        """Initialize the MCP client with server parameters."""
        self.sse_url = sse_url
        self.session = None
        self._client = None

    async def __aenter__(self) -> "MCPClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        """Async context manager exit."""
        if self.session:
            await self.session.__aexit__(exc_type, exc_val, exc_tb)
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)

    async def connect(self) -> None:
        """Establishes connection to MCP server."""
        self._client = sse_client(self.sse_url)
        self.read, self.write = await self._client.__aenter__()
        session = ClientSession(self.read, self.write)
        self.session = await session.__aenter__()
        await self.session.initialize()

    async def get_available_tools(self) -> list[Any]:
        """Retrieve a list of available tools from the MCP server."""
        if not self.session:
            msg = "Not connected to MCP server"
            raise RuntimeError(msg)

        tools = await self.session.list_tools()
        return tools.tools

    def call_tool(self, tool_name: str) -> Any:  # noqa: ANN401
        """Create a callable function for a specific tool.

        This allows us to execute database operations through the MCP server.

        Args:
            tool_name: The name of the tool to create a callable for

        Returns:
            A callable async function that executes the specified tool

        """
        if not self.session:
            msg = "Not connected to MCP server"
            raise RuntimeError(msg)

        async def tool_callable(**kwargs) -> str:
            response = await self.session.call_tool(tool_name, arguments=kwargs)
            return response.content[0].text

        return tool_callable
