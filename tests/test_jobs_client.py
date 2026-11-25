import threading
import time
from unittest.mock import Mock

from api_client import APIClient
from config import APIConfig
from download_jobs import DownloadJobs
from music_service import ServiceError


def test_client_preserves_server_error():
    client = APIClient()
    response = Mock(ok=False, status_code=404)
    response.json.return_value = {'success': False, 'message': '音质不可用', 'error_code': 'Unavailable'}
    client._local.session = Mock(post=Mock(return_value=response))
    result = client.download(1)
    assert result['error']['message'] == '音质不可用'
    assert client.session.post.call_args.kwargs['timeout'] == 600


def test_job_cancel_progress_and_queue_limit():
    service = Mock(config=APIConfig(max_concurrent=1))
    service._extract_music_id.side_effect = str
    service.validate_quality.side_effect = lambda x: x
    started = threading.Event()
    def download(identifier, quality, progress, cancel):
        progress(3, 6)
        started.set()
        cancel.wait(2)
        raise ServiceError('下载已取消')
    service.download.side_effect = download
    jobs = DownloadJobs(service, capacity=1)
    try:
        job = jobs.submit(1, 'lossless')
        assert started.wait(1)
        assert jobs.get(job['id'])['downloaded'] == 3
        try:
            jobs.submit(2, 'lossless')
            assert False, 'queue must be bounded'
        except ServiceError as exc:
            assert exc.status == 429
        jobs.cancel(job['id'])
        deadline = time.monotonic() + 2
        while jobs.get(job['id'])['state'] not in ('cancelled', 'failed') and time.monotonic() < deadline:
            time.sleep(.01)
        assert jobs.get(job['id'])['state'] == 'cancelled'
    finally:
        jobs.shutdown()
