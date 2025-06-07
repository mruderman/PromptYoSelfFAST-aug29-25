import logging
import sys
try:
    from .config import Config
except ImportError:
    from config import Config

logger = logging.getLogger("mcp")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

file_handler = logging.FileHandler(Config.LOG_FILE)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler) 