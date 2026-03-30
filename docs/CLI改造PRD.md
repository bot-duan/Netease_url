# 网易云音乐API CLI改造PRD（自动化/AI调用优化版）

## 一、项目背景

### 1.1 当前状态
项目已实现完善的Flask API服务，提供以下核心功能：
- 歌曲信息获取（URL/详情/歌词）
- 音乐搜索
- 歌单/专辑解析
- 音乐下载（支持多种音质）
- 二维码登录

### 1.2 改造目标

**核心目标**：在**不破坏现有API服务逻辑**的前提下，增加CLI命令行调用方式，专为**自动化脚本和AI调用**优化。

**主要使用场景**：
- 🤖 **AI Agent调用**：LLM/AI Agent 通过Shell命令调用音乐服务
- 🔄 **自动化脚本**：CI/CD、批处理、定时任务
- 🔗 **程序集成**：其他程序通过Shell调用本服务
- 📊 **数据处理**：批量获取音乐数据

**核心原则**：
- ✅ **非侵入式改造**：原有API服务零改动
- ✅ **机器可读优先**：默认输出JSON格式，便于程序解析
- ✅ **明确退出码**：标准化退出码，便于脚本判断成功/失败
- ✅ **输出流分离**：stdout输出数据，stderr输出日志/错误
- ✅ **非交互式设计**：所有参数通过命令行传入，无需交互
- ✅ **幂等性保证**：相同输入产生相同输出

---

## 二、架构分析

### 2.1 当前架构
```
┌─────────────────────────────────────┐
│           main.py (Flask API)        │
│  ┌───────────────────────────────┐  │
│  │    MusicAPIService            │  │
│  │  - 核心业务逻辑封装           │  │
│  │  - Cookie管理                 │  │
│  │  - 文件处理                   │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │    Flask Routes               │  │
│  │  - /song, /search             │  │
│  │  - /playlist, /album          │  │
│  │  - /download                  │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
           ↓ 导入
┌─────────────────────────────────────┐
│         music_api.py                │
│    (纯函数接口，可独立调用)          │
└─────────────────────────────────────┘
```

### 2.2 改造后架构
```
┌─────────────────────────────────────┐
│         main.py (Flask API)          │
│        【保持不变，零改动】           │
└─────────────────────────────────────┘
           ↑
        导入
           │
┌───────────────────────────────────────┐
│  cli.py (新增)                        │
│  ┌─────────────────────────────────┐  │
│  │  CLI命令解析 (argparse)         │  │
│  └─────────────┬───────────────────┘  │
│                │                       │
│  ┌─────────────┴───────────────────┐  │
│  │  输出格式化层                   │  │
│  │  - JSONFormatter (默认)         │  │
│  │  - HumanReadableFormatter (可选)│  │
│  └─────────────┬───────────────────┘  │
│                │                       │
│  ┌─────────────┴───────────────────┐  │
│  │  错误处理层                     │  │
│  │  - 标准化退出码                 │  │
│  │  - 结构化错误信息               │  │
│  └─────────────┬───────────────────┘  │
│                │                       │
│  ┌─────────────┴───────────────────┐  │
│  │  复用 MusicAPIService           │  │
│  └─────────────────────────────────┘  │
└───────────────────────────────────────┘
                ↓
┌───────────────────────────────────────┐
│  music_api.py (保持不变)               │
│  cookie_manager.py (保持不变)          │
│  music_downloader.py (保持不变)        │
└───────────────────────────────────────┘
```

**关键设计**：
- `cli.py` 直接导入并复用 `main.py` 中的 `MusicAPIService`
- `main.py` **完全不动**，保证API服务稳定性
- CLI专注于输出格式化和错误处理

---

## 三、CLI命令设计（自动化优先）

### 3.1 命令结构

```bash
python cli.py <command> [arguments] [options]
```

**重要设计原则**：
- 🚫 **无交互式输入**：所有参数通过命令行传入
- 📤 **默认JSON输出**：便于程序解析
- 🔢 **标准化退出码**：便于脚本判断结果
- 📊 **输出流分离**：stdout输出数据，stderr输出日志

