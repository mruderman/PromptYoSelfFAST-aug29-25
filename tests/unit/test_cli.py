import pytest
import json
import subprocess

# The CLI script to test
CLI_SCRIPT = "promptyoself/cli.py"

def run_cli_command(args):
    """Helper function to run the CLI command and return the result."""
    process = subprocess.run(
        ["python", CLI_SCRIPT] + args,
        capture_output=True,
        text=True
    )
    return process

def extract_json(text):
    """Extracts the first valid JSON object from a string."""
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != 0:
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        return None
    return None

def test_register_prompt_missing_agent_id():
    args = ["register", "--prompt", "Hello"]
    result = run_cli_command(args)
    assert result.returncode != 0
    assert "required: --agent-id" in result.stderr

def test_register_prompt_missing_prompt():
    args = ["register", "--agent-id", "test-agent"]
    result = run_cli_command(args)
    assert result.returncode != 0
    assert "required: --prompt" in result.stderr

def test_register_prompt_no_schedule_option():
    args = ["register", "--agent-id", "test-agent", "--prompt", "Hello"]
    result = run_cli_command(args)
    assert result.returncode == 1
    output = extract_json(result.stdout)
    assert "error" in output
    assert "Must specify one of" in output["error"]

def test_register_prompt_multiple_schedule_options():
    args = [
        "register",
        "--agent-id", "test-agent",
        "--prompt", "Hello",
        "--time", "2025-01-01T12:00:00",
        "--cron", "* * * * *"
    ]
    result = run_cli_command(args)
    assert result.returncode == 1
    output = extract_json(result.stdout)
    assert "error" in output
    assert "Cannot specify multiple scheduling options" in output["error"]

def test_cancel_prompt_missing_id():
    args = ["cancel"]
    result = run_cli_command(args)
    assert result.returncode != 0
    assert "required: --id" in result.stderr
