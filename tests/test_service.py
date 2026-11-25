import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest

from config import APIConfig, QUALITY_NAMES
from main import create_app
from music_service import MusicAPIService
from music_downloader import DownloadResult
from music_api import NeteaseAPI
from cli.commands import CLICommand
from test_downloads import info


@pytest.fixture
def service(tmp_path):
    config = APIConfig(cookie_file=str(tmp_path/'auth'/'cookie.txt'), downloads_dir=str(tmp_path/'music'))
    service = MusicAPIService(config)
    return service


@pytest.fixture
def client(service):
    app = create_app(service.config, service)
    yield app.test_client()
    app.extensions['download_jobs'].shutdown()


def test_config_propagates(service):
    assert service.cookie_manager is service.downloader.cookie_manager
    assert service.netease_api is service.downloader.api
    assert service.downloads_path == service.downloader.download_dir
    assert service.cookie_manager.cookie_file == Path(service.config.cookie_file)


def test_env_and_cli_override(tmp_path, monkeypatch):
    monkeypatch.setenv('NETEASE_DOWNLOADS_DIR', str(tmp_path/'env'))
    monkeypatch.setenv('NETEASE_COOKIE_FILE', str(tmp_path/'env.cookie'))
    monkeypatch.setenv('NETEASE_REQUEST_TIMEOUT', '9')
    cli = CLICommand(cookie_file=str(tmp_path/'explicit.cookie'))
    assert cli.service.cookie_manager.cookie_file.name == 'explicit.cookie'
    assert cli.service.downloader.download_dir == tmp_path/'env'
    assert cli.service.netease_api.timeout == 9


def test_http_query_vs_download_and_file_name(service, client):
    service.downloader.get_music_info = Mock(return_value=info())
    path = service.downloads_path/'real.flac'
    path.write_bytes(b'abcdef')
    service.downloader.download_music_file = Mock(return_value=DownloadResult(True, str(path), 6, music_info=info()))
    response = client.post('/download', json={'id': 1, 'format': 'info'})
    assert response.status_code == 200
    service.downloader.download_music_file.assert_not_called()
    result = client.post('/download', json={'id': 1, 'format': 'json'}).json['data']
    assert result['filename'] == Path(result['file_path']).name == 'real.flac'
    assert result['quality'] == 'lossless'
    service.downloader.get_music_info.assert_called_once()


def test_search_type_offset_and_totals(service, client):
    api = service.netease_api
    api._local.session = Mock()
    api.session.post.return_value.json.return_value = {
        'code': 200, 'result': {'albums': [{'id': 3}], 'albumCount': 42}}
    response = client.post('/search', json={'keywords': 'a', 'type': '10', 'offset': 20, 'limit': 5})
    assert response.json['data']['total'] == 42
    assert response.json['data']['albums'] == [{'id': 3}]
    sent = api.session.post.call_args.kwargs['data']
    assert sent == {'s': 'a', 'type': 10, 'offset': 20, 'limit': 5}


def test_song_search_legacy_array(service, client):
    service.netease_api.search = Mock(return_value={'songs': [{'id': 1}], 'total': 7,
                                                  'returned': 1, 'offset': 0, 'type': '1'})
    response = client.get('/Search?keywords=a')
    assert response.json['data'] == [{'id': 1}]
    assert response.json['pagination']['total'] == 7


@pytest.mark.parametrize('payload', [[], {'id': 'bad'}, {'id': 1, 'level': 'nope'}])
def test_bad_parameters(client, payload):
    response = client.post('/song', json=payload)
    assert response.status_code == 400
    assert response.json['error']['message']


def test_alias_and_quality(service, client):
    service.netease_api.get_song_url = Mock(return_value={'data': [{'id': 1, 'url': 'x', 'level': 'dolby'}]})
    assert client.get('/Song_V1?id=1&level=dolby').status_code == 200
    assert set(client.get('/api/info').json['data']['supported_qualities']) == set(QUALITY_NAMES)


def test_cli_import_has_no_side_effects(tmp_path):
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, 'PYTHONPATH': str(root)}
    result = subprocess.run([sys.executable, '-c', 'import cli.commands'], cwd=tmp_path,
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert not list(tmp_path.iterdir())


def test_cli_json_health_and_error(tmp_path):
    root = Path(__file__).resolve().parents[1]
    for args, code in [(['health'], 0), (['song', 'bad'], 2)]:
        result = subprocess.run([sys.executable, str(root/'cli.py'), '--cookie', str(tmp_path/'cookie'),
                                 '--downloads-dir', str(tmp_path/'music'), *args],
                                cwd=tmp_path, capture_output=True, text=True)
        assert result.returncode == code, result.stderr
        assert json.loads(result.stdout)['success'] == (code == 0)


def test_song_details_remain_available_without_playback_link(service, client):
    service.netease_api.get_song_url = Mock(return_value={'data': [{'url': None}]})
    service.netease_api.get_song_detail = Mock(return_value={'songs': [{'name': '曲目'}]})
    service.netease_api.get_lyric = Mock(return_value={})
    assert client.get('/song?id=1').status_code == 404
    result = client.get('/song?id=1&type=json')
    assert result.status_code == 200
    assert result.json['data']['name'] == '曲目'
    assert result.json['data']['url'] == ''


def test_background_download_routes_stream_and_save(service, client, monkeypatch):
    import time
    import requests
    from test_downloads import Response

    service.netease_api.get_song_url = Mock(return_value={'data': [{
        'url': 'https://example.invalid/audio', 'type': 'flac', 'size': 6,
        'level': 'lossless',
    }]})
    service.netease_api.get_song_detail = Mock(return_value={'songs': [{'name': '曲目'}]})
    service.netease_api.get_lyric = Mock(return_value={})
    monkeypatch.setattr(requests.Session, 'get', Mock(return_value=Response()))
    monkeypatch.setattr(service.downloader, '_write_music_tags', Mock(return_value=[]))

    submitted = client.post('/downloads/jobs', json={'id': 123, 'quality': 'hires'})
    assert submitted.status_code == 202
    job_url = '/downloads/jobs/' + submitted.json['data']['id']
    until = time.monotonic() + 2
    while True:
        job = client.get(job_url).json['data']
        if job['state'] in ('completed', 'failed') or time.monotonic() >= until:
            break
        time.sleep(.01)

    assert job['state'] == 'completed', job
    assert job['downloaded'] == job['total'] == 6
    assert job['result']['requested_quality'] == 'hires'
    assert job['result']['quality'] == 'lossless'
    assert Path(job['result']['file_path']).read_bytes() == b'abcdef'
    assert service.netease_api.get_song_url.call_count == 1
    assert service.netease_api.get_song_detail.call_count == 1

    response = client.get('/download?id=123&quality=hires')
    assert response.status_code == 200
    assert response.data == b'abcdef'
    assert requests.Session.get.call_count == 1
