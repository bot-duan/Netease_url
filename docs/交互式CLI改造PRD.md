# 交互式CLI改造PRD

## 文档信息

- **创建时间**: 2026-03-31
- **版本**: v2.0
- **最后更新**: 2026-04-08
- **状态**: 核心功能已完成，TUI升级进行中
- **目标**: 为网易云音乐CLI工具添加现代化TUI体验，同时保持AI友好性

---

## 1. 项目背景

### 1.1 当前状态

项目已实现功能完整的CLI工具，支持：
- ✅ AI模式（命令式）：完全兼容，专为自动化和AI调用优化
- ✅ 交互模式v1（Rich Prompt版）：基础功能已实现
  - 搜索歌曲并显示表格
  - 下载歌单/专辑（批量选择）
  - 设置管理
  - Rich美化输出

**技术栈**：
- AI模式：argparse + JSON输出
- 交互模式v1：Rich + Prompt（输入数字选择）
- API调用：HTTP请求到Flask服务

**交互模式v1的问题**：
- 需要输入数字选择，不够优雅
- 静态输出，不支持实时刷新
- 无法提供类似htop的全屏TUI体验

### 1.2 需求来源

**用户需求**：
- ✅ 提供更友好的交互式体验
- ✅ 降低普通用户的使用门槛
- ⭐ **升级目标**：用Textual TUI替换Rich Prompt，提供键盘导航式全屏界面
- ⭐ **期望体验**：类似htop的实时TUI应用，支持↑↓选择、Enter确认

**技术需求**：
- 保持现有AI友好特性
- 不破坏现有CLI接口
- 代码复用，避免重复开发
- 升级到现代化TUI框架（Textual）

---

## 2. 设计目标

### 2.1 双模式架构

```
统一入口 cli.py
    ├─ AI模式 (现有功能 - 保持不变)
    │   ├─ 命令式调用：cli.py <command> [args]
    │   ├─ JSON输出
    │   ├─ 确定性行为
    │   └─ 适合：AI、脚本、CI/CD
    │
    └─ 交互模式 (升级到Textual TUI) 🚀
        ├─ 启动方式：cli.py --interactive / cli.py -i / cli.py
        ├─ 技术升级：Rich Prompt → Textual TUI
        ├─ 全屏TUI界面
        ├─ 键盘导航（↑↓选择，Enter确认）
        ├─ 实时刷新
        └─ 适合：人类用户
```

**交互模式演进**：
- v1 (已实现)：Rich + Prompt → 输入数字选择
- v2 (升级中)：Textual TUI → 键盘导航 + 全屏界面

### 2.2 核心原则

1. **不破坏现有功能**：AI模式和Rich交互模式保持完全兼容
2. **统一入口**：单一 `cli.py` 文件，支持多模式
3. **模式隔离**：明确的触发条件，不会误触发
4. **代码复用**：通过HTTP调用现有API服务
5. **一致体验**：配置统一管理
6. **渐进增强**：从Rich Prompt升级到Textual TUI

---

## 3. 功能需求

### 3.1 模式切换机制

#### AI模式触发条件
- 有命令参数：`cli.py <command> [args]`
- 显式指定非交互：`cli.py --output json ...`

#### 交互模式触发条件
- 无参数运行：`cli.py`
- 显式指定交互：`cli.py --interactive` 或 `cli.py -i`

#### 示例

```bash
# AI模式
uv run python cli.py search "周杰伦"
uv run python cli.py download 185668 --quality lossless

# 交互模式
uv run python cli.py
uv run python cli.py -i
uv run python cli.py --interactive
```

### 3.2 交互模式功能清单

#### 3.2.1 主菜单

```
╔════════════════════════════════════════╗
║     🎵 网易云音乐下载工具 v2.0          ║
╚════════════════════════════════════════╝

📋 主菜单
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. 🔍 搜索歌曲
  2. 📋 下载歌单
  3. 💿 下载专辑
  4. ⚙️  设置
  0. 🚪 退出
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

请选择操作 [1-4, 0]:
```

