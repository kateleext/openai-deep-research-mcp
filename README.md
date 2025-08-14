# OpenAI Deep Research MCP Server

A Model Context Protocol (MCP) server that proxies to OpenAI's Deep Research capabilities via the Responses API. This allows Claude Code to leverage OpenAI's o3/o4 deep research models for complex research tasks, particularly useful for demand compass analyses in the Takuma OS ecosystem.

## Quick Start for Team Members

### Prerequisites
- Claude Code CLI installed
- OpenAI API key with Deep Research access
- Python 3.11+ on your system

### Installation (5 minutes)

1. **Clone this repo** (or use as submodule):
```bash
# As standalone
git clone https://github.com/kateleext/openai-deep-research-mcp.git
cd openai-deep-research-mcp

# Or as submodule in takuma-os
cd /path/to/takuma-os
git submodule add https://github.com/kateleext/openai-deep-research-mcp.git tools/mcp/openai-deep-research-mcp
git submodule update --init --recursive
```

2. **Set up environment**:
```bash
cd openai-deep-research-mcp
cp .env.example .env
# Add your OpenAI API key to .env file
```

3. **Install dependencies**:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

4. **Add to Claude Code**:
```bash
# Get the full path
pwd  # Copy this path

# Add to Claude (replace PATH with your actual path)
claude mcp add --scope user openai-deep-research -- PATH/venv/bin/python PATH/server.py
```

5. **Verify**:
```bash
claude mcp list  # Should show ✓ Connected
# In Claude chat, type: /mcp
```

## What This Does

This MCP server exposes two tools to Claude Code:
- `start_research(query, model?, max_tool_calls?)` - Initiates a background Deep Research task
- `get_result(id)` - Polls for and retrieves research results including report, citations, and steps

Perfect for running demand compass analyses or any deep research that requires comprehensive web searching and synthesis.

## Setup

### 1. Get Your OpenAI API Key

1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign in or create an account
3. Navigate to API Keys: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
4. Click "Create new secret key"
5. Copy the key (it starts with `sk-`)

### 2. Configure Environment

```bash
cd /Users/kate/Documents/Manual\ Library/Projects/takuma-os/tools/mcp/openai-deep-research-mcp

# Copy the example environment file
cp .env.example .env

# Edit .env and add your API key
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

### 3. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 4. Test the Server

```bash
# Run the server
python server.py
```

You should see: `Starting OpenAI Deep Research MCP server`

Press Ctrl+C to stop.

## Add to Claude Code

Install the MCP server at user scope (available to all projects):

```bash
claude mcp add --scope user openai-deep-research -- python /Users/kate/Documents/Manual\ Library/Projects/takuma-os/tools/mcp/openai-deep-research-mcp/server.py
```

Verify it's installed:

```bash
claude mcp list
claude mcp get openai-deep-research
```

In Claude Code chat, verify with:
```
/mcp
```

## Usage Examples

### Basic Research Query

Tell Claude:
```
Use the openai-deep-research server to research "What are the main customer complaints about Dropbox in 2024?"
```

### Demand Compass Analysis

```
Use start_research to analyze these companies for JTBD consulting readiness:
- Dropbox
- Notion
- Airtable

Look for:
1. New product/research leadership
2. Customer understanding struggles
3. Failed product launches
4. Competitive pressure

Return companies with strong demand signals.
```

### Get Results

```
Check the status of research ID [xyz] using get_result
```

## Tool Details

### start_research

Parameters:
- `query` (required): The research question
- `model` (optional): Default "o4-mini-deep-research", can use "o3-deep-research"
- `max_tool_calls` (optional): Default 50, max number of web searches
- `use_code_interpreter` (optional): Default false, enable code execution

Returns:
```json
{
  "id": "response_abc123",
  "status": "in_progress"
}
```

### get_result

Parameters:
- `id` (required): The research ID from start_research

Returns when complete:
```json
{
  "id": "response_abc123",
  "status": "completed",
  "report": "Full research report text...",
  "citations": [
    {
      "url": "https://example.com",
      "title": "Source Title",
      "start_index": 100,
      "end_index": 200
    }
  ],
  "steps": [
    {
      "type": "tool_call",
      "tool": "web_search_preview",
      "summary": "Searched for customer complaints"
    }
  ]
}
```

## Models

- **o4-mini-deep-research** (default): Faster, more cost-effective for most research
- **o3-deep-research**: Deeper analysis, use for complex multi-step research
- Date-stamped variants (e.g., "o4-mini-deep-research-2025-01-15") also supported

## Troubleshooting

### "OPENAI_API_KEY not found"
- Make sure you created the `.env` file with your API key
- Verify the key starts with `sk-`

### Timeout Errors
- Deep Research can take 30-120 seconds
- The server has a 120-second timeout configured
- For very long research, poll with get_result multiple times

### Rate Limits
- OpenAI has rate limits on the Responses API
- Default max_tool_calls is 50 to balance thoroughness and speed
- Reduce if hitting limits

### Windows Users
- Use forward slashes in paths or escape backslashes
- May need to use full Python path in MCP add command

## Cost Considerations

- o4-mini: ~$0.01-0.05 per research query
- o3: ~$0.10-0.50 per research query
- Costs vary based on query complexity and tool calls

## Security

- API keys are stored in `.env` (never commit this file)
- The server never logs or echoes API keys
- All requests go directly to OpenAI's API

## Advanced Usage

### Running as Remote SSE Server

For remote access (optional):

```python
# Add --transport sse flag when running
python server.py --transport sse --port 8080
```

Then add to Claude:
```bash
claude mcp add --transport sse openai-dr http://localhost:8080/sse
```

## Development

Run tests:
```bash
pytest tests/
```

## Support

For issues with:
- This MCP server: Check this README or the code
- OpenAI API: [platform.openai.com/docs](https://platform.openai.com/docs)
- Claude Code MCP: [claude.ai/docs](https://claude.ai/docs)