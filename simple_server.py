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
    model: str = "o4-mini-deep-research",
    max_tool_calls: int = 50,
    use_code_interpreter: bool = False
) -> Dict[str, Any]:
    """
    Start a Deep Research task using the Responses API.
    
    Args:
        query: The research question
        model: Deep Research model to use (o4-mini-deep-research or o3-deep-research)
        max_tool_calls: Maximum number of tool calls
        use_code_interpreter: Whether to enable code interpreter
    
    Returns:
        Dict with id and status
    """
    session_id = str(uuid.uuid4())
    
    try:
        # Build tools list for Deep Research
        tools = [{"type": "web_search_preview"}]
        if use_code_interpreter:
            tools.append({
                "type": "code_interpreter",
                "container": {"type": "auto"}
            })
        
        # Use the Responses API format - input needs "message" type
        data = {
            "model": model,
            "input": [{
                "type": "message",
                "role": "user",
                "content": f"You are a deep research assistant. Provide comprehensive, well-sourced research with citations.\n\nUser Query: {query}"
            }],
            "text": {},  # Empty as per OpenAI docs
            "reasoning": {"summary": "auto"},
            "tools": tools,
            "store": True
        }
        
        # Call the Responses API
        response = make_openai_request("responses", method="POST", data=data)
        
        if "error" not in response:
            # Store the response ID for polling
            response_id = response.get("id", session_id)
            research_sessions[response_id] = {
                "query": query,
                "model": model,
                "started_at": datetime.now().isoformat(),
                "status": response.get("status", "in_progress"),
                "response_id": response_id
            }
            
            return {
                "id": response_id,
                "status": response.get("status", "in_progress"),
                "message": f"Deep Research started with {model}"
            }
        else:
            # Fallback to chat completions if Responses API fails
            logger.warning(f"Responses API failed: {response['error']}, falling back to chat completions")
            
            data = {
                "model": "gpt-4-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a deep research assistant. Provide comprehensive, well-sourced research with citations."
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "max_tokens": 4000
            }
            
            fallback_response = make_openai_request("chat/completions", method="POST", data=data)
            
            if "error" not in fallback_response:
                research_sessions[session_id] = {
                    "query": query,
                    "model": "gpt-4-turbo (fallback)",
                    "started_at": datetime.now().isoformat(),
                    "status": "completed",
                    "response": fallback_response
                }
                
                return {
                    "id": session_id,
                    "status": "completed",
                    "message": "Research completed using GPT-4 Turbo (fallback)"
                }
            else:
                return {
                    "id": session_id,
                    "status": "failed",
                    "error": fallback_response["error"]
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
    
    # If it's a Deep Research task, poll for updates
    if "response_id" in session and session["status"] != "completed":
        try:
            # Poll the Responses API for status
            response = make_openai_request(f"responses/{session['response_id']}")
            
            if "error" not in response:
                session["status"] = response.get("status", "in_progress")
                
                if response.get("status") == "completed":
                    # Extract the research output
                    output = response.get("output", [])
                    if output and len(output) > 0:
                        last_output = output[-1]
                        content = last_output.get("content", [])
                        if content and len(content) > 0:
                            report = content[0].get("text", "No content available")
                        else:
                            report = "No content in response"
                    else:
                        report = "No output in response"
                    
                    # Extract citations if available
                    citations = []
                    for out in output:
                        for content_item in out.get("content", []):
                            for annotation in content_item.get("annotations", []):
                                if "url" in annotation:
                                    citations.append({
                                        "title": annotation.get("title", ""),
                                        "url": annotation.get("url", "")
                                    })
                    
                    session["report"] = report
                    session["citations"] = citations
                    session["status"] = "completed"
                    
                    return {
                        "id": id,
                        "status": "completed",
                        "query": session["query"],
                        "report": report,
                        "citations": citations[:10],  # Limit to 10 citations
                        "model": session["model"],
                        "started_at": session["started_at"]
                    }
                else:
                    return {
                        "id": id,
                        "status": session["status"],
                        "query": session["query"],
                        "model": session["model"],
                        "started_at": session["started_at"],
                        "message": "Deep Research in progress, poll again in a few seconds"
                    }
            else:
                return {
                    "id": id,
                    "status": "error",
                    "error": response["error"]
                }
        except Exception as e:
            return {
                "id": id,
                "status": "error",
                "error": str(e)
            }
    
    # Handle fallback chat completions
    elif session["status"] == "completed" and "response" in session:
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