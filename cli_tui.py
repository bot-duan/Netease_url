#!/usr/bin/env python3
"""
网易云音乐TUI模块

使用Textual框架实现的终端用户界面，提供全屏交互式体验。

使用示例:
    python cli.py -i
    python cli.py --interactive
"""

import sys
import asyncio
from typing import Optional, Dict, List
from pathlib import Path

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import (
    ListView, ListItem, Label, Header, Footer,
    Input, Button, ProgressBar, Static, DataTable
)
from textual.containers import Horizontal, Vertical, Container
from textual.screen import ModalScreen
from textual import events
from textual import on


# ==================== API Client ====================

class APIClientWrapper:
    """API客户端包装器（延迟导入）"""
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            from api_client import APIClient
            cls._client = APIClient()
        return cls._client


# ==================== Screens ====================

class QualitySelectionScreen(ModalScreen):
    """音质选择屏幕"""

    CSS = """
    QualitySelectionScreen {
        align: center middle;
    }
    #quality-dialog {
        width: 60;
        height: 25;
        border: thick $primary;
        background: $surface;
    }
    #quality-title {
        text-align: center;
        text-style: bold;
        padding: 1;
    }
    #quality-list {
        height: 1fr;
    }
    """

    def __init__(self, current_quality: str = "lossless"):
        super().__init__()
        self.current_quality = current_quality
        self.qualities = [
            ("standard", "标准音质 (128kbps)"),
            ("exhigh", "极高音质 (320kbps)"),
            ("lossless", "无损音质 (FLAC) ⭐"),
            ("hires", "Hi-Res (24bit/96kHz)"),
            ("sky", "沉浸环绕声 (VIP)"),
            ("jymaster", "超清母带 (SVIP)"),
        ]

    def compose(self) -> ComposeResult:
        with Vertical(id="quality-dialog"):
            yield Static("🎯 选择下载音质", id="quality-title")
            yield Static("💡 提示: ↑↓选择 | Enter确认 | Esc取消", id="quality-hint")
            yield ListView(id="quality-list")

    def on_mount(self) -> None:
        """组件挂载时初始化列表"""
        list_view = self.query_one("#quality-list", ListView)

        for code, name in self.qualities:
            item = ListItem(Label(name))
            list_view.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """处理音质选择"""
        if event.list_view.id == "quality-list":
            index = event.list_view.index
            if 0 <= index < len(self.qualities):
                selected_quality = self.qualities[index][0]
                self.dismiss(selected_quality)

    def on_key(self, event: events.Key) -> None:
        """处理按键事件"""
        if event.key == "escape":
            # ESC键关闭对话框
            self.dismiss(None)


class DownloadProgressScreen(ModalScreen):
    """下载进度屏幕"""

    CSS = """
    DownloadProgressScreen {
        align: center middle;
    }
    #download-dialog {
        width: 70;
        height: 15;
        border: thick $primary;
        background: $surface;
    }
    #progress-bar {
        width: 1fr;
    }
    """

    def __init__(self, songs: List[Dict], quality: str):
        super().__init__()
        self.songs = songs
        self.quality = quality
        self.total = len(songs)
        self.current = 0
        self.success_count = 0
        self.fail_count = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="download-dialog"):
            yield Static("⬇️  批量下载中...", id="download-title")
            yield ProgressBar(show_eta=True, id="progress-bar")
            yield Static("", id="download-status")

    def on_mount(self) -> None:
        """组件挂载时开始下载"""
        progress_bar = self.query_one("#progress-bar", ProgressBar)
        progress_bar.total = self.total
        self.run_download()

    def run_download(self):
        """执行下载"""
        client = APIClientWrapper.get_client()

        for idx, song in enumerate(self.songs, 1):
            song_id = song.get('id')
            song_name = song.get('name', 'Unknown')

            self.query_one("#download-status", Static).update(
                f"[{idx}/{self.total}] {song_name}"
            )

            result = client.download(
                song_id=song_id,
                quality=self.quality,
                return_format="json"
            )

            if result.get('success'):
                self.success_count += 1
            else:
                self.fail_count += 1

            progress_bar = self.query_one("#progress-bar", ProgressBar)
            progress_bar.advance(1)

        # 显示结果
        self.query_one("#download-status", Static).update(
            f"✅ 成功: {self.success_count} | ❌ 失败: {self.fail_count}"
        )

        # 2秒后自动关闭
        self.call_later(2.0, self.close_screen)

    def close_screen(self):
        """关闭屏幕"""
        self.dismiss((self.success_count, self.fail_count))


# ==================== Playlist Screen ====================

