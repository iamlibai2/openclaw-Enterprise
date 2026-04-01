"""
OpenClaw Gateway WebSocket 客户端

通过 WebSocket 协议与 OpenClaw Gateway 通信，实现远程配置管理。
"""
import json
import asyncio
import uuid
from typing import Any, Dict, Optional
import websockets


# WebSocket 协议版本
PROTOCOL_VERSION = 3


class GatewayError(Exception):
    """Gateway 错误"""
    def __init__(self, code: str, message: str, details: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")


class GatewayClient:
    """
    OpenClaw Gateway WebSocket 客户端

    使用方法:
        client = GatewayClient("ws://127.0.0.1:4444")
        await client.connect()

        # 获取配置
        result = await client.call("config.get")
        config = result["config"]

        # 创建 Agent
        result = await client.call("agents.create", {"name": "neo", "model": {"primary": "gpt-4"}})
    """

    def __init__(self, gateway_url: str = "ws://127.0.0.1:4444", auth_token: Optional[str] = None):
        """
        初始化客户端

        Args:
            gateway_url: Gateway WebSocket 地址
            auth_token: 认证 Token（可选，本地连接可能不需要）
        """
        self.gateway_url = gateway_url
        self.auth_token = auth_token
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.request_id = 0
        self.pending: Dict[str, asyncio.Future] = {}
        self.connected = False
        self._receive_task: Optional[asyncio.Task] = None

        # 连接信息
        self.conn_id: Optional[str] = None
        self.server_version: Optional[str] = None
        self.features: Dict = {}

    async def connect(self) -> Dict:
        """
        建立 WebSocket 连接并完成握手

        Returns:
            hello-ok 响应数据
        """
        if self.connected:
            return {"connId": self.conn_id}

        self.ws = await websockets.connect(
            self.gateway_url,
            max_size=10 * 1024 * 1024,  # 10MB
            ping_interval=30,
            ping_timeout=10,
            additional_headers={"Origin": self.gateway_url}
        )

        # 启动接收任务
        self._receive_task = asyncio.create_task(self._receive_loop())

        # 发送 connect 握手
        self.request_id += 1
        connect_params = {
            "client": {
                "id": "openclaw-control-ui",
                "displayName": "Admin UI",
                "platform": "node",
                "mode": "ui",
                "version": "1.0.0"
            },
            "role": "operator",
            "scopes": [
                "operator.read",
                "operator.write",
                "operator.admin",
                "operator.approvals",
                "operator.pairing"
            ],
            "minProtocol": PROTOCOL_VERSION,
            "maxProtocol": PROTOCOL_VERSION
        }

        # 如果有 token，添加认证
        if self.auth_token:
            connect_params["auth"] = {"token": self.auth_token}

        request = {
            "type": "req",
            "id": str(self.request_id),
            "method": "connect",
            "params": connect_params
        }

        await self.ws.send(json.dumps(request))

        # 等待响应
        response = await self._wait_response(str(self.request_id), timeout=30)

        if not response.get("ok"):
            error = response.get("error", {})
            raise GatewayError(
                error.get("code", "CONNECT_FAILED"),
                error.get("message", "连接失败"),
                error.get("details")
            )

        # 保存连接信息
        payload = response.get("payload", {})
        self.conn_id = payload.get("server", {}).get("connId")
        self.server_version = payload.get("server", {}).get("version")
        self.features = payload.get("features", {})
        self.connected = True

        return payload

    async def close(self):
        """关闭连接"""
        self.connected = False
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        if self.ws:
            await self.ws.close()
            self.ws = None

    async def call(self, method: str, params: Optional[Dict] = None) -> Dict:
        """
        调用 Gateway 方法

        Args:
            method: 方法名，如 "config.get", "agents.list"
            params: 方法参数

        Returns:
            响应 payload

        Raises:
            GatewayError: Gateway 返回错误
        """
        if not self.connected:
            await self.connect()

        self.request_id += 1
        req_id = str(self.request_id)

        request = {
            "type": "req",
            "id": req_id,
            "method": method,
            "params": params or {}
        }

        await self.ws.send(json.dumps(request))
        response = await self._wait_response(req_id)

        if not response.get("ok"):
            error = response.get("error", {})
            raise GatewayError(
                error.get("code", "CALL_FAILED"),
                error.get("message", f"{method} 调用失败"),
                error.get("details")
            )

        return response.get("payload", {})

    async def _wait_response(self, req_id: str, timeout: float = 60) -> Dict:
        """等待特定请求的响应"""
        future = asyncio.get_event_loop().create_future()
        self.pending[req_id] = future

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self.pending.pop(req_id, None)
            raise GatewayError("TIMEOUT", f"请求超时: {req_id}")
        finally:
            self.pending.pop(req_id, None)

    async def _receive_loop(self):
        """接收消息循环"""
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    pass
        except websockets.ConnectionClosed:
            self.connected = False
            # 取消所有等待中的请求
            for future in self.pending.values():
                if not future.done():
                    future.set_exception(GatewayError("CONNECTION_CLOSED", "连接已关闭"))
            self.pending.clear()

    async def _handle_message(self, data: Dict):
        """处理接收到的消息"""
        msg_type = data.get("type")

        if msg_type == "res":
            # 响应消息
            req_id = data.get("id")
            if req_id in self.pending:
                future = self.pending[req_id]
                if not future.done():
                    future.set_result(data)

        elif msg_type == "event":
            # 事件消息，暂时忽略
            pass

    # ============ 便捷方法 ============

    async def config_get(self) -> Dict:
        """获取配置"""
        return await self.call("config.get")

    async def config_patch(self, raw: str, base_hash: str) -> Dict:
        """
        部分更新配置

        Args:
            raw: JSON5 格式的配置片段
            base_hash: 配置基础 hash（用于乐观锁）
        """
        return await self.call("config.patch", {"raw": raw, "baseHash": base_hash})

    async def config_apply(self, raw: str, base_hash: str) -> Dict:
        """
        应用完整配置

        Args:
            raw: JSON5 格式的完整配置
            base_hash: 配置基础 hash
        """
        return await self.call("config.apply", {"raw": raw, "baseHash": base_hash})

    async def config_schema(self) -> Dict:
        """获取配置 Schema"""
        return await self.call("config.schema")

    async def agents_list(self) -> list:
        """获取 Agent 列表"""
        result = await self.call("agents.list")
        return result.get("agents", [])

    async def agents_create(self, name: str, model: Optional[Dict] = None,
                           workspace: Optional[str] = None) -> Dict:
        """创建 Agent"""
        params = {"name": name}
        if model:
            params["model"] = model
        if workspace:
            params["workspace"] = workspace
        return await self.call("agents.create", params)

    async def agents_update(self, agent_id: str, updates: Dict) -> Dict:
        """更新 Agent"""
        params = {"agentId": agent_id, **updates}
        return await self.call("agents.update", params)

    async def agents_delete(self, agent_id: str, delete_files: bool = True) -> Dict:
        """删除 Agent"""
        return await self.call("agents.delete", {
            "agentId": agent_id,
            "deleteFiles": delete_files
        })

    async def agents_files_list(self, agent_id: str) -> Dict:
        """获取 Agent 工作区文件列表"""
        return await self.call("agents.files.list", {"agentId": agent_id})

    async def agents_files_get(self, agent_id: str, name: str) -> Dict:
        """获取 Agent 工作区文件内容"""
        return await self.call("agents.files.get", {"agentId": agent_id, "name": name})

    async def agents_files_set(self, agent_id: str, name: str, content: str) -> Dict:
        """设置 Agent 工作区文件内容"""
        return await self.call("agents.files.set", {
            "agentId": agent_id,
            "name": name,
            "content": content
        })

    async def models_list(self) -> list:
        """获取模型列表"""
        result = await self.call("models.list")
        return result.get("models", [])


# 全局客户端实例（延迟初始化）
_global_client: Optional[GatewayClient] = None


async def get_client() -> GatewayClient:
    """获取全局客户端实例"""
    global _global_client
    if _global_client is None or not _global_client.connected:
        from settings import settings
        _global_client = GatewayClient(
            gateway_url=settings.GATEWAY_URL,
            auth_token=settings.GATEWAY_AUTH_TOKEN
        )
        await _global_client.connect()
    return _global_client