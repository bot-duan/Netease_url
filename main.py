"""HTTP adapter for the shared music service. Default port: 5023."""
import argparse
import logging
import atexit
from urllib.parse import quote
from flask import Flask, request, send_file, render_template

from config import APIConfig, QUALITY_NAMES
from music_service import MusicAPIService, ServiceError
from music_api import APIException
from music_downloader import DownloadException
from download_jobs import DownloadJobs


class APIResponse:
    @staticmethod
    def success(data=None, message='success', status_code=200):
        return {'status': status_code, 'success': True, 'message': message, 'data': data}, status_code

    @staticmethod
    def error(message, status_code=400, error_code='RequestError'):
        return {'status': status_code, 'success': False, 'message': message,
                'error_code': error_code, 'error': {'type': error_code, 'message': message}}, status_code


def create_app(config=None, service=None):
    config = config or APIConfig.from_env()
    app = Flask(__name__)
    service = service or MusicAPIService(config)
    app.extensions['music_service'] = service
    jobs = DownloadJobs(service)
    app.extensions['download_jobs'] = jobs
    atexit.register(jobs.shutdown)

    def data():
        if request.method == 'GET':
            return request.args.to_dict()
        payload = request.get_json(silent=True)
        if payload is not None and not isinstance(payload, dict):
            raise ServiceError('JSON 请求必须为对象')
        return {**request.form.to_dict(), **(payload or {})}

    @app.after_request
    def cors(response):
        response.headers['Access-Control-Allow-Origin'] = config.cors_origins
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
        return response

    @app.errorhandler(ServiceError)
    def service_error(exc):
        return APIResponse.error(str(exc), exc.status, exc.kind)

    @app.errorhandler(APIException)
    @app.errorhandler(DownloadException)
    def upstream_error(exc):
        return APIResponse.error(str(exc), 502, type(exc).__name__)

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(405)
    def http_error(exc):
        return APIResponse.error(exc.description, exc.code)

    @app.errorhandler(Exception)
    def unexpected_error(exc):
        app.logger.exception('请求处理失败')
        return APIResponse.error('服务器内部错误', 500, 'InternalError')

    @app.get('/')
    def index():
        return render_template('index.html')

    @app.get('/health')
    def health():
        return APIResponse.success(service.health(), 'API服务运行正常')

    @app.route('/song', methods=['GET', 'POST'])
    @app.route('/Song_V1', methods=['GET', 'POST'])
    def song():
        params = data()
        info_type = params.get('type', 'url')
        result = service.song(params.get('id') or params.get('ids') or params.get('url'),
                              params.get('level'), info_type)
        if info_type == 'json':
            # Preserve the web player's formatted size field.
            result['size_bytes'] = result['size']
            result['size'] = result['size_formatted']
        return APIResponse.success(result)

    @app.route('/search', methods=['GET', 'POST'])
    @app.route('/Search', methods=['GET', 'POST'])
    def search():
        params = data()
        result = service.search(params.get('keyword') or params.get('keywords') or params.get('q'),
                                params.get('limit', 30), params.get('offset', 0), params.get('type', '1'))
        # Keep the existing song array shape, expose real pagination alongside it.
        response, status = APIResponse.success(result['songs'] if result['type'] == '1' else result)
        response['pagination'] = {key: result[key] for key in ('total', 'returned', 'offset', 'type')}
        return response, status

    @app.route('/playlist', methods=['GET', 'POST'])
    @app.route('/Playlist', methods=['GET', 'POST'])
    def playlist():
        return APIResponse.success(service.playlist(data().get('id')))

    @app.route('/album', methods=['GET', 'POST'])
    @app.route('/Album', methods=['GET', 'POST'])
    def album():
        return APIResponse.success(service.album(data().get('id')))

    @app.route('/download', methods=['GET', 'POST'])
    @app.route('/Download', methods=['GET', 'POST'])
    def download():
        params = data()
        return_format = params.get('format', 'file')
        if return_format not in ('file', 'json', 'info'):
            raise ServiceError('format 必须为 file、json 或 info')
        if return_format == 'info':
            return APIResponse.success(service.download_info(params.get('id'), params.get('quality')))
        result = service.download(params.get('id'), params.get('quality'))
        if return_format == 'json':
            return APIResponse.success(result, '下载完成')
        response = send_file(result['file_path'], as_attachment=True, download_name=result['filename'],
                             mimetype={'mp3': 'audio/mpeg', 'm4a': 'audio/mp4'}.get(result['file_type'], 'audio/flac'))
        response.headers['X-Download-Filename'] = quote(result['filename'], safe='')
        return response

    @app.post('/downloads/jobs')
    def submit_job():
        params = data()
        return APIResponse.success(jobs.submit(params.get('id'), params.get('quality')), status_code=202)

    @app.get('/downloads/jobs/<job_id>')
    def job_status(job_id):
        return APIResponse.success(jobs.get(job_id))

    @app.post('/downloads/jobs/<job_id>/cancel')
    def cancel_job(job_id):
        return APIResponse.success(jobs.cancel(job_id))

    @app.get('/api/info')
    def api_info():
        return APIResponse.success({'name': '网易云音乐API服务', 'version': '2.0.0',
            'supported_qualities': list(QUALITY_NAMES),
            'endpoints': {rule.rule: ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
                          for rule in app.url_map.iter_rules() if rule.endpoint != 'static'},
            'config': {'downloads_dir': str(service.downloads_path.resolve()),
                       'max_file_size': config.max_file_size, 'request_timeout': config.request_timeout}})

    return app


def start_api_server():
    config = APIConfig.from_env()
    parser = argparse.ArgumentParser(description='网易云音乐 API 服务')
    parser.add_argument('--host', default=config.host)
    parser.add_argument('--port', type=int, default=config.port)
    parser.add_argument('--cookie', default=config.cookie_file)
    parser.add_argument('--downloads-dir', default=config.downloads_dir)
    parser.add_argument('--level', choices=list(QUALITY_NAMES), default=config.default_quality)
    args = parser.parse_args()
    config.host, config.port = args.host, args.port
    config.cookie_file, config.downloads_dir = args.cookie, args.downloads_dir
    config.default_quality = args.level
    logging.basicConfig(level=config.log_level)
    app = create_app(config)
    app.run(host=config.host, port=config.port, debug=config.debug, threaded=True)


if __name__ == '__main__':
    start_api_server()
