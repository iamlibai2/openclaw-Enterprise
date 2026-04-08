"""
Gateway 同步包装器

每次请求创建新连接，支持自动重试。
"""
import asyncio
import concurrent.futures
import time
from typing import Any, Dict, Optional
from gateway_client import GatewayClient, GatewayError
from settings import settings

# 线程池执行器
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def _get_auth_token() -> str:
    """获取 Gateway 认证令牌"""
    # 优先使用设置中的令牌
    if settings.GATEWAY_AUTH_TOKEN:
        return settings.GATEWAY_AUTH_TOKEN
    return ''


def _execute_call(gateway_url: str, auth_token: str, method: str, params: Optional[Dict], max_retries: int = 3) -> Dict:
    """执行单次调用（带重试）"""
    last_error = None

    for attempt in range(max_retries):
        try:
            return asyncio.run(_do_call(gateway_url, auth_token, method, params))
        except (GatewayError, ConnectionError, OSError) as e:
            last_error = e
            error_str = str(e).lower()

            # 连接问题，等待重试
            if any(x in error_str for x in ['connection', 'closed', 'refused', 'reset', 'timeout']):
                if attempt < max_retries - 1:
                    wait_time = 0.5 * (attempt + 1)
                    time.sleep(wait_time)
                    continue
            raise

    raise last_error


async def _do_call(gateway_url: str, auth_token: str, method: str, params: Optional[Dict]) -> Dict:
    """执行单次 WebSocket 调用"""
    client = GatewayClient(gateway_url=gateway_url, auth_token=auth_token)
    try:
        await client.connect()
        result = await client.call(method, params)
        return result
    finally:
        try:
            await client.close()
        except Exception:
            pass


def _get_gateway_config(gateway_id: Optional[int] = None) -> Dict:
    """从数据库获取 Gateway 配置"""
    from database import db

    if gateway_id is not None:
        gateway = db.fetch_one("SELECT * FROM gateways WHERE id = ?", (gateway_id,))
        if gateway:
            return {
                'id': gateway['id'],
                'name': gateway['name'],
                'url': gateway['url'],
                'auth_token': gateway['auth_token'] or _get_auth_token()
            }
        raise ValueError(f"Gateway ID {gateway_id} 不存在")

    if settings.current_gateway_id is not None:
        gateway = db.fetch_one("SELECT * FROM gateways WHERE id = ?", (settings.current_gateway_id,))
        if gateway:
            return {
                'id': gateway['id'],
                'name': gateway['name'],
                'url': gateway['url'],
                'auth_token': gateway['auth_token'] or _get_auth_token()
            }

    gateway = db.fetch_one("SELECT * FROM gateways WHERE is_default = 1")
    if gateway:
        return {
            'id': gateway['id'],
            'name': gateway['name'],
            'url': gateway['url'],
            'auth_token': gateway['auth_token'] or _get_auth_token()
        }

    return {
        'id': None,
        'name': '环境变量配置',
        'url': settings.GATEWAY_URL,
        'auth_token': _get_auth_token()
    }


def sync_call(method: str, params: Optional[Dict] = None, gateway_id: Optional[int] = None) -> Dict:
    """同步调用 Gateway 方法"""
    config = _get_gateway_config(gateway_id)

    def run_in_thread():
        return _execute_call(config['url'], config['auth_token'], method, params)

    future = _executor.submit(run_in_thread)
    return future.result(timeout=60)


class SyncGatewayClient:
    """同步 Gateway 客户端"""

    def __init__(self, gateway_id: Optional[int] = None):
        self._gateway_id = gateway_id

    def call(self, method: str, params: Optional[Dict] = None) -> Dict:
        return sync_call(method, params, self._gateway_id)

    def config_get(self) -> Dict:
        return self.call("config.get")

    def config_patch(self, raw: str, base_hash: str) -> Dict:
        return self.call("config.patch", {"raw": raw, "baseHash": base_hash})

    def agents_list(self) -> list:
        result = self.call("agents.list")
        return result.get("agents", [])

    def models_list(self) -> list:
        result = self.call("models.list")
        return result.get("models", [])


def get_sync_client(gateway_id: Optional[int] = None) -> SyncGatewayClient:
    return SyncGatewayClient(gateway_id=gateway_id)


def set_current_gateway(gateway_id: int):
    """切换当前使用的 Gateway"""
    settings.current_gateway_id = gateway_id

    # 重置全局客户端，强制下次调用时重新连接
    from gateway_client import _global_client
    import asyncio

    global_client = _global_client
    if global_client and global_client.connected:
        try:
            asyncio.run(global_client.close())
        except Exception:
            pass

    # 清除全局客户端引用
    import gateway_client
    gateway_client._global_client = None