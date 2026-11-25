"""Transport-independent business operations shared by HTTP and CLI."""
import logging
import re
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from config import APIConfig, QUALITY_NAMES
from cookie_manager import CookieManager, CookieException
from music_api import NeteaseAPI
from music_downloader import MusicDownloader


class ServiceError(Exception):
    def __init__(self, message, status=400, kind='ParameterError'):
        super().__init__(message)
        self.status = status
        self.kind = kind


class MusicAPIService:
    def __init__(self, config=None):
        self.config = config or APIConfig.from_env()
        self.logger = logging.getLogger('music_service')
        self.cookie_manager = CookieManager(self.config.cookie_file)
        self.netease_api = NeteaseAPI(timeout=self.config.request_timeout)
        self.downloads_path = Path(self.config.downloads_dir)
        self.downloader = MusicDownloader(
            str(self.downloads_path), self.config.max_concurrent,
            cookie_manager=self.cookie_manager, api=self.netease_api,
            timeout=self.config.request_timeout, max_file_size=self.config.max_file_size)

    def _get_cookies(self):
        try:
            return self.cookie_manager.parse_cookies()
        except CookieException:
            return {}

    def _extract_music_id(self, value):
        value = str(value or '').strip()
        if re.fullmatch(r'[0-9]+', value) and int(value) > 0:
            return value
        parsed = urlparse(value)
        if parsed.scheme in ('https', 'http') and parsed.hostname == '163cn.tv':
            response = self.netease_api.session.get(value, allow_redirects=False,
                                                   timeout=self.config.request_timeout)
            value = response.headers.get('Location', '')
            parsed = urlparse(value)
        if parsed.scheme in ('https', 'http') and parsed.hostname in ('music.163.com', 'y.music.163.com'):
            query = parsed.query or urlparse(parsed.fragment).query
            identifier = parse_qs(query).get('id', [''])[0]
            if re.fullmatch(r'[0-9]+', identifier) and int(identifier) > 0:
                return identifier
        raise ServiceError('请提供有效的网易云音乐 ID 或链接')

    def validate_quality(self, quality):
        quality = quality or self.config.default_quality
        if quality not in QUALITY_NAMES:
            raise ServiceError('无效的音质参数，支持: ' + ', '.join(QUALITY_NAMES))
        return quality

    @staticmethod
    def _format_file_size(size):
        value = float(size or 0)
        for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
            if value < 1024 or unit == 'TB':
                return f'{value:.2f}{unit}'
            value /= 1024

    @staticmethod
    def _get_quality_display_name(quality):
        return QUALITY_NAMES.get(quality, quality)

    def health(self):
        return {'service': 'running', 'timestamp': int(time.time()), 'version': '2.0.0',
                'cookie_status': 'valid' if self.cookie_manager.is_cookie_valid() else 'invalid',
                'cookie_check': 'local_format_only',
                'downloads_dir': str(self.downloads_path.resolve())}

    def song(self, song_id, level=None, info_type='url'):
        identifier = self._extract_music_id(song_id)
        level = self.validate_quality(level)
        if info_type not in ('url', 'name', 'lyric', 'json'):
            raise ServiceError('信息类型必须是 url、name、lyric 或 json')
        cookies = self._get_cookies()
        api = self.netease_api
        if info_type == 'name':
            result = api.get_song_detail(identifier)
            if not result.get('songs'):
                raise ServiceError('歌曲不存在或无法访问', 404, 'SongNotFoundError')
            return result
        if info_type == 'lyric':
            return api.get_lyric(identifier, cookies)
        urls = api.get_song_url(identifier, level, cookies).get('data') or []
        url = urls[0] if urls else {}
        if info_type == 'url' and not url.get('url'):
            raise ServiceError('无可用下载链接，可能是版权限制或音质不支持', 404, 'SongUnavailableError')
        result = {'id': url.get('id', identifier), 'url': url.get('url') or '',
                  'level': url.get('level') or level, 'requested_quality': level,
                  'size': url.get('size', 0), 'type': url.get('type'), 'bitrate': url.get('br')}
        result['quality_name'] = self._get_quality_display_name(result['level'])
        result['size_formatted'] = self._format_file_size(result['size'])
        if info_type == 'json':
            songs = api.get_song_detail(identifier).get('songs') or []
            if not songs:
                raise ServiceError('歌曲不存在或无法访问', 404, 'SongNotFoundError')
            song = songs[0]
            lyric = api.get_lyric(identifier, cookies) or {}
            result.update(name=song.get('name', ''),
                          ar_name=', '.join(a['name'] for a in song.get('ar', [])),
                          al_name=song.get('al', {}).get('name', ''),
                          pic=song.get('al', {}).get('picUrl', ''),
                          lyric=lyric.get('lrc', {}).get('lyric', ''),
                          tlyric=lyric.get('tlyric', {}).get('lyric', ''))
        return result

    def search(self, keyword, limit=30, offset=0, search_type='1'):
        if not isinstance(keyword, str) or not keyword.strip():
            raise ServiceError('搜索关键词不能为空')
        try:
            limit, offset = int(limit), int(offset)
        except (TypeError, ValueError):
            raise ServiceError('limit 和 offset 必须是整数')
        if limit < 1 or offset < 0 or str(search_type) not in ('1', '10', '100', '1000'):
            raise ServiceError('无效的搜索数量、偏移量或类型')
        return self.netease_api.search(keyword.strip(), self._get_cookies(),
                                      min(limit, 100), offset, str(search_type))

    def playlist(self, identifier):
        return {'status': 'success', 'playlist': self.netease_api.get_playlist_detail(
            self._extract_music_id(identifier), self._get_cookies())}

    def album(self, identifier):
        return {'status': 200, 'album': self.netease_api.get_album_detail(
            self._extract_music_id(identifier), self._get_cookies())}

    def download_info(self, identifier, quality=None):
        quality = self.validate_quality(quality)
        info = self.downloader.get_music_info(self._extract_music_id(identifier), quality)
        return {'download_available': True, 'music_info': {
            'id': info.id, 'name': info.name, 'artist': info.artists, 'album': info.album,
            'quality': info.quality, 'requested_quality': quality,
            'url': info.download_url, 'file_size': info.file_size}}

    def download(self, identifier, quality=None, *, progress=None, cancel=None):
        quality = self.validate_quality(quality)
        identifier = self._extract_music_id(identifier)
        result = self.downloader.download_music_file(identifier, quality, progress=progress, cancel=cancel)
        if not result.success:
            raise ServiceError(result.error_message, 502, 'DownloadError')
        info = result.music_info
        return {'music_id': identifier, 'name': info.name, 'artist': info.artists,
                'album': info.album, 'quality': info.quality, 'requested_quality': quality,
                'quality_name': self._get_quality_display_name(info.quality),
                'file_type': info.file_type, 'file_size': result.file_size,
                'file_size_formatted': self._format_file_size(result.file_size),
                'file_path': str(Path(result.file_path).resolve()),
                'filename': Path(result.file_path).name, 'duration': info.duration,
                'warnings': result.warnings}
