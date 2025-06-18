"""
Unit tests for DevOps plugin.
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the plugins directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "mcp" / "plugins" / "devops"))

from cli import deploy, rollback, status


class TestDevOpsPlugin:
    """Test cases for DevOps plugin."""
    
    def test_deploy_success(self):
        """Test successful deployment."""
        args = {
            "app-name": "myapp",
            "environment": "production"
        }
        
        result = deploy(args)
        
        assert "result" in result
        assert "Deployed myapp to production" in result["result"]
    
    def test_deploy_with_default_environment(self):
        """Test deployment with default environment."""
        args = {
            "app-name": "myapp"
        }
        
        result = deploy(args)
        
        assert "result" in result
        assert "Deployed myapp to production" in result["result"]
    
    def test_deploy_missing_app_name(self):
        """Test deployment with missing app name."""
        args = {
            "environment": "staging"
        }
        
        result = deploy(args)
        
        assert "error" in result
        assert "Missing required argument: app-name" in result["error"]
    
    def test_deploy_empty_args(self):
        """Test deployment with empty arguments."""
        args = {}
        
        result = deploy(args)
        
        assert "error" in result
        assert "Missing required argument: app-name" in result["error"]
    
    def test_rollback_success(self):
        """Test successful rollback."""
        args = {
            "app-name": "myapp",
            "version": "v1.2.3"
        }
        
        result = rollback(args)
        
        assert "result" in result
        assert "Rolled back myapp to version v1.2.3" in result["result"]
    
    def test_rollback_missing_app_name(self):
        """Test rollback with missing app name."""
        args = {
            "version": "v1.2.3"
        }
        
        result = rollback(args)
        
        assert "error" in result
        assert "Missing required arguments" in result["error"]
        assert "app-name" in result["error"]
    
    def test_rollback_missing_version(self):
        """Test rollback with missing version."""
        args = {
            "app-name": "myapp"
        }
        
        result = rollback(args)
        
        assert "error" in result
        assert "Missing required arguments" in result["error"]
        assert "version" in result["error"]
    
    def test_rollback_missing_both_args(self):
        """Test rollback with missing both arguments."""
        args = {}
        
        result = rollback(args)
        
        assert "error" in result
        assert "Missing required arguments" in result["error"]
        assert "app-name" in result["error"]
        assert "version" in result["error"]
    
    def test_status_success(self):
        """Test successful status check."""
        args = {
            "app-name": "myapp"
        }
        
        result = status(args)
        
        assert "result" in result
        assert "Status for myapp: healthy" in result["result"]
    
    def test_status_missing_app_name(self):
        """Test status check with missing app name."""
        args = {}
        
        result = status(args)
        
        assert "error" in result
        assert "Missing required argument: app-name" in result["error"]
    
    def test_deploy_with_special_characters(self):
        """Test deployment with special characters in app name."""
        args = {
            "app-name": "my-app_123",
            "environment": "staging"
        }
        
        result = deploy(args)
        
        assert "result" in result
        assert "Deployed my-app_123 to staging" in result["result"]
    
    def test_rollback_with_special_characters(self):
        """Test rollback with special characters in version."""
        args = {
            "app-name": "myapp",
            "version": "v1.2.3-beta"
        }
        
        result = rollback(args)
        
        assert "result" in result
        assert "Rolled back myapp to version v1.2.3-beta" in result["result"]
    
    def test_status_with_special_characters(self):
        """Test status check with special characters in app name."""
        args = {
            "app-name": "my-app_123"
        }
        
        result = status(args)
        
        assert "result" in result
        assert "Status for my-app_123: healthy" in result["result"]
    
    def test_deploy_with_long_app_name(self):
        """Test deployment with long app name."""
        long_app_name = "a" * 100
        args = {
            "app-name": long_app_name,
            "environment": "production"
        }
        
        result = deploy(args)
        
        assert "result" in result
        assert f"Deployed {long_app_name} to production" in result["result"]
    
    def test_rollback_with_long_version(self):
        """Test rollback with long version string."""
        long_version = "v" + "1" * 50
        args = {
            "app-name": "myapp",
            "version": long_version
        }
        
        result = rollback(args)
        
        assert "result" in result
        assert f"Rolled back myapp to version {long_version}" in result["result"] 