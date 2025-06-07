import queue
import threading
import uuid
from typing import Any, Dict

class Job:
    def __init__(self, data: Dict[str, Any]):
        self.id = str(uuid.uuid4())
        self.data = data
        self.status = 'queued'
        self.result = None
        self.error = None

class JobQueue:
    def __init__(self):
        self.q = queue.Queue()
        self.lock = threading.Lock()
        self.jobs = {}

    def add_job(self, data: Dict[str, Any]) -> Job:
        job = Job(data)
        with self.lock:
            self.jobs[job.id] = job
        self.q.put(job)
        return job

    def get_job(self) -> Job:
        return self.q.get()

    def set_result(self, job_id: str, result: Any, error: str = None):
        with self.lock:
            job = self.jobs.get(job_id)
            if job:
                job.result = result
                job.error = error
                job.status = 'success' if not error else 'error'

    def get_status(self, job_id: str) -> str:
        with self.lock:
            job = self.jobs.get(job_id)
            if job:
                return job.status
            return 'not_found' 