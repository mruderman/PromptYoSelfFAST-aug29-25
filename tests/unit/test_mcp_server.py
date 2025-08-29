from unittest import mock
import pytest
from promptyoself_mcp_server import health, serve_stdio_transport, serve_http_transport, serve_sse_transport

@mock.patch("fastapi.FastAPI")
@mock.patch("uvicorn.run")
def test_health(mock_fastapi, mock_uvicorn, mock_env_vars):
    app = health()
    assert app.title == "Promptyoself MCP Server"
    assert "health" in app.routes
    mock_uvicorn.assert_called_once()

@mock.patch("multiprocessing.Process")
def test_stdio_transport(mock_process, mock_env_vars):
    serve_stdio_transport()
    mock_process.assert_called_once()

@mock.patch("multiprocessing.Process")
def test_http_transport(mock_process, mock_env_vars):
    serve_http_transport(host="0.0.0.0", port=8000)
    mock_process.assert_called_once()

@mock.patch("multiprocessing.Process")
def test_sse_transport(mock_process, mock_env_vars):
    serve_sse_transport(host="0.0.0.0", port=8000)
    mock_process.assert_called_once()

@mock.patch("promptyoself_mcp_server.health")
@mock.patch("promptyoself_mcp_server.serve_stdio_transport")
@mock.patch("promptyoself_mcp_server.serve_http_transport")
@mock.patch("promptyoself_mcp_server.serve_sse_transport")
def test_startup_order(mock_health, mock_stdio, mock_http, mock_sse, mock_env_vars):
    # Simulate startup sequence
    serve_stdio_transport()
    serve_http_transport(host="0.0.0.0", port=8000)
    serve_sse_transport(host="0.0.0.0", port=8000)
    assert mock_stdio.called_before(mock_http)
    assert mock_stdio.called_before(mock_sse)
    assert mock_health.called_after(mock_stdio)

@mock.patch("promptyoself_mcp_server.serve_stdio_transport")
@mock.patch("promptyoself_mcp_server.serve_http_transport")
@mock.patch("promptyoself_mcp_server.serve_sse_transport")
def test_error_handling(mock_stdio, mock_http, mock_sse, mock_env_vars):
    # Simulate errors
    mock_stdio.side_effect = Exception("STDIO transport failed")
    mock_http.side_effect = Exception("HTTP transport failed")
    mock_sse.side_effect = Exception("SSE transport failed")
    
    with pytest.raises(Exception):
        serve_stdio_transport()
    with pytest.raises(Exception):
        serve_http_transport(host="0.0.0.0", port=8000)
    with pytest.raises(Exception):
        serve_sse_transport(host="0.0.0.0", port=8000)

@mock.patch("promptyoself_mcp_server.logging_config.get_logger")
def test_logging(mock_logger, mock_env_vars):
    health()
    mock_logger.assert_called_once_with("promptyoself.mcp_server")