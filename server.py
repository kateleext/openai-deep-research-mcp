#!/usr/bin/env python3
"""MCP server that proxies to OpenAI Deep Research via Responses API."""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI
import fastmcp

# Load environment variables from .env file in the script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
load_dotenv(env_path)

# Setup logging to stderr (reduced verbosity for MCP)
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("OPENAI_API_KEY not found in environment")
    logger.error(f"Looked for .env at: {env_path}")
    sys.exit(1)

client = OpenAI(
    api_key=api_key,
    project=os.getenv("OPENAI_PROJECT"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    timeout=120.0
)

# Initialize MCP server
mcp = fastmcp.FastMCP("openai-deep-research")

# Track active research sessions
research_sessions: Dict[str, Dict[str, Any]] = {}

@mcp.tool()
def start_research(
    query: str,
    model: str = "o4-mini-deep-research",
    max_tool_calls: int = 50,
    use_code_interpreter: bool = False
) -> Dict[str, Any]:
    """
    Start a Deep Research task using OpenAI's Responses API.
    
    Args:
        query: The research question or query
        model: Model to use (default: o4-mini-deep-research, can use o3-deep-research)
        max_tool_calls: Maximum number of tool calls (default: 50)
        use_code_interpreter: Whether to enable code interpreter (default: False)
    
    Returns:
        Dict with id and status of the created research task
    """
    try:
        # Build tools list
        tools = [{"type": "web_search_preview"}]
        if use_code_interpreter:
            tools.append({
                "type": "code_interpreter",
                "container": {"type": "auto"}
            })
        
        # Create the response using the official API format
        response = client.responses.create(
            model=model,
            input=[],
            text={
                "content": f"You are a deep research assistant. Provide comprehensive, well-sourced research with citations.\n\nUser Query: {query}"
            },
            reasoning={"summary": "auto"},
            tools=tools,
            store=True
        )
        
        # Store session info
        session_id = response.id
        research_sessions[session_id] = {
            "query": query,
            "model": model,
            "started_at": datetime.now().isoformat(),
            "status": response.status
        }
        
        return {
            "id": session_id,
            "status": response.status
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }

@mcp.tool()
def get_result(id: str) -> Dict[str, Any]:
    """
    Get the status and results of a research task.
    
    Args:
        id: The research task ID returned by start_research
    
    Returns:
        Dict with id, status, and optionally report, citations, and steps
    """
    try:
        # Fetch the response
        response = client.responses.get(id)
        
        # Update session status
        if id in research_sessions:
            research_sessions[id]["status"] = response.status
        
        result = {
            "id": id,
            "status": response.status
        }
        
        # If completed, extract the results
        if response.status == "completed":
            # Extract final report text
            if response.output and len(response.output) > 0:
                last_output = response.output[-1]
                if hasattr(last_output, 'content') and len(last_output.content) > 0:
                    final_text = last_output.content[0].text if hasattr(last_output.content[0], 'text') else str(last_output.content[0])
                    result["report"] = final_text
            
            # Extract citations from annotations
            citations = []
            if hasattr(response, 'output') and response.output:
                for output in response.output:
                    if hasattr(output, 'content'):
                        for content_item in output.content:
                            if hasattr(content_item, 'annotations'):
                                for annotation in content_item.annotations:
                                    if hasattr(annotation, 'url'):
                                        citation = {
                                            "url": annotation.url,
                                            "title": getattr(annotation, 'title', 'Untitled'),
                                            "start_index": getattr(annotation, 'start_index', None),
                                            "end_index": getattr(annotation, 'end_index', None)
                                        }
                                        citations.append(citation)
            
            if citations:
                result["citations"] = citations
            
            # Extract key steps (simplified)
            steps = []
            if hasattr(response, 'reasoning') and response.reasoning:
                if hasattr(response.reasoning, 'summary'):
                    steps.append({
                        "type": "reasoning_summary",
                        "content": response.reasoning.summary
                    })
            
            # Add tool calls as steps
            if hasattr(response, 'tool_calls'):
                for i, tool_call in enumerate(response.tool_calls[:5]):  # Limit to first 5
                    if hasattr(tool_call, 'function'):
                        steps.append({
                            "type": "tool_call",
                            "tool": tool_call.function.name,
                            "summary": f"Called {tool_call.function.name}"
                        })
            
            if steps:
                result["steps"] = steps
            
            # Clean up session
            if id in research_sessions:
                research_sessions[id]["completed_at"] = datetime.now().isoformat()
        
        elif response.status == "failed":
            result["error"] = "Research task failed"
            if hasattr(response, 'error'):
                result["error_details"] = str(response.error)
        
        return result
        
    except Exception as e:
        return {
            "id": id,
            "status": "error",
            "error": str(e)
        }

def main():
    """Run the MCP server."""
    # Verify API key
    if not api_key:
        print("Error: OPENAI_API_KEY not set in environment", file=sys.stderr)
        print("Please create a .env file with your OpenAI API key", file=sys.stderr)
        sys.exit(1)
    
    # Run the server with stdio transport and no banner
    mcp.run(transport="stdio", show_banner=False)

if __name__ == "__main__":
    main()