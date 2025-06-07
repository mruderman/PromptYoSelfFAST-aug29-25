import os
from fastapi.testclient import TestClient
from mcp.main import app

client = TestClient(app)

# Ensure the plugin directory exists and the mock plugin is present
PLUGIN_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins", "botfather", "cli.py")

def test_run_click_button():
    if not os.path.exists(PLUGIN_PATH):
        # Skip test if plugin is missing
        import pytest
        pytest.skip("botfather/cli.py not found")
    payload = {
        "plugin": "botfather",
        "command": "click-button",
        "args": {"button-text": "Payments", "msg-id": 12345678},
        "timeout": 5
    }
    response = client.post("/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["plugin"] == "botfather"
    assert data["command"] == "click-button"
    assert "Clicked button" in str(data["output"]) 