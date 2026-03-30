"""CLI命令处理模块

包含所有CLI命令的实现逻辑。
"""

import logging
import sys
from typing import Dict, Any, Optional
from datetime import datetime

from main import MusicAPIService, APIConfig
from music_api import APIException
from music_api import url_v1, name_v1, lyric_v1, search_music, playlist_detail, album_detail

from .errors import CLIException, ExitCode
from .formatters import JSONFormatter


class CLICommand:
    """CLI命令处理器

    封装所有CLI命令的实现逻辑，复用MusicAPIService。
    """

    def __init__(self, cookie_file: Optional[str] = None, verbose: bool = False, quiet: bool = False):
        """
        初始化CLI命令处理器

        Args:
            cookie_file: Cookie文件路径
            verbose: 是否输出详细日志
            quiet: 是否静默模式
        """
        self.config = APIConfig()

        # 如果指定了cookie文件，更新配置
        if cookie_file:
            self.config.cookie_file = cookie_file

        self.service = MusicAPIService(self.config)
        self.setup_logging(verbose, quiet)

    def setup_logging(self, verbose: bool, quiet: bool):
        """设置日志"""
        self.logger = logging.getLogger('cli')
        self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)

        # 清除现有的处理器
        self.logger.handlers.clear()

        if not quiet:
            handler = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter(
                '[%(levelname)s] %(asctime)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def health(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            self.logger.info("执行健康检查")

            # 检查Cookie状态
            cookie_valid = self.service.cookie_manager.is_cookie_valid()

            data = {
                "service": "running",
                "timestamp": int(datetime.now().timestamp()),
                "cookie_status": "valid" if cookie_valid else "invalid",
                "version": "2.0.0"
            }

            return JSONFormatter.success(data, "API服务运行正常")

        except Exception as e:
            self.logger.error(f"健康检查失败: {e}")
            raise CLIException(
                ExitCode.SYSTEM_ERROR,
                "HealthCheckError",
                "健康检查失败",
                {"error": str(e)}
            )

    def song(self, song_id: str, level: str = "lossless", info_type: str = "url") -> Dict[str, Any]:
        """获取歌曲信息

        Args:
            song_id: 歌曲ID或URL
            level: 音质等级
            info_type: 信息类型 (url/name/lyric/json)

        Returns:
            格式化的JSON响应
        """
        try:
            # 提取音乐ID
            music_id = self.service._extract_music_id(song_id)
            self.logger.info(f"开始处理歌曲ID: {music_id}, 类型: {info_type}, 音质: {level}")

            # 获取Cookie
            cookies = self.service._get_cookies()

            # 根据类型获取不同信息
            if info_type == 'url':
                result = url_v1(music_id, level, cookies)
                if result and result.get('data') and len(result['data']) > 0:
                    song_data = result['data'][0]
                    response_data = {
                        "id": song_data.get('id'),
                        "url": song_data.get('url'),
                        "level": song_data.get('level'),
                        "size": song_data.get('size'),
                        "type": song_data.get('type'),
                        "bitrate": song_data.get('br')
                    }
                    return JSONFormatter.success(response_data, "获取歌曲URL成功")
                else:
                    raise CLIException(
                        ExitCode.BUSINESS_ERROR,
                        "SongNotFoundError",
                        "歌曲不存在或无法访问",
                        {"song_id": str(music_id), "level": level, "suggestion": "请检查歌曲ID是否正确或降低音质"}
                    )

            elif info_type == 'name':
                result = name_v1(music_id)
                if result and result.get('songs'):
                    return JSONFormatter.success(result, "获取歌曲信息成功")
                else:
                    raise CLIException(
                        ExitCode.BUSINESS_ERROR,
                        "SongNotFoundError",
                        "歌曲不存在或无法访问",
                        {"song_id": str(music_id)}
                    )

            elif info_type == 'lyric':
                result = lyric_v1(music_id, cookies)
                if result:
                    return JSONFormatter.success(result, "获取歌词成功")
                else:
                    raise CLIException(
                        ExitCode.BUSINESS_ERROR,
                        "LyricNotFoundError",
                        "歌词不存在或无法访问",
                        {"song_id": str(music_id)}
                    )

            elif info_type == 'json':
                # 获取完整的歌曲信息
                song_info = name_v1(music_id)
                url_info = url_v1(music_id, level, cookies)
                lyric_info = lyric_v1(music_id, cookies)

                if not song_info or 'songs' not in song_info or not song_info['songs']:
                    raise CLIException(
                        ExitCode.BUSINESS_ERROR,
                        "SongNotFoundError",
                        "歌曲不存在或无法访问",
                        {"song_id": str(music_id)}
                    )

                song_data = song_info['songs'][0]

                # 构建完整响应
                response_data = {
                    'id': music_id,
                    'name': song_data.get('name', ''),
                    'ar_name': ', '.join(artist['name'] for artist in song_data.get('ar', [])),
                    'al_name': song_data.get('al', {}).get('name', ''),
                    'pic': song_data.get('al', {}).get('picUrl', ''),
                    'level': level,
                    'lyric': lyric_info.get('lrc', {}).get('lyric', '') if lyric_info else '',
                    'tlyric': lyric_info.get('tlyric', {}).get('lyric', '') if lyric_info else ''
                }

                # 添加URL和大小信息
                if url_info and url_info.get('data') and len(url_info['data']) > 0:
                    url_data = url_info['data'][0]
                    response_data.update({
                        'url': url_data.get('url', ''),
                        'size': url_data.get('size', 0),
                        'level': url_data.get('level', level)
                    })
                else:
                    response_data.update({
                        'url': '',
                        'size': 0
                    })

                return JSONFormatter.success(response_data, "获取歌曲完整信息成功")

            else:
                raise CLIException(
                    ExitCode.PARAMETER_ERROR,
                    "InvalidTypeError",
                    f"不支持的信息类型: {info_type}",
                    {"supported_types": ["url", "name", "lyric", "json"]}
                )

        except CLIException:
            raise
        except APIException as e:
            self.logger.error(f"API调用失败: {e}")
            raise CLIException(
                ExitCode.SYSTEM_ERROR,
                "APICallError",
                f"API调用失败: {e}",
                {"song_id": song_id, "type": info_type}
            )
        except Exception as e:
            self.logger.error(f"处理歌曲信息时发生错误: {e}")
            raise CLIException(
                ExitCode.SYSTEM_ERROR,
                "SongProcessingError",
                f"处理歌曲信息时发生错误: {e}",
                {"song_id": song_id}
            )

    def search(self, keyword: str, limit: int = 30, offset: int = 0, search_type: str = "1") -> Dict[str, Any]:
        """搜索音乐

        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
            offset: 偏移量
            search_type: 搜索类型 (1-歌曲, 10-专辑, 100-歌手, 1000-歌单)

        Returns:
            格式化的JSON响应
        """
        try:
            # 参数验证
            if not keyword or not keyword.strip():
                raise CLIException(
                    ExitCode.PARAMETER_ERROR,
                    "MissingKeywordError",
                    "搜索关键词不能为空",
                    {}
                )

            # 限制搜索数量
            limit = min(limit, 100)

            self.logger.info(f"执行搜索: 关键词='{keyword}', 类型={search_type}, 限制={limit}")

            cookies = self.service._get_cookies()
            result = search_music(keyword, cookies, limit)

            if result:
                # 添加艺术家字符串
                for song in result:
                    if 'artists' in song:
                        song['artist_string'] = song['artists']

                response_data = {
                    "result": {
                        "songs": result,
                        "total": len(result),
                        "returned": len(result)
                    }
                }
                return JSONFormatter.success(response_data, "搜索完成")
            else:
                # 搜索无结果
                response_data = {
                    "result": {
                        "songs": [],
                        "total": 0,
                        "returned": 0
                    }
                }
                return JSONFormatter.success(response_data, "未找到相关结果")

        except CLIException:
            raise
        except APIException as e:
            self.logger.error(f"API调用失败: {e}")
            raise CLIException(
                ExitCode.SYSTEM_ERROR,
                "APICallError",
                f"搜索API调用失败: {e}",
                {"keyword": keyword}
            )
        except Exception as e:
            self.logger.error(f"搜索时发生错误: {e}")
            raise CLIException(
                ExitCode.SYSTEM_ERROR,
                "SearchError",
                f"搜索时发生错误: {e}",
                {"keyword": keyword}
            )

    def playlist(self, playlist_id: str) -> Dict[str, Any]:
        """获取歌单详情

        Args:
            playlist_id: 歌单ID或URL

        Returns:
            格式化的JSON响应
        """
        try:
            # 提取歌单ID
            # 支持URL格式: https://music.163.com/playlist?id=xxx
            if 'music.163.com' in playlist_id and 'playlist?id=' in playlist_id:
                import re
                match = re.search(r'playlist\?id=(\d+)', playlist_id)
                if match:
                    playlist_id = match.group(1)
                else:
                    raise CLIException(
                        ExitCode.PARAMETER_ERROR,
                        "InvalidPlaylistURLError",
                        "无法从URL中提取歌单ID",
                        {"url": playlist_id}
                    )

            self.logger.info(f"获取歌单详情: {playlist_id}")

            cookies = self.service._get_cookies()
            result = playlist_detail(playlist_id, cookies)

            response_data = {
                "status": "success",
                "playlist": result
            }
            return JSONFormatter.success(response_data, "获取歌单详情成功")

        except CLIException:
            raise
        except APIException as e:
            self.logger.error(f"API调用失败: {e}")
            raise CLIException(
                ExitCode.SYSTEM_ERROR,
                "APICallError",
                f"获取歌单API调用失败: {e}",
                {"playlist_id": playlist_id}
            )
        except Exception as e:
            self.logger.error(f"获取歌单时发生错误: {e}")
            raise CLIException(
                ExitCode.SYSTEM_ERROR,
                "PlaylistError",
                f"获取歌单时发生错误: {e}",
                {"playlist_id": playlist_id}
            )

    def album(self, album_id: str) -> Dict[str, Any]:
        """获取专辑详情

        Args:
            album_id: 专辑ID或URL

        Returns:
            格式化的JSON响应
        """
        try:
            # 提取专辑ID
            # 支持URL格式: https://music.163.com/album?id=xxx
            if 'music.163.com' in album_id and 'album?id=' in album_id:
                import re
                match = re.search(r'album\?id=(\d+)', album_id)
                if match:
                    album_id = match.group(1)
                else:
                    raise CLIException(
                        ExitCode.PARAMETER_ERROR,
                        "InvalidAlbumURLError",
                        "无法从URL中提取专辑ID",
                        {"url": album_id}
                    )

            self.logger.info(f"获取专辑详情: {album_id}")

            cookies = self.service._get_cookies()
            result = album_detail(album_id, cookies)

            response_data = {
                "status": 200,
                "album": result
            }
            return JSONFormatter.success(response_data, "获取专辑详情成功")

        except CLIException:
            raise
        except APIException as e:
            self.logger.error(f"API调用失败: {e}")
            raise CLIException(
                ExitCode.SYSTEM_ERROR,
                "APICallError",
                f"获取专辑API调用失败: {e}",
                {"album_id": album_id}
            )
        except Exception as e:
            self.logger.error(f"获取专辑时发生错误: {e}")
            raise CLIException(
                ExitCode.SYSTEM_ERROR,
                "AlbumError",
                f"获取专辑时发生错误: {e}",
                {"album_id": album_id}
            )

    def download(self, music_id: str, quality: str = "lossless", return_format: str = "file") -> Dict[str, Any]:
        """下载音乐

        Args:
            music_id: 音乐ID或URL
            quality: 音质等级
            return_format: 返回格式 (file-下载文件, json-仅返回信息)

        Returns:
            格式化的JSON响应
        """
        try:
            # 提取音乐ID
            extracted_id = self.service._extract_music_id(music_id)
            self.logger.info(f"开始下载: 音乐ID={extracted_id}, 音质={quality}, 格式={return_format}")

            # 如果只是获取信息，不下载文件
            if return_format == 'json':
                cookies = self.service._get_cookies()
                music_info = self.service.downloader.get_music_info(extracted_id, quality)

                response_data = {
                    "download_available": True,
                    "music_info": {
                        "id": music_info.id,
                        "name": music_info.name,
                        "artist": music_info.artists,
                        "album": music_info.album,
                        "quality": quality,
                        "url": music_info.download_url,
                        "file_size": music_info.file_size
                    }
                }
                return JSONFormatter.success(response_data, "获取下载信息成功")

            else:
                # 下载文件到本地
                result = self.service.downloader.download_music_file(extracted_id, quality)

                if result.success:
                    response_data = {
                        "music_id": extracted_id,
                        "name": result.music_info.name,
                        "artist": result.music_info.artists,
                        "album": result.music_info.album,
                        "quality": quality,
                        "quality_name": self.service._get_quality_display_name(quality),
                        "file_type": result.music_info.file_type,
                        "file_size": result.file_size,
                        "file_size_formatted": self.service._format_file_size(result.file_size),
                        "file_path": result.file_path,
                        "filename": result.file_path.split('/')[-1] if result.file_path else "",
                        "duration": result.music_info.duration
                    }
                    return JSONFormatter.success(response_data, "下载完成")
                else:
                    raise CLIException(
                        ExitCode.BUSINESS_ERROR,
                        "DownloadError",
                        result.error_message or "下载失败",
                        {"music_id": extracted_id, "quality": quality}
                    )

        except CLIException:
            raise
        except Exception as e:
            self.logger.error(f"下载时发生错误: {e}")
            raise CLIException(
                ExitCode.SYSTEM_ERROR,
                "DownloadError",
                f"下载时发生错误: {e}",
                {"music_id": music_id, "quality": quality}
            )
