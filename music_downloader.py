"""音乐下载器模块

提供网易云音乐下载功能，包括：
- 音乐信息获取
- 文件下载到本地
- 内存下载
- 音乐标签写入
- 异步下载支持
"""

import os
import re
import asyncio
import logging
import hashlib
import json
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import field
from io import BytesIO
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

import requests
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, APIC
from mutagen.mp4 import MP4

from music_api import NeteaseAPI, APIException, QualityLevel
from cookie_manager import CookieManager


class AudioFormat(Enum):
    """音频格式枚举"""
    MP3 = "mp3"
    FLAC = "flac"
    M4A = "m4a"
    UNKNOWN = "unknown"


@dataclass
class MusicInfo:
    """音乐信息数据类"""
    id: int
    name: str
    artists: str
    album: str
    pic_url: str
    duration: int
    track_number: int
    download_url: str
    file_type: str
    file_size: int
    quality: str
    lyric: str = ""
    tlyric: str = ""
    requested_quality: str = ""


@dataclass
class DownloadResult:
    """下载结果数据类"""
    success: bool
    file_path: Optional[str] = None
    file_size: int = 0
    error_message: str = ""
    music_info: Optional[MusicInfo] = None
    warnings: List[str] = field(default_factory=list)


class DownloadException(Exception):
    """下载异常类"""
    pass


