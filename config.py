"""Shared configuration. Environment defaults are evaluated when loading, not importing."""
import os
from dataclasses import dataclass, fields

QUALITY_NAMES = {
    'standard': '标准音质', 'exhigh': '极高音质', 'lossless': '无损音质',
    'hires': 'Hi-Res音质', 'sky': '沉浸环绕声', 'jyeffect': '高清环绕声',
    'jymaster': '超清母带', 'dolby': '杜比全景声',
}

@dataclass
class APIConfig:
    host: str = '0.0.0.0'
    port: int = 5023
    debug: bool = False
    downloads_dir: str = 'downloads'
    cookie_file: str = 'cookie.txt'
    max_file_size: int = 500 * 1024 * 1024
    request_timeout: int = 30
    download_timeout: int = 600
    max_concurrent: int = 3
    log_level: str = 'INFO'
    cors_origins: str = '*'
    default_quality: str = 'lossless'

    @classmethod
    def from_env(cls):
        values = {}
        for item in fields(cls):
            value = os.environ.get('NETEASE_' + item.name.upper())
            if value is not None:
                values[item.name] = (value.lower() in ('1', 'true', 'yes') if item.type is bool
                                     else item.type(value))
        config = cls(**values)
        if config.default_quality not in QUALITY_NAMES:
            raise ValueError('无效的 NETEASE_DEFAULT_QUALITY')
        if min(config.port, config.request_timeout, config.download_timeout,
               config.max_concurrent, config.max_file_size) <= 0:
            raise ValueError('端口、超时、并发和文件大小限制必须为正数')
        return config
