import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PLUGIN_DIR = os.getenv("PLUGIN_DIR", os.path.join(BASE_DIR, "plugins"))
    DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", 60))
    LOG_FILE = os.getenv("LOG_FILE", "mcp.log") 