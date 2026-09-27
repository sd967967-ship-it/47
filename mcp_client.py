"""
MCP (Model Context Protocol) integration for 47.

This is the fix for "shallow action depth." Instead of only running the
hardcoded commands in actions.py, 47 can now use any MCP server's
tools — and the LLM decides *when* and *how* to chain them itself
(e.g. "fetch that page and summarize the pricing section" becomes:
call fetch -> read result -> reason about it -> reply), all in one turn.

Free and open protocol, no cost. Servers run locally as subprocesses.

SETUP:
    pip install mcp mcp-server-fetch
On first run this creates mcp_servers.json with the free "fetch" server
already configured (lets 47 retrieve and read any URL, converted to
clean markdown). Add more servers by adding entries to that file — see
https://github.com/modelcontextprotocol/servers for a list of free ones
(filesystem, git, sqlite, github, slack, etc.)
"""

import asyncio
import json
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

CONFIG_PATH = Path(__file__).parent / "mcp_servers.json"

_tools_cache = None  # avoid re-spawning server subprocesses on every message


def _load_config():
    if not CONFIG_PATH.exists():
        default = [
            {"name": "fetch", "command": "python", "args": ["-m", "mcp_server_fetch"]}
        ]
        CONFIG_PATH.write_text(json.dumps(default, indent=2))
        return default
    return json.loads(CONFIG_PATH.read_text())


async def _list_tools_async(server_cfg):
    params = StdioServerParameters(command=server_cfg["command"], args=server_cfg.get("args", []))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            return [
                {
                    "type": "function",
                    "function": {
                        "name": f'{server_cfg["name"]}__{t.name}',
                        "description": t.description or "",
                        "parameters": t.inputSchema or {"type": "object", "properties": {}},
                    },
                }
                for t in tools.tools
            ]


async def _call_tool_async(server_cfg, tool_name, arguments):
    params = StdioServerParameters(command=server_cfg["command"], args=server_cfg.get("args", []))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            parts = [c.text for c in result.content if hasattr(c, "text")]
            return "\n".join(parts) if parts else str(result)


def list_all_tools(force_refresh: bool = False):
    """OpenAI/Groq-style function-calling tool defs from every configured MCP server. Cached."""
    global _tools_cache
    if _tools_cache is not None and not force_refresh:
        return _tools_cache

    servers = _load_config()
    all_tools = []
    for server in servers:
        try:
            tools = asyncio.run(_list_tools_async(server))
            all_tools.extend(tools)
        except Exception as e:
            print(f"[MCP] Couldn't list tools from '{server['name']}': {e}")
    _tools_cache = all_tools
    return all_tools


def call_tool(qualified_name: str, arguments: dict) -> str:
    """qualified_name is 'servername__toolname', e.g. 'fetch__fetch'."""
    servers = _load_config()
    server_name, _, tool_name = qualified_name.partition("__")
    server_cfg = next((s for s in servers if s["name"] == server_name), None)
    if not server_cfg:
        return f"No MCP server named '{server_name}' configured."
    try:
        return asyncio.run(_call_tool_async(server_cfg, tool_name, arguments))
    except Exception as e:
        return f"MCP tool call failed: {e}"
