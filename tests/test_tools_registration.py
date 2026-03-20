"""Tests that verify all expected tools are registered on the MCP server."""

import asyncio

import pytest
from mcp.server.fastmcp import FastMCP

from server.tools import register_tools

EXPECTED_TOOLS = {
    "save_memory",
    "search_memories",
    "list_memories",
    "delete_memory",
    "update_memory",
    "get_project_context",
    "get_memory",
    "list_tags",
    "list_contributors",
    "search_by_file",
    "bulk_save_memories",
    "find_similar",
}


@pytest.fixture()
def mcp_server() -> FastMCP:
    """Create a fresh FastMCP instance with all tools registered."""
    server = FastMCP("test-synccontext")
    register_tools(server)
    return server


def test_all_tools_registered(mcp_server: FastMCP) -> None:
    """All 12 expected tools must be present after register_tools is called."""
    tools = asyncio.run(mcp_server.list_tools())
    registered_names = {t.name for t in tools}
    assert registered_names == EXPECTED_TOOLS


def test_tool_count(mcp_server: FastMCP) -> None:
    """Exactly 12 tools should be registered — no more, no less."""
    tools = asyncio.run(mcp_server.list_tools())
    assert len(tools) == 12


@pytest.mark.parametrize("tool_name", sorted(EXPECTED_TOOLS))
def test_each_tool_is_registered(mcp_server: FastMCP, tool_name: str) -> None:
    """Each individual tool must be present on the server."""
    tools = asyncio.run(mcp_server.list_tools())
    registered_names = {t.name for t in tools}
    assert tool_name in registered_names, f"Tool '{tool_name}' is not registered"


def test_tools_have_descriptions(mcp_server: FastMCP) -> None:
    """Every tool must have a non-empty description (docstring)."""
    tools = asyncio.run(mcp_server.list_tools())
    for tool in tools:
        assert tool.description, f"Tool '{tool.name}' has no description"
        assert len(tool.description.strip()) > 0, f"Tool '{tool.name}' has empty description"