### 3.2 标准化退出码规范

```python
退出码    含义                    示例场景
─────────────────────────────────────────────
0        成功                    操作正常完成
1        业务错误                歌曲不存在、版权限制
2        参数错误                缺少必需参数、参数格式错误
3        系统错误                网络错误、文件读写错误
4        认证错误                Cookie无效、Cookie过期
130      用户中断                Ctrl+C
```

### 3.3 输出格式规范

#### 3.3.1 默认JSON输出（适用于自动化/AI）

**成功响应**（stdout）：
```json
{
  "success": true,
  "code": 0,
  "data": {
    // 具体业务数据
  },
  "message": "操作成功"
}
```

**错误响应**（stdout）：
```json
{
  "success": false,
  "code": 1,
  "error": {
    "type": "SongNotFoundError",
    "message": "歌曲不存在",
    "details": {
      "song_id": "999999999"
    }
  }
}
```

**日志信息**（stderr）：
```
[INFO] 2026-03-31 12:00:00 - 开始处理歌曲ID: 185668
[INFO] 2026-03-31 12:00:01 - 获取歌曲信息成功
```

#### 3.3.2 人类可读输出（可选，通过 `--output human` 启用）

仅在调试或人工查看时使用：
```
歌曲信息
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ID: 185668
歌名: 稻香
音质: lossless (无损音质)
大小: 18.5MB
格式: flac
URL: https://music.126.net/...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 四、详细命令设计

### 4.1 健康检查

```bash
python cli.py health
```

**默认输出（JSON）**：
```json
{
  "success": true,
  "code": 0,
  "data": {
    "service": "running",
    "timestamp": 1730376000,
    "cookie_status": "valid",
    "version": "2.0.0"
  },
  "message": "API服务运行正常"
}
```

**人类可读输出**：
```bash
python cli.py health --output human
```
```
✓ API服务运行正常
  Cookie状态: valid
  版本: 2.0.0
```

**错误情况**（Cookie无效）：
```json
{
  "success": false,
  "code": 4,
  "error": {
    "type": "AuthenticationError",
    "message": "Cookie无效或已过期",
    "details": {
      "cookie_file": "cookie.txt",
      "suggestion": "请运行 qr_login.py 重新登录"
    }
  }
}
```

**退出码**：
- 成功：`0`
- Cookie无效：`4`

---

### 4.2 获取歌曲信息

```bash
# 基本用法
python cli.py song 185668

# 指定音质
python cli.py song 185668 --level hires

# 获取不同类型信息
python cli.py song 185668 --type name     # 歌曲详情
python cli.py song 185668 --type lyric    # 歌词
python cli.py song 185668 --type json     # 完整信息

# 支持URL输入
python cli.py song https://music.163.com/song?id=185668

# 人类可读输出
python cli.py song 185668 --output human

# 指定Cookie文件
python cli.py --cookie /path/to/cookie.txt song 185668

