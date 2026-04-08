#!/usr/bin/env python3
"""
交互式CLI模块

提供用户友好的交互式命令行界面，支持：
- 搜索歌曲
- 下载音乐
- 下载歌单
- 下载专辑
- 设置管理
"""

import sys
import os
import json
import time
import requests
from pathlib import Path
from typing import Optional, Dict, List, Any

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import box
from rich.text import Text


# API服务配置
API_BASE_URL = "http://127.0.0.1:5023"


def call_api(endpoint: str, method: str = "GET", params: Dict = None, data: Dict = None) -> Dict:
    """调用API服务

    Args:
        endpoint: API端点路径
        method: HTTP方法 (GET/POST)
        params: URL参数
        data: POST数据

    Returns:
        API响应的JSON数据
    """
    url = f"{API_BASE_URL}{endpoint}"

    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=30)
        else:  # POST
            response = requests.post(url, params=params, json=data, timeout=30)

        response.raise_for_status()
        return response.json()

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": {
                "type": "ConnectionError",
                "message": "无法连接到API服务，请确保main.py正在运行"
            }
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": {
                "type": "TimeoutError",
                "message": "请求超时"
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


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """加载配置"""
        default_config = {
            "default_quality": "lossless",
            "download_dir": "./downloads/",
            "max_concurrent": 3,
            "auto_retry": 3,
            "show_notification": True
        }

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception:
                pass

        return default_config

    def save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            console = Console()
            console.print(f"保存配置失败: {e}", style="red")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """设置配置项"""
        self.config[key] = value
        self.save_config()


