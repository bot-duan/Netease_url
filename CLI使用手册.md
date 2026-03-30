# 网易云音乐CLI使用手册

[![Version](https://img.shields.io/badge/version-2.0.0-blue)](./README.md)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

专为**自动化脚本**和**AI调用**优化的网易云音乐命令行接口。

---

## 📖 目录

- [快速开始](#快速开始)
- [命令详解](#命令详解)
  - [health - 健康检查](#health---健康检查)
  - [song - 获取歌曲信息](#song---获取歌曲信息)
  - [search - 搜索音乐](#search---搜索音乐)
  - [playlist - 获取歌单详情](#playlist---获取歌单详情)
  - [album - 获取专辑详情](#album---获取专辑详情)
  - [download - 下载音乐](#download---下载音乐)
- [全局选项](#全局选项)
- [输出格式](#输出格式)
- [退出码说明](#退出码说明)
- [自动化调用示例](#自动化调用示例)
- [常见问题](#常见问题)

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- uv（Python包管理器）
- 网易云音乐账号（推荐黑胶会员）

### 安装uv

如果尚未安装uv，请执行以下命令：

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用Homebrew
brew install uv

# 验证安装
uv --version
```

### 基本语法

```bash
uv run uv run python cli.py <command> [arguments] [options]
```

### 第一个命令

```bash
# 检查服务状态
uv run uv run python cli.py health

# 输出示例：
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

### 查看帮助

```bash
# 查看所有命令
uv run uv run python cli.py --help

# 查看特定命令的帮助
uv run uv run python cli.py song --help
uv run uv run python cli.py download --help
```

---

## 📚 命令详解

### health - 健康检查

检查API服务运行状态和Cookie有效性。

#### 语法

```bash
uv run python cli.py health
```

#### 示例

```bash
# JSON格式（默认）
uv run python cli.py health

# 人类可读格式
uv run python cli.py --output human health

# 静默模式
uv run python cli.py --quiet health
```

#### 返回字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| service | string | 服务状态，"running"表示正常 |
| timestamp | integer | 当前时间戳（秒） |
| cookie_status | string | Cookie状态："valid"或"invalid" |
| version | string | CLI版本号 |

---

### song - 获取歌曲信息

获取单首歌曲的详细信息，支持多种信息类型。

#### 语法

```bash
uv run python cli.py song <歌曲ID或URL> [options]
```

#### 参数

| 参数 | 说明 | 示例 |
|------|------|------|
| id | 歌曲ID或URL | `185668` 或 `https://music.163.com/song?id=185668` |

#### 选项

| 选项 | 说明 | 默认值 | 可选值 |
|------|------|--------|--------|
| --level | 音质等级 | lossless | standard, exhigh, lossless, hires, sky, jyeffect, jymaster, dolby |
| --type | 信息类型 | url | url, name, lyric, json |

#### 示例

##### 1. 获取歌曲URL（默认）

```bash
uv run python cli.py song 185668
```

**返回：**
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

##### 2. 获取歌曲详情

```bash
uv run python cli.py song 185668 --type name
```

**返回：**
```json
{
  "success": true,
  "code": 0,
  "data": {
    "songs": [
      {
        "name": "稻香",
        "id": 185668,
        "ar": [{"name": "周杰伦"}],
        "al": {"name": "魔杰座"}
      }
    ]
  },
  "message": "获取歌曲信息成功"
}
```

##### 3. 获取歌词

```bash
uv run python cli.py song 185668 --type lyric
```

##### 4. 获取完整信息

```bash
uv run python cli.py song 185668 --type json
```

##### 5. 指定音质

```bash
uv run python cli.py song 185668 --level hires
```

##### 6. 使用URL输入

```bash
uv run python cli.py song "https://music.163.com/song?id=185668"
```

---

### search - 搜索音乐

根据关键词搜索歌曲、专辑、歌手或歌单。

#### 语法

```bash
uv run python cli.py search <关键词> [options]
```

#### 参数

| 参数 | 说明 | 示例 |
|------|------|------|
| keyword | 搜索关键词 | `"周杰伦"` `"稻香 周杰伦"` |

#### 选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| --limit | 返回数量限制（最多100） | 30 |
| --offset | 偏移量（用于分页） | 0 |
| --type | 搜索类型 | 1 |

**搜索类型说明：**
- `1` - 歌曲（默认）
- `10` - 专辑
- `100` - 歌手
- `1000` - 歌单

#### 示例

##### 1. 基本搜索

```bash
uv run python cli.py search "周杰伦"
```

##### 2. 限制返回数量

```bash
uv run python cli.py search "周杰伦" --limit 10
```

##### 3. 人类可读输出

```bash
uv run python cli.py --output human search "周杰伦" --limit 5
```

**输出示例：**
```
✓ 搜索完成
==================================================
result:
  songs:
    [0]: {
      name: 晴天
      artists: 周杰伦
      id: 186016
    }
    [1]: {
      name: 稻香
      artists: 周杰伦
      id: 185668
    }
  total: 5
  returned: 5
==================================================
```

##### 4. 搜索专辑

```bash
uv run python cli.py search "周杰伦" --type 10 --limit 5
```

---

### playlist - 获取歌单详情

获取歌单的详细信息和所有歌曲列表。

#### 语法

```bash
uv run python cli.py playlist <歌单ID或URL>
```

#### 参数

| 参数 | 说明 | 示例 |
|------|------|------|
| id | 歌单ID或URL | `123456` 或 `https://music.163.com/playlist?id=123456` |

#### 示例

```bash
# 使用歌单ID
uv run python cli.py playlist 123456

# 使用URL
uv run python cli.py playlist "https://music.163.com/playlist?id=123456"
```

---

### album - 获取专辑详情

获取专辑的详细信息和所有歌曲列表。

#### 语法

```bash
uv run python cli.py album <专辑ID或URL>
```

#### 参数

| 参数 | 说明 | 示例 |
|------|------|------|
| id | 专辑ID或URL | `123456` 或 `https://music.163.com/album?id=123456` |

#### 示例

```bash
# 使用专辑ID
uv run python cli.py album 16906

# 使用URL
uv run python cli.py album "https://music.163.com/album?id=16906"
```

---

### download - 下载音乐

下载音乐文件到本地，或获取下载信息。

#### 语法

```bash
uv run python cli.py download <歌曲ID或URL> [options]
```

#### 参数

| 参数 | 说明 | 示例 |
|------|------|------|
| id | 歌曲ID或URL | `185668` 或 `https://music.163.com/song?id=185668` |

#### 选项

| 选项 | 说明 | 默认值 | 可选值 |
|------|------|--------|--------|
| --quality | 音质等级 | lossless | standard, exhigh, lossless, hires, sky, jyeffect, jymaster, dolby |
| --format | 返回格式 | file | file（下载文件）, json（仅返回信息） |

#### 示例

##### 1. 下载文件（默认）

```bash
uv run python cli.py download 185668
```

**返回：**
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

##### 2. 仅获取下载信息（不下载文件）

```bash
uv run python cli.py download 185668 --format json
```

**返回：**
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
      "album": "魔杰座",
      "quality": "lossless",
      "url": "https://music.126.net/...",
      "file_size": 19398656
    }
  },
  "message": "获取下载信息成功"
}
```

##### 3. 指定音质下载

```bash
uv run python cli.py download 185668 --quality hires
```

##### 4. 批量下载（Shell脚本）

```bash
#!/bin/bash
# 批量下载歌曲
for id in 185668 186016 186017; do
    uv run python cli.py download $id --quality lossless
done
```

---

## 🎛️ 全局选项

这些选项可以用于任何命令：

| 选项 | 说明 | 示例 |
|------|------|------|
| `--output FORMAT` | 输出格式：json（默认）或 human | `--output human` |
| `--cookie FILE` | 指定Cookie文件路径 | `--cookie /path/to/cookie.txt` |
| `--verbose` | 输出详细日志到stderr | `--verbose` |
| `--quiet` | 静默模式，不输出日志 | `--quiet` |

### 使用示例

```bash
# 人类可读输出
uv run python cli.py --output human health

# 使用自定义Cookie文件
uv run python cli.py --cookie /custom/path/cookie.txt song 185668

# 详细日志模式
uv run python cli.py --verbose search "周杰伦"

# 静默模式
uv run python cli.py --quiet download 185668
```

---

## 📤 输出格式

### JSON格式（默认）

适用于程序解析和自动化脚本。

```bash
uv run python cli.py song 185668
```

**输出：**
```json
{
  "success": true,
  "code": 0,
  "data": { ... },
  "message": "操作成功"
}
```

**字段说明：**
- `success`: 操作是否成功
- `code`: 状态码（0表示成功）
- `data`: 响应数据
- `message`: 操作消息

### 人类可读格式

适用于调试和人工查看。

```bash
uv run python cli.py --output human song 185668
```

**输出：**
```
✓ 获取歌曲URL成功
==================================================
data:
  id: 185668
  url: https://music.126.net/...
  level: lossless
  size: 19398656
==================================================
```

---

## 🔢 退出码说明

CLI使用标准化退出码，便于脚本判断执行结果：

| 退出码 | 含义 | 说明 |
|--------|------|------|
| 0 | 成功 | 操作正常完成 |
| 1 | 业务错误 | 歌曲不存在、版权限制等 |
| 2 | 参数错误 | 缺少必需参数、参数格式错误 |
| 3 | 系统错误 | 网络错误、文件读写错误 |
| 4 | 认证错误 | Cookie无效、Cookie过期 |
| 130 | 用户中断 | Ctrl+C |

### 使用示例

```bash
#!/bin/bash
# 根据退出码判断结果
uv run python cli.py song 185668
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "操作成功"
elif [ $exit_code -eq 1 ]; then
    echo "业务错误：歌曲可能不存在"
elif [ $exit_code -eq 4 ]; then
    echo "认证错误：请检查Cookie"
else
    echo "其他错误：退出码 $exit_code"
fi
```

---

## 🤖 自动化调用示例

### Shell脚本

```bash
#!/bin/bash
# 批量下载歌曲

SONG_IDS=(185668 186016 186017)

for id in "${SONG_IDS[@]}"; do
    echo "正在处理歌曲ID: $id"

    # 调用CLI
    result=$(uv run python cli.py download "$id" --quality lossless)

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

### Python脚本

```python
#!/usr/bin/env python3
import subprocess
import json

def download_song(song_id, quality='lossless'):
    """调用CLI下载歌曲"""
    cmd = ['uv', 'run', 'python', 'cli.py', 'download', song_id, '--quality', quality]

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

# 使用示例
song_info = download_song('185668')
if song_info:
    print(f"下载成功: {song_info['filename']}")
```

### AI Agent调用

```python
# AI Agent通过工具调用
tools = [
    {
        "name": "netease_music_search",
        "description": "搜索网易云音乐",
        "function": lambda keyword: subprocess.run(
            ['uv', 'run', 'python', 'cli.py', 'search', keyword, '--limit', '10'],
            capture_output=True,
            text=True
        ).stdout
    },
    {
        "name": "netease_music_download",
        "description": "下载网易云音乐",
        "function": lambda song_id: subprocess.run(
            ['uv', 'run', 'python', 'cli.py', 'download', song_id, '--quality', 'lossless'],
            capture_output=True,
            text=True
        ).stdout
    }
]

# AI调用示例
result = tools[0]['function']('周杰伦 稻香')
data = json.loads(result)
print(json.dumps(data, indent=2, ensure_ascii=False))
```

---

## ❓ 常见问题

### 1. Cookie无效怎么办？

**错误信息：**
```json
{
  "success": false,
  "code": 4,
  "error": {
    "type": "AuthenticationError",
    "message": "Cookie无效或已过期"
  }
}
```

**解决方法：**
```bash
# 使用二维码登录重新获取Cookie
uv run python qr_login.py

# 或者指定自定义Cookie文件
uv run python cli.py --cookie /path/to/your/cookie.txt song 185668
```

### 2. 歌曲无法下载？

**错误信息：**
```json
{
  "success": false,
  "code": 1,
  "error": {
    "type": "DownloadNotAllowedError",
    "message": "无法下载，可能原因：版权限制或音质不支持"
  }
}
```

**解决方法：**
- 尝试降低音质（如从 `hires` 改为 `lossless`）
- 确认账号是否为黑胶会员
- 检查歌曲是否有版权限制

```bash
# 尝试标准音质
uv run python cli.py download 185668 --quality standard
```

### 3. 如何批量下载歌单？

```bash
#!/bin/bash
# 1. 获取歌单详情
playlist_result=$(uv run python cli.py playlist 123456)

# 2. 提取歌曲ID（需要jq工具）
song_ids=$(echo "$playlist_result" | jq -r '.data.playlist.tracks[].id')

# 3. 逐个下载
for id in $song_ids; do
    echo "下载歌曲ID: $id"
    uv run python cli.py download $id --quality lossless
    sleep 1  # 避免请求过快
done
```

### 4. JSON输出太长怎么处理？

```bash
# 使用jq过滤需要的字段
uv run python cli.py song 185668 | jq '.data | {name, url, size}'

# 美化输出
uv run python cli.py song 185668 | jq '.'
```

### 5. 如何在Python中集成？

```python
import subprocess
import json

def call_cli(command):
    """调用CLI命令"""
    cmd = ['uv', 'run', 'python', 'cli.py'] + command
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)

# 使用示例
data = call_cli(['song', '185668', '--level', 'hires'])
print(data['data']['url'])
```

### 6. 支持哪些音质？

| 音质 | 代码 | 说明 |
|------|------|------|
| 标准音质 | standard | 128kbps |
| 极高音质 | exhigh | 320kbps |
| 无损音质 | lossless | FLAC格式 |
| Hi-Res | hires | 24bit/96kHz |
| 沉浸环绕声 | sky | VIP专属 |
| 高清环绕声 | jyeffect | VIP专属 |
| 超清母带 | jymaster | SVIP专属 |
| 杜比全景声 | dolby | SVIP专属 |

---

## 📞 获取帮助

### 查看命令帮助

```bash
# 查看所有命令
uv run python cli.py --help

# 查看特定命令帮助
uv run python cli.py song --help
uv run python cli.py download --help
```

### 问题反馈

如果遇到问题，请：
1. 查看 [常见问题](#常见问题)
2. 检查退出码和错误信息
3. 在GitHub提交Issue

---

## 📄 许可证

MIT License - 详见 [LICENSE](./LICENSE)

---

**最后更新**: 2026-03-31
**版本**: 2.0.0
