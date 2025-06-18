"""
Unit tests for plugin execution functionality.
"""

import pytest
import json
import subprocess
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add the mcp directory to the path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp"))

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
    
    @pytest.mark.timeout(30)  # 30 second timeout for plugin execution
    @pytest.mark.asyncio
    async def test_execute_plugin_tool_success(self, mock_plugin_cli):
        """Test successful plugin tool execution."""
        with patch('subprocess.run') as mock_run:
            # Mock successful subprocess execution
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps({"result": "Test execution successful"}).encode()
            mock_run.return_value = mock_result
            
            result = await execute_plugin_tool(str(mock_plugin_cli), "test-command", {"param": "test_value"})
            
            # Verify subprocess was called correctly
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == [str(mock_plugin_cli), "test-command", "--param", "test_value"]
            assert call_args[1]["capture_output"] is True
            assert call_args[1]["text"] is False
            
            # Verify result
            assert result["result"] == "Test execution successful"
    
    @pytest.mark.timeout(30)  # 30 second timeout for plugin execution error
    @pytest.mark.asyncio
    async def test_execute_plugin_tool_error(self, mock_plugin_cli):
        """Test plugin tool execution with error."""
        with patch('subprocess.run') as mock_run:
            # Mock subprocess execution with error
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = b"Plugin execution failed"
            mock_run.return_value = mock_result
            
            with pytest.raises(Exception) as exc_info:
                await execute_plugin_tool(str(mock_plugin_cli), "test-command", {"param": "test_value"})
            
            assert "Plugin execution failed" in str(exc_info.value)
    
    @pytest.mark.timeout(30)  # 30 second timeout for invalid JSON
    @pytest.mark.asyncio
    async def test_execute_plugin_tool_invalid_json(self, mock_plugin_cli):
        """Test plugin tool execution with invalid JSON output."""
        with patch('subprocess.run') as mock_run:
            # Mock subprocess execution with invalid JSON
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = b"Invalid JSON output"
            mock_run.return_value = mock_result
            
            with pytest.raises(json.JSONDecodeError):
                await execute_plugin_tool(str(mock_plugin_cli), "test-command", {"param": "test_value"})
    
    @pytest.mark.timeout(30)  # 30 second timeout for subprocess failure
    @pytest.mark.asyncio
    async def test_execute_plugin_tool_subprocess_failure(self, mock_plugin_cli):
        """Test plugin tool execution when subprocess fails to start."""
        with patch('subprocess.run') as mock_run:
            # Mock subprocess failure
            mock_run.side_effect = FileNotFoundError("Plugin not found")
            
            with pytest.raises(FileNotFoundError):
                await execute_plugin_tool(str(mock_plugin_cli), "test-command", {"param": "test_value"})
    
    @pytest.mark.timeout(30)  # 30 second timeout for timeout handling
    @pytest.mark.asyncio
    async def test_execute_plugin_tool_timeout(self, mock_plugin_cli):
        """Test plugin tool execution timeout handling."""
        with patch('subprocess.run') as mock_run:
            # Mock subprocess timeout
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=[str(mock_plugin_cli)], timeout=5)
            
            with pytest.raises(subprocess.TimeoutExpired):
                await execute_plugin_tool(str(mock_plugin_cli), "test-command", {"param": "test_value"})
    
    @pytest.mark.timeout(30)  # 30 second timeout for empty arguments
    @pytest.mark.asyncio
    async def test_execute_plugin_tool_empty_arguments(self, mock_plugin_cli):
        """Test plugin tool execution with empty arguments."""
        with patch('subprocess.run') as mock_run:
            # Mock successful subprocess execution
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps({"result": "Default result"}).encode()
            mock_run.return_value = mock_result
            
            result = await execute_plugin_tool(str(mock_plugin_cli), "test-command", {})
            
            # Verify subprocess was called with default arguments
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == [str(mock_plugin_cli), "test-command", "--param", "default"]
            
            # Verify result
            assert result["result"] == "Default result"
    
    @pytest.mark.timeout(30)  # 30 second timeout for complex arguments
    @pytest.mark.asyncio
    async def test_execute_plugin_tool_complex_arguments(self, mock_plugin_cli):
        """Test plugin tool execution with complex arguments."""
        with patch('subprocess.run') as mock_run:
            # Mock successful subprocess execution
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps({"result": "Complex execution"}).encode()
            mock_run.return_value = mock_result
            
            complex_args = {
                "param": "complex_value",
                "number": 42,
                "flag": True
            }
            
            result = await execute_plugin_tool(str(mock_plugin_cli), "test-command", complex_args)
            
            # Verify subprocess was called with complex arguments
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            expected_args = [str(mock_plugin_cli), "test-command", "--param", "complex_value"]
            assert call_args[0][0] == expected_args
            
            # Verify result
            assert result["result"] == "Complex execution"
    
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