# 详细日志（输出到stderr）
python cli.py --verbose song 185668
```

#### 4.2.1 获取歌曲URL（默认）

```bash
python cli.py song 185668
```

**成功输出**：
```json
{
  "success": true,
  "code": 0,
  "data": {
    "id": 185668,
    "url": "https://music.126.net/...",
    "level": "lossless",
    "size": 19398656,
    "type": "flac",
    "bitrate": 0
  },
  "message": "获取歌曲URL成功"
}
```

#### 4.2.2 获取歌曲详情

```bash
python cli.py song 185668 --type name
```

**输出**：
```json
{
  "success": true,
  "code": 0,
  "data": {
    "songs": [
      {
        "id": 185668,
        "name": "稻香",
        "ar": [
          {"id": 6452, "name": "周杰伦", "tns": [], "alias": []}
        ],
        "al": {
          "id": 16906,
          "name": "魔杰座",
          "picUrl": "https://p3.music.126.net/..."
        },
        "dt": 223000
      }
    ]
  },
  "message": "获取歌曲信息成功"
}
```

#### 4.2.3 获取歌词

```bash
python cli.py song 185668 --type lyric
```

**输出**：
```json
{
  "success": true,
  "code": 0,
  "data": {
    "lrc": {
      "version": 1,
      "lyric": "对这个世界如果你有太多的抱怨..."
    },
    "tlyric": {
      "version": 0,
      "lyric": ""
    }
  },
  "message": "获取歌词成功"
}
```

#### 4.2.4 错误处理

**歌曲不存在**：
```bash
python cli.py song 999999999
```

**输出**（stdout）：
```json
{
  "success": false,
  "code": 1,
  "error": {
    "type": "SongNotFoundError",
    "message": "歌曲不存在或无法访问",
    "details": {
      "song_id": "999999999",
      "suggestion": "请检查歌曲ID是否正确"
    }
  }
}
```

**日志**（stderr）：
```
[ERROR] 2026-03-31 12:00:00 - 歌曲不存在: 999999999
```

**退出码**：`1`

**参数错误**：
```bash
python cli.py song  # 缺少必需参数
```

**输出**（stderr）：
```
usage: cli.py song [-h] [--level LEVEL] [--type TYPE] [--output OUTPUT] id
cli.py song: error: the following arguments are required: id
```

**退出码**：`2`

---

### 4.3 搜索音乐

```bash
# 基本用法
python cli.py search "周杰伦 稻香"

# 限制返回数量
python cli.py search "周杰伦" --limit 10

# 指定搜索类型
python cli.py search "周杰伦" --type 1    # 歌曲（默认）
python cli.py search "周杰伦" --type 10   # 专辑
python cli.py search "周杰伦" --type 100  # 歌手
python cli.py search "周杰伦" --type 1000 # 歌单

# 人类可读输出
python cli.py search "周杰伦" --output human
```

**默认输出（JSON）**：
```json
{
  "success": true,
  "code": 0,
  "data": {
    "result": {
      "songs": [
        {
          "id": 185668,
          "name": "稻香",
          "artists": "周杰伦",
          "album": "魔杰座",
          "picUrl": "https://p3.music.126.net/..."
        },
        {
          "id": 186016,
          "name": "晴天",
          "artists": "周杰伦",
          "album": "七里香",
          "picUrl": "https://p3.music.126.net/..."
        }
      ],
      "total": 100,
      "returned": 30
    }
  },
  "message": "搜索完成"
}
```

**人类可读输出**：
```
搜索结果：周杰伦 (共100条，返回30条)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[1] 稻香 - 周杰伦 | 魔杰座 | ID: 185668
[2] 晴天 - 周杰伦 | 七里香 | ID: 186016
[3] 青花瓷 - 周杰伦 | 我很忙 | ID: 186017
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### 4.4 歌单解析

```bash
# 基本用法
python cli.py playlist 123456789

# 支持URL输入
python cli.py playlist https://music.163.com/playlist?id=123456789

# 人类可读输出
python cli.py playlist 123456789 --output human
```

**默认输出（JSON）**：
```json
{
  "success": true,
  "code": 0,
  "data": {
    "status": "success",
    "playlist": {
      "id": 123456789,
      "name": "我的华语歌单",
      "coverImgUrl": "https://p3.music.126.net/...",
      "creator": "用户昵称",
      "trackCount": 50,
      "description": "这是一个精选歌单",
      "tracks": [
        {
          "id": 185668,
          "name": "稻香",
          "artists": "周杰伦",
          "album": "魔杰座",
          "picUrl": "https://p3.music.126.net/..."
        }
      ]
    }
  },
  "message": "获取歌单详情成功"
}
```

---

### 4.5 专辑解析

```bash
# 基本用法
python cli.py album 123456789

# 支持URL输入
python cli.py album https://music.163.com/album?id=123456789
```