class PlaylistScreen(Screen):
    """歌单下载屏幕"""

    CSS = """
    PlaylistScreen {
        layout: vertical;
    }
    #playlist-title {
        text-align: center;
        text-style: bold;
        padding: 1;
    }
    #playlist-input {
        width: 1fr;
        margin: 1 2;
    }
    #playlist-info {
        margin: 1 2;
        text-style: bold;
    }
    #playlist-songs {
        height: 1fr;
        margin: 0 2;
    }
    #playlist-hint {
        margin: 0 2;
        text-style: dim;
    }
    """

    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance
        self.playlist_data = None
        self.songs = []

    def compose(self) -> ComposeResult:
        yield Label("📋 下载歌单", id="playlist-title")
        yield Input(
            placeholder="输入歌单ID或URL",
            id="playlist-input"
        )
        yield Label("", id="playlist-info")
        yield ListView(id="playlist-songs")
        yield Label("💡 提示: Esc返回主菜单", id="playlist-hint")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理歌单ID输入"""
        if event.input.id == "playlist-input":
            playlist_input = event.value.strip()

            if not playlist_input:
                return

            self.fetch_playlist(playlist_input)

    def fetch_playlist(self, playlist_input: str):
        """获取歌单信息"""
        # 提取歌单ID
        playlist_id = self.extract_id(playlist_input)
        if not playlist_id:
            self.query_one("#playlist-info", Label).update("❌ 无效的歌单ID或URL")
            return

        # 显示加载中
        self.query_one("#playlist-info", Label).update("⏳ 正在获取歌单信息...")

        # 调用API
        client = APIClientWrapper.get_client()
        result = client.get_playlist(playlist_id)

        if result.get('success'):
            self.playlist_data = result.get('data', {})
            self.songs = self.playlist_data.get('songs', [])

            # 显示歌单信息
            playlist_info = self.playlist_data.get('playlist', {})
            playlist_name = playlist_info.get('name', 'Unknown')
            creator = playlist_info.get('creator', {}).get('nickname', 'Unknown')

            self.query_one("#playlist-info", Label).update(
                f"📀 {playlist_name} | 👤 {creator} | 🎵 {len(self.songs)}首"
            )

            # 显示歌曲列表
            songs_list = self.query_one("#playlist-songs", ListView)
            songs_list.clear()

            for idx, song in enumerate(self.songs[:50], 1):  # 限制显示50首
                name = song.get('name', 'Unknown')
                artists = song.get('artists', 'Unknown')

                item = ListItem(Label(f"{idx}. {name} - {artists}"))
                songs_list.append(item)

            if len(self.songs) > 50:
                self.query_one("#playlist-hint", Label).update(
                    f"💡 显示前50首，共{len(self.songs)}首 | Esc返回"
                )
        else:
            self.query_one("#playlist-info", Label).update("❌ 获取歌单失败")

    def extract_id(self, input_str: str) -> str:
        """从URL或输入中提取ID"""
        import re

        input_str = input_str.strip()

        # 如果是纯数字，直接返回
        if input_str.isdigit():
            return input_str

        # 尝试从URL中提取ID
        if 'music.163.com' in input_str:
            match = re.search(r'[?&]id=(\d+)', input_str)
            if match:
                return match.group(1)

        return ""

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """处理歌曲选择"""
        if len(self.songs) > 0:
            # 下载全部歌曲
            self.download_all_songs()

    def download_all_songs(self):
        """下载全部歌曲"""
        if not self.songs:
            return

        # 显示音质选择对话框
        def on_quality_selected(quality):
            # 显示下载进度
            self.app_instance.push_screen(
                DownloadProgressScreen(self.songs, quality)
            )

        self.app_instance.push_screen(
            QualitySelectionScreen(),
            on_quality_selected
        )

    def on_key(self, event: events.Key) -> None:
        """处理按键事件"""
        if event.key == "escape":
            # 按ESC返回主菜单
            self.app.pop_screen()


# ==================== Album Screen ====================

class AlbumScreen(Screen):
    """专辑下载屏幕"""

    CSS = """
    AlbumScreen {
        layout: vertical;
    }
    #album-title {
        text-align: center;
        text-style: bold;
        padding: 1;
    }
    #album-input {
        width: 1fr;
        margin: 1 2;
    }
    #album-info {
        margin: 1 2;
        text-style: bold;
    }
    #album-songs {
        height: 1fr;
        margin: 0 2;
    }
    #album-hint {
        margin: 0 2;
        text-style: dim;
    }
    """

    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance
        self.album_data = None
        self.songs = []

    def compose(self) -> ComposeResult:
        yield Label("💿 下载专辑", id="album-title")
        yield Input(
            placeholder="输入专辑ID或URL",
            id="album-input"
        )
        yield Label("", id="album-info")
        yield ListView(id="album-songs")
        yield Label("💡 提示: Esc返回主菜单", id="album-hint")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理专辑ID输入"""
        if event.input.id == "album-input":
            album_input = event.value.strip()

            if not album_input:
                return

            self.fetch_album(album_input)

    def fetch_album(self, album_input: str):
        """获取专辑信息"""
        # 提取专辑ID
        album_id = self.extract_id(album_input)
        if not album_id:
            self.query_one("#album-info", Label).update("❌ 无效的专辑ID或URL")
            return

        # 显示加载中
        self.query_one("#album-info", Label).update("⏳ 正在获取专辑信息...")

        # 调用API
        client = APIClientWrapper.get_client()
        result = client.get_album(album_id)

        if result.get('success'):
            self.album_data = result.get('data', {})
            self.songs = self.album_data.get('songs', [])

            # 显示专辑信息
            album_info = self.album_data.get('album', {})
            album_name = album_info.get('name', 'Unknown')
            artist = album_info.get('artist', {}).get('name', 'Unknown')

            self.query_one("#album-info", Label).update(
                f"💿 {album_name} | 👤 {artist} | 🎵 {len(self.songs)}首"
            )

            # 显示歌曲列表
            songs_list = self.query_one("#album-songs", ListView)
            songs_list.clear()

            for idx, song in enumerate(self.songs, 1):
                name = song.get('name', 'Unknown')
                artists = song.get('artists', 'Unknown')

                item = ListItem(Label(f"{idx}. {name} - {artists}"))
                songs_list.append(item)
        else:
            self.query_one("#album-info", Label).update("❌ 获取专辑失败")

    def extract_id(self, input_str: str) -> str:
        """从URL或输入中提取ID"""
        import re

        input_str = input_str.strip()

        # 如果是纯数字，直接返回
        if input_str.isdigit():
            return input_str

        # 尝试从URL中提取ID
        if 'music.163.com' in input_str:
            match = re.search(r'[?&]id=(\d+)', input_str)
            if match:
                return match.group(1)

        return ""

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """处理歌曲选择"""
        if len(self.songs) > 0:
            # 下载全部歌曲
            self.download_all_songs()

    def download_all_songs(self):
        """下载全部歌曲"""
        if not self.songs:
            return

        # 显示音质选择对话框
        def on_quality_selected(quality):
            # 显示下载进度
            self.app_instance.push_screen(
                DownloadProgressScreen(self.songs, quality)
            )

        self.app_instance.push_screen(
            QualitySelectionScreen(),
            on_quality_selected
        )

    def on_key(self, event: events.Key) -> None:
        """处理按键事件"""
        if event.key == "escape":
            # 按ESC返回主菜单
            self.app.pop_screen()


