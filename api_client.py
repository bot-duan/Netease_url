#!/usr/bin/env python3
"""
API客户端模块

网易云音乐 HTTP 服务的 Python 客户端。
"""

import os
import threading
import requests
from typing import Optional, Dict, List, Any


class APIClientConfig:
    """API客户端配置"""

    def __init__(
        self,
        base_url: str = None,
        timeout: int = None,
        download_timeout: int = None
    ):
        self.base_url = (base_url or os.environ.get("NETEASE_API_URL", "http://127.0.0.1:5023")).rstrip("/")
        self.timeout = timeout or int(os.environ.get("NETEASE_REQUEST_TIMEOUT", "30"))
        self.download_timeout = download_timeout or int(os.environ.get("NETEASE_DOWNLOAD_TIMEOUT", "600"))


class APIClient:
    """统一的API客户端"""

    def __init__(self, config: Optional[APIClientConfig] = None):
        """
        初始化API客户端

        Args:
            config: API客户端配置，默认使用标准配置
        """
        self.config = config or APIClientConfig()
        self._local = threading.local()

    @property
    def session(self):
        if not hasattr(self._local, 'session'):
            self._local.session = requests.Session()
            self._local.session.headers.update({'User-Agent': 'NeteaseMusic-CLI/2.0'})
        return self._local.session

    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Dict = None,
        data: Dict = None,
        timeout: int = None
    ) -> Dict:
        """
        执行HTTP请求

        Args:
            endpoint: API端点路径
            method: HTTP方法 (GET/POST)
            params: URL参数
            data: POST数据

        Returns:
            API响应的JSON数据
        """
        url = f"{self.config.base_url}{endpoint}"

        try:
            if method == "GET":
                response = self.session.get(
                    url,
                    params=params,
                    timeout=timeout or self.config.timeout
                )
            else:  # POST
                response = self.session.post(
                    url,
                    params=params,
                    json=data,
                    timeout=timeout or self.config.timeout
                )

            try:
                payload = response.json()
            except ValueError:
                response.raise_for_status()
                raise ValueError('服务返回了非 JSON 数据')
            if not isinstance(payload, dict):
                raise ValueError('服务返回了无效的数据格式')
            if not response.ok or not payload.get('success', True):
                payload['success'] = False
                payload.setdefault('error', {'type': payload.get('error_code', 'HTTPError'),
                                             'message': payload.get('message', f'HTTP错误: {response.status_code}')})
            return payload

        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": {
                    "type": "ConnectionError",
                    "message": f"无法连接到API服务 ({self.config.base_url})，请确保main.py正在运行"
                }
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": {
                    "type": "TimeoutError",
                    "message": f"请求超时（超过{self.config.timeout}秒）"
                }
            }
        except requests.exceptions.HTTPError as e:
            return {
                "success": False,
                "error": {
                    "type": "HTTPError",
                    "message": f"HTTP错误: {e.response.status_code}"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": {
                    "type": "RequestError",
                    "message": f"请求失败: {str(e)}"
                }
            }

    def health(self) -> Dict:
        """健康检查"""
        return self._make_request("/health")

    def search(
        self,
        keyword: str,
        limit: int = 30,
        offset: int = 0,
        search_type: str = "1"
    ) -> Dict:
        """
        搜索音乐

        Args:
            keyword: 搜索关键词
            limit: 返回数量限制（最多100）
            offset: 偏移量（用于分页）
            search_type: 搜索类型（1=歌曲, 10=专辑, 100=歌手, 1000=歌单）

        Returns:
            搜索结果
        """
        return self._make_request(
            "/search",
            method="POST",
            data={
                "keywords": keyword,
                "limit": limit,
                "offset": offset,
                "type": search_type
            }
        )

    def get_song(
        self,
        song_id: int,
        level: str = "lossless",
        info_type: str = "json"
    ) -> Dict:
        """
        获取歌曲信息

        Args:
            song_id: 歌曲ID
            level: 音质等级
            info_type: 信息类型（url/name/lyric/json）

        Returns:
            歌曲信息
        """
        return self._make_request(
            "/song",
            method="POST",
            data={"id": song_id, "level": level, "type": info_type}
        )

    def get_playlist(self, playlist_id: str) -> Dict:
        """
        获取歌单详情

        Args:
            playlist_id: 歌单ID

        Returns:
            歌单详情
        """
        return self._make_request(
            "/playlist",
            method="POST",
            data={"id": playlist_id}
        )

    def get_album(self, album_id: str) -> Dict:
        """
        获取专辑详情

        Args:
            album_id: 专辑ID

        Returns:
            专辑详情
        """
        return self._make_request(
            "/album",
            method="POST",
            data={"id": album_id}
        )

    def download(
        self,
        song_id: int,
        quality: str = "lossless",
        return_format: str = "json"
    ) -> Dict:
        """
        下载音乐

        Args:
            song_id: 歌曲ID
            quality: 音质等级
            return_format: 返回格式（file=下载文件, json=仅返回信息）

        Returns:
            下载结果
        """
        return self._make_request(
            "/download",
            method="POST",
            data={
                "id": song_id,
                "quality": quality,  # 修复：使用正确的参数名
                "format": return_format
            },
            timeout=self.config.download_timeout
        )

    def download_info(self, song_id, quality="lossless"):
        return self.download(song_id, quality, return_format="info")

    def start_download(self, song_id, quality="lossless"):
        return self._make_request('/downloads/jobs', method='POST',
                                  data={'id': song_id, 'quality': quality})

    def download_status(self, job_id):
        return self._make_request(f'/downloads/jobs/{job_id}')

    def cancel_download(self, job_id):
        return self._make_request(f'/downloads/jobs/{job_id}/cancel', method='POST')

    def check_connection(self) -> bool:
        """
        检查API连接是否正常

        Returns:
            连接是否正常
        """
        result = self.health()
        return result.get("success", False)


# 单例实例，供其他模块直接使用
_default_client: Optional[APIClient] = None


def get_api_client() -> APIClient:
    """获取默认API客户端实例"""
    global _default_client
    if _default_client is None:
        _default_client = APIClient()
    return _default_client


def call_api(
    endpoint: str,
    method: str = "GET",
    params: Dict = None,
    data: Dict = None
) -> Dict:
    """
    便捷的API调用函数（向后兼容）

    Args:
        endpoint: API端点路径
        method: HTTP方法 (GET/POST)
        params: URL参数
        data: POST数据

    Returns:
        API响应的JSON数据
    """
    client = get_api_client()
    return client._make_request(endpoint, method, params, data)
