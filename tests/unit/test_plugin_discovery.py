"""
Unit tests for plugin discovery functionality.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from mcp.mcp_server import discover_plugins


class TestPluginDiscovery:
    """Test cases for plugin discovery functionality."""
    
    def test_discover_plugins_empty_directory(self, temp_plugins_dir):
        """Test discovering plugins when plugins directory is empty."""
        with patch.dict('os.environ', {'MCP_PLUGINS_DIR': str(temp_plugins_dir)}):
            plugins = discover_plugins()
            
            assert isinstance(plugins, dict)
            assert len(plugins) == 0
    
    def test_discover_plugins_with_valid_plugin(self, temp_plugins_dir):
        """Test discovering plugins when a valid plugin exists."""
        # Create a mock plugin
        plugin_dir = temp_plugins_dir / "test_plugin"
        plugin_dir.mkdir()
        cli_path = plugin_dir / "cli.py"
        cli_path.touch()
        
        with patch.dict('os.environ', {'MCP_PLUGINS_DIR': str(temp_plugins_dir)}):
            plugins = discover_plugins()
            
            assert isinstance(plugins, dict)
            assert len(plugins) == 1
            assert "test_plugin" in plugins
            assert plugins["test_plugin"]["path"] == str(cli_path)
            assert "commands" in plugins["test_plugin"]
    
    def test_discover_plugins_ignores_non_directory(self, temp_plugins_dir):
        """Test that non-directory items are ignored."""
        # Create a file (not a directory)
        file_path = temp_plugins_dir / "not_a_plugin.txt"
        file_path.touch()
        
        with patch.dict('os.environ', {'MCP_PLUGINS_DIR': str(temp_plugins_dir)}):
            plugins = discover_plugins()
            
            assert len(plugins) == 0
    
    def test_discover_plugins_ignores_missing_cli(self, temp_plugins_dir):
        """Test that directories without cli.py are ignored."""
        # Create a plugin directory without cli.py
        plugin_dir = temp_plugins_dir / "incomplete_plugin"
        plugin_dir.mkdir()
        
        with patch.dict('os.environ', {'MCP_PLUGINS_DIR': str(temp_plugins_dir)}):
            plugins = discover_plugins()
            
            assert len(plugins) == 0
    
    def test_discover_plugins_multiple_plugins(self, temp_plugins_dir):
        """Test discovering multiple plugins."""
        # Create multiple valid plugins
        for i in range(3):
            plugin_dir = temp_plugins_dir / f"plugin_{i}"
            plugin_dir.mkdir()
            cli_path = plugin_dir / "cli.py"
            cli_path.touch()
        
        with patch.dict('os.environ', {'MCP_PLUGINS_DIR': str(temp_plugins_dir)}):
            plugins = discover_plugins()
            
            assert len(plugins) == 3
            for i in range(3):
                assert f"plugin_{i}" in plugins
    
    def test_discover_plugins_mixed_content(self, temp_plugins_dir):
        """Test discovering plugins with mixed content (files, dirs, incomplete plugins)."""
        # Create a file
        file_path = temp_plugins_dir / "not_a_plugin.txt"
        file_path.touch()
        
        # Create an incomplete plugin (no cli.py)
        incomplete_dir = temp_plugins_dir / "incomplete"
        incomplete_dir.mkdir()
        
        # Create a valid plugin
        valid_dir = temp_plugins_dir / "valid_plugin"
        valid_dir.mkdir()
        cli_path = valid_dir / "cli.py"
        cli_path.touch()
        
        with patch.dict('os.environ', {'MCP_PLUGINS_DIR': str(temp_plugins_dir)}):
            plugins = discover_plugins()
            
            assert len(plugins) == 1
            assert "valid_plugin" in plugins
    
    def test_discover_plugins_nonexistent_directory(self):
        """Test discovering plugins when plugins directory doesn't exist."""
        with patch.dict('os.environ', {'MCP_PLUGINS_DIR': '/nonexistent/path'}):
            plugins = discover_plugins()
            
            assert isinstance(plugins, dict)
            assert len(plugins) == 0
    
    def test_discover_plugins_with_env_var(self, tmp_path, monkeypatch):
        """Test plugin discovery with MCP_PLUGINS_DIR environment variable set."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        plugin_dir = plugins_dir / "env_plugin"
        plugin_dir.mkdir()
        cli_path = plugin_dir / "cli.py"
        cli_path.touch()
        monkeypatch.setenv("MCP_PLUGINS_DIR", str(plugins_dir))
        from mcp.mcp_server import discover_plugins
        plugins = discover_plugins()
        assert "env_plugin" in plugins
        monkeypatch.delenv("MCP_PLUGINS_DIR")

    def test_discover_plugins_error_handling(self, tmp_path, monkeypatch):
        """Test error handling in discover_plugins when plugins_dir is not a directory."""
        file_path = tmp_path / "not_a_dir"
        file_path.write_text("not a dir")
        monkeypatch.setenv("MCP_PLUGINS_DIR", str(file_path))
        from mcp.mcp_server import discover_plugins
        
        # The function should raise an exception when trying to iterate over a file
        with pytest.raises(NotADirectoryError):
            plugins = discover_plugins()
        
        monkeypatch.delenv("MCP_PLUGINS_DIR")

    def test_init_app_and_main(self, monkeypatch):
        """Test init_app and main startup logic."""
        import importlib
        mcp_server = importlib.import_module("mcp.mcp_server")
        # Patch web.run_app to prevent actual server start
        monkeypatch.setattr(mcp_server.web, "run_app", lambda *a, **kw: None)
        # Patch asyncio.run to just call the function
        monkeypatch.setattr(mcp_server.asyncio, "run", lambda coro: None)
        # Should not raise
        mcp_server.main() 