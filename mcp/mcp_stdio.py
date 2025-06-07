import sys
import os
import json
import threading
import queue
import uuid
import signal
import time
import subprocess
from typing import Dict, Any
try:
    from .logger import logger
except ImportError:
    from logger import logger
import glob

PLUGIN_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")
DEFAULT_TIMEOUT = 60

class Job:
    def __init__(self, job_id, plugin, action, args, timeout):
        self.id = job_id
        self.plugin = plugin
        self.action = action
        self.args = args
        self.timeout = timeout or DEFAULT_TIMEOUT
        self.status = 'queued'
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None

class MCPStdio:
    def __init__(self):
        self.job_queue = queue.Queue()
        self.jobs = {}
        self.plugins = self.discover_plugins()
        self.help_cache = {}
        self.shutdown_flag = threading.Event()
        self.worker = threading.Thread(target=self.worker_loop, daemon=True)
        self.worker.start()
        signal.signal(signal.SIGTERM, self.handle_sigterm)

    def discover_plugins(self):
        plugins = {}
        for plugin_dir in glob.glob(os.path.join(PLUGIN_ROOT, "*")):
            if os.path.isdir(plugin_dir):
                cli_path = os.path.join(plugin_dir, "cli.py")
                if os.path.exists(cli_path):
                    plugin_name = os.path.basename(plugin_dir)
                    plugins[plugin_name] = cli_path
        return plugins

    def build_help_cache(self):
        self.help_cache = {}
        for plugin_name, cli_path in self.plugins.items():
            try:
                proc = subprocess.run(["python", cli_path, "--help"], capture_output=True, text=True, timeout=5)
                self.help_cache[plugin_name] = proc.stdout
            except Exception as e:
                self.help_cache[plugin_name] = f"Error: {e}"

    def handle_sigterm(self, signum, frame):
        self.shutdown_flag.set()
        self.send_event({"status": "shutdown"})
        sys.stdout.flush()
        sys.exit(0)

    def send_event(self, obj: Dict[str, Any]):
        sys.stdout.write(json.dumps(obj) + "\n")
        sys.stdout.flush()

    def worker_loop(self):
        while not self.shutdown_flag.is_set():
            try:
                job = self.job_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            job.status = "started"
            job.start_time = time.time()
            self.send_event({"id": job.id, "status": "started", "payload": {}})
            result, status, error = self.run_plugin(job)
            job.status = status
            job.result = result
            job.error = error
            job.end_time = time.time()
            payload = result if status == "success" else {"error": error}
            self.send_event({"id": job.id, "status": status, "payload": payload})
            logger.info({
                "job_id": job.id,
                "plugin": job.plugin,
                "action": job.action,
                "status": status,
                "duration": round(job.end_time - job.start_time, 3) if job.end_time and job.start_time else None
            })

    def run_plugin(self, job: Job):
        cli_path = self.plugins.get(job.plugin)
        if not cli_path:
            return None, "error", "not_found"
        cmd = ["python", cli_path, job.action]
        for k, v in (job.args or {}).items():
            if v is not None:
                cmd.append(f"--{k.replace('_', '-')}")
                cmd.append(str(v))
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=job.timeout,
                stdin=subprocess.DEVNULL
            )
            try:
                output = json.loads(proc.stdout)
            except Exception:
                output = proc.stdout.strip()
                if output:
                    output = {"output": output}
                else:
                    output = {}
            if proc.returncode == 0:
                return output, "success", None
            else:
                err = output.get("error") if isinstance(output, dict) else proc.stderr.strip()
                return output, "error", err or "error"
        except subprocess.TimeoutExpired:
            return None, "timeout", "timeout"
        except Exception as e:
            return None, "error", str(e)

    def main(self):
        self.build_help_cache()
        self.send_event({"status": "ready"})
        while not self.shutdown_flag.is_set():
            line = sys.stdin.readline()
            if not line:
                self.shutdown_flag.set()
                self.send_event({"status": "shutdown"})
                break
            try:
                req = json.loads(line)
            except Exception:
                continue
            req_id = req.get("id") or str(uuid.uuid4())
            cmd = req.get("command")
            payload = req.get("payload") or {}
            if cmd == "help":
                self.send_event({"id": req_id, "status": "success", "payload": self.help_cache})
            elif cmd == "reload-help":
                self.build_help_cache()
                self.send_event({"id": req_id, "status": "success", "payload": "ok"})
            elif cmd == "health":
                self.send_event({"id": req_id, "status": "success", "payload": "ok"})
            elif cmd == "run":
                plugin = payload.get("plugin")
                action = payload.get("action")
                args = payload.get("args") or {}
                timeout = payload.get("timeout")
                job = Job(req_id, plugin, action, args, timeout)
                self.jobs[job.id] = job
                self.send_event({"id": job.id, "status": "queued", "payload": {}})
                self.job_queue.put(job)
                logger.info({"job_id": job.id, "plugin": plugin, "action": action, "status": "queued"})
            else:
                self.send_event({"id": req_id, "status": "error", "payload": {"error": "not_found"}})

if __name__ == "__main__":
    MCPStdio().main() 