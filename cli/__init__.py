"""CLI命令行接口模块

提供网易云音乐API的命令行接口，专为自动化脚本和AI调用优化。
"""

from .errors import ExitCode, CLIException
from .formatters import JSONFormatter, HumanFormatter
from .commands import CLICommand

__all__ = [
    'ExitCode',
    'CLIException',
    'JSONFormatter',
    'HumanFormatter',
    'CLICommand',
]
