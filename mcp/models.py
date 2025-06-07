from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class RunJobRequest(BaseModel):
    plugin: str
    command: str
    args: Dict[str, Any] = Field(default_factory=dict)
    timeout: Optional[int] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "plugin": "botfather",
                "command": "click-button",
                "args": {"button-text": "Payments", "msg-id": 12345678},
                "timeout": 90
            }
        }
    }

class RunJobResponse(BaseModel):
    status: str
    plugin: str
    command: str
    args: Dict[str, Any]
    output: Any = None
    error: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "plugin": "botfather",
                "command": "click-button",
                "args": {"button-text": "Payments", "msg-id": 12345678},
                "output": {"result": "Clicked button Payments on message 12345678"},
                "error": None
            }
        }
    } 