**输出**：
```json
{
  "success": true,
  "code": 0,
  "data": {
    "status": 200,
    "album": {
      "id": 123456789,
      "name": "专辑名",
      "coverImgUrl": "https://p3.music.126.net/...",
      "artist": "歌手名",
      "publishTime": 1234567890000,
      "description": "专辑描述",
      "songs": [
        {
          "id": 185668,
          "name": "歌曲名",
          "artists": "歌手名",
          "album": "专辑名",
          "picUrl": "https://p3.music.126.net/..."
        }
      ]
    }
  },
  "message": "获取专辑详情成功"
}
```

---

### 4.6 音乐下载

```bash
# 基本用法（下载文件）
python cli.py download 185668

# 指定音质
python cli.py download 185668 --quality hires

# 只输出下载信息（不下载文件）
python cli.py download 185668 --format json

# 指定输出目录
python cli.py download 185668 --output-dir /path/to/music

# 支持URL输入
python cli.py download https://music.163.com/song?id=185668

# 静默模式（不输出日志到stderr）
python cli.py --quiet download 185668
```

#### 4.6.1 下载文件（默认）

```bash
python cli.py download 185668
```

**成功输出**（stdout）：
```json
{
  "success": true,
  "code": 0,
  "data": {
    "music_id": 185668,
    "name": "稻香",
    "artist": "周杰伦",
    "album": "魔杰座",
    "quality": "lossless",
    "quality_name": "无损音质",
    "file_type": "flac",
    "file_size": 19398656,
    "file_size_formatted": "18.50MB",
    "file_path": "/path/to/downloads/周杰伦 - 稻香.flac",
    "filename": "周杰伦 - 稻香.flac",
    "duration": 223
  },
  "message": "下载完成"
}
```

**日志**（stderr）：
```
[INFO] 2026-03-31 12:00:00 - 开始下载: 周杰伦 - 稻香
[INFO] 2026-03-31 12:00:05 - 下载进度: 100%
[INFO] 2026-03-31 12:00:05 - 写入音乐标签完成
```

**退出码**：`0`

#### 4.6.2 获取下载信息（不下载文件）

```bash
python cli.py download 185668 --format json
```

**输出**：
```json
{
  "success": true,
  "code": 0,
  "data": {
    "download_available": true,
    "music_info": {
      "id": 185668,
      "name": "稻香",
      "artist": "周杰伦",
      "quality": "lossless",
      "url": "https://music.126.net/...",
      "file_size": 19398656
    }
  },
  "message": "获取下载信息成功"
}
```

#### 4.6.3 错误处理

**版权限制**：
```bash
python cli.py download 999999999
```

**输出**（stdout）：
```json
{
  "success": false,
  "code": 1,
  "error": {
    "type": "DownloadNotAllowedError",
    "message": "无法下载，可能原因：版权限制或音质不支持",
    "details": {
      "music_id": "999999999",
      "quality": "lossless",
      "suggestion": "请尝试降低音质或检查VIP状态"
    }
  }
}
```

**退出码**：`1`

---

## 五、全局选项

### 5.1 输出格式选项

```bash
# JSON格式（默认，适用于自动化/AI）
python cli.py song 185668
python cli.py song 185668 --output json

# 人类可读格式（适用于调试/人工查看）
python cli.py song 185668 --output human
```

### 5.2 Cookie选项

```bash
# 使用默认Cookie文件（cookie.txt）
python cli.py song 185668

# 指定Cookie文件
python cli.py --cookie /path/to/cookie.txt song 185668

# 直接传入Cookie字符串
python cli.py --cookie "MUSIC_U=xxx;" song 185668
```

### 5.3 日志选项

```bash
# 正常模式（重要信息到stderr）
python cli.py song 185668

# 详细模式（所有日志到stderr）
python cli.py --verbose song 185668

# 静默模式（无日志输出）
python cli.py --quiet song 185668
```

### 5.4 超时选项

```bash
# 设置请求超时时间（秒）
python cli.py --timeout 60 download 185668
```

---

## 六、自动化调用示例

### 6.1 Shell脚本调用