# ==================== Search Screen ====================

class SearchScreen(Screen):
    """搜索屏幕"""

    CSS = """
    SearchScreen {
        layout: vertical;
    }
    #search-title {
        text-align: center;
        text-style: bold;
        padding: 1;
    }
    #search-input {
        width: 1fr;
        margin: 1 2;
    }
    #search-results {
        height: 1fr;
        margin: 0 2;
    }
    #search-info {
        margin: 1 2;
        text-style: bold;
    }
    #search-hint {
        margin: 0 2;
        text-style: dim;
    }
    """

    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance
        self.search_results: List[Dict] = []

    def compose(self) -> ComposeResult:
        yield Label("🔍 搜索歌曲", id="search-title")
        yield Input(
            placeholder="输入关键词后按Enter搜索",
            id="search-input"
        )
        yield ListView(id="search-results")
        yield Label("", id="search-info")
        yield Label("💡 提示: Esc返回主菜单", id="search-hint")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理搜索输入"""
        if event.input.id == "search-input":
            keyword = event.value.strip()

            if not keyword:
                return

            self.perform_search(keyword)

    def perform_search(self, keyword: str):
        """执行搜索"""
        client = APIClientWrapper.get_client()
        result = client.search(keyword=keyword, limit=10)

        if result.get('success'):
            self.search_results = result.get('data', [])

            # 更新信息
            self.query_one("#search-info", Label).update(
                f"🔍 找到 {len(self.search_results)} 首歌曲"
            )

            # 显示结果
            results_list = self.query_one("#search-results", ListView)
            results_list.clear()

            for idx, song in enumerate(self.search_results, 1):
                name = song.get('name', 'Unknown')
                artists = song.get('artists', 'Unknown')

                item = ListItem(Label(f"{idx}. {name} - {artists}"))
                results_list.append(item)
        else:
            self.query_one("#search-info", Label).update("❌ 搜索失败")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """处理歌曲选择"""
        if len(self.search_results) > 0:
            index = event.list_view.index
            if 0 <= index < len(self.search_results):
                song = self.search_results[index]
                self.download_song(song)

    def on_key(self, event: events.Key) -> None:
        """处理按键事件"""
        if event.key == "escape":
            # 按ESC返回主菜单
            self.app.pop_screen()

    def download_song(self, song: Dict):
        """下载单首歌曲"""
        # 显示音质选择对话框
        def on_quality_selected(quality):
            client = APIClientWrapper.get_client()
            song_id = song.get('id')

            result = client.download(
                song_id=song_id,
                quality=quality,
                return_format="json"
            )

            if result.get('success'):
                data = result.get('data', {})
                self.query_one("#search-info", Label).update(
                    f"✅ 下载成功: {data.get('name', 'Unknown')}"
                )
            else:
                self.query_one("#search-info", Label).update(
                    "❌ 下载失败"
                )

        self.app_instance.push_screen(
            QualitySelectionScreen(),
            on_quality_selected
        )


# ==================== Main App ====================

class MusicTuiApp(App):
    """网易云音乐TUI应用主类"""

    CSS = """
    Screen {
        background: $background;
    }
    #main-menu {
        width: 1fr;
        height: 1fr;
    }
    ListItem {
        padding: 1 2;
    }
    ListItem.-highlighted {
        background: $primary;
        color: $text;
    }
    """

    TITLE = "网易云音乐 🎵"
    SUB_TITLE = "交互式下载工具 v2.0"

    def __init__(self):
        super().__init__()
        self.current_quality = "lossless"

    def compose(self) -> ComposeResult:
        """组合界面组件"""
        yield Header()
        yield Footer()
        yield ListView(id="main-menu")

    def on_mount(self) -> None:
        """应用启动时初始化主菜单"""
        self.show_main_menu()

    def show_main_menu(self):
        """显示主菜单"""
        main_list = self.query_one("#main-menu", ListView)
        main_list.clear()

        menu_items = [
            "🔍 搜索歌曲",
            "📋 下载歌单",
            "💿 下载专辑",
            "⚙️  设置",
            "🚪 退出",
        ]

        for item in menu_items:
            main_list.append(ListItem(Label(item)))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """处理主菜单选择"""
        if event.list_view.id == "main-menu":
            index = event.list_view.index

            if index == 0:  # 搜索歌曲
                self.show_search_screen()
            elif index == 1:  # 下载歌单
                self.show_playlist_screen()
            elif index == 2:  # 下载专辑
                self.show_album_screen()
            elif index == 3:  # 设置
                self.show_settings_screen()
            elif index == 4:  # 退出
                self.exit()

    def show_search_screen(self):
        """显示搜索屏幕"""
        search_screen = SearchScreen(self)
        self.push_screen(search_screen)

    def show_playlist_screen(self):
        """显示歌单下载屏幕"""
        playlist_screen = PlaylistScreen(self)
        self.push_screen(playlist_screen)

    def show_album_screen(self):
        """显示专辑下载屏幕"""
        album_screen = AlbumScreen(self)
        self.push_screen(album_screen)

    def show_settings_screen(self):
        """显示设置屏幕（简化版）"""
        def on_quality_selected(quality):
            self.current_quality = quality
            self.show_settings_info()

        self.push_screen(
            QualitySelectionScreen(self.current_quality),
            on_quality_selected
        )

    def on_key(self, event: events.Key) -> None:
        """处理全局按键"""
        if event.key == "escape":
            # ESC键返回主菜单或退出
            # 如果有额外的Screen（除了默认screen），关闭它
            if len(self.screen_stack) > 1:
                self.pop_screen()
            # 如果已经在主菜单，不做任何事（避免误操作退出）

    def show_settings_info(self):
        """显示设置信息"""
        self.query_one("#main-menu", ListView).clear()
        self.query_one("#main-menu", ListView).append(
            ListItem(Label(f"⚙️  默认音质: {self.current_quality}"))
        )
        self.query_one("#main-menu", ListView).append(
            ListItem(Label("💡 按Esc返回主菜单"))
        )


# ==================== Entry Point ====================

def main():
    """主入口函数"""
    app = MusicTuiApp()
    app.run()


if __name__ == "__main__":
    main()
