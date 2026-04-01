"""
OpenClaw Admin UI 配置

管理应用配置，包括 Gateway 连接参数等。
"""
import os
from pathlib import Path


class Settings:
    """应用配置"""

    # 数据库配置
    DATABASE_PATH: str = os.environ.get(
        'DATABASE_PATH',
        str(Path(__file__).parent / 'data' / 'admin.db')
    )

    # JWT 配置
    JWT_SECRET: str = os.environ.get('JWT_SECRET', 'openclaw-admin-secret-key-change-in-production')
    JWT_EXPIRE_HOURS: int = int(os.environ.get('JWT_EXPIRE_HOURS', '24'))

    # OpenClaw 配置文件路径（用于 fallback，当 WebSocket 不可用时）
    OPENCLAW_CONFIG_PATH: str = os.environ.get(
        'OPENCLAW_CONFIG_PATH',
        str(Path.home() / '.openclaw' / 'openclaw.json')
    )

    # 运行模式
    DEBUG: bool = os.environ.get('DEBUG', 'false').lower() == 'true'

    # Gateway 配置（从环境变量获取默认值，实际使用时从数据库读取）
    GATEWAY_URL: str = os.environ.get('GATEWAY_URL', 'ws://127.0.0.1:4444')
    GATEWAY_AUTH_TOKEN: str = os.environ.get('GATEWAY_AUTH_TOKEN', '')

    # 当前使用的 Gateway ID（None 表示使用默认 Gateway）
    current_gateway_id: int = None


# 全局配置实例
settings = Settings()