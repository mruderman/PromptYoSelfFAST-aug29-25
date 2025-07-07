"""
Unit tests for tools manifest building functionality.
"""

import pytest
import subprocess
from unittest.mock import patch, MagicMock
import sys

from mcp.mcp_server import build_tools_manifest


class TestToolsManifest:
    """Test cases for tools manifest building functionality."""
    
    def test_build_tools_manifest_empty_registry(self):
        """Test building tools manifest with empty plugin registry."""
        with patch.object(sys.modules['mcp.mcp_server'], 'plugin_registry', {}):
            tools = build_tools_manifest()
            
            assert isinstance(tools, list)
            assert len(tools) == 0
    
    def test_build_tools_manifest_with_plugin(self):
        """Test building tools manifest with a plugin in registry."""
        mock_plugin_info = {
            "path": "/path/to/plugin/cli.py",
            "commands": {}
        }
        
        with patch.object(sys.modules['mcp.mcp_server'], 'plugin_registry', {"test_plugin": mock_plugin_info}):
            with patch('mcp.mcp_server.subprocess.run') as mock_run:
                # Mock successful help command execution
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = """
usage: cli.py [-h] {click-button,send-message} ...

BotFather automation plugin

positional arguments:
  {click-button,send-message}
                        Available commands
    click-button         Click a button in a message
    send-message         Send a message to BotFather

optional arguments:
  -h, --help            show this help message and exit
                """
                mock_run.return_value = mock_result
                
                tools = build_tools_manifest()
                
                assert isinstance(tools, list)
                assert len(tools) == 2
                
                # Check for click-button tool
                click_tool = next((t for t in tools if t["name"] == "test_plugin.click-button"), None)
                assert click_tool is not None
                assert click_tool["description"] == "test_plugin click-button command"
                assert "inputSchema" in click_tool
                assert click_tool["inputSchema"]["type"] == "object"
                assert "button-text" in click_tool["inputSchema"]["properties"]
                assert "msg-id" in click_tool["inputSchema"]["properties"]
                
                # Check for send-message tool
                send_tool = next((t for t in tools if t["name"] == "test_plugin.send-message"), None)
                assert send_tool is not None
                assert send_tool["description"] == "test_plugin send-message command"
                assert "inputSchema" in send_tool
                assert "message" in send_tool["inputSchema"]["properties"]
    
    def test_build_tools_manifest_plugin_help_failure(self):
        """Test building tools manifest when plugin help command fails."""
        mock_plugin_info = {
            "path": "/path/to/plugin/cli.py",
            "commands": {}
        }
        
        with patch.object(sys.modules['mcp.mcp_server'], 'plugin_registry', {"test_plugin": mock_plugin_info}):
            with patch('mcp.mcp_server.subprocess.run') as mock_run:
                # Mock failed help command execution
                mock_result = MagicMock()
                mock_result.returncode = 1
                mock_result.stderr = "Command not found"
                mock_run.return_value = mock_result
                
                tools = build_tools_manifest()
                
                assert isinstance(tools, list)
                assert len(tools) == 0
    
    def test_build_tools_manifest_plugin_timeout(self):
        """Test building tools manifest when plugin help command times out."""
        mock_plugin_info = {
            "path": "/path/to/plugin/cli.py",
            "commands": {}
        }
        
        with patch.object(sys.modules['mcp.mcp_server'], 'plugin_registry', {"test_plugin": mock_plugin_info}):
            with patch('mcp.mcp_server.subprocess.run') as mock_run:
                # Mock timeout exception
                mock_run.side_effect = subprocess.TimeoutExpired("cli.py", 10)
                
                tools = build_tools_manifest()
                
                assert isinstance(tools, list)
                assert len(tools) == 0
    
    def test_build_tools_manifest_multiple_plugins(self):
        """Test building tools manifest with multiple plugins."""
        mock_plugins = {
            "botfather": {
                "path": "/path/to/botfather/cli.py",
                "commands": {}
            },
            "devops": {
                "path": "/path/to/devops/cli.py",
                "commands": {}
            }
        }
        
        with patch.object(sys.modules['mcp.mcp_server'], 'plugin_registry', mock_plugins):
            with patch('mcp.mcp_server.subprocess.run') as mock_run:
                # Mock successful help command execution for both plugins
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = """
usage: cli.py [-h] {deploy,rollback,status} ...

DevOps automation plugin

positional arguments:
  {deploy,rollback,status}
                        Available commands
    deploy              Deploy an application
    rollback            Rollback an application deployment
    status              Get deployment status
                """
                mock_run.return_value = mock_result
                
                tools = build_tools_manifest()
                
                assert isinstance(tools, list)
                assert len(tools) == 6  # 2 plugins * 3 commands each
                
                # Check that tools from both plugins are present
                botfather_tools = [t for t in tools if t["name"].startswith("botfather.")]
                devops_tools = [t for t in tools if t["name"].startswith("devops.")]
                
                assert len(botfather_tools) == 3
                assert len(devops_tools) == 3
    
    def test_build_tools_manifest_specific_command_schemas(self):
        """Test that specific commands have correct input schemas."""
        mock_plugin_info = {
            "path": "/path/to/plugin/cli.py",
            "commands": {}
        }
        
        with patch.object(sys.modules['mcp.mcp_server'], 'plugin_registry', {"test_plugin": mock_plugin_info}):
            with patch('mcp.mcp_server.subprocess.run') as mock_run:
                # Mock help output that includes all command types
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = """
usage: cli.py [-h] {click-button,send-message,deploy,rollback,status} ...

Test plugin

positional arguments:
  {click-button,send-message,deploy,rollback,status}
                        Available commands
    click-button         Click a button in a message
    send-message         Send a message
    deploy               Deploy an application
    rollback             Rollback an application
    status               Get status
                """
                mock_run.return_value = mock_result
                
                tools = build_tools_manifest()
                
                # Check click-button schema
                click_tool = next((t for t in tools if t["name"] == "test_plugin.click-button"), None)
                assert click_tool is not None
                assert "button-text" in click_tool["inputSchema"]["properties"]
                assert "msg-id" in click_tool["inputSchema"]["properties"]
                assert "button-text" in click_tool["inputSchema"]["required"]
                assert "msg-id" in click_tool["inputSchema"]["required"]
                
                # Check send-message schema
                send_tool = next((t for t in tools if t["name"] == "test_plugin.send-message"), None)
                assert send_tool is not None
                assert "message" in send_tool["inputSchema"]["properties"]
                assert "message" in send_tool["inputSchema"]["required"]
                
                # Check deploy schema
                deploy_tool = next((t for t in tools if t["name"] == "test_plugin.deploy"), None)
                assert deploy_tool is not None
                assert "app-name" in deploy_tool["inputSchema"]["properties"]
                assert "environment" in deploy_tool["inputSchema"]["properties"]
                assert "app-name" in deploy_tool["inputSchema"]["required"]
                assert "environment" not in deploy_tool["inputSchema"]["required"]  # Has default
                
                # Check rollback schema
                rollback_tool = next((t for t in tools if t["name"] == "test_plugin.rollback"), None)
                assert rollback_tool is not None
                assert "app-name" in rollback_tool["inputSchema"]["properties"]
                assert "version" in rollback_tool["inputSchema"]["properties"]
                assert "app-name" in rollback_tool["inputSchema"]["required"]
                assert "version" in rollback_tool["inputSchema"]["required"]
                
                # Check status schema
                status_tool = next((t for t in tools if t["name"] == "test_plugin.status"), None)
                assert status_tool is not None
                assert "app-name" in status_tool["inputSchema"]["properties"]
                assert "app-name" in status_tool["inputSchema"]["required"]
    
    def test_build_tools_manifest_error_handling(self):
        """Test error handling in build_tools_manifest when subprocess.run raises an exception."""
        mock_plugin_info = {
            "path": "/path/to/plugin/cli.py",
            "commands": {}
        }
        with patch.object(sys.modules['mcp.mcp_server'], 'plugin_registry', {"test_plugin": mock_plugin_info}):
            with patch('mcp.mcp_server.subprocess.run', side_effect=Exception("subprocess error")):
                tools = build_tools_manifest()
                assert isinstance(tools, list)
                assert len(tools) == 0 