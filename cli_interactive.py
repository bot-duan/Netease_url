"""Step-by-step interactive CLI backed by the local music service."""
import json
import os
import re
from pathlib import Path

from rich.console import Console
from rich.progress import BarColumn, DownloadColumn, Progress, TaskProgressColumn, TransferSpeedColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from config import QUALITY_NAMES
from music_api import APIException
from music_service import MusicAPIService, ServiceError


def parse_selection(choice, first, last):
    """Return sorted, unique numbers from the current page."""
    numbers = set()
    for part in choice.split(','):
        match = re.fullmatch(r'([0-9]+)(?:\s*-\s*([0-9]+))?', part.strip())
        if not match:
            raise ValueError
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if not first <= start <= end <= last:
            raise ValueError
        numbers.update(range(start, end + 1))
    return sorted(numbers)


class InteractiveShell:
    PAGE_SIZE = 10

    def __init__(self, service, console=None):
        self.service = service
        self.console = console if console is not None else Console()
        self.default_quality = service.config.default_quality
        # Continue to honor a preference saved by the previous interactive modes.
        settings_path = Path(os.environ.get('NETEASE_TUI_CONFIG', 'config.json'))
        try:
            settings = json.loads(settings_path.read_text(encoding='utf-8'))
            quality = settings.get('default_quality') if isinstance(settings, dict) else None
            if isinstance(quality, str) and quality in QUALITY_NAMES:
                self.default_quality = quality
        except (OSError, ValueError):
            pass

    def ask(self, message, **kwargs):
        return Prompt.ask(message, console=self.console, **kwargs).strip()

    def write(self, message):
        self.console.print(message, markup=False, highlight=False)

    def run(self):
        self.write('网易云音乐下载')
        try:
            while True:
                self.write('\n1. 搜索歌曲  2. 下载歌单  3. 下载专辑  0. 退出')
                choice = self.ask('请选择', choices=['1', '2', '3', '0'], default='1')
                if choice == '0':
                    return 0
                try:
                    if choice == '1':
                        self.search()
                    else:
                        self.collection('playlist' if choice == '2' else 'album')
                except (ServiceError, APIException, OSError) as exc:
                    self.write(f'操作失败：{exc}')
                except KeyboardInterrupt:
                    self.write('\n已取消当前操作。')
        except EOFError:
            return 0
        except KeyboardInterrupt:
            self.write('\n已退出。')
            return 130

    def search(self):
        keyword = self.ask('搜索关键词，直接回车返回', default='')
        if not keyword:
            return

        def fetch(offset):
            result = self.service.search(keyword, limit=self.PAGE_SIZE, offset=offset)
            return result['songs'], result['total']

        self.select_songs(fetch)

    def collection(self, kind):
        if kind == 'playlist':
            identifier = self.ask('歌单 ID 或链接，直接回车返回', default='')
            if not identifier:
                return
            collection = self.service.playlist(identifier)['playlist']
            songs = collection['tracks']
        else:
            identifier = self.ask('专辑 ID 或链接，直接回车返回', default='')
            if not identifier:
                return
            collection = self.service.album(identifier)['album']
            songs = collection['songs']

        self.write(f"{collection.get('name') or '未命名'} · 共 {len(songs)} 首")
        self.select_songs(lambda offset: (songs[offset:offset + self.PAGE_SIZE], len(songs)),
                          all_songs=songs)

    def select_songs(self, fetch, *, all_songs=None):
        offset = 0
        while True:
            songs, total = fetch(offset)
            if not songs:
                self.write('没有更多歌曲。' if offset else '没有找到歌曲。')
                if offset:
                    offset -= self.PAGE_SIZE
                    continue
                return
            first, last = offset + 1, offset + len(songs)
            table = Table('编号', '歌曲', '歌手', '专辑', box=None)
            for number, song in enumerate(songs, first):
                table.add_row(str(number), *(
                    Text(str(song.get(key) or '—')) for key in ('name', 'artists', 'album')
                ))
            self.console.print(table)
            self.write(f'显示 {first}–{last} / {max(last, total)} 首')
            options = ['b 返回']
            if all_songs is not None:
                options.insert(0, 'all 全部')
            if offset:
                options.insert(0, 'p 上一页')
            if last < total:
                options.insert(0, 'n 下一页')
            while True:
                choice = self.ask('输入编号（如 1,3 或 1-3），' + '，'.join(options),
                                  default='b').lower()
                if choice == 'b':
                    return
                if choice == 'n' and last < total:
                    offset += self.PAGE_SIZE
                    break
                if choice == 'p' and offset:
                    offset -= self.PAGE_SIZE
                    break
                if choice == 'all' and all_songs is not None:
                    selected = all_songs
                else:
                    try:
                        numbers = parse_selection(choice, first, last)
                    except ValueError:
                        self.write(f'请输入当前页的编号（{first}–{last}）或提示中的命令。')
                        continue
                    selected = [songs[number - first] for number in numbers]
                if self.confirm_download(selected):
                    return

    def confirm_download(self, songs):
        quality = self.default_quality
        while True:
            choice = self.ask(
                f'已选 {len(songs)} 首，当前音质 {QUALITY_NAMES[quality]}。Enter 下载，q 改音质，b 返回',
                default='y', choices=['y', 'q', 'b'], show_choices=False, show_default=False,
            )
            if choice == 'b':
                return False
            if choice == 'y':
                self.download(songs, quality)
                return True
            for number, name in enumerate(QUALITY_NAMES.values(), 1):
                self.write(f'{number}. {name}')
            levels = dict(zip(map(str, range(1, len(QUALITY_NAMES) + 1)), QUALITY_NAMES))
            value = self.ask('选择音质，b 返回', choices=[*levels, 'b'], default='b')
            if value != 'b':
                quality = levels[value]

    def download(self, songs, quality):
        pending = songs
        while pending:
            failures = []
            successes = 0
            for index, song in enumerate(pending, 1):
                label = f"[{index}/{len(pending)}] {song.get('name') or song['id']}"
                self.write(f'{label} 开始下载')
                try:
                    with Progress(
                        BarColumn(), TaskProgressColumn(), DownloadColumn(), TransferSpeedColumn(),
                        transient=True, console=self.console,
                    ) as progress:
                        task = progress.add_task('下载', total=None)

                        def update(received, total):
                            progress.update(task, completed=received, total=total or None)

                        result = self.service.download(song['id'], quality, progress=update)
                except KeyboardInterrupt:
                    remaining = len(pending) - index + 1
                    self.write(f'\n下载已取消。已保存 {successes} 首，失败 {len(failures)} 首，取消 {remaining} 首。')
                    return
                except (ServiceError, APIException, OSError) as exc:
                    failures.append(song)
                    self.write(f'{label} 下载失败：{exc}')
                else:
                    successes += 1
                    self.write(f"{label} 已保存（{result['quality_name']}） {result['file_path']}")
                    for warning in result.get('warnings', []):
                        self.write(f'  {warning}')
            self.write(f'本轮成功 {successes} 首，失败 {len(failures)} 首。')
            if not failures or not Confirm.ask('重试失败歌曲？', default=False, console=self.console):
                return
            pending = failures


if __name__ == '__main__':
    raise SystemExit(InteractiveShell(MusicAPIService()).run())
