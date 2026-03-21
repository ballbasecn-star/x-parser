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

---

## Cloud Deployment (Remote MCP Server)

You can deploy the MCP server to the cloud and connect Claude Code remotely.

### Running in SSE Mode

```bash
# Install additional dependencies
pip install starlette uvicorn

# Run with SSE transport
python -m mcp_server.server --transport sse --port 8080

# Or with environment variable
TAVILY_API_KEY=your_key python -m mcp_server.server --transport sse --port 8080
```

The server will be available at:
- SSE endpoint: `http://localhost:8080/sse`
- Messages: `http://localhost:8080/messages`

### Claude Code Configuration (Remote)

In your `.claude/settings.json` or Claude Code config:

```json
{
  "mcpServers": {
    "x-parser": {
      "url": "https://your-server.com/sse"
    }
  }
}
```

### Deploy to Cloud Platforms

#### Railway

1. Create `railway.json`:
   ```json
   {
     "$schema": "https://railway.app/railway.schema.json",
     "build": {
       "builder": "NIXPACKS"
     },
     "deploy": {
       "startCommand": "python -m mcp_server.server --transport sse --port $PORT",
       "restartPolicyType": "ON_FAILURE"
     }
   }
   ```

2. Set environment variable: `TAVILY_API_KEY`

3. Deploy: `railway up`

#### Fly.io

1. Create `fly.toml`:
   ```toml
   app = "x-parser-mcp"
   primary_region = "sin"

   [build]
     builder = "paketobuildpacks/builder:base"

   [env]
     PORT = "8080"

   [[services]]
     internal_port = 8080
     protocol = "tcp"

     [[services.ports]]
       handlers = ["http"]
       port = 80

     [[services.ports]]
       handlers = ["tls", "http"]
       port = 443
   ```

2. Deploy:
   ```bash
   fly launch
   fly secrets set TAVILY_API_KEY=your_key
   fly deploy
   ```

#### Render

1. Create a Web Service
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `python -m mcp_server.server --transport sse --port $PORT`
4. Add environment variable: `TAVILY_API_KEY`

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080

EXPOSE 8080

CMD ["python", "-m", "mcp_server.server", "--transport", "sse", "--port", "8080"]
```

Build and run:
```bash
docker build -t x-parser-mcp .
docker run -p 8080:8080 -e TAVILY_API_KEY=your_key x-parser-mcp
```

### Security Considerations

When deploying to the cloud:

1. **API Key Protection**: Never expose your TAVILY_API_KEY in client config
2. **Rate Limiting**: Consider adding rate limiting to prevent abuse
3. **Authentication**: For production, add authentication to the MCP endpoints
4. **HTTPS**: Always use HTTPS in production