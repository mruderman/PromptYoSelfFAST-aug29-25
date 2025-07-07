"""
Unit tests for tools manifest functionality.
"""

import pytest
import json
import sys
from unittest.mock import patch, MagicMock

from smcp.mcp_server import build_tools_manifest


class TestToolsManifest:
    """Test cases for tools manifest functionality."""
    
    def test_build_tools_manifest_empty_registry(self):
        """Test building tools manifest with empty plugin registry."""
        with patch.object(sys.modules['smcp.mcp_server'], 'plugin_registry', {}):
            tools = build_tools_manifest()
            
            assert isinstance(tools, list)
            assert len(tools) == 0
    
    def test_build_tools_manifest_with_plugin(self):
        """Test building tools manifest with a plugin in registry."""
        mock_plugin_info = {
            "path": "/path/to/plugin/cli.py",
            "commands": {}
        }
        
        with patch.object(sys.modules['smcp.mcp_server'], 'plugin_registry', {"test_plugin": mock_plugin_info}):
            with patch('smcp.mcp_server.subprocess.run') as mock_run:
                # Mock successful help command execution
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = """
usage: cli.py [-h] {click-button,send-message} ...

BotFather automation plugin

positional arguments:
  {click-button,send-message}
                        Available commands:
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
                assert "properties" in click_tool["inputSchema"]
                
                # Check for send-message tool
                send_tool = next((t for t in tools if t["name"] == "test_plugin.send-message"), None)
                assert send_tool is not None
                assert send_tool["description"] == "test_plugin send-message command"
    
    def test_build_tools_manifest_help_command_failure(self):
        """Test building tools manifest when help command fails."""
        mock_plugin_info = {
            "path": "/path/to/plugin/cli.py",
            "commands": {}
        }
        
        with patch.object(sys.modules['smcp.mcp_server'], 'plugin_registry', {"test_plugin": mock_plugin_info}):
            with patch('smcp.mcp_server.subprocess.run') as mock_run:
                # Mock failed help command execution
                mock_result = MagicMock()
                mock_result.returncode = 1
                mock_result.stderr = "Command not found"
                mock_run.return_value = mock_result
                
                tools = build_tools_manifest()
                
                assert isinstance(tools, list)
                assert len(tools) == 0
    
    def test_build_tools_manifest_invalid_help_output(self):
        """Test building tools manifest with invalid help output."""
        mock_plugin_info = {
            "path": "/path/to/plugin/cli.py",
            "commands": {}
        }
        
        with patch.object(sys.modules['smcp.mcp_server'], 'plugin_registry', {"test_plugin": mock_plugin_info}):
            with patch('smcp.mcp_server.subprocess.run') as mock_run:
                # Mock help command with invalid output
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "Invalid help output without expected format"
                mock_run.return_value = mock_result
                
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
        
        with patch.object(sys.modules['smcp.mcp_server'], 'plugin_registry', mock_plugins):
            with patch('smcp.mcp_server.subprocess.run') as mock_run:
                # Mock successful help command execution for both plugins
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = """
usage: cli.py [-h] {deploy,rollback,status} ...

DevOps automation plugin

positional arguments:
  {deploy,rollback,status}
                        Available commands:
    deploy              Deploy an application
    rollback            Rollback an application deployment
    status              Get deployment status
                """
                mock_run.return_value = mock_result
                
                tools = build_tools_manifest()
                
                assert isinstance(tools, list)
                assert len(tools) == 6  # 2 plugins * 3 commands each
                
                # Check botfather tools
                botfather_tools = [t for t in tools if t["name"].startswith("botfather.")]
                assert len(botfather_tools) == 3
                
                # Check devops tools
                devops_tools = [t for t in tools if t["name"].startswith("devops.")]
                assert len(devops_tools) == 3
    
    def test_build_tools_manifest_specific_command_schemas(self):
        """Test that specific commands have correct input schemas."""
        mock_plugin_info = {
            "path": "/path/to/plugin/cli.py",
            "commands": {}
        }
        
        with patch.object(sys.modules['smcp.mcp_server'], 'plugin_registry', {"test_plugin": mock_plugin_info}):
            with patch('smcp.mcp_server.subprocess.run') as mock_run:
                # Mock help output that includes all command types
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = """
usage: cli.py [-h] {click-button,send-message,deploy,rollback,status} ...

Test plugin

positional arguments:
  {click-button,send-message,deploy,rollback,status}
                        Available commands:
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
                assert click_tool["inputSchema"]["type"] == "object"
                assert "properties" in click_tool["inputSchema"]
                
                # Check send-message schema
                send_tool = next((t for t in tools if t["name"] == "test_plugin.send-message"), None)
                assert send_tool is not None
                assert send_tool["inputSchema"]["type"] == "object"
                assert "properties" in send_tool["inputSchema"]
                
                # Check deploy schema
                deploy_tool = next((t for t in tools if t["name"] == "test_plugin.deploy"), None)
                assert deploy_tool is not None
                assert deploy_tool["inputSchema"]["type"] == "object"
                assert "properties" in deploy_tool["inputSchema"]
    
    def test_build_tools_manifest_command_extraction(self):
        """Test that commands are correctly extracted from help output."""
        mock_plugin_info = {
            "path": "/path/to/plugin/cli.py",
            "commands": {}
        }
        
        with patch.object(sys.modules['smcp.mcp_server'], 'plugin_registry', {"test_plugin": mock_plugin_info}):
            with patch('smcp.mcp_server.subprocess.run') as mock_run:
                # Mock help output with specific command format
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = """
usage: cli.py [-h] {test-command} ...

Test plugin

positional arguments:
  {test-command}
                        Available commands:
    test-command         Test command description
                """
                mock_run.return_value = mock_result
                
                tools = build_tools_manifest()
                
                assert len(tools) == 1
                tool = tools[0]
                assert tool["name"] == "test_plugin.test-command"
                assert tool["description"] == "test_plugin test-command command"
    
    def test_build_tools_manifest_ignores_examples_section(self):
        """Test that the Examples section is ignored when extracting commands."""
        mock_plugin_info = {
            "path": "/path/to/plugin/cli.py",
            "commands": {}
        }
        
        with patch.object(sys.modules['smcp.mcp_server'], 'plugin_registry', {"test_plugin": mock_plugin_info}):
            with patch('smcp.mcp_server.subprocess.run') as mock_run:
                # Mock help output with Examples section
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = """
usage: cli.py [-h] {test-command} ...

Test plugin

positional arguments:
  {test-command}
                        Available commands:
    test-command         Test command description

Examples:
    cli.py test-command --param value
    cli.py test-command --flag
                """
                mock_run.return_value = mock_result
                
                tools = build_tools_manifest()
                
                assert len(tools) == 1
                tool = tools[0]
                assert tool["name"] == "test_plugin.test-command"
                # Should not include any "Examples" commands
                assert len(tools) == 1 