```bash
#!/bin/bash
# 批量下载歌曲

SONG_IDS=(185668 186016 186017)

for id in "${SONG_IDS[@]}"; do
  echo "正在处理歌曲ID: $id"

  # 调用CLI
  result=$(python cli.py download "$id" --quality lossless)

  # 解析结果（使用jq）
  success=$(echo "$result" | jq -r '.success')

  if [ "$success" = "true" ]; then
    filename=$(echo "$result" | jq -r '.data.filename')
    echo "✓ 下载成功: $filename"
  else
    error_msg=$(echo "$result" | jq -r '.error.message')
    echo "✗ 下载失败: $error_msg"
  fi
done
```

### 6.2 Python脚本调用

```python
#!/usr/bin/env python3
import subprocess
import json

def download_song(song_id, quality='lossless'):
    """调用CLI下载歌曲"""
    cmd = ['python', 'cli.py', 'download', song_id, '--quality', quality]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False
    )

    # 解析JSON输出
    try:
        data = json.loads(result.stdout)
        if data['success']:
            return data['data']
        else:
            print(f"错误: {data['error']['message']}")
            return None
    except json.JSONDecodeError:
        print(f"解析失败: {result.stdout}")
        return None

# 使用
song_info = download_song('185668')
if song_info:
    print(f"下载成功: {song_info['filename']}")
```

### 6.3 AI Agent调用示例

```python
# AI Agent通过工具调用
tools = [
    {
        "name": "netease_music_search",
        "description": "搜索网易云音乐",
        "function": lambda keyword: subprocess.run(
            ['python', 'cli.py', 'search', keyword, '--limit', '10'],
            capture_output=True,
            text=True
        ).stdout
    },
    {
        "name": "netease_music_download",
        "description": "下载网易云音乐",
        "function": lambda song_id: subprocess.run(
            ['python', 'cli.py', 'download', song_id, '--quality', 'lossless'],
            capture_output=True,
            text=True
        ).stdout
    }
]
```

---

## 七、技术实现方案

### 7.1 文件结构

```
Netease_url/
├── cli.py              # 【新增】CLI命令行入口
│   ├── CLICommand      # 命令处理类
│   ├── JSONFormatter   # JSON输出格式化
│   ├── HumanFormatter  # 人类可读输出格式化
│   └── ErrorHandler    # 错误处理和退出码管理
├── main.py             # 【保持不变】Flask API服务
├── music_api.py        # 【保持不变】
├── cookie_manager.py   # 【保持不变】
├── music_downloader.py # 【保持不变】
├── qr_login.py         # 【保持不变】
└── docs/
    └── CLI改造PRD.md   # 本文档
```

### 7.2 核心代码结构

