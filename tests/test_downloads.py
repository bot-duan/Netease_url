import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from unittest.mock import Mock

import pytest
import requests

from music_downloader import MusicDownloader, MusicInfo


@pytest.fixture
def downloader(tmp_path):
    item = MusicDownloader(str(tmp_path), cookie_manager=Mock(), api=Mock())
    item._write_music_tags = Mock(return_value=[])
    return item


def info(quality='lossless', song_id=1):
    return MusicInfo(song_id, '同名歌曲', '歌手', '专辑', '', 120, 1,
                     'https://example.invalid/audio', 'flac', 6, quality)


class Response:
    headers = {'Content-Length': '6'}
    def __init__(self, chunks=(b'abc', b'def')):
        self.chunks = chunks
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def raise_for_status(self): pass
    def iter_content(self, chunk_size):
        for chunk in self.chunks:
            if isinstance(chunk, Exception): raise chunk
            yield chunk


def test_interrupted_retry_and_corrupted_cache(downloader):
    session = Mock()
    downloader._local.session = session
    session.get.side_effect = [Response((b'abc', requests.ConnectionError('broken'))),
                               Response(), Response()]
    result = downloader.download_music_file(1, music_info=info())
    assert not result.success
    assert not list(downloader.download_dir.glob('*.flac'))
    assert not list(downloader.download_dir.glob('.download-*'))
    result = downloader.download_music_file(1, music_info=info())
    assert result.success
    assert downloader.download_music_file(1, music_info=info()).success
    assert session.get.call_count == 2
    from pathlib import Path
    Path(result.file_path).write_bytes(b'broken')
    assert downloader.download_music_file(1, music_info=info()).success
    assert session.get.call_count == 3


def test_identity_quality_and_metadata_extension(downloader):
    downloader._local.session = Mock(get=Mock(side_effect=lambda *a, **k: Response()))
    paths = [downloader.download_music_file(i.id, music_info=i).file_path
             for i in (info(), info('hires'), info(song_id=2))]
    assert len(set(paths)) == 3
    assert all(path.endswith('.flac') for path in paths)


def test_short_body_and_cancel_not_published(downloader):
    downloader._local.session = Mock(get=Mock(return_value=Response((b'abc',))))
    assert not downloader.download_music_file(1, music_info=info()).success
    stop = threading.Event()
    stop.set()
    assert not downloader.download_music_file(1, music_info=info(), cancel=stop).success
    assert not list(downloader.download_dir.glob('*.flac'))


def test_duplicate_concurrent_downloads(downloader):
    calls = []
    def get(*args, **kwargs):
        calls.append(1)
        time.sleep(.03)
        return Response()
    def run():
        downloader._local.session = Mock(get=get)
        return downloader.download_music_file(1, music_info=info())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert all(result.success for result in results)
    assert len(calls) == 1


def test_actual_quality_recorded(downloader):
    downloader.api.get_song_url.return_value = {'data': [{'url': 'x', 'type': 'flac', 'level': 'lossless'}]}
    downloader.api.get_song_detail.return_value = {'songs': [{'name': 'song'}]}
    downloader.api.get_lyric.return_value = {}
    result = downloader.get_music_info(1, 'hires')
    assert result.quality == 'lossless'
    assert result.requested_quality == 'hires'


def test_async_metadata_does_not_block_event_loop(downloader):
    def slow(*args, **kwargs):
        time.sleep(.08)
        return True
    downloader.download_music_file = slow
    async def run():
        task = asyncio.create_task(downloader.download_music_file_async(1))
        await asyncio.sleep(.01)
        assert not task.done()
        assert await task
    asyncio.run(run())


def test_ctrl_c_during_transfer_removes_partial_file(downloader):
    def cancel_after_chunk():
        yield b'abc'
        raise KeyboardInterrupt

    downloader._local.session = Mock(get=Mock(return_value=Response(cancel_after_chunk())))
    with pytest.raises(KeyboardInterrupt):
        downloader.download_music_file(1, music_info=info())
    assert not list(downloader.download_dir.glob('*.flac'))
    assert not list(downloader.download_dir.glob('.download-*'))
