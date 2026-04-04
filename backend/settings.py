"""
OpenClaw Admin UI 配置

管理应用配置，包括 Gateway 连接参数、加密密钥等。
"""
import os
import json
from pathlib import Path


# 加载 .env 文件（如果存在）
_env_file = Path(__file__).parent / '.env'
if _env_file.exists():
    with open(_env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # 只设置未定义的环境变量
                if key not in os.environ:
                    os.environ[key] = value


def _get_device_auth_token() -> str:
    """从 OpenClaw 设备身份文件获取认证令牌"""
    try:
        device_auth_path = Path.home() / '.openclaw' / 'identity' / 'device-auth.json'
        if device_auth_path.exists():
            with open(device_auth_path, 'r') as f:
                data = json.load(f)
                tokens = data.get('tokens', {})
                operator_token = tokens.get('operator', {})
                return operator_token.get('token', '')
    except Exception:
        pass
    return ''


def _get_gateway_token() -> str:
    """从 OpenClaw 配置文件获取 Gateway 认证令牌"""
    # 优先从环境变量获取
    env_token = os.environ.get('GATEWAY_AUTH_TOKEN')
    if env_token:
        return env_token

    # 从 openclaw.json 获取
    try:
        config_path = Path.home() / '.openclaw' / 'openclaw.json'
        if config_path.exists():
            with open(config_path, 'r') as f:
                data = json.load(f)
                gateway = data.get('gateway', {})
                auth = gateway.get('auth', {})
                token = auth.get('token', '')
                if token:
                    return token
    except Exception:
        pass

    # 最后尝试 device auth
    return _get_device_auth_token()


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

    # OpenClaw Workspace 目录（用于访问 Agent 生成的文件）
    OPENCLAW_WORKSPACE_DIR: str = os.environ.get(
        'OPENCLAW_WORKSPACE_DIR',
        str(Path.home() / '.openclaw' / 'workspace')
    )

    # 运行模式
    DEBUG: bool = os.environ.get('DEBUG', 'false').lower() == 'true'

    # Gateway 配置（从环境变量获取默认值，实际使用时从数据库读取）
    GATEWAY_URL: str = os.environ.get('GATEWAY_URL', 'ws://127.0.0.1:18789')

    # Gateway 认证令牌：优先使用环境变量，否则从配置文件读取
    GATEWAY_AUTH_TOKEN: str = _get_gateway_token()

    # 当前使用的 Gateway ID（None 表示使用默认 Gateway）
    current_gateway_id: int = None


# 全局配置实例
settings = Settings()