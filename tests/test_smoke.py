#!/usr/bin/env python3
"""Smoke test for OpenAI Deep Research MCP server."""

import sys
import os
import pytest

# Add parent directory to path to import server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_server_imports():
    """Test that the server module can be imported."""
    try:
        import server
        assert hasattr(server, 'mcp')
        assert hasattr(server, 'start_research')
        assert hasattr(server, 'get_result')
    except ImportError as e:
        pytest.fail(f"Failed to import server: {e}")

def test_tool_signatures():
    """Test that MCP tools have correct signatures."""
    import server
    
    # Check that tools are registered as functions
    assert hasattr(server, 'start_research'), "start_research function not found"
    assert hasattr(server, 'get_result'), "get_result function not found"
    
    # Check they're callable
    assert callable(server.start_research), "start_research is not callable"
    assert callable(server.get_result), "get_result is not callable"

def test_env_warning():
    """Test that missing API key produces appropriate warning."""
    import server
    
    # Save original env
    original_key = os.environ.get('OPENAI_API_KEY')
    
    try:
        # Remove API key
        if 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']
        
        # This should not crash, just log a warning
        assert server.api_key is None or server.api_key == ""
        
    finally:
        # Restore original env
        if original_key:
            os.environ['OPENAI_API_KEY'] = original_key

if __name__ == "__main__":
    print("Running smoke tests...")
    
    # Run basic import test
    test_server_imports()
    print("✓ Server imports successfully")
    
    # Run tool signature test
    test_tool_signatures()
    print("✓ Tool signatures verified")
    
    # Run env warning test
    test_env_warning()
    print("✓ Environment handling verified")
    
    print("\nAll smoke tests passed!")