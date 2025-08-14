#!/usr/bin/env python3
"""Alternative research MCP server using local web search + Claude Code's built-in capabilities."""

import os
import sys
import json
import logging
import uuid
from typing import Dict, Any
from datetime import datetime

from dotenv import load_dotenv
import fastmcp

# Load environment variables
load_dotenv()

# Setup minimal logging
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = fastmcp.FastMCP("research-assistant")

# Track research sessions
research_sessions: Dict[str, Dict[str, Any]] = {}

@mcp.tool()
def start_research(
    query: str,
    approach: str = "comprehensive",
    max_sources: int = 5
) -> Dict[str, Any]:
    """
    Start a research task that will be handled by Claude Code's built-in capabilities.
    
    Args:
        query: The research question
        approach: Research approach ("comprehensive", "quick", "academic")
        max_sources: Maximum number of sources to gather
    
    Returns:
        Dict with id and instructions for manual research
    """
    session_id = str(uuid.uuid4())
    
    research_sessions[session_id] = {
        "query": query,
        "approach": approach,
        "max_sources": max_sources,
        "started_at": datetime.now().isoformat(),
        "status": "manual_required"
    }
    
    # Provide detailed instructions for manual research using Claude Code's capabilities
    instructions = f"""
RESEARCH REQUEST: {query}

To complete this research using Claude Code's built-in capabilities:

1. Use Claude Code's WebSearch tool to search for: "{query}"
2. Follow up with specific searches for:
   - "{query} latest research"
   - "{query} expert analysis"
   - "{query} case studies"
   
3. For demand compass analysis, also search:
   - "company struggles with {query}"
   - "leadership changes {query} industry"
   - "{query} customer complaints"

4. When you have gathered {max_sources} quality sources, use get_result('{session_id}') to mark as complete.

Research Approach: {approach}
Session ID: {session_id}
"""
    
    return {
        "id": session_id,
        "status": "manual_required",
        "instructions": instructions,
        "next_step": f"Use Claude Code's built-in search, then call get_result('{session_id}') when complete"
    }

@mcp.tool()
def get_result(id: str, report: str = None) -> Dict[str, Any]:
    """
    Mark research as complete and store the results.
    
    Args:
        id: The research session ID
        report: Optional research report to store
    
    Returns:
        Dict with the research session information
    """
    if id not in research_sessions:
        return {
            "id": id,
            "status": "not_found",
            "error": "Research session not found"
        }
    
    session = research_sessions[id]
    
    if report:
        session["report"] = report
        session["status"] = "completed"
        session["completed_at"] = datetime.now().isoformat()
    
    return {
        "id": id,
        "query": session["query"],
        "status": session["status"],
        "started_at": session["started_at"],
        "completed_at": session.get("completed_at"),
        "report": session.get("report", "Research in progress - use Claude Code's WebSearch tools"),
        "instructions": "Use Claude Code's built-in WebSearch capabilities to research this query"
    }

@mcp.tool()
def list_sessions() -> Dict[str, Any]:
    """List all research sessions."""
    return {
        "sessions": [
            {
                "id": sid,
                "query": session["query"],
                "status": session["status"],
                "started_at": session["started_at"]
            }
            for sid, session in research_sessions.items()
        ]
    }

def main():
    """Run the alternative research MCP server."""
    mcp.run(transport="stdio", show_banner=False)

if __name__ == "__main__":
    main()