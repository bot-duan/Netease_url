"""CLI输出格式化模块

提供JSON和人类可读两种输出格式化器。
"""

from typing import Any, Dict


class JSONFormatter:
    """JSON输出格式化器

    为自动化脚本和AI调用优化，输出结构化JSON数据。
    """

    @staticmethod
    def success(data: Any, message: str = "操作成功") -> Dict[str, Any]:
        """
        格式化成功响应

        Args:
            data: 响应数据
            message: 成功消息

        Returns:
            格式化的JSON字典
        """
        return {
            "success": True,
            "code": 0,
            "data": data,
            "message": message
        }

    @staticmethod
    def error(code: int, error_type: str, message: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        格式化错误响应

        Args:
            code: 错误码
            error_type: 错误类型
            message: 错误消息
            details: 错误详情

        Returns:
            格式化的错误JSON字典
        """
        return {
            "success": False,
            "code": code,
            "error": {
                "type": error_type,
                "message": message,
                "details": details or {}
            }
        }


class HumanFormatter:
    """人类可读输出格式化器

    用于调试和人工查看，提供友好的文本输出。
    """

    @staticmethod
    def format_success(data: Dict[str, Any], message: str = "操作成功") -> str:
        """
        格式化成功响应为人类可读格式

        Args:
            data: 响应数据
            message: 成功消息

        Returns:
            格式化的文本字符串
        """
        lines = [
            f"✓ {message}",
            "=" * 50
        ]

        # 递归格式化数据
        formatted = HumanFormatter._format_data(data, indent=0)
        lines.extend(formatted)

        lines.append("=" * 50)
        return "\n".join(lines)

    @staticmethod
    def format_error(error_type: str, message: str, details: Dict[str, Any] = None) -> str:
        """
        格式化错误响应为人类可读格式

        Args:
            error_type: 错误类型
            message: 错误消息
            details: 错误详情

        Returns:
            格式化的错误文本字符串
        """
        lines = [
            f"✗ 错误: {message}",
            f"  类型: {error_type}",
            "=" * 50
        ]

        if details:
            lines.append("  详细信息:")
            for key, value in details.items():
                lines.append(f"    {key}: {value}")

        lines.append("=" * 50)
        return "\n".join(lines)

    @staticmethod
    def _format_data(data: Any, indent: int = 0) -> list:
        """
        递归格式化数据

        Args:
            data: 要格式化的数据
            indent: 缩进层级

        Returns:
            格式化后的行列表
        """
        lines = []
        prefix = "  " * indent

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}{key}:")
                    lines.extend(HumanFormatter._format_data(value, indent + 1))
                else:
                    lines.append(f"{prefix}{key}: {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}[{i}]:")
                    lines.extend(HumanFormatter._format_data(item, indent + 1))
                else:
                    lines.append(f"{prefix}[{i}]: {item}")
        else:
            lines.append(f"{prefix}{data}")

        return lines
