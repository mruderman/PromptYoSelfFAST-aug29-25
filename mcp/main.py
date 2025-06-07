from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from .models import RunJobRequest, RunJobResponse
from .queue import JobQueue
from .config import Config
from .logger import logger
from .help import get_help
import subprocess
import threading
import os
import json
from typing import Dict, Any
import glob

app = FastAPI(
    title="MCP (Master Control Program)",
    description="Internal tools orchestration server for managing command-line tools and automation scripts.",
    version="1.0.0"
)

queue = JobQueue()

PLUGIN_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")

def discover_plugins():
    plugins = {}
    for plugin_dir in glob.glob(os.path.join(PLUGIN_ROOT, "*")):
        if os.path.isdir(plugin_dir):
            cli_path = os.path.join(plugin_dir, "cli.py")
            if os.path.exists(cli_path):
                plugin_name = os.path.basename(plugin_dir)
                plugins[plugin_name] = cli_path
    return plugins

PLUGINS = discover_plugins()

# Global cache for help output
HELP_CACHE = {}

def build_help_cache():
    global HELP_CACHE
    HELP_CACHE = {}
    for plugin_name, cli_path in PLUGINS.items():
        try:
            proc = subprocess.run(["python", cli_path, "--help"], capture_output=True, text=True, timeout=5)
            HELP_CACHE[plugin_name] = proc.stdout
        except Exception as e:
            HELP_CACHE[plugin_name] = f"Error: {e}"

# Populate cache on startup
build_help_cache()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/run", response_model=RunJobResponse)
async def run_job(request: RunJobRequest) -> RunJobResponse:
    job = queue.add_job(request.model_dump())
    event = threading.Event()
    result_holder: Dict[str, Any] = {}

    def worker():
        try:
            plugin_name = request.plugin
            cli_path = PLUGINS.get(plugin_name)
            if not cli_path:
                raise HTTPException(status_code=404, detail=f"Plugin {plugin_name} not found")

            cmd = ["python", cli_path, request.command]
            for k, v in (request.args or {}).items():
                if v is not None:
                    cmd.append(f"--{k.replace('_', '-')}")
                    cmd.append(str(v))

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=request.timeout or Config.DEFAULT_TIMEOUT
            )

            try:
                output = json.loads(proc.stdout)
            except json.JSONDecodeError:
                output = proc.stdout

            if proc.returncode == 0:
                result_holder["result"] = RunJobResponse(
                    status="success",
                    plugin=request.plugin,
                    command=request.command,
                    args=request.args or {},
                    output=output,
                    error=None
                )
            else:
                result_holder["result"] = RunJobResponse(
                    status="error",
                    plugin=request.plugin,
                    command=request.command,
                    args=request.args or {},
                    output=output,
                    error=output.get("error") if isinstance(output, dict) else proc.stderr
                )
        except subprocess.TimeoutExpired:
            result_holder["result"] = RunJobResponse(
                status="timeout",
                plugin=request.plugin,
                command=request.command,
                args=request.args or {},
                output=None,
                error="timeout"
            )
        except Exception as e:
            result_holder["result"] = RunJobResponse(
                status="error",
                plugin=request.plugin,
                command=request.command,
                args=request.args or {},
                output=None,
                error=str(e)
            )
        finally:
            event.set()

    t = threading.Thread(target=worker)
    t.start()
    event.wait()
    
    if "result" not in result_holder:
        raise HTTPException(status_code=500, detail="Internal server error during job execution")
    
    logger.info(f"Job {job.id}: {result_holder['result'].status}")
    return result_holder["result"]

@app.get("/help")
def help_endpoint():
    help_data = HELP_CACHE.copy()
    help_data["core"] = {
        "reload-help": "Rebuild the help cache for all plugins."
    }
    return JSONResponse(help_data)

@app.post("/reload-help")
def reload_help():
    build_help_cache()
    return {"status": "success", "message": "Help cache rebuilt"} 