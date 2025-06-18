"""
Unit tests for DevOps plugin.
"""

import pytest
import importlib.util
import sys
import subprocess
import json
from pathlib import Path

# Dynamically import the correct cli.py for devops
cli_path = Path(__file__).parent.parent.parent.parent / "mcp" / "plugins" / "devops" / "cli.py"
spec = importlib.util.spec_from_file_location("devops_cli", cli_path)
devops_cli = importlib.util.module_from_spec(spec)
sys.modules["devops_cli"] = devops_cli
spec.loader.exec_module(devops_cli)

deploy = devops_cli.deploy
rollback = devops_cli.rollback
status = devops_cli.status

class TestDevOpsPlugin:
    """Test cases for DevOps plugin."""
    def test_deploy_success(self):
        args = {"app-name": "myapp", "environment": "production"}
        result = deploy(args)
        assert "result" in result
        assert "Deployed myapp to production" in result["result"]
    def test_deploy_with_default_environment(self):
        args = {"app-name": "myapp"}
        result = deploy(args)
        assert "result" in result
        assert "Deployed myapp to production" in result["result"]
    def test_deploy_missing_app_name(self):
        args = {"environment": "staging"}
        result = deploy(args)
        assert "error" in result
        assert "Missing required argument: app-name" in result["error"]
    def test_deploy_empty_args(self):
        args = {}
        result = deploy(args)
        assert "error" in result
        assert "Missing required argument: app-name" in result["error"]
    def test_rollback_success(self):
        args = {"app-name": "myapp", "version": "v1.2.3"}
        result = rollback(args)
        assert "result" in result
        assert "Rolled back myapp to version v1.2.3" in result["result"]
    def test_rollback_missing_app_name(self):
        args = {"version": "v1.2.3"}
        result = rollback(args)
        assert "error" in result
        assert "Missing required arguments" in result["error"]
        assert "app-name" in result["error"]
    def test_rollback_missing_version(self):
        args = {"app-name": "myapp"}
        result = rollback(args)
        assert "error" in result
        assert "Missing required arguments" in result["error"]
        assert "version" in result["error"]
    def test_rollback_missing_both_args(self):
        args = {}
        result = rollback(args)
        assert "error" in result
        assert "Missing required arguments" in result["error"]
        assert "app-name" in result["error"]
        assert "version" in result["error"]
    def test_status_success(self):
        args = {"app-name": "myapp"}
        result = status(args)
        assert "result" in result
        assert "Status for myapp: healthy" in result["result"]
    def test_status_missing_app_name(self):
        args = {}
        result = status(args)
        assert "error" in result
        assert "Missing required argument: app-name" in result["error"]
    def test_deploy_with_special_characters(self):
        args = {"app-name": "my-app_123", "environment": "staging"}
        result = deploy(args)
        assert "result" in result
        assert "Deployed my-app_123 to staging" in result["result"]
    def test_rollback_with_special_characters(self):
        args = {"app-name": "myapp", "version": "v1.2.3-beta"}
        result = rollback(args)
        assert "result" in result
        assert "Rolled back myapp to version v1.2.3-beta" in result["result"]
    def test_status_with_special_characters(self):
        args = {"app-name": "my-app_123"}
        result = status(args)
        assert "result" in result
        assert "Status for my-app_123: healthy" in result["result"]
    def test_deploy_with_long_app_name(self):
        long_app_name = "a" * 100
        args = {"app-name": long_app_name, "environment": "production"}
        result = deploy(args)
        assert "result" in result
        assert f"Deployed {long_app_name} to production" in result["result"]
    def test_rollback_with_long_version(self):
        long_version = "v" + "1" * 50
        args = {"app-name": "myapp", "version": long_version}
        result = rollback(args)
        assert "result" in result
        assert f"Rolled back myapp to version {long_version}" in result["result"]

def test_devops_cli_exposes_functions():
    spec = importlib.util.spec_from_file_location("devops_cli", cli_path)
    devops_cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(devops_cli)
    assert hasattr(devops_cli, "deploy")
    assert hasattr(devops_cli, "rollback")
    assert hasattr(devops_cli, "status")

def test_devops_cli_deploy_subprocess():
    result = subprocess.run(
        [sys.executable, str(cli_path), "deploy", "--app-name", "myapp"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert "result" in output

def test_devops_cli_status_subprocess():
    result = subprocess.run(
        [sys.executable, str(cli_path), "status", "--app-name", "myapp"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert "result" in output 