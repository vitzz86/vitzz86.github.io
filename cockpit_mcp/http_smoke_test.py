"""Local Streamable HTTP handshake for Project Cockpit MCP."""

from __future__ import annotations

import asyncio
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def run() -> None:
    url = os.getenv("COCKPIT_MCP_TEST_URL", "http://127.0.0.1:8790/mcp")
    token = os.getenv("COCKPIT_MCP_BEARER_TOKEN", "").strip()
    headers = {"Authorization": "Bearer %s" % token} if token else None
    async with streamablehttp_client(url, headers=headers) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool("search_news", {"market": "ID", "limit": 2})
            read_only = sum(bool(tool.annotations and tool.annotations.readOnlyHint) for tool in tools.tools)
            print("HTTP tools=%d read_only=%d search_news_error=%s" % (
                len(tools.tools), read_only, result.isError,
            ))


if __name__ == "__main__":
    asyncio.run(run())