**功能点**：
- ✅ 美观的ASCII艺术界面
- ✅ 彩色输出（成功/错误/警告）
- ✅ 数字选择 + 快捷键支持
- ✅ 返回主菜单机制

**说明**：移除了历史记录功能，保持简洁的4个主要功能。

#### 3.2.2 搜索功能

**输入界面**：
```
🔍 搜索歌曲

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
请输入搜索关键词: 周杰伦

💡 提示：
  - 输入歌曲名、歌手名或专辑名
  - 支持关键词组合，如"周杰伦 稻香"
  - 输入 'b' 返回主菜单
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**结果展示**：
```
🔍 搜索结果: "周杰伦" (共 50 首)

┏━━━┳━━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━┓
┃ # ┃ 歌曲名  ┃ 歌手   ┃ 专辑   ┃ 时长 ┃
┡━━━╇━━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━┩
│ 1 │ 晴天    │ 周杰伦 │ 七里香 │ 4:29 │
│ 2 │ 稻香    │ 周杰伦 │ 魔杰座 │ 3:43 │
│ 3 │ 告白气球 │ 周杰伦 │ 周杰伦的床边故事 │ 3:34 │
│ 4 │ 静花     │ 周杰伦 │ 最伟大的作品 │ 4:18 │
│ 5 │ 错过的烟火 │ 周杰伦 │ 最伟大的作品 │ 4:47 │
└───┴─────────┴────────┴────────┴──────┘

页码: 1/5  |  显示: 1-5/50

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
操作提示:
  输入序号选择歌曲 (如: 1,3,5 或 1-5)
  [n]下一页  [p]上一页  [s]重新搜索  [b]返回
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

选择歌曲:
```

**功能点**：
- ✅ 表格化展示（使用 rich.Table）
- ✅ 分页显示（每页10首）
- ✅ 多选支持（逗号分隔或范围）
- ✅ 快捷键导航（n/p/s/b）
- ✅ 搜索历史记录

#### 3.2.3 下载功能

**音质选择**：
```
🎯 选择下载音质

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
已选择: 3 首歌曲

  1. 标准音质 (128kbps)       - 3-5MB/首
  2. 极高音质 (320kbps)       - 8-10MB/首
  3. 无损音质 (FLAC) ⭐        - 15-25MB/首 [推荐]
  4. Hi-Res (24bit/96kHz)     - 40-60MB/首
  5. 沉浸环绕声 (sky)         - VIP专享
  6. 杜比全景声 (dolby)       - SVIP专享

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
默认音质: 无损音质
当前账号: 黑胶VIP ✓

选择音质 [1-6, 默认:3]:
```

**下载进度**：
```
⬇️  正在下载 (1/3): 周杰伦 - 晴天.flac

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Downloading... ━━━━━━━━━━━━━━━━━━━ 100%  2.3 MB/s

✅ 下载完成！
   文件: 周杰伦 - 晴天.flac
   大小: 18.5 MB
   音质: Lossless (FLAC)
   时长: 4:29
   位置: /path/to/downloads/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**批量下载**：
