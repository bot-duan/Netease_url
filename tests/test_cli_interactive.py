import io
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest
from rich.console import Console

from cli_interactive import InteractiveShell
from config import APIConfig
from music_service import ServiceError


@pytest.fixture
def shell(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('NETEASE_TUI_CONFIG', raising=False)
    output = io.StringIO()
    service = Mock(config=APIConfig())
    return InteractiveShell(service, Console(file=output, width=100)), output


def enter(monkeypatch, *answers):
    inputs = iter(answers)

    def read():
        try:
            return next(inputs)
        except StopIteration:
            raise EOFError from None

    monkeypatch.setattr('builtins.input', read)


def test_search_pages_ranges_and_retries_only_failures(shell, monkeypatch):
    ui, output = shell
    page_one = [{'id': i, 'name': str(i)} for i in range(1, 11)]
    page_two = [{'id': 11, 'name': '[red]歌曲'}, {'id': 12, 'name': '重试歌曲'}]
    ui.service.search.side_effect = [
        {'songs': page_one, 'total': 12}, {'songs': page_two, 'total': 12},
    ]

    attempts = []

    def download(song_id, quality, *, progress):
        attempts.append((song_id, quality))
        progress(32, 64)
        if song_id == 12 and attempts.count((12, 'hires')) == 1:
            raise ServiceError('网络超时', 502)
        return {'quality_name': 'Hi-Res音质', 'file_path': f'/music/{song_id}.flac'}

    ui.service.download.side_effect = download
    enter(monkeypatch, '', '关键词', 'n', '1,11', '11-12,11', 'q', '4', '', 'y', '0')
    assert ui.run() == 0
    assert [c.kwargs['offset'] for c in ui.service.search.call_args_list] == [0, 10]
    assert attempts == [(11, 'hires'), (12, 'hires'), (12, 'hires')]
    assert '[red]歌曲' in output.getvalue()
    assert '网络超时' in output.getvalue()
    assert '/music/12.flac' in output.getvalue()


@pytest.mark.parametrize(('option', 'kind', 'items_key'), [
    ('2', 'playlist', 'tracks'), ('3', 'album', 'songs'),
])
def test_collection_all_requires_confirmation(shell, monkeypatch, option, kind, items_key):
    ui, output = shell
    songs = [{'id': i, 'name': str(i)} for i in range(1, 13)]
    getattr(ui.service, kind).return_value = {kind: {'name': '合集', items_key: songs}}
    ui.service.download.return_value = {'quality_name': '无损音质', 'file_path': '/music/track.flac'}
    enter(monkeypatch, option, '42', 'all', 'b', 'all', '', '0')
    assert ui.run() == 0
    assert [c.args for c in ui.service.download.call_args_list] == [(i, 'lossless') for i in range(1, 13)]
    assert '合集 · 共 12 首' in output.getvalue()


def test_ctrl_c_skips_remaining_downloads_and_returns_to_menu(shell, monkeypatch):
    ui, output = shell
    ui.service.album.return_value = {'album': {'songs': [{'id': 1}, {'id': 2}]}}
    ui.service.download.side_effect = KeyboardInterrupt
    enter(monkeypatch, '3', '42', 'all', '', '0')
    assert ui.run() == 0
    ui.service.download.assert_called_once()
    assert '取消 2 首' in output.getvalue()


@pytest.mark.parametrize('options', [[], ['-i', '--downloads-dir', 'music', '--cookie', 'custom.cookie']])
def test_normal_entry_runs_interactive_without_server(tmp_path, options):
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, 'NETEASE_API_URL': 'http://127.0.0.1:1',
           'NETEASE_DOWNLOADS_DIR': 'downloads', 'NETEASE_COOKIE_FILE': 'cookie.txt'}
    process = subprocess.run([sys.executable, str(root / 'cli.py'), *options], cwd=tmp_path,
                             input='0\n', capture_output=True, text=True, env=env, timeout=5)
    assert process.returncode == 0, process.stderr
    assert '1. 搜索歌曲' in process.stdout
    assert '\x1b[?1049h' not in process.stdout
    if options:
        assert (tmp_path / 'music').is_dir()
        assert (tmp_path / 'custom.cookie').is_file()
