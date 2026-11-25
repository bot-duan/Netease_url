# CLAUDE.md

本项目提供网易云音乐搜索、歌曲详情与歌词、歌单和专辑解析，以及音频下载。终端交互使用 Rich 逐步问答。

## 开发命令

```bash
uv sync --locked
uv run --locked python -m pytest -q
uv run python cli.py                       # 逐步问答
uv run python cli.py health                # 本地 CLI 健康检查
uv run python main.py                      # HTTP 服务，默认端口 5023
NETEASE_HOST=127.0.0.1 uv run python main.py
uv run python qr_login.py login
```

本地配置使用 `NETEASE_*` 环境变量，见 [README 的服务配置](README.md#服务配置)。Docker Compose 使用 `.env` 和挂载的 `cookie.txt`，启动方式见 [使用文档](使用文档.md#-docker部署)。服务日志输出到控制台，日志级别由 `NETEASE_LOG_LEVEL` 控制。

## 模块与调用关系

| 模块 | 职责 |
|---|---|
| `cli.py`、`cli/commands.py` | 子命令解析、JSON 输出和退出码 |
| `cli_interactive.py` | Rich 问答、翻页、按编号选歌、下载进度和失败重试 |
| `music_service.py`、`config.py` | CLI 和 HTTP 共享的业务逻辑、参数校验、配置与音质选项 |
| `music_api.py` | 上游接口请求、eapi 参数加密和响应解析 |
| `music_downloader.py` | 流式下载、完整性校验、缓存和音频标签 |
| `cookie_manager.py`、`qr_login.py` | 本地 Cookie 读写和扫码登录 |
| `main.py`、`templates/index.html` | Flask 路由与网页 |
| `download_jobs.py`、`api_client.py` | HTTP 后台任务和 Python 客户端 |

普通 CLI 和交互 CLI 都直接调用本地业务层。HTTP 保留 `/Song_V1`、`/Search`、`/Playlist`、`/Album` 和 `/Download` 兼容路由。更改下载行为时，注意 HTTP 的 `format=json` 会下载文件，CLI 的旧版 `--format json` 仅查询信息。两端统一使用 `info` 表示只查询。

下载器先写临时文件，通过大小检查后写标签并发布正式文件。复用缓存时会校验文件记录和哈希。文件身份由歌曲 ID、上游返回的实际音质和格式决定。后台任务状态只保存在单个 HTTP 服务进程中。

测试在 `tests/` 中，使用模拟上游响应和临时目录，无需真实 Cookie。
