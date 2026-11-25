"""Bounded in-process download jobs for one server process; completed jobs expire."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import threading
import time
import uuid

from music_service import ServiceError


class DownloadJobs:
    def __init__(self, service, capacity=100, ttl=3600):
        self.service = service
        self.capacity, self.ttl = capacity, ttl
        self.executor = ThreadPoolExecutor(max_workers=service.config.max_concurrent,
                                           thread_name_prefix='music-download')
        self.lock = threading.Lock()
        self.jobs = {}

    def submit(self, identifier, quality):
        identifier = self.service._extract_music_id(identifier)
        quality = self.service.validate_quality(quality)
        with self.lock:
            now = time.time()
            self.jobs = {key: job for key, job in self.jobs.items()
                         if not job['finished'] or now - job['finished'] < self.ttl}
            if len(self.jobs) >= self.capacity:
                # Evict oldest completed jobs before rejecting active queue overflow.
                for key in sorted(self.jobs, key=lambda k: self.jobs[k]['finished'] or float('inf')):
                    if self.jobs[key]['finished']:
                        del self.jobs[key]
                        break
            if len(self.jobs) >= self.capacity:
                raise ServiceError('下载队列已满，请稍后再试', 429, 'QueueFullError')
            job_id = uuid.uuid4().hex
            self.jobs[job_id] = {'id': job_id, 'state': 'queued', 'downloaded': 0, 'total': 0,
                                 'result': None, 'error': None, 'cancel': threading.Event(), 'finished': 0}
            self.executor.submit(self._run, job_id, identifier, quality)
            return self._snapshot(self.jobs[job_id])

    def _run(self, job_id, identifier, quality):
        with self.lock:
            job = self.jobs[job_id]
            cancel = job['cancel']
            job['state'] = 'running'
        def progress(downloaded, total):
            with self.lock:
                job.update(downloaded=downloaded, total=total)
        try:
            if cancel.is_set():
                raise ServiceError('下载已取消')
            result = self.service.download(identifier, quality, progress=progress, cancel=cancel)
            with self.lock:
                job.update(state='completed', result=result)
        except Exception as exc:
            with self.lock:
                job.update(state='cancelled' if cancel.is_set() else 'failed',
                           error={'type': getattr(exc, 'kind', type(exc).__name__), 'message': str(exc)})
        finally:
            with self.lock:
                job['finished'] = time.time()

    @staticmethod
    def _snapshot(job):
        return deepcopy({key: value for key, value in job.items() if key != 'cancel'})

    def _lookup(self, job_id):
        job = self.jobs.get(job_id)
        if job and job['finished'] and time.time() - job['finished'] >= self.ttl:
            del self.jobs[job_id]
            job = None
        if job is None:
            raise ServiceError('下载任务不存在或已过期', 404, 'JobNotFoundError')
        return job

    def get(self, job_id):
        with self.lock:
            return self._snapshot(self._lookup(job_id))

    def cancel(self, job_id):
        with self.lock:
            job = self._lookup(job_id)
            job['cancel'].set()
            return self._snapshot(job)

    def shutdown(self):
        with self.lock:
            for job in self.jobs.values():
                job['cancel'].set()
        self.executor.shutdown(wait=True, cancel_futures=True)