class InteractiveShell:
    """交互式Shell主类"""

    def __init__(self):
        self.console = Console()
        self.config_manager = ConfigManager()
        self.running = True

    def run(self):
        """运行交互式Shell"""
        self.show_welcome()

        while self.running:
            try:
                choice = self.show_main_menu()
                self.handle_menu_choice(choice)
            except KeyboardInterrupt:
                self.console.print("\n\n👋 再见！", style="bold green")
                break
            except Exception as e:
                self.console.print(f"\n❌ 发生错误: {e}", style="red")
                import traceback
                self.console.print(traceback.format_exc(), style="dim red")

    def show_welcome(self):
        """显示欢迎界面"""
        self.console.clear()
        welcome_text = """
╔═════════════════════════════════════════╗
║     🎵 网易云音乐下载工具 v2.0          ║
╚═════════════════════════════════════════╝
        """
        self.console.print(Panel(welcome_text, style="bold blue", box=box.DOUBLE))
        self.console.print("\n💡 提示: 按 Ctrl+C 随时退出\n", style="dim")

    def show_main_menu(self) -> str:
        """显示主菜单"""
        menu = """
📋 主菜单
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. 🔍 搜索歌曲
  2. 📋 下载歌单
  3. 💿 下载专辑
  4. ⚙️  设置
  0. 🚪 退出
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """
        self.console.print(menu)

        choice = Prompt.ask(
            "\n请选择操作",
            choices=["1", "2", "3", "4", "0"],
            default="1"
        )
        return choice

    def handle_menu_choice(self, choice: str):
        """处理菜单选择"""
        if choice == "1":
            self.search_music()
        elif choice == "2":
            self.download_playlist()
        elif choice == "3":
            self.download_album()
        elif choice == "4":
            self.show_settings()
        elif choice == "0":
            self.console.print("\n👋 再见！", style="bold green")
            self.running = False

    def search_music(self):
        """搜索音乐"""
        self.console.print("\n🔍 搜索歌曲", style="bold cyan")
        self.console.print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", style="dim")

        keyword = Prompt.ask(
            "\n请输入搜索关键词",
            default="",
            show_default=False
        )

        if not keyword.strip():
            self.console.print("❌ 关键词不能为空", style="red")
            return

        if keyword.lower() in ['b', 'back', '返回']:
            return

        self.console.print(f"\n⏳ 正在搜索: {keyword}", style="dim")
        time.sleep(0.5)  # 给用户一点反馈时间

        try:
            # 调用搜索API
            result = call_api("/search", method="POST", data={"keywords": keyword})

            if not result.get('success'):
                error = result.get('error', {})
                self.console.print(
                    f"❌ 搜索失败: {error.get('message', '未知错误')}",
                    style="red"
                )
                return

            # data是直接返回的歌曲列表
            songs = result.get('data', [])
            if not songs:
                self.console.print("❌ 未找到相关歌曲", style="yellow")
                return

            # 显示搜索结果
            self.display_search_results(songs, keyword)

            # 选择歌曲
            self.select_and_download(songs)

        except Exception as e:
            self.console.print(f"❌ 搜索失败: {e}", style="red")

    def display_search_results(self, songs: List[Dict], keyword: str):
        """显示搜索结果表格"""
        total = len(songs)
        showing = min(10, total)

        # 创建表格
        table = Table(
            title=f"🔍 搜索结果: \"{keyword}\" (共 {total} 首)",
            box=box.ROUNDED,
            header_style="bold magenta",
            border_style="cyan"
        )

        table.add_column("#", width=4, style="cyan", justify="right")
        table.add_column("歌曲名", style="magenta", no_wrap=False)
        table.add_column("歌手", style="green", no_wrap=False)
        table.add_column("专辑", style="blue", no_wrap=False)

        for idx, song in enumerate(songs[:showing], 1):
            name = song.get('name', 'Unknown')
            artists = song.get('artists', 'Unknown')
            album = song.get('album', 'Unknown')

            table.add_row(str(idx), name, artists, album)

        self.console.print("\n")
        self.console.print(table)

        if total > showing:
            self.console.print(
                f"\n📌 显示前 {showing}/{total} 首歌曲（更多功能开发中）",
                style="dim"
            )

        self.console.print(
            "\n💡 提示: 输入序号选择歌曲，输入 'b' 返回",
            style="dim"
        )

    def select_and_download(self, songs: List[Dict]):
        """选择歌曲并下载"""
        choice = Prompt.ask(
            "\n选择歌曲 (输入序号)",
            default="b",
            show_default=False
        )

        if choice.lower() in ['b', 'back', '返回', '']:
            return

        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(songs):
                self.console.print("❌ 无效的序号", style="red")
                return

            song = songs[idx]
            song_id = song.get('id')
            song_name = song.get('name', 'Unknown')

            # 选择音质
            quality = self.select_quality()

            # 下载
            self.console.print(f"\n⬇️  准备下载: {song_name}", style="cyan")
            self.download_song(song_id, song, quality)

        except ValueError:
            self.console.print("❌ 无效的输入", style="red")
        except Exception as e:
            self.console.print(f"❌ 选择失败: {e}", style="red")

    def select_quality(self) -> str:
        """选择音质"""
        qualities = [
            ("1", "standard", "标准音质 (128kbps)"),
            ("2", "exhigh", "极高音质 (320kbps)"),
            ("3", "lossless", "无损音质 (FLAC) ⭐"),
            ("4", "hires", "Hi-Res (24bit/96kHz)"),
            ("5", "sky", "沉浸环绕声 (VIP)"),
            ("6", "jymaster", "超清母带 (SVIP)"),
        ]

        self.console.print("\n🎯 选择下载音质")
        self.console.print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", style="dim")

        for num, code, name in qualities:
            self.console.print(f"  {num}. {name}")

        default_quality = self.config_manager.get("default_quality", "lossless")
        default_choice = "3"  # 默认无损

        choice = Prompt.ask(
            "\n选择音质",
            choices=[str(i) for i in range(1, 7)],
            default=default_choice
        )

        for num, code, name in qualities:
            if num == choice:
                return code

        return "lossless"

    def download_song(self, song_id: int, song_info: Dict, quality: str):
        """下载单首歌曲"""
        try:
            with self.console.status("[bold yellow]正在下载...", spinner="dots"):
                # 使用format=json，API会下载文件并返回信息
                result = call_api(
                    "/download",
                    method="POST",
                    data={"id": song_id, "level": quality, "format": "json"}
                )

            if result.get('success'):
                data = result.get('data', {})

                self.console.print(f"\n✅ 下载完成！", style="bold green")
                self.console.print(f"   歌曲: {data.get('name', 'Unknown')}", style="green")
                self.console.print(f"   歌手: {data.get('artist', 'Unknown')}", style="green")
                self.console.print(f"   大小: {data.get('file_size_formatted', '0MB')}", style="green")
                self.console.print(f"   音质: {data.get('quality_name', quality)}", style="green")
                self.console.print(f"   文件: {data.get('filename', 'Unknown')}", style="dim")

                # 是否继续
                continue_download = Confirm.ask(
                    "\n是否继续下载",
                    default=False
                )

                if continue_download:
                    self.search_music()

            else:
                error = result.get('error', {})
                error_msg = error.get('message', result.get('message', '未知错误'))
                error_type = error.get('type', 'UnknownError')

                self.console.print(f"\n❌ 下载失败", style="bold red")
                self.console.print(f"   错误类型: {error_type}", style="red")
                self.console.print(f"   错误信息: {error_msg}", style="red")

        except Exception as e:
            import traceback
            self.console.print(f"\n❌ 下载失败: {e}", style="bold red")
            if self.config_manager.get('show_notification', True):
                self.console.print(f"详细错误:\n{traceback.format_exc()}", style="dim red")

    def download_playlist(self):
        """下载歌单"""
        self.console.print("\n📋 下载歌单", style="bold cyan")
        self.console.print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", style="dim")

        playlist_input = Prompt.ask(
            "\n请输入歌单ID或URL",
            default="",
            show_default=False
        )

        if not playlist_input.strip():
            self.console.print("❌ 歌单ID不能为空", style="red")
            return

        if playlist_input.lower() in ['b', 'back', '返回']:
            return

        # 提取歌单ID
        playlist_id = self.extract_id_from_url(playlist_input)
        if not playlist_id:
            self.console.print("❌ 无效的歌单ID或URL", style="red")
            return

        self.console.print(f"\n⏳ 正在获取歌单信息...", style="dim")
        time.sleep(0.5)

        try:
            # 调用歌单API
            result = call_api("/playlist", method="POST", data={"id": playlist_id})

            if not result.get('success'):
                error = result.get('error', {})
                self.console.print(
                    f"❌ 获取歌单失败: {error.get('message', '未知错误')}",
                    style="red"
                )
                return

            playlist_data = result.get('data', {})
            playlist_info = playlist_data.get('playlist', {})
            songs = playlist_data.get('songs', [])

            if not songs:
                self.console.print("❌ 歌单为空或无权访问", style="yellow")
                return

            # 显示歌单信息
            playlist_name = playlist_info.get('name', 'Unknown')
            creator = playlist_info.get('creator', {}).get('nickname', 'Unknown')
            track_count = len(songs)

            self.console.print(f"\n📀 歌单: {playlist_name}", style="bold magenta")
            self.console.print(f"👤 创建者: {creator}", style="dim")
            self.console.print(f"🎵 歌曲: {track_count} 首", style="dim")

            # 显示歌曲列表
            self.display_playlist_songs(songs)

            # 选择并下载
            self.select_and_download_playlist_songs(songs)

        except Exception as e:
            self.console.print(f"❌ 获取歌单失败: {e}", style="red")

    def extract_id_from_url(self, input_str: str) -> Optional[str]:
        """从URL或输入中提取ID"""
        input_str = input_str.strip()

        # 如果是纯数字，直接返回
        if input_str.isdigit():
            return input_str

        # 尝试从URL中提取ID
        if 'music.163.com' in input_str:
            import re
            match = re.search(r'[?&]id=(\d+)', input_str)
            if match:
                return match.group(1)

        return None

    def display_playlist_songs(self, songs: List[Dict]):
        """显示歌单歌曲列表"""
        showing = min(20, len(songs))

        # 创建表格
        table = Table(
            title=f"歌单歌曲列表 (显示前 {showing}/{len(songs)} 首)",
            box=box.ROUNDED,
            header_style="bold magenta",
            border_style="cyan"
        )

        table.add_column("#", width=4, style="cyan", justify="right")
        table.add_column("歌曲名", style="magenta", no_wrap=False)
        table.add_column("歌手", style="green", no_wrap=False)
        table.add_column("专辑", style="blue", no_wrap=False)

        for idx, song in enumerate(songs[:showing], 1):
            name = song.get('name', 'Unknown')
            artists = song.get('artists', 'Unknown')
            album = song.get('album', 'Unknown')

            table.add_row(str(idx), name, artists, album)

        self.console.print("\n")
        self.console.print(table)

        if len(songs) > showing:
            self.console.print(
                f"\n📌 显示前 {showing}/{len(songs)} 首歌曲",
                style="dim"
            )
            self.console.print(
                "💡 提示: 输入 'all' 下载全部，输入序号选择歌曲，输入 'b' 返回",
                style="dim"
            )
        else:
            self.console.print(
                "\n💡 提示: 输入 'all' 下载全部，输入序号选择歌曲，输入 'b' 返回",
                style="dim"
            )

    def select_and_download_playlist_songs(self, songs: List[Dict]):
        """选择歌单歌曲并下载"""
        choice = Prompt.ask(
            "\n选择歌曲 (输入序号，如 1,3,5 或 1-5，输入 all 下载全部)",
            default="b",
            show_default=False
        )

        if choice.lower() in ['b', 'back', '返回', '']:
            return

        selected_songs = []

        if choice.lower() == 'all':
            selected_songs = songs
            self.console.print(f"\n✅ 已选择全部 {len(songs)} 首歌曲", style="green")
        else:
            # 解析选择
            try:
                indices = self.parse_selection(choice, len(songs))
                for idx in indices:
                    if 0 <= idx < len(songs):
                        selected_songs.append(songs[idx])

                if not selected_songs:
                    self.console.print("❌ 无效的选择", style="red")
                    return

                self.console.print(f"\n✅ 已选择 {len(selected_songs)} 首歌曲", style="green")
            except Exception as e:
                self.console.print(f"❌ 无效的选择: {e}", style="red")
                return

        # 选择音质
        quality = self.select_quality()

        # 批量下载
        self.download_songs_batch(selected_songs, quality)

    def parse_selection(self, choice: str, max_count: int) -> List[int]:
        """解析用户选择（支持 1,3,5 和 1-5 格式）"""
        indices = []

        # 处理逗号分隔
        parts = choice.split(',')
        for part in parts:
            part = part.strip()

            # 处理范围
            if '-' in part:
                start, end = part.split('-')
                start_idx = int(start.strip()) - 1
                end_idx = int(end.strip()) - 1

                if start_idx < 0 or end_idx >= max_count or start_idx > end_idx:
                    continue

                indices.extend(range(start_idx, end_idx + 1))
            else:
                idx = int(part) - 1
                if 0 <= idx < max_count:
                    indices.append(idx)

        return sorted(set(indices))  # 去重并排序

    def download_songs_batch(self, songs: List[Dict], quality: str):
        """批量下载歌曲"""
        total = len(songs)
        success_count = 0
        fail_count = 0

        self.console.print(f"\n⬇️  开始批量下载 ({total} 首)", style="bold cyan")

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=self.console
        ) as progress:

            task = progress.add_task("下载中...", total=total)

            for idx, song in enumerate(songs, 1):
                song_id = song.get('id')
                song_name = song.get('name', 'Unknown')

                progress.update(task, description=f"[{idx}/{total}] {song_name}")

                try:
                    result = call_api(
                        "/download",
                        method="POST",
                        data={"id": song_id, "level": quality, "format": "json"}
                    )

                    if result.get('success'):
                        data = result.get('data', {})
                        filename = data.get('filename', 'Unknown')

                        self.console.print(f"  ✅ [{idx}/{total}] {filename}", style="green")
                        success_count += 1
                    else:
                        error_msg = result.get('message', '未知错误')
                        self.console.print(f"  ❌ [{idx}/{total}] {song_name}: {error_msg}", style="red")
                        fail_count += 1

                except Exception as e:
                    self.console.print(f"  ❌ [{idx}/{total}] {song_name}: {str(e)}", style="red")
                    fail_count += 1

                progress.update(task, advance=1)

                # 避免请求过快
                time.sleep(0.5)

        # 显示统计
        self.console.print("\n📊 下载统计", style="bold cyan")
        self.console.print(f"  ✅ 成功: {success_count} 首", style="green")
        self.console.print(f"  ❌ 失败: {fail_count} 首", style="red")
        self.console.print(f"  📁 总计: {total} 首", style="cyan")

        # 是否继续
        continue_download = Confirm.ask(
            "\n是否继续下载",
            default=False
        )

        if continue_download:
            self.download_playlist()

    def download_album(self):
        """下载专辑"""
        self.console.print("\n💿 下载专辑", style="bold cyan")
        self.console.print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", style="dim")

        album_input = Prompt.ask(
            "\n请输入专辑ID或URL",
            default="",
            show_default=False
        )

        if not album_input.strip():
            self.console.print("❌ 专辑ID不能为空", style="red")
            return

        if album_input.lower() in ['b', 'back', '返回']:
            return

        # 提取专辑ID
        album_id = self.extract_id_from_url(album_input)
        if not album_id:
            self.console.print("❌ 无效的专辑ID或URL", style="red")
            return

        self.console.print(f"\n⏳ 正在获取专辑信息...", style="dim")
        time.sleep(0.5)

        try:
            # 调用专辑API
            result = call_api("/album", method="POST", data={"id": album_id})

            if not result.get('success'):
                error = result.get('error', {})
                self.console.print(
                    f"❌ 获取专辑失败: {error.get('message', '未知错误')}",
                    style="red"
                )
                return

            album_data = result.get('data', {})
            album_info = album_data.get('album', {})
            songs = album_data.get('songs', [])

            if not songs:
                self.console.print("❌ 专辑为空或无权访问", style="yellow")
                return

            # 显示专辑信息
            album_name = album_info.get('name', 'Unknown')
            artist = album_info.get('artist', {}).get('name', 'Unknown')
            track_count = len(songs)

            self.console.print(f"\n💿 专辑: {album_name}", style="bold magenta")
            self.console.print(f"👤 歌手: {artist}", style="dim")
            self.console.print(f"🎵 歌曲: {track_count} 首", style="dim")

            # 显示歌曲列表
            self.display_album_songs(songs)

            # 选择并下载
            self.select_and_download_album_songs(songs)

        except Exception as e:
            self.console.print(f"❌ 获取专辑失败: {e}", style="red")

    def display_album_songs(self, songs: List[Dict]):
        """显示专辑歌曲列表"""
        showing = min(20, len(songs))

        # 创建表格
        table = Table(
            title=f"专辑歌曲列表 (显示前 {showing}/{len(songs)} 首)",
            box=box.ROUNDED,
            header_style="bold magenta",
            border_style="cyan"
        )

        table.add_column("#", width=4, style="cyan", justify="right")
        table.add_column("歌曲名", style="magenta", no_wrap=False)
        table.add_column("歌手", style="green", no_wrap=False)
        table.add_column("专辑", style="blue", no_wrap=False)

        for idx, song in enumerate(songs[:showing], 1):
            name = song.get('name', 'Unknown')
            artists = song.get('artists', 'Unknown')
            album = song.get('album', 'Unknown')

            table.add_row(str(idx), name, artists, album)

        self.console.print("\n")
        self.console.print(table)

        if len(songs) > showing:
            self.console.print(
                f"\n📌 显示前 {showing}/{len(songs)} 首歌曲",
                style="dim"
            )
            self.console.print(
                "💡 提示: 输入 'all' 下载全部，输入序号选择歌曲，输入 'b' 返回",
                style="dim"
            )
        else:
            self.console.print(
                "\n💡 提示: 输入 'all' 下载全部，输入序号选择歌曲，输入 'b' 返回",
                style="dim"
            )

    def select_and_download_album_songs(self, songs: List[Dict]):
        """选择专辑歌曲并下载"""
        choice = Prompt.ask(
            "\n选择歌曲 (输入序号，如 1,3,5 或 1-5，输入 all 下载全部)",
            default="b",
            show_default=False
        )

        if choice.lower() in ['b', 'back', '返回', '']:
            return

        selected_songs = []

        if choice.lower() == 'all':
            selected_songs = songs
            self.console.print(f"\n✅ 已选择全部 {len(songs)} 首歌曲", style="green")
        else:
            # 解析选择
            try:
                indices = self.parse_selection(choice, len(songs))
                for idx in indices:
                    if 0 <= idx < len(songs):
                        selected_songs.append(songs[idx])

                if not selected_songs:
                    self.console.print("❌ 无效的选择", style="red")
                    return

                self.console.print(f"\n✅ 已选择 {len(selected_songs)} 首歌曲", style="green")
            except Exception as e:
                self.console.print(f"❌ 无效的选择: {e}", style="red")
                return

        # 选择音质
        quality = self.select_quality()

        # 批量下载
        self.download_songs_batch(selected_songs, quality)

    def show_settings(self):
        """显示设置"""
        self.console.print("\n⚙️  设置", style="bold cyan")
        self.console.print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", style="dim")

        config = self.config_manager.config

        self.console.print(f"\n1. 默认音质: {config.get('default_quality', 'lossless')}")
        self.console.print(f"2. 下载目录: {config.get('download_dir', './downloads/')}")
        self.console.print(f"3. 并发下载数: {config.get('max_concurrent', 3)}")
        self.console.print(f"4. 自动重试: {config.get('auto_retry', 3)} 次")
        self.console.print(f"5. 显示通知: {'开启' if config.get('show_notification', True) else '关闭'}")

        self.console.print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", style="dim")

        choice = Prompt.ask(
            "\n是否修改设置",
            choices=["y", "n"],
            default="n"
        )

        if choice == "y":
            self.edit_settings()
        else:
            self.console.print("\n✅ 设置已保存", style="green")

    def edit_settings(self):
        """编辑设置"""
        self.console.print("\n📝 编辑设置", style="bold cyan")
        self.console.print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", style="dim")

        # 修改默认音质
        current_quality = self.config_manager.get("default_quality", "lossless")
        self.console.print(f"\n当前默认音质: {current_quality}")

        change_quality = Confirm.ask("是否修改默认音质", default=False)
        if change_quality:
            new_quality = self.select_quality()
            self.config_manager.set("default_quality", new_quality)
            self.console.print(f"✅ 默认音质已更新为: {new_quality}", style="green")

        # 修改下载目录
        current_dir = self.config_manager.get("download_dir", "./downloads/")
        self.console.print(f"\n当前下载目录: {current_dir}")

        change_dir = Confirm.ask("是否修改下载目录", default=False)
        if change_dir:
            new_dir = Prompt.ask("输入新的下载目录", default=current_dir)
            self.config_manager.set("download_dir", new_dir)
            self.console.print(f"✅ 下载目录已更新为: {new_dir}", style="green")

        self.console.print("\n✅ 设置已保存", style="green")
        time.sleep(1)


def main():
    """主入口"""
    shell = InteractiveShell()
    shell.run()


if __name__ == "__main__":
    main()
