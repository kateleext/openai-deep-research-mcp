#!/usr/bin/env python3
"""Simplified MCP server using direct HTTP requests instead of OpenAI client."""

import os
import sys
import json
import logging
import uuid
import requests
from typing import Dict, Any
from datetime import datetime

from dotenv import load_dotenv
import fastmcp

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
load_dotenv(env_path)

# Setup minimal logging
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Get API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("OPENAI_API_KEY not found in environment")
    sys.exit(1)

# Initialize MCP server
mcp = fastmcp.FastMCP("openai-deep-research")

# Track research sessions
research_sessions: Dict[str, Dict[str, Any]] = {}

# Base URL for OpenAI API
BASE_URL = "https://api.openai.com/v1"

def make_openai_request(endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
    """Make a direct HTTP request to OpenAI API."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    url = f"{BASE_URL}/{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        else:
            response = requests.post(url, headers=headers, json=data, timeout=120)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}: {response.text[:500]}"}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def test_connection() -> Dict[str, Any]:
    """Test the OpenAI API connection."""
    result = {
        "api_key_configured": bool(api_key),
        "api_key_format": f"sk-{'proj' if api_key and 'proj' in api_key else 'other'}..." if api_key else "missing"
    }
    
    # Test models endpoint
    models_response = make_openai_request("models")
    if "error" not in models_response:
        result["connection"] = "working"
        result["model_count"] = len(models_response.get("data", []))
        # Check for deep research models
        dr_models = [m["id"] for m in models_response.get("data", []) 
                     if "deep-research" in m["id"] or "o3" in m["id"] or "o4" in m["id"]]
        result["deep_research_models"] = dr_models[:5]
    else:
        result["connection"] = "failed"
        result["error"] = models_response["error"]
    
    return result

@mcp.tool()
def start_research(
    query: str,
    model: str = "gpt-4-turbo",  # Use standard model as fallback
    max_tokens: int = 4000
) -> Dict[str, Any]:
    """
    Start a research task using chat completions (since Responses API may not be available).
    
    Args:
        query: The research question
        model: Model to use (defaults to gpt-4-turbo)
        max_tokens: Maximum tokens in response
    
    Returns:
        Dict with id and status
    """
    session_id = str(uuid.uuid4())
    
    try:
        # Use chat completions API which we know works
        data = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a deep research assistant. Provide comprehensive, well-sourced research with citations. Search for multiple perspectives and provide detailed analysis."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        response = make_openai_request("chat/completions", method="POST", data=data)
        
        if "error" not in response:
            # Store the response
            research_sessions[session_id] = {
                "query": query,
                "model": model,
                "started_at": datetime.now().isoformat(),
                "status": "completed",
                "response": response
            }
            
            return {
                "id": session_id,
                "status": "completed",
                "message": "Research completed using chat completions"
            }
        else:
            return {
                "id": session_id,
                "status": "failed",
                "error": response["error"]
            }
            
    except Exception as e:
        return {
            "id": session_id,
            "status": "failed",
            "error": str(e)
        }

@mcp.tool()
def get_result(id: str) -> Dict[str, Any]:
    """
    Get the results of a research task.
    
    Args:
        id: The research session ID
    
    Returns:
        Dict with research results
    """
    if id not in research_sessions:
        return {
            "id": id,
            "status": "not_found",
            "error": "Research session not found"
        }
    
    session = research_sessions[id]
    
    if session["status"] == "completed" and "response" in session:
        response = session["response"]
        
        # Extract the message content
        message = response.get("choices", [{}])[0].get("message", {})
        content = message.get("content", "No content available")
        
        return {
            "id": id,
            "status": "completed",
            "query": session["query"],
            "report": content,
            "model": session["model"],
            "started_at": session["started_at"]
        }
    else:
        return {
            "id": id,
            "status": session["status"],
            "query": session["query"],
            "started_at": session["started_at"]
        }

def main():
    """Run the MCP server."""
    mcp.run(transport="stdio", show_banner=False)

if __name__ == "__main__":
    main()