#!/usr/bin/env python3
"""Test script to demonstrate the openai-deep-research MCP functionality."""

import os
import sys
import json
import time
from dotenv import load_dotenv
from openai import OpenAI

# Add the script directory to path and load environment
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
load_dotenv(env_path)

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("OPENAI_API_KEY not found in environment")
    sys.exit(1)

client = OpenAI(api_key=api_key, timeout=120.0)

def start_research(query, model="o4-mini-deep-research", max_tool_calls=50):
    """Start a Deep Research task."""
    try:
        tools = [{"type": "web_search_preview"}]
        
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
        
        return {
            "id": response.id,
            "status": response.status
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }

def get_result(id):
    """Get the results of a research task."""
    try:
        response = client.responses.get(id)
        
        result = {
            "id": id,
            "status": response.status
        }
        
        if response.status == "completed":
            if response.output and len(response.output) > 0:
                last_output = response.output[-1]
                if hasattr(last_output, 'content') and len(last_output.content) > 0:
                    final_text = last_output.content[0].text if hasattr(last_output.content[0], 'text') else str(last_output.content[0])
                    result["report"] = final_text
        
        return result
    except Exception as e:
        return {
            "id": id,
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    print("Starting quantum computing research...")
    
    # Start research
    result = start_research("What are the latest developments in quantum computing in 2024?")
    print(f"Research started: {json.dumps(result, indent=2)}")
    
    if 'id' in result and result['status'] != 'failed':
        research_id = result['id']
        
        # Poll for results
        max_attempts = 24  # 2 minutes max
        for attempt in range(max_attempts):
            print(f"Checking results (attempt {attempt + 1})...")
            final_result = get_result(research_id)
            
            if final_result['status'] == 'completed':
                print("Research completed!")
                print(json.dumps(final_result, indent=2))
                break
            elif final_result['status'] == 'failed':
                print("Research failed:")
                print(json.dumps(final_result, indent=2))
                break
            else:
                print(f"Status: {final_result['status']}, waiting...")
                time.sleep(5)
    else:
        print("Failed to start research")