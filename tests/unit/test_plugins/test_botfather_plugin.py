"""
Unit tests for BotFather plugin.
"""

import importlib.util
import sys
import subprocess
import json
from pathlib import Path

def test_botfather_cli_exposes_functions():
    cli_path = Path(__file__).parent.parent.parent.parent / "mcp" / "plugins" / "botfather" / "cli.py"
    spec = importlib.util.spec_from_file_location("botfather_cli", cli_path)
    botfather_cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(botfather_cli)
    assert hasattr(botfather_cli, "click_button")
    assert hasattr(botfather_cli, "send_message")

def test_botfather_cli_click_button_subprocess():
    cli_path = Path(__file__).parent.parent.parent.parent / "mcp" / "plugins" / "botfather" / "cli.py"
    result = subprocess.run(
        [sys.executable, str(cli_path), "click-button", "--button-text", "Test", "--msg-id", "123"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert "result" in output

def test_botfather_cli_send_message_subprocess():
    cli_path = Path(__file__).parent.parent.parent.parent / "mcp" / "plugins" / "botfather" / "cli.py"
    result = subprocess.run(
        [sys.executable, str(cli_path), "send-message", "--message", "Hello"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert "result" in output 