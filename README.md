# 网易云音乐无损解析

<div align="center">

![GitHub stars](https://img.shields.io/github/stars/Suxiaoqinx/Netease_url?style=flat-square)
![GitHub forks](https://img.shields.io/github/forks/Suxiaoqinx/Netease_url?style=flat-square)
![GitHub issues](https://img.shields.io/github/issues/Suxiaoqinx/Netease_url?style=flat-square)
![GitHub license](https://img.shields.io/github/license/Suxiaoqinx/Netease_url?style=flat-square)

**功能强大的网易云音乐解析工具**

支持歌曲搜索 | 单曲解析 | 歌单解析 | 专辑解析 | 音乐下载

[在线体验](https://wyapi.toubiec.cn) • [使用文档](./使用文档.md) • [问题反馈](https://github.com/Suxiaoqinx/Netease_url/issues)

</div>

---

> **⚠️ 重要声明**  
> 本项目采用 MIT 许可证开源。根据 MIT 许可证的条款，任何个人或组织均可自由使用、修改和分发本项目的源代码，包括用于商业项目。

**注意**：本项目旨在为开源社区做贡献，我们鼓励用户：
- 在遵守开源精神的前提下使用和分享代码
- 如有改进，欢迎贡献回本项目
- 在商业使用中，请考虑对开源项目的支持和回馈

虽然 MIT 许可证允许商业使用，但我们希望用户能尊重开源精神，合理使用本项目。

## ✨ 功能特性

### 🎵 核心功能
- **🔍 歌曲搜索**：支持关键词搜索网易云音乐库中的歌曲
- **🎧 单曲解析**：解析单首歌曲的详细信息和下载链接
- **📋 歌单解析**：批量解析歌单中的所有歌曲信息
- **💿 专辑解析**：批量解析专辑中的所有歌曲信息
- **⬇️ 音乐下载**：支持多种音质的音乐文件下载

### 🎼 音质支持
- `standard`：标准音质 (128kbps)
- `exhigh`：极高音质 (320kbps)
- `lossless`：无损音质 (FLAC)
- `hires`：Hi-Res音质 (24bit/96kHz)
- `jyeffect`：高清环绕声
- `sky`：沉浸环绕声
- `jymaster`：超清母带

### 🌐 使用方式
- **Web界面**：直观友好的网页操作界面
- **RESTful API**：完整的API接口支持
- **CLI命令行**：专为自动化脚本和AI调用优化的命令行接口（新增！）
- **批量处理**：支持歌单和专辑的批量解析
- **多格式支持**：支持ID和链接多种输入格式

---

## 🚀 快速开始

### 环境要求
- Python 3.10+
- 网易云音乐黑胶会员账号
- uv（推荐的Python包管理器）

### 安装步骤

#### 1. 克隆项目
```bash
git clone https://github.com/bot-duan/Netease_url.git
cd Netease_url
```

#### 2. 安装uv（如果未安装）
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用Homebrew
brew install uv

# 验证安装
uv --version
```

#### 3. 安装项目依赖
```bash
# uv会自动创建虚拟环境并安装所有依赖
uv sync
```

#### 4. 配置Cookie
在 `cookie.txt` 文件中填入黑胶会员账号的Cookie：

> 💡 **获取Cookie方法**：登录网易云音乐网页版 → F12开发者工具 → Network标签页 → 复制任意请求的Cookie值

#### 5. 启动服务
```bash
# 使用uv运行
uv run python main.py

# 或使用启动脚本
chmod +x run.sh
./run.sh
```

服务将运行在 `http://localhost:5023`

#### 6. 访问界面
打开浏览器访问：`http://localhost:5023`

### 🐳 Docker部署

```bash
# 使用Docker Compose
docker-compose up -d

# 或使用Docker
docker build -t netease-music-api .
docker run -d -p 5000:5000 netease-music-api
```

---

## 📖 使用指南

### Web界面使用

#### 🔍 歌曲搜索
1. 选择功能：**歌曲搜索**
2. 输入关键词（歌曲名、歌手名等）
3. 点击**搜索**按钮
4. 在搜索结果中点击**解析**或**下载**按钮

#### 🎧 单曲解析
1. 选择功能：**单曲解析**
2. 输入歌曲ID或网易云音乐链接
   - 支持格式：`1234567890` 或 `https://music.163.com/song?id=1234567890`
3. 点击**解析**按钮查看歌曲信息

#### 📋 歌单解析
1. 选择功能：**歌单解析**
2. 输入歌单ID或网易云音乐歌单链接
   - 支持格式：`1234567890` 或 `https://music.163.com/playlist?id=1234567890`
3. 点击**解析**按钮查看歌单中所有歌曲
4. 点击单首歌曲的**解析**或**下载**按钮

#### 💿 专辑解析
1. 选择功能：**专辑解析**
2. 输入专辑ID或网易云音乐专辑链接
   - 支持格式：`1234567890` 或 `https://music.163.com/album?id=1234567890`
3. 点击**解析**按钮查看专辑中所有歌曲
4. 点击单首歌曲的**解析**或**下载**按钮

#### ⬇️ 音乐下载
1. 选择功能：**音乐下载**
2. 输入歌曲ID或链接
3. 选择音质（标准/极高/无损/Hi-Res等）
4. 点击**下载**按钮

### CLI命令行使用（新功能！）

专为**自动化脚本**和**AI调用**优化的命令行接口，默认输出JSON格式，支持标准化退出码。

#### 基本语法

```bash
uv run python cli.py <command> [arguments] [options]
```

#### 可用命令

| 命令 | 功能 | 示例 |
|------|------|------|
| `health` | 健康检查 | `uv run python cli.py health` |
| `song` | 获取歌曲信息 | `uv run python cli.py song 185668` |
| `search` | 搜索音乐 | `uv run python cli.py search "周杰伦"` |
| `playlist` | 获取歌单详情 | `uv run python cli.py playlist 123456` |
| `album` | 获取专辑详情 | `uv run python cli.py album 123456` |
| `download` | 下载音乐 | `uv run python cli.py download 185668` |

#### 全局选项

```bash
--output FORMAT    输出格式：json（默认）或 human
--cookie FILE      指定Cookie文件路径
--verbose          输出详细日志到stderr
--quiet            静默模式，不输出日志
```

#### 常用示例

##### 1. 健康检查
```bash
# 默认JSON输出
uv run python cli.py health

# 人类可读输出
uv run python cli.py --output human health
```

##### 2. 获取歌曲信息
```bash
# 获取歌曲URL（默认无损音质）
uv run python cli.py song 185668

# 获取歌曲详情
uv run python cli.py song 185668 --type name

# 获取歌词
uv run python cli.py song 185668 --type lyric

# 获取完整信息
uv run python cli.py song 185668 --type json

# 指定音质
uv run python cli.py song 185668 --level hires

# 支持URL输入
uv run python cli.py song "https://music.163.com/song?id=185668"
```

##### 3. 搜索音乐
```bash
# 搜索歌曲（默认返回30条）
uv run python cli.py search "周杰伦 稻香"

# 限制返回数量
uv run python cli.py search "周杰伦" --limit 10

# 人类可读输出
uv run python cli.py --output human search "周杰伦"
```

##### 4. 下载音乐
```bash
# 下载到本地（默认无损音质）
uv run python cli.py download 185668

# 仅获取下载信息（不下载文件）
uv run python cli.py download 185668 --format json

# 指定音质下载
uv run python cli.py download 185668 --quality hires
```

#### 退出码说明

```bash
0    # 成功
1    # 业务错误（歌曲不存在、版权限制）
2    # 参数错误
3    # 系统错误（网络、文件）
4    # 认证错误（Cookie无效）
130  # 用户中断（Ctrl+C）
```

#### 自动化调用示例

##### Shell脚本
```bash
#!/bin/bash
# 批量下载歌曲

SONG_IDS=(185668 186016 186017)

for id in "${SONG_IDS[@]}"; do
    result=$(uv run python cli.py download "$id" --quality lossless)
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

##### Python脚本
```python
#!/usr/bin/env python3
import subprocess
import json

def download_song(song_id, quality='lossless'):
    """调用CLI下载歌曲"""
    cmd = ['uv', 'run', 'python', 'cli.py', 'download', song_id, '--quality', quality]

    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)

    if data['success']:
        return data['data']
    else:
        print(f"错误: {data['error']['message']}")
        return None

# 使用
song_info = download_song('185668')
if song_info:
    print(f"下载成功: {song_info['filename']}")
```

### 支持的链接格式

```
# 歌曲链接
https://music.163.com/song?id=1234567890
https://music.163.com/#/song?id=1234567890

# 歌单链接
https://music.163.com/playlist?id=1234567890
https://music.163.com/#/playlist?id=1234567890

# 专辑链接
https://music.163.com/album?id=1234567890
https://music.163.com/#/album?id=1234567890

# 直接使用ID
1234567890
```

## 🔌 API接口文档

### 基础信息
- **Base URL**: `http://localhost:5000`
- **请求方式**: GET / POST
- **响应格式**: JSON

### 接口列表

#### 1. 健康检查
```http
GET /health
```
**响应示例**:
```json
{
  "status": "ok",
  "message": "Service is running"
}
```

#### 2. 歌曲搜索
```http
POST /search
Content-Type: application/json

{
  "keywords": "周杰伦 稻香",
  "limit": 10
}
```
**响应示例**:
```json
{
  "code": 200,
  "result": {
    "songs": [
      {
        "id": 185668,
        "name": "稻香",
        "artists": ["周杰伦"],
        "album": "魔杰座",
        "duration": 223000
      }
    ]
  }
}
```

#### 3. 单曲解析
```http
POST /song
Content-Type: application/json

{
  "id": "185668"
}
```

#### 4. 歌单解析
```http
POST /playlist
Content-Type: application/json

{
  "id": "123456789"
}
```

#### 5. 专辑解析
```http
POST /album
Content-Type: application/json

{
  "id": "123456789"
}
```

#### 6. 音乐下载
```http
POST /download
Content-Type: application/json

{
  "id": "185668",
  "quality": "lossless"
}
```
**响应**: 直接返回音频文件流

---

## 音质参数说明（仅限单曲解析）

- `standard`：标准音质
- `exhigh`：极高音质
- `lossless`：无损音质
- `hires`：Hi-Res音质
- `jyeffect`：高清环绕声
- `sky`：沉浸环绕声
- `jymaster`：超清母带

> 黑胶VIP音质：standard, exhigh, lossless, hires, jyeffect  
> 黑胶SVIP音质：sky, jymaster

---

## Docker 一键部署

1. **修改参数**

   - 如需修改端口，请编辑 `.env` 或 `docker-compose.yml` 文件中的 `ports` 配置，例如：

     ```yaml
     ports:
       - "8080:5000"
     ```

2. **启动服务**

   ```bash
   docker-compose up -d
   ```

---

## 在线演示

[在线解析](https://wyapi.toubiec.cn/)

---

## 注意事项

- 必须使用黑胶会员账号的 Cookie 才能解析高音质资源。
- Cookie 格式请严格按照 `cookie.txt` 示例填写。

---

## 致谢

- [Ravizhan](https://github.com/ravizhan)

---

## 反馈与交流

- 在 Github [Issues](https://github.com/Suxiaoqinx/Netease_url/issues) 提交反馈
- 或访问 [我的博客](https://www.toubiec.cn)

---

欢迎 Star、Fork 和 PR！