```
📦 批量下载 (3 首)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
正在下载: 1/3
  ✓ 周杰伦 - 晴天.flac (18.5 MB)
  ↓ 周杰伦 - 稻香.flac (正在下载...)  67%
  ○ 周杰伦 - 告白气球.flac (等待中)

总进度: ████████░░░░░░░░░░░ 33%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**功能点**：
- ✅ 音质选择（支持默认值）
- ✅ 进度条显示（使用 rich.Progress）
- ✅ 批量下载队列
- ✅ 下载速度显示
- ✅ 错误重试机制
- ✅ 完成统计（成功/失败）

#### 3.2.4 设置功能

```
⚙️  设置

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 默认音质: lossless (无损音质)
2. 下载目录: ./downloads/
3. 同时下载: 3 个
4. 自动重试: 3 次
5. 显示通知: 开启

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[1-5] 修改设置  [r]恢复默认  [b]返回
```

**功能点**：
- ✅ 配置持久化（config.json）
- ✅ 默认音质设置
- ✅ 下载目录设置
- ✅ 并发下载数控制
- ✅ 重试次数设置

### 3.3 AI模式（保持不变）

**完全兼容现有功能**：
```bash
# 所有现有命令保持不变
uv run python cli.py health
uv run python cli.py song 185668
uv run python cli.py search "周杰伦"
uv run python cli.py download 185668 --quality lossless
uv run python cli.py playlist 123456
uv run python cli.py album 123456
```

**关键特性**：
- ✅ JSON输出格式不变
- ✅ 退出码定义不变
- ✅ 参数接口不变
- ✅ 向后完全兼容

---

## 4. 技术方案

### 4.1 技术栈

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| API调用 | `requests>=2.28.2` | HTTP调用现有API服务 |
| AI模式 | 现有 `cli.py` | 保持不变 |
| 交互模式 | 新建 `cli_interactive.py` | 新增交互逻辑 |
| 界面美化 | `rich>=13.0.0` | 表格、进度条、面板 |
| 配置管理 | JSON文件 | `config.json` |

### 4.2 依赖更新

**pyproject.toml**：
```toml
dependencies = [
    # ... 现有依赖
    "rich>=13.0.0",           # 输出美化（保留，Textual也依赖）
    "textual>=0.50.0",        # TUI框架（新增）
]
```

**Textual vs Rich**：
- Rich：提供表格、面板、进度条等组件（继续使用）
- Textual：提供全屏TUI应用框架、键盘导航、布局系统（新增）

### 4.3 文件结构

```
项目根目录/
├── cli.py                        # 统一入口（修改）
│   ├─ main()                     # 模式路由逻辑
│   ├─ AI模式调用                 # 现有逻辑
│   └─ 交互模式调用               # Textual TUI
│
├── cli_commands.py               # AI模式命令（保持不变）
│   ├─ HealthCommand
│   ├─ SongCommand
│   ├─ SearchCommand
│   ├─ DownloadCommand
│   └─ ... 其他命令
│
├── cli_tui.py                    # Textual TUI应用（新增）
│   ├─ MusicTuiApp                # Textual应用主类
│   ├─ screens/                   # TUI屏幕
│   │   ├─ MainMenu              # 主菜单屏幕
│   │   ├─ SearchScreen           # 搜索屏幕
│   │   ├─ PlaylistScreen         # 歌单屏幕
│   │   ├─ AlbumScreen            # 专辑屏幕
│   │   └─ SettingsScreen         # 设置屏幕
│   ├─ widgets/                   # 自定义组件
│   │   ├─ SongListWidget         # 歌曲列表组件
│   │   ├─ DownloadProgress       # 下载进度组件
│   │   └─ QualitySelector        # 音质选择组件
│   └─ styles/                    # 样式定义
│       └─ tui_styles.css         # Textual CSS样式
│
├── music_api.py                  # 核心API（保持不变）
│   ├─ QRLoginManager
│   ├─ MusicAPI
│   └─ ... 其他类
│
├── config.json                   # 配置文件（已有）
│   ├─ default_quality
│   ├─ download_dir
│   └─ ... 其他配置
│
└── downloads/                    # 下载目录（已有）
    └─ 音乐文件
```

### 4.4 关键代码结构

#### cli.py (统一入口)

```python
#!/usr/bin/env python3
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(
        description="网易云音乐CLI工具",
        add_help=False
    )

    # 交互模式标志
    parser.add_argument('-i', '--interactive',
                       action='store_true',
                       help='启动TUI交互模式')

    # 现有参数...
    parser.add_argument('command', nargs='?', help='命令')
    parser.add_argument('args', nargs='*', help='命令参数')

    # 解析
    args = parser.parse_args()

    # 模式路由
    if args.interactive or len(sys.argv) == 1:
        # TUI交互模式
        from cli_tui import MusicTuiApp
        app = MusicTuiApp()
        app.run()
    else:
        # AI模式（现有逻辑）
        from cli_commands import main as cmd_main
        cmd_main()