```python
#!/usr/bin/env python3
"""网易云音乐CLI - 自动化/AI调用优化版"""

import argparse
import sys
import json
import logging

from main import MusicAPIService, APIConfig
from music_api import APIException

# 退出码规范
class ExitCode:
    SUCCESS = 0
    BUSINESS_ERROR = 1      # 业务错误（歌曲不存在、版权限制）
    PARAMETER_ERROR = 2     # 参数错误
    SYSTEM_ERROR = 3        # 系统错误（网络、文件）
    AUTH_ERROR = 4          # 认证错误（Cookie无效）

class JSONFormatter:
    """JSON输出格式化器"""

    @staticmethod
    def success(data, message="操作成功"):
        return {
            "success": True,
            "code": 0,
            "data": data,
            "message": message
        }

    @staticmethod
    def error(code, error_type, message, details=None):
        return {
            "success": False,
            "code": code,
            "error": {
                "type": error_type,
                "message": message,
                "details": details or {}
            }
        }

class CLICommand:
    """CLI命令处理器"""

    def __init__(self, cookie_file=None, verbose=False, quiet=False):
        self.config = APIConfig()
        self.service = MusicAPIService(self.config)
        self.setup_logging(verbose, quiet)

    def setup_logging(self, verbose, quiet):
        """设置日志"""
        self.logger = logging.getLogger('cli')
        self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)

        if not quiet:
            handler = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter(
                '[%(levelname)s] %(asctime)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def song(self, song_id, **kwargs):
        """获取歌曲信息"""
        try:
            # 提取音乐ID
            music_id = self.service._extract_music_id(song_id)
            self.logger.info(f"开始处理歌曲ID: {music_id}")

            # 获取Cookie
            cookies = self.service._get_cookies()

            # 根据类型获取信息
            info_type = kwargs.get('type', 'url')
            level = kwargs.get('level', 'lossless')

            if info_type == 'url':
                result = url_v1(music_id, level, cookies)
                if result and result.get('data'):
                    return JSONFormatter.success(result['data'][0])
                else:
                    raise CLIException(
                        ExitCode.BUSINESS_ERROR,
                        "SongNotFoundError",
                        "歌曲不存在或无法访问",
                        {"song_id": music_id}
                    )

            # ... 其他类型处理

        except APIException as e:
            raise CLIException(
                ExitCode.SYSTEM_ERROR,
                "APICallError",
                str(e)
            )

    # ... 其他命令方法

def main():
    """CLI入口"""
    parser = argparse.ArgumentParser(
        description='网易云音乐CLI - 自动化/AI调用版',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # 全局选项
    parser.add_argument('--cookie', help='Cookie文件或字符串')
    parser.add_argument('--verbose', action='store_true', help='详细日志')
    parser.add_argument('--quiet', action='store_true', help='静默模式')
    parser.add_argument('--output', choices=['json', 'human'], default='json',
                       help='输出格式')

    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # health命令
    subparsers.add_parser('health', help='健康检查')

    # song命令
    song_parser = subparsers.add_parser('song', help='获取歌曲信息')
    song_parser.add_argument('id', help='歌曲ID或URL')
    song_parser.add_argument('--level', default='lossless',
                            choices=['standard', 'exhigh', 'lossless', 'hires',
                                   'sky', 'jyeffect', 'jymaster'],
                            help='音质等级')
    song_parser.add_argument('--type', default='url',
                            choices=['url', 'name', 'lyric', 'json'],
                            help='信息类型')

    # ... 其他命令

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(ExitCode.PARAMETER_ERROR)

    # 创建CLI实例
    cli = CLICommand(
        cookie_file=args.cookie,
        verbose=args.verbose,
        quiet=args.quiet
    )

    # 执行命令
    try:
        if args.command == 'health':
            result = cli.health()
        elif args.command == 'song':
            result = cli.song(args.id, level=args.level, type=args.type)
        # ... 其他命令

        # 输出结果
        if args.output == 'json':
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # 人类可读格式
            print(format_human_readable(result))

        sys.exit(ExitCode.SUCCESS)

    except CLIException as e:
        # 错误处理
        error_result = JSONFormatter.error(e.code, e.error_type, e.message, e.details)
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        cli.logger.error(f"{e.error_type}: {e.message}")
        sys.exit(e.code)

    except KeyboardInterrupt:
        cli.logger.warning("用户中断操作")
        sys.exit(130)

    except Exception as e:
        error_result = JSONFormatter.error(
            ExitCode.SYSTEM_ERROR,
            "UnexpectedError",
            str(e)
        )
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        cli.logger.exception("未预期的错误")
        sys.exit(ExitCode.SYSTEM_ERROR)

if __name__ == '__main__':
    main()
```

---

## 八、测试策略

### 8.1 自动化测试用例

#### 8.1.1 功能测试

```bash
# 测试1: 正常获取歌曲信息
python cli.py song 185668
echo $?
# 预期: 输出JSON，退出码为0

# 测试2: 歌曲不存在
python cli.py song 999999999
echo $?
# 预期: 输出错误JSON，退出码为1

# 测试3: 参数错误
python cli.py song
echo $?
# 预期: 输出帮助信息，退出码为2

# 测试4: 搜索功能
python cli.py search "周杰伦" --limit 5 | jq '.data.result.songs | length'
# 预期: 输出5
```

#### 8.1.2 输出格式测试

