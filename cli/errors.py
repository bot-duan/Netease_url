"""CLI错误处理模块

定义CLI使用的退出码和异常类。
"""


class ExitCode:
    """标准化退出码

    遵循POSIX标准，0表示成功，非0表示各种错误情况。
    """

    SUCCESS = 0          # 成功
    BUSINESS_ERROR = 1   # 业务错误（歌曲不存在、版权限制）
    PARAMETER_ERROR = 2  # 参数错误
    SYSTEM_ERROR = 3     # 系统错误（网络、文件）
    AUTH_ERROR = 4       # 认证错误（Cookie无效）
    USER_INTERRUPT = 130 # 用户中断（Ctrl+C）


class CLIException(Exception):
    """CLI异常类

    用于在CLI执行过程中抛出结构化错误，
    包含错误类型、消息和详细信息。
    """

    def __init__(self, code: int, error_type: str, message: str, details: dict = None):
        """
        初始化CLI异常

        Args:
            code: 退出码（参考ExitCode类）
            error_type: 错误类型标识符
            message: 人类可读的错误消息
            details: 额外的错误详情（字典形式）
        """
        self.code = code
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self):
        """将异常转换为字典格式"""
        return {
            "code": self.code,
            "type": self.error_type,
            "message": self.message,
            "details": self.details
        }
