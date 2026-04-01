"""
Gateway 同步包装器

将异步的 WebSocket 调用包装为同步方法，供 Flask 使用。
支持多 Gateway 配置，从数据库读取 Gateway 信息。

注意：每次调用创建新连接，适合 Flask 同步上下文。
"""
import asyncio
from typing import Any, Dict, Optional
from gateway_client import GatewayClient, GatewayError
from settings import settings


def _run_with_client(coro_func, gateway_id: Optional[int] = None):
    """
    创建新连接并运行协程

    Args:
        coro_func: 接受 GatewayClient 参数的协程函数
        gateway_id: 可选的 Gateway ID
    """
    config = _get_gateway_config(gateway_id)

    async def run():
        client = GatewayClient(
            gateway_url=config['url'],
            auth_token=config['auth_token']
        )
        try:
            await client.connect()
            result = await coro_func(client)
            return result
        finally:
            await client.close()

    return asyncio.run(run())


def _get_gateway_config(gateway_id: Optional[int] = None) -> Dict:
    """从数据库获取 Gateway 配置"""
    from database import db

    if gateway_id is not None:
        # 获取指定的 Gateway
        gateway = db.fetch_one("SELECT * FROM gateways WHERE id = ?", (gateway_id,))
        if gateway:
            return {
                'id': gateway['id'],
                'name': gateway['name'],
                'url': gateway['url'],
                'auth_token': gateway['auth_token'] or ''
            }
        raise ValueError(f"Gateway ID {gateway_id} 不存在")

    # 使用当前设置的 Gateway ID 或默认 Gateway
    if settings.current_gateway_id is not None:
        gateway = db.fetch_one("SELECT * FROM gateways WHERE id = ?", (settings.current_gateway_id,))
        if gateway:
            return {
                'id': gateway['id'],
                'name': gateway['name'],
                'url': gateway['url'],
                'auth_token': gateway['auth_token'] or ''
            }

    # 获取默认 Gateway
    gateway = db.fetch_one("SELECT * FROM gateways WHERE is_default = 1")
    if gateway:
        return {
            'id': gateway['id'],
            'name': gateway['name'],
            'url': gateway['url'],
            'auth_token': gateway['auth_token'] or ''
        }

    # 没有配置的 Gateway，使用环境变量或默认值
    return {
        'id': None,
        'name': '环境变量配置',
        'url': settings.GATEWAY_URL,
        'auth_token': settings.GATEWAY_AUTH_TOKEN
    }


def set_current_gateway(gateway_id: int):
    """设置当前使用的 Gateway"""
    settings.current_gateway_id = gateway_id


class SyncGatewayClient:
    """
    同步 Gateway 客户端

    使用方法:
        client = get_sync_client()
        config = client.config_get()
        agents = client.agents_list()
    """

    def __init__(self, gateway_id: Optional[int] = None):
        self._gateway_id = gateway_id

    def call(self, method: str, params: Optional[Dict] = None) -> Dict:
        """
        调用 Gateway 方法

        Args:
            method: 方法名
            params: 方法参数

        Returns:
            响应 payload

        Raises:
            GatewayError: Gateway 返回错误
        """
        async def do_call(client):
            return await client.call(method, params)

        return _run_with_client(do_call, self._gateway_id)

    # ============ 配置管理 ============

    def config_get(self) -> Dict:
        """获取配置"""
        return self.call("config.get")

    def config_patch(self, raw: str, base_hash: str) -> Dict:
        """部分更新配置"""
        return self.call("config.patch", {"raw": raw, "baseHash": base_hash})

    def config_apply(self, raw: str, base_hash: str) -> Dict:
        """应用完整配置"""
        return self.call("config.apply", {"raw": raw, "baseHash": base_hash})

    def config_schema(self) -> Dict:
        """获取配置 Schema"""
        return self.call("config.schema")

    # ============ Agent 管理 ============

    def agents_list(self) -> list:
        """获取 Agent 列表"""
        result = self.call("agents.list")
        return result.get("agents", [])

    def agents_create(self, name: str, model: Optional[Dict] = None,
                     workspace: Optional[str] = None) -> Dict:
        """创建 Agent"""
        params = {"name": name}
        if model:
            params["model"] = model
        if workspace:
            params["workspace"] = workspace
        return self.call("agents.create", params)

    def agents_update(self, agent_id: str, updates: Dict) -> Dict:
        """更新 Agent"""
        params = {"agentId": agent_id, **updates}
        return self.call("agents.update", params)

    def agents_delete(self, agent_id: str, delete_files: bool = True) -> Dict:
        """删除 Agent"""
        return self.call("agents.delete", {
            "agentId": agent_id,
            "deleteFiles": delete_files
        })

    # ============ 文件管理 ============

    def agents_files_list(self, agent_id: str) -> Dict:
        """获取 Agent 工作区文件列表"""
        return self.call("agents.files.list", {"agentId": agent_id})

    def agents_files_get(self, agent_id: str, name: str) -> Dict:
        """获取 Agent 工作区文件内容"""
        return self.call("agents.files.get", {"agentId": agent_id, "name": name})

    def agents_files_set(self, agent_id: str, name: str, content: str) -> Dict:
        """设置 Agent 工作区文件内容"""
        return self.call("agents.files.set", {
            "agentId": agent_id,
            "name": name,
            "content": content
        })

    # ============ 模型管理 ============

    def models_list(self) -> list:
        """获取模型列表"""
        result = self.call("models.list")
        return result.get("models", [])


def get_sync_client(gateway_id: Optional[int] = None) -> SyncGatewayClient:
    """获取全局同步客户端实例"""
    if gateway_id is not None:
        # 指定了 gateway_id，创建新客户端
        return SyncGatewayClient(gateway_id=gateway_id)
    return SyncGatewayClient()


# ============ 便捷函数 ============

def sync_call(method: str, params: Optional[Dict] = None, gateway_id: Optional[int] = None) -> Dict:
    """
    同步调用 Gateway 方法

    这是使用 WebSocket 的最简单方式：
        result = sync_call("config.get")
        config = result["config"]
    """
    return get_sync_client(gateway_id).call(method, params)