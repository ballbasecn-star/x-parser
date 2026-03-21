"""
MCP Server for X/Twitter Parser

This module provides an MCP (Model Context Protocol) server that allows
AI assistants to parse Twitter/X tweets.

Usage:
    # Local (stdio)
    python -m mcp_server.server

    # Remote (HTTP/SSE)
    python -m mcp_server.server --transport sse --port 8080

Claude Desktop config (local):
    {
        "mcpServers": {
            "x-parser": {
                "command": "python",
                "args": ["-m", "mcp_server.server"],
                "env": {
                    "TAVILY_API_KEY": "your_api_key"
                }
            }
        }
    }

Claude Code config (remote):
    {
        "mcpServers": {
            "x-parser": {
                "url": "https://your-server.com/sse"
            }
        }
    }
"""
import os
import sys
import argparse
import logging
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("MCP package not installed. Run: pip install mcp")
    sys.exit(1)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from xparser.parser import parse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server instance
server = Server("x-parser")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="parse_tweet",
            description="""Parse a Twitter/X tweet URL and extract its content.

Use this tool when you need to:
- Extract the full text content from a tweet
- Get engagement metrics (likes, retweets, replies, views)
- Retrieve images from a tweet
- Parse long articles/posts from X

Returns:
- content: The cleaned text content of the tweet
- metrics: Engagement data (likes, retweets, replies, views, bookmarks)
- images: List of image URLs
- title: Article title (if it's a long article)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The Twitter/X tweet URL to parse. "
                        "Format: https://x.com/username/status/123456789 "
                        "or https://twitter.com/username/status/123456789"
                    }
                },
                "required": ["url"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    if name != "parse_tweet":
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]

    url = arguments.get("url", "").strip()

    if not url:
        return [TextContent(
            type="text",
            text="Error: URL is required"
        )]

    # Validate URL
    if "x.com/" not in url and "twitter.com/" not in url:
        return [TextContent(
            type="text",
            text="Error: Invalid URL. Must be a Twitter/X tweet URL."
        )]

    logger.info(f"Parsing tweet: {url}")

    try:
        result = parse(url)

        if not result.success:
            return [TextContent(
                type="text",
                text=f"Error: {result.error}"
            )]

        tweet = result.tweet

        # Format response
        response_parts = []

        # Basic info
        response_parts.append(f"**Author:** {tweet.display_name} (@{tweet.username})")
        response_parts.append(f"**URL:** {tweet.url}")
        response_parts.append(f"**Posted:** {tweet.created_at}")
        response_parts.append("")

        # Title (if article)
        if tweet.title:
            response_parts.append(f"**Title:** {tweet.title}")
            response_parts.append("")

        # Metrics
        metrics = tweet.metrics
        metrics_str = (
            f"**Metrics:** "
            f"{metrics.replies} replies | "
            f"{metrics.retweets} reposts | "
            f"{metrics.likes} likes | "
            f"{metrics.views} views | "
            f"{metrics.bookmarks} bookmarks"
        )
        response_parts.append(metrics_str)
        response_parts.append("")

        # Content
        response_parts.append("**Content:**")
        response_parts.append(tweet.content_clean)

        # Images
        if tweet.images:
            response_parts.append("")
            response_parts.append(f"**Images ({len(tweet.images)}):**")
            for i, img in enumerate(tweet.images[:5], 1):
                response_parts.append(f"{i}. {img}")
            if len(tweet.images) > 5:
                response_parts.append(f"... and {len(tweet.images) - 5} more")

        # Hashtags
        if tweet.hashtags:
            response_parts.append("")
            response_parts.append(f"**Hashtags:** {' '.join(tweet.hashtags)}")

        return [TextContent(
            type="text",
            text="\n".join(response_parts)
        )]

    except Exception as e:
        logger.exception("Failed to parse tweet")
        return [TextContent(
            type="text",
            text=f"Error: Failed to parse tweet - {str(e)}"
        )]


def main():
    """Run the MCP server."""
    parser = argparse.ArgumentParser(description="X Parser MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport type: stdio (local) or sse (remote)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8080")),
        help="Port for SSE transport (default: 8080)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for SSE transport (default: 0.0.0.0)"
    )

    args = parser.parse_args()

    # Check for API key
    if not os.getenv("TAVILY_API_KEY"):
        logger.warning("TAVILY_API_KEY not set. Set it in environment variables.")

    import asyncio

    if args.transport == "stdio":
        logger.info("Starting X Parser MCP Server (stdio mode)...")
        asyncio.run(stdio_server(server).serve())
    else:
        # SSE mode for remote deployment
        logger.info(f"Starting X Parser MCP Server (SSE mode) on {args.host}:{args.port}...")
        try:
            from mcp.server.sse import SseServerTransport
            from starlette.applications import Starlette
            from starlette.routing import Route
        except ImportError as e:
            print(f"SSE transport requires additional packages: {e}")
            print("Install with: pip install mcp[cli] starlette uvicorn")
            sys.exit(1)

        sse = SseServerTransport("/messages")

        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,
            ) as streams:
                await server.run(
                    streams[0],
                    streams[1],
                    server.create_initialization_options(),
                )

        async def handle_messages(request):
            await sse.handle_post_message(request._receive, request._send)

        app = Starlette(
            routes=[
                Route("/sse", endpoint=handle_sse),
                Route("/messages", endpoint=handle_messages, methods=["POST"]),
            ]
        )

        import uvicorn
        uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()