```

#### cli_tui.py (Textual TUI应用)

```python
from textual.app import App, ComposeResult
from textual.widgets import (
    ListView, ListItem, Label, Header, Footer,
    Input, ProgressBar, Static
)

class MusicTuiApp(App):
    """网易云音乐TUI应用"""

    CSS = """
    Screen {
        background: $background;
    }
    ListView {
        border: solid $primary;
        height: 100%;
    }
    ListItem {
        padding: 1 2;
    }
    ListItem.-highlighted {
        background: $primary;
        color: $text;
    }
    """

    def compose(self) -> ComposeResult:
        """构建TUI界面"""
        yield Header()
        yield ListView(
            ListItem(Label("🔍 搜索歌曲")),
            ListItem(Label("📋 下载歌单")),
            ListItem(Label("💿 下载专辑")),
            ListItem(Label("⚙️  设置")),
            ListItem(Label("🚪 退出")),
        )
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """处理菜单选择"""
        option_index = event.item_index
        
        if option_index == 0:
            self.push_screen("search")
        elif option_index == 1:
            self.push_screen("playlist")
        elif option_index == 2:
            self.push_screen("album")
        elif option_index == 3:
            self.push_screen("settings")
        elif option_index == 4:
            self.exit()
```

### 4.5 Textual TUI界面设计

#### 主菜单屏幕

```python
from textual.screen import Screen
from textual.widgets import ListView, ListItem, Label

class MainMenu(Screen):
    """主菜单屏幕"""

    def compose(self) -> ComposeResult:
        yield ListView(
            ListItem(Label("🔍 搜索歌曲")),
            ListItem(Label("📋 下载歌单")),
            ListItem(Label("💿 下载专辑")),
            ListItem(Label("⚙️  设置")),
            ListItem(Label("🚪 退出")),
        )
```

#### 搜索屏幕

```python
class SearchScreen(Screen):
    """搜索屏幕"""

    def compose(self) -> ComposeResult:
        yield Input(placeholder="输入搜索关键词...", id="search_input")
        yield ListView(id="search_results")
        yield Static("按 Enter 搜索，↑↓ 选择，q 返回")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理搜索输入"""
        keyword = event.value
        # 调用搜索API
        results = self.search_music(keyword)
        # 更新列表视图
        self.query_one(ListView).remove_children()
        for song in results:
            yield ListItem(Label(f"{song['name']} - {song['artist']}"))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """处理歌曲选择"""
        song_index = event.item_index
        # 进入下载界面
        self.push_screen("download", {"song": self.search_results[song_index]})
```

#### 下载进度屏幕

```python
class DownloadScreen(Screen):
    """下载进度屏幕"""

    def compose(self) -> ComposeResult:
        yield Label("⬇️  下载中...", id="status")
        yield ProgressBar(total=100, show_eta=True, id="progress")
        yield Label("", id="current_file")

    def on_mount(self) -> None:
        """屏幕加载时开始下载"""
        self.download_next()

    def download_next(self):
        """下载下一首歌曲"""
        if self.current_index < len(self.songs):
            song = self.songs[self.current_index]
            self.query_one(Label, "#current_file").update(
                f"[{self.current_index + 1}/{len(self.songs)}] {song['name']}"
            )
            # 异步下载
            # ...下载逻辑
            self.current_index += 1
            self.download_next()
        else:
            self.app.pop_screen()
```

#### 键盘快捷键

| 按键 | 功能 | 适用屏幕 |
|------|------|---------|
| ↑↓ | 导航选项 | 所有列表 |
| Enter | 确认选择 | 所有列表 |
| Esc/q | 返回上级 | 所有屏幕 |
| / | 搜索 | 列表屏幕 |
| n | 下页 | 分页列表 |
| p | 上页 | 分页列表 |

            except KeyboardInterrupt:
                self.console.print("\n👋 再见！", style="bold green")
                break
            except Exception as e:
                self.console.print(f"❌ 错误: {e}", style="red")

    def show_welcome(self):
        """显示欢迎界面"""
        welcome_text = """