class MusicDownloader:
    """音乐下载器主类"""
    
    def __init__(self, download_dir: str = "downloads", max_concurrent: int = 3,
                 cookie_manager=None, api=None, timeout=30, max_file_size=500 * 1024 * 1024):
        """
        初始化音乐下载器
        
        Args:
            download_dir: 下载目录
            max_concurrent: 最大并发下载数
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.max_concurrent = max_concurrent
        
        # 初始化依赖
        self.cookie_manager = cookie_manager or CookieManager()
        self.api = api or NeteaseAPI()
        self.timeout = timeout
        self.max_file_size = max_file_size
        self.logger = logging.getLogger(__name__)
        self._local = threading.local()
        
        # 支持的文件格式
        self.supported_formats = {
            'mp3': AudioFormat.MP3,
            'flac': AudioFormat.FLAC,
            'm4a': AudioFormat.M4A
        }
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除非法字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            清理后的安全文件名
        """
        # 移除或替换非法字符
        illegal_chars = r'[<>:"/\\|?*]'
        filename = re.sub(illegal_chars, '_', filename)
        
        # 移除前后空格和点
        filename = filename.strip(' .')
        
        # 限制长度
        if len(filename) > 200:
            filename = filename[:200]
        
        return filename or "unknown"
    
    def _determine_file_extension(self, url: str, content_type: str = "") -> str:
        """根据URL和Content-Type确定文件扩展名
        
        Args:
            url: 下载URL
            content_type: HTTP Content-Type头
            
        Returns:
            文件扩展名
        """
        # 首先尝试从URL获取
        if '.flac' in url.lower():
            return '.flac'
        elif '.mp3' in url.lower():
            return '.mp3'
        elif '.m4a' in url.lower():
            return '.m4a'
        
        # 从Content-Type获取
        content_type = content_type.lower()
        if 'flac' in content_type:
            return '.flac'
        elif 'mpeg' in content_type or 'mp3' in content_type:
            return '.mp3'
        elif 'mp4' in content_type or 'm4a' in content_type:
            return '.m4a'
        
        return '.mp3'  # 默认
    
    def get_music_info(self, music_id: int, quality: str = "standard") -> MusicInfo:
        """获取音乐详细信息
        
        Args:
            music_id: 音乐ID
            quality: 音质等级
            
        Returns:
            音乐信息对象
            
        Raises:
            DownloadException: 获取信息失败时抛出
        """
        try:
            # 获取cookies
            cookies = self.cookie_manager.parse_cookies()
            
            # 获取音乐URL信息
            url_result = self.api.get_song_url(music_id, quality, cookies)
            if not url_result.get('data') or not url_result['data']:
                raise DownloadException(f"无法获取音乐ID {music_id} 的播放链接")
            
            song_data = url_result['data'][0]
            download_url = song_data.get('url', '')
            if not download_url:
                raise DownloadException(f"音乐ID {music_id} 无可用的下载链接")
            
            # 获取音乐详情
            detail_result = self.api.get_song_detail(music_id)
            if not detail_result.get('songs') or not detail_result['songs']:
                raise DownloadException(f"无法获取音乐ID {music_id} 的详细信息")
            
            song_detail = detail_result['songs'][0]
            
            # 获取歌词
            lyric_result = self.api.get_lyric(music_id, cookies)
            lyric = lyric_result.get('lrc', {}).get('lyric', '') if lyric_result else ''
            tlyric = lyric_result.get('tlyric', {}).get('lyric', '') if lyric_result else ''
            
            # 构建艺术家字符串
            artists = '/'.join(artist['name'] for artist in song_detail.get('ar', []))
            
            # 创建MusicInfo对象
            music_info = MusicInfo(
                id=music_id,
                name=song_detail.get('name', '未知歌曲'),
                artists=artists or '未知艺术家',
                album=song_detail.get('al', {}).get('name', '未知专辑'),
                pic_url=song_detail.get('al', {}).get('picUrl', ''),
                duration=song_detail.get('dt', 0) // 1000,  # 转换为秒
                track_number=song_detail.get('no', 0),
                download_url=download_url,
                file_type=song_data.get('type', 'mp3').lower(),
                file_size=song_data.get('size', 0),
                quality=song_data.get('level') or quality,
                requested_quality=quality,
                lyric=lyric,
                tlyric=tlyric
            )
            
            return music_info
            
        except APIException as e:
            raise DownloadException(f"API调用失败: {e}")
        except Exception as e:
            raise DownloadException(f"获取音乐信息时发生错误: {e}")
    
    @property
    def session(self):
        # A connection pool per worker; requests sessions are not shared across threads.
        if not hasattr(self._local, "session"):
            self._local.session = requests.Session()
        return self._local.session

    def _file_path(self, info):
        if info.file_type not in self.supported_formats:
            raise DownloadException(f"不支持的音频格式: {info.file_type}")
        name = self._sanitize_filename(f"{info.artists} - {info.name}")
        name = name.encode('utf-8')[:150].decode('utf-8', errors='ignore')
        identity = self._sanitize_filename(f"{info.id}-{info.quality}")
        return self.download_dir / f"{name} [{identity}].{info.file_type}"

    @staticmethod
    def _digest(path):
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        return digest.hexdigest()

    @contextmanager
    def _file_lock(self, path):
        # flock coordinates CLI and server processes on supported macOS/Linux hosts.
        import fcntl
        lock_dir = self.download_dir / '.locks'
        lock_dir.mkdir(exist_ok=True)
        key = hashlib.sha256(str(path.resolve()).encode()).hexdigest()
        with (lock_dir / key).open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _cached(self, path, info):
        try:
            receipt = json.loads(path.with_suffix(path.suffix + '.json').read_text())
            return (str(receipt['id']) == str(info.id)
                    and receipt['quality'] == info.quality
                    and receipt['size'] == path.stat().st_size > 0
                    and receipt['sha256'] == self._digest(path))
        except (OSError, ValueError, KeyError, TypeError):
            return False

    def download_music_file(self, music_id, quality="standard", *, music_info=None,
                            progress=None, cancel=None):
        """Download atomically. Only a verified file with a receipt is reusable."""
        temporary = receipt_tmp = None
        try:
            info = music_info or self.get_music_info(music_id, quality)
            path = self._file_path(info)
            with self._file_lock(path):
                if cancel and cancel.is_set():
                    raise DownloadException("下载已取消")
                if self._cached(path, info):
                    receipt = json.loads(path.with_suffix(path.suffix + '.json').read_text())
                    if progress:
                        progress(info.file_size, info.file_size)
                    return DownloadResult(True, str(path), path.stat().st_size,
                                          music_info=info, warnings=receipt.get('warnings', []))
                if info.file_size > self.max_file_size:
                    raise DownloadException("文件超过下载大小限制")
                fd, name = tempfile.mkstemp(prefix='.download-', suffix=path.suffix, dir=self.download_dir)
                os.close(fd)
                temporary = Path(name)
                with self.session.get(info.download_url, stream=True, timeout=self.timeout,
                                      headers={'Accept-Encoding': 'identity'}) as response:
                    response.raise_for_status()
                    length = int(response.headers.get('Content-Length', 0))
                    if length > self.max_file_size:
                        raise DownloadException("文件超过下载大小限制")
                    expected = info.file_size or length
                    downloaded = 0
                    with temporary.open('wb') as stream:
                        for chunk in response.iter_content(chunk_size=64 * 1024):
                            if cancel and cancel.is_set():
                                raise DownloadException("下载已取消")
                            if not chunk:
                                continue
                            downloaded += len(chunk)
                            if downloaded > self.max_file_size:
                                raise DownloadException("文件超过下载大小限制")
                            stream.write(chunk)
                            if progress:
                                progress(downloaded, expected)
                        stream.flush()
                        os.fsync(stream.fileno())
                    if not downloaded or (expected and downloaded != expected) or (length and downloaded != length):
                        raise DownloadException(f"文件不完整: 收到 {downloaded} 字节，预期 {expected or length} 字节")
                if cancel and cancel.is_set():
                    raise DownloadException("下载已取消")
                warnings = self._write_music_tags(temporary, info) or []
                if cancel and cancel.is_set():
                    raise DownloadException("下载已取消")
                receipt = {'id': str(info.id), 'quality': info.quality,
                           'size': temporary.stat().st_size, 'sha256': self._digest(temporary),
                           'warnings': warnings}
                fd, name = tempfile.mkstemp(prefix='.receipt-', suffix='.tmp', dir=self.download_dir)
                os.close(fd)
                receipt_tmp = Path(name)
                receipt_tmp.write_text(json.dumps(receipt, ensure_ascii=False), encoding='utf-8')
                os.replace(temporary, path)
                os.replace(receipt_tmp, path.with_suffix(path.suffix + '.json'))
                return DownloadResult(True, str(path), path.stat().st_size,
                                      music_info=info, warnings=warnings)
        except Exception as exc:
            return DownloadResult(False, error_message=str(exc))
        finally:
            for leftover in (temporary, receipt_tmp):
                if leftover is not None:
                    leftover.unlink(missing_ok=True)

    async def download_music_file_async(self, music_id, quality="standard"):
        # Reuse the verified sync pipeline; metadata and tag writes must not block the loop.
        cancel = threading.Event()
        try:
            return await asyncio.to_thread(self.download_music_file, music_id, quality, cancel=cancel)
        except asyncio.CancelledError:
            cancel.set()
            raise

    def download_music_to_memory(self, music_id: int, quality: str = "standard") -> Tuple[bool, BytesIO, MusicInfo]:
        """下载音乐到内存
        
        Args:
            music_id: 音乐ID
            quality: 音质等级
            
        Returns:
            (是否成功, 音乐数据流, 音乐信息)
            
        Raises:
            DownloadException: 下载失败时抛出
        """
        try:
            # 获取音乐信息
            music_info = self.get_music_info(music_id, quality)
            
            if music_info.file_size > self.max_file_size:
                raise DownloadException("文件超过下载大小限制")
            audio_data = BytesIO()
            with self.session.get(music_info.download_url, stream=True, timeout=self.timeout,
                                  headers={'Accept-Encoding': 'identity'}) as response:
                response.raise_for_status()
                length = int(response.headers.get('Content-Length', 0))
                if length > self.max_file_size:
                    raise DownloadException("文件超过下载大小限制")
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if audio_data.tell() + len(chunk) > self.max_file_size:
                        raise DownloadException("文件超过下载大小限制")
                    audio_data.write(chunk)
                size = audio_data.tell()
                if not size or (music_info.file_size and size != music_info.file_size) or (length and size != length):
                    raise DownloadException("文件不完整")
            audio_data.seek(0)

            return True, audio_data, music_info
            
        except DownloadException:
            raise
        except requests.RequestException as e:
            raise DownloadException(f"下载到内存失败: {e}")
        except Exception as e:
            raise DownloadException(f"内存下载过程中发生错误: {e}")
    
    async def download_batch_async(self, music_ids: List[int], quality: str = "standard") -> List[DownloadResult]:
        """批量异步下载音乐
        
        Args:
            music_ids: 音乐ID列表
            quality: 音质等级
            
        Returns:
            下载结果列表
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def download_with_semaphore(music_id: int) -> DownloadResult:
            async with semaphore:
                return await self.download_music_file_async(music_id, quality)
        
        tasks = [download_with_semaphore(music_id) for music_id in music_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(DownloadResult(
                    success=False,
                    error_message=f"下载音乐ID {music_ids[i]} 时发生异常: {result}"
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    def _write_music_tags(self, file_path: Path, music_info: MusicInfo) -> None:
        """写入音乐标签信息
        
        Args:
            file_path: 音乐文件路径
            music_info: 音乐信息
        """
        try:
            file_ext = file_path.suffix.lower()
            
            if file_ext == '.mp3':
                self._write_mp3_tags(file_path, music_info)
            elif file_ext == '.flac':
                self._write_flac_tags(file_path, music_info)
            elif file_ext == '.m4a':
                self._write_m4a_tags(file_path, music_info)
                
        except Exception as e:
            self.logger.warning("写入音乐标签失败: %s", e)
            return [f"标签写入失败: {e}"]
        return []
    
    def _write_mp3_tags(self, file_path: Path, music_info: MusicInfo) -> None:
        """写入MP3标签"""
        try:
            audio = MP3(str(file_path), ID3=ID3)
            
            if audio.tags is None:
                audio.add_tags()
            # 添加ID3标签
            audio.tags.add(TIT2(encoding=3, text=music_info.name))
            audio.tags.add(TPE1(encoding=3, text=music_info.artists))
            audio.tags.add(TALB(encoding=3, text=music_info.album))
            
            if music_info.track_number > 0:
                audio.tags.add(TRCK(encoding=3, text=str(music_info.track_number)))
            
            # 下载并添加封面
            if music_info.pic_url:
                try:
                    pic_response = self.session.get(music_info.pic_url, timeout=self.timeout)
                    pic_response.raise_for_status()
                    audio.tags.add(APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3,
                        desc='Cover',
                        data=pic_response.content
                    ))
                except:
                    pass  # 封面下载失败不影响主流程
            
            audio.save()
        except Exception as e:
            raise DownloadException(f"标签写入失败: {e}") from e
    
    def _write_flac_tags(self, file_path: Path, music_info: MusicInfo) -> None:
        """写入FLAC标签"""
        try:
            audio = FLAC(str(file_path))
            
            audio['TITLE'] = music_info.name
            audio['ARTIST'] = music_info.artists
            audio['ALBUM'] = music_info.album
            
            if music_info.track_number > 0:
                audio['TRACKNUMBER'] = str(music_info.track_number)
            
            # 下载并添加封面
            if music_info.pic_url:
                try:
                    pic_response = self.session.get(music_info.pic_url, timeout=self.timeout)
                    pic_response.raise_for_status()
                    
                    from mutagen.flac import Picture
                    picture = Picture()
                    picture.type = 3  # Cover (front)
                    picture.mime = 'image/jpeg'
                    picture.desc = 'Cover'
                    picture.data = pic_response.content
                    audio.add_picture(picture)
                except:
                    pass  # 封面下载失败不影响主流程
            
            audio.save()
        except Exception as e:
            raise DownloadException(f"标签写入失败: {e}") from e
    
    def _write_m4a_tags(self, file_path: Path, music_info: MusicInfo) -> None:
        """写入M4A标签"""
        try:
            audio = MP4(str(file_path))
            
            audio['\xa9nam'] = music_info.name
            audio['\xa9ART'] = music_info.artists
            audio['\xa9alb'] = music_info.album
            
            if music_info.track_number > 0:
                audio['trkn'] = [(music_info.track_number, 0)]
            
            # 下载并添加封面
            if music_info.pic_url:
                try:
                    pic_response = self.session.get(music_info.pic_url, timeout=self.timeout)
                    pic_response.raise_for_status()
                    audio['covr'] = [pic_response.content]
                except:
                    pass  # 封面下载失败不影响主流程
            
            audio.save()
        except Exception as e:
            raise DownloadException(f"标签写入失败: {e}") from e
    
    def get_download_progress(self, music_id, quality="standard"):
        info = self.get_music_info(music_id, quality)
        path = self._file_path(info)
        complete = self._cached(path, info)
        return {'music_id': music_id, 'filename': path.name,
                'total_size': info.file_size, 'current_size': path.stat().st_size if complete else 0,
                'progress': 100 if complete else 0, 'completed': complete}