```bash
# 测试JSON输出格式
python cli.py song 185668 | jq '.success'
# 预期: true

# 测试人类可读输出
python cli.py song 185668 --output human
# 预期: 格式化的文本输出

# 测试静默模式
python cli.py --quiet song 185668 2>&1 | grep -c "INFO"
# 预期: 0（无日志输出）
```

#### 8.1.3 退出码测试

```bash
# 测试各种退出码
python cli.py song 185668; echo $?  # 0
python cli.py song 999999999; echo $?  # 1
python cli.py song; echo $?  # 2
```

### 8.2 AI调用测试

```python
# 测试AI Agent调用
import subprocess
import json

def ai_call_test():
    """模拟AI调用"""
    # 搜索歌曲
    result = subprocess.run(
        ['python', 'cli.py', 'search', '周杰伦', '--limit', '1'],
        capture_output=True,
        text=True
    )

    data = json.loads(result.stdout)
    assert data['success'] == True
    assert result.returncode == 0

    # 下载歌曲
    song_id = data['data']['result']['songs'][0]['id']
    result = subprocess.run(
        ['python', 'cli.py', 'download', str(song_id), '--format', 'json'],
        capture_output=True,
        text=True
    )

    data = json.loads(result.stdout)
    assert data['success'] == True
    assert result.returncode == 0

ai_call_test()
```

---

## 九、实施计划

### 9.1 开发阶段

#### Phase 1: 基础框架（1-2小时）
- [ ] 创建 `cli.py` 文件
- [ ] 实现 argparse 框架
- [ ] 实现 JSONFormatter 和 ErrorHandler
- [ ] 实现 `health` 命令
- [ ] 测试退出码规范

#### Phase 2: 核心命令（3-4小时）
- [ ] 实现 `song` 命令（支持所有type）
- [ ] 实现 `search` 命令
- [ ] 实现 `playlist` 命令
- [ ] 实现 `album` 命令
- [ ] 实现 `download` 命令

#### Phase 3: 输出优化（2-3小时）
- [ ] 实现 JSONFormatter（默认）
- [ ] 实现 HumanFormatter（可选）
- [ ] 添加日志级别控制
- [ ] 添加进度输出（下载时）

#### Phase 4: 测试与文档（1-2小时）
- [ ] 自动化测试用例
- [ ] AI调用测试
- [ ] 更新 README.md
- [ ] 添加自动化调用示例

### 9.2 里程碑
- **M1**: 基础框架完成，可运行 `health` 命令
- **M2**: 核心命令完成，功能与API对齐
- **M3**: 输出格式优化完成，JSON输出标准化
- **M4**: 测试完善，可发布使用

---

## 十、成功标准

### 10.1 自动化友好性
- ✅ 默认输出结构化JSON
- ✅ 标准化退出码
- ✅ 输出流分离（stdout数据，stderr日志）
- ✅ 错误信息结构化

### 10.2 AI调用友好性
- ✅ 输出格式稳定、可预测
- ✅ 错误类型明确，便于AI理解
- ✅ 参数设计直观，便于LLM生成
- ✅ 提供丰富的调用示例

### 10.3 非侵入性
- ✅ main.py 零改动
- ✅ API服务无任何影响
- ✅ 原有功能完全兼容

---

## 十一、参考工具

### 11.1 CLI设计参考
- **kubectl**: Kubernetes CLI（输出格式设计）
- **gh**: GitHub CLI（子命令设计）
- **jq**: JSON处理（输出格式参考）
- **ffmpeg**: 媒体处理CLI（退出码规范）

### 11.2 技术栈
- **参数解析**: argparse (Python标准库)
- **JSON处理**: json (Python标准库)
- **日志**: logging (Python标准库)
- **测试**: pytest, subprocess

---

**文档版本**: v2.0 (自动化/AI调用优化版)
**创建日期**: 2026-03-31
**最后更新**: 2026-03-31
**主要变更**:
- 🔄 默认输出改为JSON格式
- 🔢 添加标准化退出码规范
- 📤 添加输出流分离设计
- 🤖 优化AI调用场景
- ❌ 移除交互模式设计