╔════════════════════════════════════════╗
║     🎵 网易云音乐下载工具 v2.0          ║
╚════════════════════════════════════════╝
        """
        self.console.print(Panel(welcome_text, style="bold blue"))

    def show_main_menu(self):
        """显示主菜单"""
        menu = """
📋 主菜单
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. 🔍 搜索歌曲
  2. 📋 下载歌单
  3. 💿 下载专辑
  4. 📜 下载历史
  5. ⚙️  设置
  0. 🚪 退出
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """
        self.console.print(menu)

        choice = Prompt.ask(
            "请选择操作",
            choices=["1", "2", "3", "4", "5", "0"],
            default="1"
        )
        return choice

    def search_music(self):
        """搜索音乐"""
        # 输入关键词
        keyword = Prompt.ask("请输入搜索关键词")

        # 调用API搜索
        results = self.api.search(keyword, limit=50)

        # 显示结果表格
        self.display_search_results(results)

        # 选择歌曲
        selected = self.select_songs(results)

        if selected:
            # 选择音质
            quality = self.select_quality()

            # 下载
            self.download_songs(selected, quality)

    def display_search_results(self, results):
        """显示搜索结果表格"""
        table = Table(title="搜索结果")
        table.add_column("#", style="cyan")
        table.add_column("歌曲名", style="magenta")
        table.add_column("歌手", style="green")
        table.add_column("专辑", style="blue")
        table.add_column("时长", style="yellow")

        for idx, song in enumerate(results, 1):
            table.add_row(
                str(idx),
                song['name'],
                song['artist'],
                song['album'],
                song['duration']
            )

        self.console.print(table)

    def select_songs(self, results):
        """选择歌曲（支持多选）"""
        choice = Prompt.ask(
            "选择歌曲 (输入序号，如 1,3,5 或 1-5)",
            default="all"
        )

        # 解析选择
        # ...

        return selected_songs

    def select_quality(self):
        """选择音质"""
        qualities = {
            '1': ('standard', '标准音质 (128kbps)'),
            '2': ('exhigh', '极高音质 (320kbps)'),
            '3': ('lossless', '无损音质 (FLAC) ⭐'),
            '4': ('hires', 'Hi-Res (24bit/96kHz)'),
            '5': ('sky', '沉浸环绕声 (VIP)'),
            '6': ('dolby', '杜比全景声 (SVIP)'),
        }

        self.console.print("🎯 选择下载音质")
        for key, (code, name) in qualities.items():
            self.console.print(f"  {key}. {name}")

        choice = Prompt.ask(
            "选择音质",
            choices=list(qualities.keys()),
            default='3'
        )

        return qualities[choice][0]

    def download_songs(self, songs, quality):
        """下载歌曲"""
        with Progress() as progress:
            task = progress.add_task(
                "下载中...",
                total=len(songs)
            )

            for song in songs:
                # 下载逻辑
                result = self.api.download_song(
                    song['id'],
                    quality=quality
                )

                if result['success']:
                    progress.update(task, advance=1)
                    self.console.print(
                        f"✅ {song['name']} 下载完成",
                        style="green"
                    )
                else:
                    self.console.print(
                        f"❌ {song['name']} 下载失败",
                        style="red"
                    )

                # 保存历史
                self.history.add_record(song, result)

    def show_history(self):
        """显示下载历史"""
        # 显示历史记录
        pass

    def show_settings(self):
        """显示设置"""
        # 设置界面
        pass

    def load_config(self):
        """加载配置"""
        # 加载config.json
        pass
```

---

## 5. 开发计划

### 5.1 实施阶段

#### Phase 1-5: Rich交互模式（已完成）✅

**实际开发时间**: 约 4-5 小时

**实施状态**: 核心功能已完成，可投入使用

**已完成功能**:
- ✅ Rich美化界面
- ✅ 搜索歌曲并显示表格
- ✅ 下载歌单/专辑（批量选择）
- ✅ 设置管理
- ✅ 进度显示和统计

#### Phase 6: Textual TUI升级（进行中）🚀

**预计开发时间**: 约 3-4 小时

**实施步骤**:

1. **环境准备** (30分钟)
   - [ ] 添加 `textual>=0.50.0` 到依赖
   - [ ] 创建 `cli_tui.py` 基础框架
   - [ ] 修改 `cli.py` 添加TUI路由

2. **主菜单屏幕** (1小时)
   - [ ] 实现 MainMenu 屏幕
   - [ ] 添加 Header 和 Footer
   - [ ] 定义 CSS 样式
   - [ ] 测试键盘导航

3. **搜索功能屏幕** (1小时)
   - [ ] 实现 SearchScreen
   - [ ] 添加搜索输入框
   - [ ] 实现结果列表视图
   - [ ] 支持键盘选择和确认

4. **下载进度屏幕** (1小时)
   - [ ] 实现 DownloadScreen
   - [ ] 添加进度条组件
   - [ ] 实时状态更新
   - [ ] 支持批量下载

5. **其他屏幕** (30分钟)
   - [ ] 歌单下载屏幕
   - [ ] 专辑下载屏幕
   - [ ] 设置屏幕

6. **测试和优化** (30分钟)
   - [ ] 完整功能测试
   - [ ] 性能优化
   - [ ] 错误处理完善

---

### 5.2 验收标准

#### 功能验收
- ✅ 交互模式可正常启动
- ✅ 搜索歌曲功能完整
- ✅ 下载功能完整，有进度显示
- ✅ AI模式完全不受影响
- ✅ 所有现有命令正常工作

#### 质量验收
- ✅ 无明显bug
- ✅ 错误处理完善
- ✅ 界面美观友好
- ✅ 代码质量良好

#### 文档验收
- ✅ 使用文档更新
- ✅ README更新
- ✅ 代码注释完整

---

## 6. 风险评估

### 6.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 破坏现有AI模式 | 高 | 低 | 充分测试，保持接口不变 |
| 交互模式与AI模式冲突 | 中 | 低 | 明确的模式触发条件 |
| rich库兼容性问题 | 低 | 低 | 选择稳定版本（13.0.0+） |
| 代码复杂度增加 | 中 | 中 | 良好的代码结构和注释 |

### 6.2 兼容性风险

- ✅ 向后兼容：AI模式完全不变
- ✅ Python版本：需要3.10+（已满足）
- ✅ 依赖冲突：rich库与现有依赖无冲突

---

## 7. 成功指标

### 7.1 功能指标
- ✅ 交互模式启动成功率 100%
- ✅ 搜索响应时间 < 2秒
- ✅ 下载成功率 > 95%
- ✅ AI模式回归测试通过率 100%

### 7.2 用户体验指标
- ✅ 新用户5分钟内完成首次下载
- ✅ 界面直观，无需查看文档即可使用
- ✅ 错误提示清晰友好

---

## 8. 后续优化方向

### 8.1 短期优化（可选）
- 🎵 播放预览功能
- 🎨 主题切换（亮色/暗色）
- 🔍 搜索历史和自动补全
- 📊 下载统计

### 8.2 长期优化（可选）
- 🎬 TUI模式（全屏终端UI）
- 🔄 歌单同步功能
- 📱 移动端适配（通过ssh）
- 🤖 AI智能推荐

---

## 9. 附录

### 9.1 参考资料
- [Rich库官方文档](https://rich.readthedocs.io/)
- [CLI设计最佳实践](https://clig.dev/)
- [项目README](../README.md)
- [CLI使用手册](../CLI使用手册.md)

### 9.2 相关文档
- [CLI改造PRD (v1.0)](./CLI改造PRD.md) - 原CLI实现PRD
- [使用文档](../使用文档.md) - 用户使用指南
- [CLAUDE.md](../CLAUDE.md) - 项目架构文档

---

**文档版本**: v1.0
**最后更新**: 2026-03-31
**状态**: 待评审
