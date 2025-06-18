"""
Unit tests for plugin execution functionality.
"""

import pytest
import json
import subprocess
from unittest.mock import patch, MagicMock
import sys

from mcp_server import execute_plugin_tool


class TestPluginExecution:
    """Test cases for plugin execution functionality."""
    
    @pytest.mark.asyncio
    async def test_execute_plugin_tool_invalid_format(self):
        """Test executing plugin tool with invalid tool name format."""
        with patch('mcp_server.plugin_registry', {}):
            result = await execute_plugin_tool("invalid_tool_name", {})
            
            assert "error" in result
            assert "Invalid tool name format" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_plugin_tool_plugin_not_found(self):
        """Test executing plugin tool when plugin is not found."""
        with patch('mcp_server.plugin_registry', {}):
            result = await execute_plugin_tool("nonexistent_plugin.command", {})
            
            assert "error" in result
            assert "Plugin not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_plugin_tool_success(self):
        """Test successful plugin tool execution."""
        mock_plugin_info = {
            "path": "/path/to/plugin/cli.py",
            "commands": {}
        }
        
        with patch('mcp_server.plugin_registry', {"test_plugin": mock_plugin_info}):
            with patch('subprocess.run') as mock_run:
                # Mock successful plugin execution
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = json.dumps({"result": "Success!"})
                mock_run.return_value = mock_result
                
                result = await execute_plugin_tool("test_plugin.test-command", {"param": "value"})
                
                assert "result" in result
                assert result["result"] == "Success!"
                
                # Verify subprocess was called correctly
                mock_run.assert_called_once()
                call_args = mock_run.call_args[0][0]
                assert call_args[0] == sys.executable  # sys.executable
                assert call_args[1] == "/path/to/plugin/cli.py"
                assert call_args[2] == "test-command"
                assert "--param" in call_args
                assert "value" in call_args
    
    @pytest.mark.asyncio
    async def test_execute_plugin_tool_plugin_error(self):
        """Test plugin execution when plugin returns an error."""
        mock_plugin_info = {
            "path": "/path/to/plugin/cli.py",
            "commands": {}
        }
        
        with patch('mcp_server.plugin_registry', {"test_plugin": mock_plugin_info}):
            with patch('subprocess.run') as mock_run:
                # Mock plugin execution with error
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = json.dumps({"error": "Plugin error occurred"})
                mock_run.return_value = mock_result
                
                result = await execute_plugin_tool("test_plugin.test-command", {})
                
                assert "error" in result
                assert result["error"] == "Plugin error occurred"
    
    @pytest.mark.asyncio
    async def test_execute_plugin_tool_subprocess_error(self):
        """Test plugin execution when subprocess fails."""
        mock_plugin_info = {
            "path": "/path/to/plugin/cli.py",
            "commands": {}
        }
        
        with patch('mcp_server.plugin_registry', {"test_plugin": mock_plugin_info}):
            with patch('subprocess.run') as mock_run:
                # Mock subprocess failure
                mock_result = MagicMock()
                mock_result.returncode = 1
                mock_result.stderr = "Command failed"
                mock_run.return_value = mock_result
                
                result = await execute_plugin_tool("test_plugin.test-command", {})
                
                assert "error" in result
                assert result["error"] == "Command failed"
    
    @pytest.mark.asyncio
    async def test_execute_plugin_tool_timeout(self):
        """Test plugin execution timeout."""
        mock_plugin_info = {
            "path": "/path/to/plugin/cli.py",
            "commands": {}
        }
        
        with patch('mcp_server.plugin_registry', {"test_plugin": mock_plugin_info}):
            with patch('subprocess.run') as mock_run:
                # Mock timeout exception
                mock_run.side_effect = subprocess.TimeoutExpired("cli.py", 60)
                
                result = await execute_plugin_tool("test_plugin.test-command", {})
                
                assert "error" in result
                assert "timed out" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_plugin_tool_invalid_json_output(self):
        """Test plugin execution when plugin returns invalid JSON."""
        mock_plugin_info = {
            "path": "/path/to/plugin/cli.py",
            "commands": {}
        }
        
        with patch('mcp_server.plugin_registry', {"test_plugin": mock_plugin_info}):
            with patch('subprocess.run') as mock_run:
                # Mock successful execution but invalid JSON output
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "This is not valid JSON"
                mock_run.return_value = mock_result
                
                result = await execute_plugin_tool("test_plugin.test-command", {})
                
                assert "result" in result
                assert result["result"] == "This is not valid JSON"
    
    @pytest.mark.asyncio
    async def test_execute_plugin_tool_multiple_arguments(self):
        """Test plugin execution with multiple arguments."""
        mock_plugin_info = {
            "path": "/path/to/plugin/cli.py",
            "commands": {}
        }
        
        arguments = {
            "param1": "value1",
            "param2": "value2",
            "flag": True
        }
        
        with patch('mcp_server.plugin_registry', {"test_plugin": mock_plugin_info}):
            with patch('subprocess.run') as mock_run:
                # Mock successful plugin execution
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = json.dumps({"result": "Success with multiple args"})
                mock_run.return_value = mock_result
                
                result = await execute_plugin_tool("test_plugin.test-command", arguments)
                
                assert "result" in result
                
                # Verify all arguments were passed correctly
                call_args = mock_run.call_args[0][0]
                assert "--param1" in call_args
                assert "value1" in call_args
                assert "--param2" in call_args
                assert "value2" in call_args
                assert "--flag" in call_args
                assert "True" in call_args
    
    @pytest.mark.asyncio
    async def test_execute_plugin_tool_exception_handling(self):
        """Test plugin execution exception handling."""
        mock_plugin_info = {
            "path": "/path/to/plugin/cli.py",
            "commands": {}
        }
        
        with patch('mcp_server.plugin_registry', {"test_plugin": mock_plugin_info}):
            with patch('subprocess.run') as mock_run:
                # Mock general exception
                mock_run.side_effect = Exception("Unexpected error")
                
                result = await execute_plugin_tool("test_plugin.test-command", {})
                
                assert "error" in result
                assert "Unexpected error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_plugin_tool_empty_arguments(self):
        """Test plugin execution with empty arguments."""
        mock_plugin_info = {
            "path": "/path/to/plugin/cli.py",
            "commands": {}
        }
        
        with patch('mcp_server.plugin_registry', {"test_plugin": mock_plugin_info}):
            with patch('subprocess.run') as mock_run:
                # Mock successful plugin execution
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = json.dumps({"result": "Success with no args"})
                mock_run.return_value = mock_result
                
                result = await execute_plugin_tool("test_plugin.test-command", {})
                
                assert "result" in result
                
                # Verify only command and subcommand were passed
                call_args = mock_run.call_args[0][0]
                assert len(call_args) == 3  # python, cli.py, command
                assert call_args[0] == sys.executable
                assert call_args[1] == "/path/to/plugin/cli.py"
                assert call_args[2] == "test-command" 