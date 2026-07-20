"""End-to-end MCP client handshake used by local verification."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run() -> None:
    root = Path(__file__).resolve().parents[1]
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "cockpit_mcp.server"],
        cwd=str(root),
    )
    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            resources = await session.list_resources()
            prompts = await session.list_prompts()
            status = await session.call_tool("cockpit_status", {})
            sentiment = await session.call_tool("get_market_sentiment", {})
            videos = await session.call_tool("search_videos", {"market": "ID", "limit": 3})
            read_only = sum(bool(tool.annotations and tool.annotations.readOnlyHint) for tool in tools.tools)
            print(json.dumps({
                "tool_count": len(tools.tools),
                "tool_names": [tool.name for tool in tools.tools],
                "read_only_tool_count": read_only,
                "resource_count": len(resources.resources),
                "prompt_count": len(prompts.prompts),
                "status_error": status.isError,
                "sentiment_error": sentiment.isError,
                "videos_error": videos.isError,
            }, indent=2))


if __name__ == "__main__":
    asyncio.run(run())
