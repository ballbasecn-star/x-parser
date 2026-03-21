"""
MCP (Model Context Protocol) Server for X Parser

This module provides an MCP server that allows AI assistants
to parse Twitter/X tweets.

Usage:
    python -m mcp.server
"""

from .server import server, main

__all__ = ["server", "main"]