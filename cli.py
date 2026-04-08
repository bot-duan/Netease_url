#!/usr/bin/env python3
"""网易云音乐CLI - 自动化/AI调用优化版

提供命令行接口调用网易云音乐API服务，专为自动化脚本和AI调用优化。

使用示例:
    python cli.py health
    python cli.py song 185668 --level hires
    python cli.py search "周杰伦" --limit 10
    python cli.py download 185668 --quality lossless
"""

import argparse
import sys
import json

from cli import CLICommand, CLIException, JSONFormatter, HumanFormatter, ExitCode


def main():
    """CLI入口函数"""
    parser = argparse.ArgumentParser(
        description='网易云音乐CLI - 自动化/AI调用优化版',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # 交互模式标志
    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='启动交互模式'
    )

    # 全局选项
    parser.add_argument(
        '--cookie',
        help='Cookie文件路径或字符串'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='输出详细日志到stderr'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='静默模式，不输出日志'
    )
    parser.add_argument(
        '--output',
        choices=['json', 'human'],
        default='json',
        help='输出格式（默认json，适用于自动化/AI调用）'
    )

    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # health命令
    health_parser = subparsers.add_parser('health', help='健康检查')

    # song命令
    song_parser = subparsers.add_parser('song', help='获取歌曲信息')
    song_parser.add_argument(
        'id',
        help='歌曲ID或URL（支持网易云音乐分享链接）'
    )
    song_parser.add_argument(
        '--level',
        default='lossless',
        choices=['standard', 'exhigh', 'lossless', 'hires', 'sky', 'jyeffect', 'jymaster', 'dolby'],
        help='音质等级'
    )
    song_parser.add_argument(
        '--type',
        default='url',
        choices=['url', 'name', 'lyric', 'json'],
        help='信息类型：url-歌曲URL, name-歌曲详情, lyric-歌词, json-完整信息'
    )

    # search命令
    search_parser = subparsers.add_parser('search', help='搜索音乐')
    search_parser.add_argument(
        'keyword',
        help='搜索关键词'
    )
    search_parser.add_argument(
        '--limit',
        type=int,
        default=30,
        help='返回数量限制（最多100）'
    )
    search_parser.add_argument(
        '--offset',
        type=int,
        default=0,
        help='偏移量（用于分页）'
    )
    search_parser.add_argument(
        '--type',
        dest='search_type',
        default='1',
        choices=['1', '10', '100', '1000'],
        help='搜索类型：1-歌曲, 10-专辑, 100-歌手, 1000-歌单'
    )

    # playlist命令
    playlist_parser = subparsers.add_parser('playlist', help='获取歌单详情')
    playlist_parser.add_argument(
        'id',
        help='歌单ID或URL（支持网易云音乐分享链接）'
    )

    # album命令
    album_parser = subparsers.add_parser('album', help='获取专辑详情')
    album_parser.add_argument(
        'id',
        help='专辑ID或URL（支持网易云音乐分享链接）'
    )

    # download命令
    download_parser = subparsers.add_parser('download', help='下载音乐')
    download_parser.add_argument(
        'id',
        help='歌曲ID或URL（支持网易云音乐分享链接）'
    )
    download_parser.add_argument(
        '--quality',
        default='lossless',
        choices=['standard', 'exhigh', 'lossless', 'hires', 'sky', 'jyeffect', 'jymaster', 'dolby'],
        help='音质等级'
    )
    download_parser.add_argument(
        '--format',
        dest='return_format',
        default='file',
        choices=['file', 'json'],
        help='file-下载文件到本地, json-仅返回下载信息'
    )

    # 解析参数
    args = parser.parse_args()

    # 判断是否进入交互模式
    # 条件：显式指定-i/--interactive，或者没有提供任何参数
    if args.interactive or len(sys.argv) == 1:
        # Textual TUI交互模式
        try:
            from cli_tui import MusicTuiApp
            app = MusicTuiApp()
            app.run()
            sys.exit(ExitCode.SUCCESS)
        except ImportError as e:
            error_result = JSONFormatter.error(
                ExitCode.SYSTEM_ERROR,
                "ImportError",
                f"无法导入TUI模块: {e}。请确保已安装textual库: uv sync"
            )
            print(json.dumps(error_result, ensure_ascii=False, indent=2))
            sys.exit(ExitCode.SYSTEM_ERROR)
        except Exception as e:
            error_result = JSONFormatter.error(
                ExitCode.SYSTEM_ERROR,
                "TUIError",
                f"TUI启动失败: {e}"
            )
            print(json.dumps(error_result, ensure_ascii=False, indent=2))
            sys.exit(ExitCode.SYSTEM_ERROR)

    # AI模式：如果没有指定命令，显示帮助
    if not args.command:
        parser.print_help()
        sys.exit(ExitCode.PARAMETER_ERROR)

    # 创建CLI实例
    try:
        cli = CLICommand(
            cookie_file=args.cookie,
            verbose=args.verbose,
            quiet=args.quiet
        )
    except Exception as e:
        error_result = JSONFormatter.error(
            ExitCode.SYSTEM_ERROR,
            "InitializationError",
            f"CLI初始化失败: {e}"
        )
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(ExitCode.SYSTEM_ERROR)

    # 执行命令
    try:
        result = None

        if args.command == 'health':
            result = cli.health()

        elif args.command == 'song':
            result = cli.song(args.id, level=args.level, info_type=args.type)

        elif args.command == 'search':
            result = cli.search(args.keyword, limit=args.limit, offset=args.offset, search_type=args.search_type)

        elif args.command == 'playlist':
            result = cli.playlist(args.id)

        elif args.command == 'album':
            result = cli.album(args.id)

        elif args.command == 'download':
            result = cli.download(args.id, quality=args.quality, return_format=args.return_format)

        else:
            error_result = JSONFormatter.error(
                ExitCode.PARAMETER_ERROR,
                "UnknownCommandError",
                f"未知命令: {args.command}"
            )
            print(json.dumps(error_result, ensure_ascii=False, indent=2))
            sys.exit(ExitCode.PARAMETER_ERROR)

        # 输出结果
        if result is not None:
            if args.output == 'json':
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                # 人类可读格式
                if result.get('success'):
                    print(HumanFormatter.format_success(result.get('data', {}), result.get('message', '操作成功')))
                else:
                    error = result.get('error', {})
                    print(HumanFormatter.format_error(
                        error.get('type', 'UnknownError'),
                        error.get('message', '未知错误'),
                        error.get('details')
                    ))

        sys.exit(ExitCode.SUCCESS)

    except CLIException as e:
        # CLI异常处理
        error_result = JSONFormatter.error(e.code, e.error_type, e.message, e.details)
        print(json.dumps(error_result, ensure_ascii=False, indent=2))

        if not args.quiet:
            cli.logger.error(f"{e.error_type}: {e.message}")

        sys.exit(e.code)

    except KeyboardInterrupt:
        if not args.quiet:
            cli.logger.warning("用户中断操作")
        sys.exit(ExitCode.USER_INTERRUPT)

    except Exception as e:
        # 未预期异常处理
        error_result = JSONFormatter.error(
            ExitCode.SYSTEM_ERROR,
            "UnexpectedError",
            str(e)
        )
        print(json.dumps(error_result, ensure_ascii=False, indent=2))

        if not args.quiet:
            cli.logger.exception("未预期的错误")

        sys.exit(ExitCode.SYSTEM_ERROR)


if __name__ == '__main__':
    main()
