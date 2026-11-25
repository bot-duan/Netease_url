"""CLI presentation adapter; business operations live in music_service."""
import logging
from config import APIConfig
from music_service import MusicAPIService, ServiceError
from music_api import APIException
from music_downloader import DownloadException
from .errors import CLIException, ExitCode
from .formatters import JSONFormatter


class CLICommand:
    def __init__(self, cookie_file=None, verbose=False, quiet=False, downloads_dir=None):
        self.config = APIConfig.from_env()
        if cookie_file:
            self.config.cookie_file = cookie_file
        if downloads_dir:
            self.config.downloads_dir = downloads_dir
        logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
        if quiet:
            logging.disable(logging.CRITICAL)
        self.logger = logging.getLogger('cli')
        self.service = MusicAPIService(self.config)

    def _call(self, operation, *args, **kwargs):
        try:
            return JSONFormatter.success(operation(*args, **kwargs))
        except ServiceError as exc:
            code = (ExitCode.PARAMETER_ERROR if exc.status == 400 else
                    ExitCode.AUTH_ERROR if exc.status in (401, 403) else
                    ExitCode.BUSINESS_ERROR if exc.status == 404 else ExitCode.SYSTEM_ERROR)
            raise CLIException(code, exc.kind, str(exc)) from exc
        except (APIException, DownloadException, OSError) as exc:
            raise CLIException(ExitCode.SYSTEM_ERROR, type(exc).__name__, str(exc)) from exc

    def health(self):
        return self._call(self.service.health)

    def song(self, song_id, level=None, info_type='url'):
        return self._call(self.service.song, song_id, level, info_type)

    def search(self, keyword, limit=30, offset=0, search_type='1'):
        result = self._call(self.service.search, keyword, limit, offset, search_type)
        result['data'] = {'result': result['data']}
        return result

    def playlist(self, playlist_id):
        return self._call(self.service.playlist, playlist_id)

    def album(self, album_id):
        return self._call(self.service.album, album_id)

    def download(self, music_id, quality=None, return_format='file'):
        if return_format not in ('file', 'json', 'info'):
            raise CLIException(ExitCode.PARAMETER_ERROR, 'ParameterError', '无效的下载格式')
        # Legacy CLI --format json remains info-only. Explicit info works in both transports.
        operation = self.service.download_info if return_format in ('json', 'info') else self.service.download
        return self._call(operation, music_id, quality)
