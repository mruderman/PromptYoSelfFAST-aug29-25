from fastapi.testclient import TestClient
from mcp.main import app

client = TestClient(app)

def test_help():
    response = client.get("/help")
    assert response.status_code == 200
    data = response.json()
    # Expect plugin names as top-level keys
    assert "botfather" in data
    help_text = data["botfather"].lower()
    assert "usage" in help_text  # Should contain argparse help output
    assert "click-button" in help_text  # Should mention the command
    # Core functions should be present
    assert "core" in data
    assert "reload-help" in data["core"]
    assert "rebuild" in data["core"]["reload-help"].lower()

def test_reload_help():
    response = client.post("/reload-help")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Help cache rebuilt" 