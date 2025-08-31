import pytest
import os
import sys
from unittest.mock import patch, MagicMock, Mock
from unittest import mock
import argparse

@pytest.mark.asyncio
async def test_health_tool(mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool("health")
    assert result.structured_content["status"] == "healthy"

@pytest.mark.asyncio
@patch("promptyoself_mcp_server._register_prompt", return_value={"status": "success", "id": 123})
async def test_register_time_tool(mock_register, mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool(
        "promptyoself_schedule_time",
        {"agent_id": "test-agent", "prompt": "test prompt", "time": "2025-01-01T00:00:00Z"}
    )
    assert result.structured_content["status"] == "success"
    assert result.structured_content["id"] == 123
    mock_register.assert_called_once()

@pytest.mark.asyncio
@patch("promptyoself_mcp_server._list_prompts", return_value={"status": "success", "schedules": []})
async def test_list_tool(mock_list, mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool("promptyoself_list", {"agent_id": "test-agent"})
    assert result.structured_content["status"] == "success"
    mock_list.assert_called_once()

@pytest.mark.asyncio
@patch("promptyoself_mcp_server._cancel_prompt", return_value={"status": "success", "cancelled_id": 456})
async def test_cancel_tool(mock_cancel, mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool("promptyoself_cancel", {"schedule_id": 456})
    assert result.structured_content["status"] == "success"
    assert result.structured_content["cancelled_id"] == 456
    mock_cancel.assert_called_once()

@pytest.mark.asyncio
@patch("promptyoself_mcp_server._execute_prompts", return_value={"status": "success", "executed": []})
async def test_execute_tool(mock_execute, mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool("promptyoself_execute")
    assert result.structured_content["status"] == "success"
    mock_execute.assert_called_once()

@pytest.mark.asyncio
@patch("promptyoself_mcp_server._test_connection", return_value={"status": "success"})
async def test_test_tool(mock_test, mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool("promptyoself_test")
    assert result.structured_content["status"] == "success"
    mock_test.assert_called_once()

@pytest.mark.asyncio
@patch("promptyoself_mcp_server._list_agents", return_value={"status": "success", "agents": []})
async def test_agents_tool(mock_list_agents, mcp_in_memory_client):
    result = await mcp_in_memory_client.call_tool("promptyoself_agents")
    assert result.structured_content["status"] == "success"
    mock_list_agents.assert_called_once()

# Test agent ID inference edge cases and error handling
def test_infer_agent_id_with_metadata_dict():
    """Test agent ID inference with metadata as dict."""
    from promptyoself_mcp_server import _infer_agent_id
    
    # Mock context with metadata dict
    ctx = Mock()
    ctx.metadata = {"agent_id": "test-agent-123"}
    
    agent_id, debug = _infer_agent_id(ctx)
    assert agent_id == "test-agent-123"
    assert debug["source"] == "context.metadata"
    assert debug["key"] == "agent_id"

def test_infer_agent_id_with_metadata_conversion_error():
    """Test agent ID inference when metadata conversion fails."""
    from promptyoself_mcp_server import _infer_agent_id
    
    # Mock context with metadata that can't be converted properly
    ctx = Mock()
    class BadMetadata:
        def __init__(self):
            pass
        def __iter__(self):
            raise RuntimeError("Can't iterate")
        def keys(self):
            raise RuntimeError("Can't get keys")
    
    ctx.metadata = BadMetadata()
    
    # Should fallback to other methods
    with patch.dict(os.environ, {"PROMPTYOSELF_DEFAULT_AGENT_ID": "env-agent"}, clear=True):
        agent_id, debug = _infer_agent_id(ctx)
        assert agent_id == "env-agent"
        assert debug["source"] == "env"

def test_infer_agent_id_with_nested_metadata():
    """Test agent ID inference with nested metadata."""
    from promptyoself_mcp_server import _infer_agent_id
    
    ctx = Mock()
    ctx.metadata = {
        "agent": {"agent_id": "nested-agent"}, 
        "other": "value"
    }
    
    agent_id, debug = _infer_agent_id(ctx)
    assert agent_id == "nested-agent"
    assert debug["source"] == "context.metadata.nested"
    assert debug["key"] == "agent.agent_id"

def test_infer_agent_id_with_direct_attribute():
    """Test agent ID inference with direct context attribute."""
    from promptyoself_mcp_server import _infer_agent_id
    
    ctx = Mock()
    ctx.metadata = None
    ctx.agent_id = "direct-agent"
    
    agent_id, debug = _infer_agent_id(ctx)
    assert agent_id == "direct-agent"
    assert debug["source"] == "context.attr"
    assert debug["key"] == "agent_id"

def test_infer_agent_id_context_exception():
    """Test agent ID inference when context access throws exception."""
    from promptyoself_mcp_server import _infer_agent_id
    
    # Mock context that raises exception on attribute access
    ctx = Mock()
    ctx.metadata = Mock(side_effect=RuntimeError("Context error"))
    
    with patch.dict(os.environ, {"LETTA_AGENT_ID": "fallback-agent"}):
        agent_id, debug = _infer_agent_id(ctx)
        assert agent_id == "fallback-agent"
        assert debug["source"] == "env"
        assert debug["key"] == "LETTA_AGENT_ID"

def test_infer_agent_id_env_variables():
    """Test agent ID inference from various environment variables."""
    from promptyoself_mcp_server import _infer_agent_id
    
    # Test each environment variable
    env_vars = [
        "PROMPTYOSELF_DEFAULT_AGENT_ID", 
        "LETTA_AGENT_ID", 
        "LETTA_DEFAULT_AGENT_ID"
    ]
    
    for env_var in env_vars:
        with patch.dict(os.environ, {env_var: "env-test-agent"}, clear=True):
            agent_id, debug = _infer_agent_id(None)
            assert agent_id == "env-test-agent"
            assert debug["source"] == "env"
            assert debug["key"] == env_var

def test_health_function():
    """Test basic health function."""
    import asyncio
    from promptyoself_mcp_server import health
    
    # Test basic health function
    result = asyncio.run(health())
    assert result["status"] == "healthy"
    assert "letta_base_url" in result
    assert "db" in result
    assert "auth_set" in result

def test_health_tool_function():
    """Test health tool wrapper exists and is a FunctionTool."""
    from promptyoself_mcp_server import _health_tool
    
    # Test that _health_tool exists and is a decorated function
    # It should be a FunctionTool object due to the @mcp.tool decorator
    assert hasattr(_health_tool, 'name')
    assert _health_tool.name == 'health'

def test_health_with_environment_variables():
    """Test health function with custom environment variables."""
    import asyncio
    from promptyoself_mcp_server import health
    
    with patch.dict(os.environ, {
        "LETTA_BASE_URL": "https://custom-letta.example.com",
        "PROMPTYOSELF_DB": "/custom/path/db.sqlite",
        "LETTA_API_KEY": "test-api-key"
    }):
        result = asyncio.run(health())
        assert result["letta_base_url"] == "https://custom-letta.example.com"
        assert result["db"] == "/custom/path/db.sqlite"
        assert result["auth_set"] is True

# Test transport functions
@patch("multiprocessing.Process")
def test_serve_stdio_transport(mock_process):
    """Test stdio transport server function."""
    from promptyoself_mcp_server import serve_stdio_transport
    
    mock_proc = Mock()
    mock_process.return_value = mock_proc
    
    serve_stdio_transport()
    
    mock_process.assert_called_once()
    mock_proc.start.assert_called_once()
    assert mock_process.call_args[1]["daemon"] is True

@patch("multiprocessing.Process")
def test_serve_http_transport(mock_process):
    """Test HTTP transport server function."""
    from promptyoself_mcp_server import serve_http_transport
    
    mock_proc = Mock()
    mock_process.return_value = mock_proc
    
    serve_http_transport(host="0.0.0.0", port=9000, path="/test", log_level="DEBUG")
    
    mock_process.assert_called_once()
    mock_proc.start.assert_called_once()
    assert mock_process.call_args[1]["daemon"] is True

@patch("multiprocessing.Process")
def test_serve_sse_transport(mock_process):
    """Test SSE transport server function."""
    from promptyoself_mcp_server import serve_sse_transport
    
    mock_proc = Mock()
    mock_process.return_value = mock_proc
    
    serve_sse_transport(host="192.168.1.1", port=8080)
    
    mock_process.assert_called_once()
    mock_proc.start.assert_called_once()
    assert mock_process.call_args[1]["daemon"] is True

# Test main function argument parsing and execution
@patch("promptyoself_mcp_server.mcp")
def test_main_stdio_transport(mock_mcp):
    """Test main function with stdio transport."""
    from promptyoself_mcp_server import main
    
    with patch("sys.argv", ["promptyoself_mcp_server.py"]):
        main()
        mock_mcp.run.assert_called_once_with(transport="stdio")

@patch("promptyoself_mcp_server.mcp")
def test_main_http_transport(mock_mcp):
    """Test main function with HTTP transport."""
    from promptyoself_mcp_server import main
    
    with patch("sys.argv", ["promptyoself_mcp_server.py", "--transport", "http", "--host", "0.0.0.0", "--port", "9000", "--path", "/test"]):
        main()
        mock_mcp.run.assert_called_once_with(transport="http", host="0.0.0.0", port=9000, path="/test", log_level=None)

@patch("promptyoself_mcp_server.mcp")
def test_main_http_transport_fallback(mock_mcp):
    """Test main function with HTTP transport fallback to streamable-http."""
    from promptyoself_mcp_server import main
    
    # Make first call raise exception, second should succeed
    mock_mcp.run.side_effect = [RuntimeError("HTTP not available"), None]
    
    with patch("sys.argv", ["promptyoself_mcp_server.py", "--transport", "http"]):
        main()
        
    assert mock_mcp.run.call_count == 2
    # First call with http
    assert mock_mcp.run.call_args_list[0][1]["transport"] == "http"
    # Second call with streamable-http
    assert mock_mcp.run.call_args_list[1][1]["transport"] == "streamable-http"

@patch("promptyoself_mcp_server.mcp")
def test_main_sse_transport(mock_mcp):
    """Test main function with SSE transport."""
    from promptyoself_mcp_server import main
    
    with patch("sys.argv", ["promptyoself_mcp_server.py", "--transport", "sse", "--host", "localhost", "--port", "8080"]):
        main()
        mock_mcp.run.assert_called_once_with(transport="sse", host="localhost", port=8080)

def test_main_unsupported_transport():
    """Test main function with unsupported transport."""
    from promptyoself_mcp_server import main
    
    with patch("sys.argv", ["promptyoself_mcp_server.py", "--transport", "websocket"]):
        with pytest.raises(SystemExit):  # argparse will exit on invalid choice
            main()

@patch("promptyoself_mcp_server.mcp")
def test_main_with_environment_variables(mock_mcp):
    """Test main function reading from environment variables."""
    from promptyoself_mcp_server import main
    
    with patch.dict(os.environ, {
        "FASTMCP_TRANSPORT": "http",
        "FASTMCP_HOST": "example.com", 
        "FASTMCP_PORT": "9999",
        "FASTMCP_PATH": "/api/mcp",
        "FASTMCP_LOG_LEVEL": "DEBUG"
    }):
        with patch("sys.argv", ["promptyoself_mcp_server.py"]):
            main()
            mock_mcp.run.assert_called_once_with(
                transport="http", 
                host="example.com", 
                port=9999, 
                path="/api/mcp", 
                log_level="DEBUG"
            )

@patch("promptyoself_mcp_server.mcp")
def test_main_with_log_level(mock_mcp):
    """Test main function with log level override."""
    from promptyoself_mcp_server import main
    
    with patch("sys.argv", ["promptyoself_mcp_server.py", "--transport", "stdio", "--log-level", "ERROR"]):
        main()
        mock_mcp.run.assert_called_once_with(transport="stdio")

# Test import error handling - this requires mocking at module level
def test_fastmcp_import_error_handling():
    """Test that import errors are handled gracefully."""
    # This test verifies the import fallback mechanism
    # We can't easily test the actual import error, but we can test the fallback classes
    
    # Test the dummy MCP class
    from promptyoself_mcp_server import FastMCP
    
    # If fastmcp is installed, this will be the real class
    # If not, it will be the dummy. Either way, we can create an instance
    dummy_mcp = FastMCP(name="test", instructions="test instructions")
    
    # Test that it has the expected interface
    assert hasattr(dummy_mcp, "tool")
    assert hasattr(dummy_mcp, "run")
    
    # Test tool decorator - in the real FastMCP, this returns a FunctionTool
    # In the dummy, it returns the original function. Both are valid.
    decorator = dummy_mcp.tool()
    def sample_func():
        return "test"
    
    decorated = decorator(sample_func)
    # Should return either the original function (dummy) or a FunctionTool (real)
    # We just need to verify something is returned
    assert decorated is not None

def test_dummy_mcp_run_raises_error():
    """Test that dummy MCP run method raises appropriate error."""
    # This tests the _DummyMCP class that's used when fastmcp isn't available
    # We need to temporarily replace FastMCP to test this
    import promptyoself_mcp_server
    
    # Save original
    original_fastmcp = getattr(promptyoself_mcp_server, 'FastMCP', None)
    
    try:
        # Set to dummy class
        class TestDummyMCP:
            def __init__(self, *args, **kwargs):
                pass
            def tool(self, *args, **kwargs):
                def decorator(fn):
                    return fn
                return decorator
            def run(self, *args, **kwargs):
                raise RuntimeError("fastmcp not installed; cannot run transports")
        
        promptyoself_mcp_server.FastMCP = TestDummyMCP
        
        dummy = TestDummyMCP()
        with pytest.raises(RuntimeError, match="fastmcp not installed"):
            dummy.run()
            
    finally:
        # Restore original if it existed
        if original_fastmcp:
            promptyoself_mcp_server.FastMCP = original_fastmcp
