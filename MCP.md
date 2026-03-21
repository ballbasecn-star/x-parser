# MCP Configuration Example

This document explains how to configure the X Parser MCP server for use with Claude Desktop or other MCP-compatible AI assistants.

## Prerequisites

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set your Tavily API key:
   ```bash
   export TAVILY_API_KEY=your_api_key_here
   ```

## Claude Desktop Configuration

Add the following to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "x-parser": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/path/to/x-parser",
      "env": {
        "TAVILY_API_KEY": "tvly-dev-your-key-here"
      }
    }
  }
}
```

Replace `/path/to/x-parser` with the actual path to this project.

## Alternative: Using uvx

If you have `uv` installed, you can use `uvx` for automatic dependency management:

```json
{
  "mcpServers": {
    "x-parser": {
      "command": "uvx",
      "args": [
        "--directory", "/path/to/x-parser",
        "run", "python", "-m", "mcp_server.server"
      ],
      "env": {
        "TAVILY_API_KEY": "tvly-dev-your-key-here"
      }
    }
  }
}
```

## Available Tools

### parse_tweet

Parse a Twitter/X tweet URL and extract its content.

**Parameters:**
- `url` (string, required): The Twitter/X tweet URL

**Example usage in Claude:**
```
Please parse this tweet: https://x.com/elonmusk/status/123456789
```

**Returns:**
- Author information (name, username)
- Post content (cleaned text)
- Engagement metrics (likes, retweets, replies, views, bookmarks)
- Images (if any)
- Hashtags and mentions

## Testing

Test the MCP server locally:

```bash
# Set environment variable
export TAVILY_API_KEY=your_key

# Run the server
python -m mcp_server.server
```

You can also use the MCP Inspector for debugging:

```bash
npx @anthropic-ai/mcp-inspector python -m mcp_server.server
```

## Troubleshooting

### "MCP package not installed"
Run: `pip install mcp`

### "TAVILY_API_KEY not set"
Make sure the environment variable is set in your configuration or shell.

### "Failed to parse tweet"
- Check if the URL is valid
- Verify your Tavily API key is working
- Check if the tweet is publicly accessible