# OpenClaw Gateway WebSocket 协议

## 协议概述

OpenClaw Gateway 使用自定义的 WebSocket 协议进行通信。协议版本由 OpenClaw 内部定义，客户端必须使用正确的协议版本才能建立连接。

**当前协议版本**: `3`

## 协议版本

| 版本 | 说明 |
|------|------|
| `1` | 旧版本，已不支持 |
| `2` | 中间版本 |
| `3` | 当前版本（必须使用） |

**错误示例**:
```
错误: protocol mismatch
原因: PROTOCOL_VERSION = 1
解决: 更新为 PROTOCOL_VERSION = 3
```

## 连接参数

### 完整连接参数示例

```json
{
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
  "minProtocol": 3,
  "maxProtocol": 3
}
```

### client.id（客户端标识）

**必须是以下允许列表中的值之一**:

| client.id | 说明 |
|-----------|------|
| `cli` | 命令行客户端 |
| `webchat` | Web 聊天客户端 |
| `test` | 测试客户端 |
| `fingerprint` | 指纹识别客户端 |
| `webchat-ui` | Web 聊天 UI |
| `openclaw-control-ui` | Admin UI（推荐使用） |
| `gateway-client` | Gateway 客户端 |
| `openclaw-macos` | macOS 客户端 |
| `openclaw-ios` | iOS 客户端 |
| `openclaw-android` | Android 客户端 |
| `node-host` | Node 主机 |
| `openclaw-probe` | 探测客户端 |

**错误示例**:
```
错误: invalid connect params: client.id must be equal to constant
原因: 使用了 "webui"、"control-ui" 等未授权的 ID
解决: 使用 "openclaw-control-ui" 或 "gateway-client"
```

### client.mode（客户端模式）

**必须是以下允许列表中的值之一**:

| client.mode | 说明 |
|-------------|------|
| `node` | 节点模式 |
| `cli` | 命令行模式 |
| `ui` | UI 模式（推荐用于 Admin UI） |
| `webchat` | Web 聊天模式 |
| `test` | 测试模式 |
| `backend` | 后端模式 |
| `probe` | 探测模式 |

### role（角色）

| role | 说明 |
|------|------|
| `operator` | 操作员（推荐用于 Admin UI） |

### scopes（权限范围）

连接时必须声明需要的权限：

| scope | 说明 |
|-------|------|
| `operator.read` | 读权限 |
| `operator.write` | 写权限 |
| `operator.admin` | 管理权限 |
| `operator.approvals` | 批准权限 |
| `operator.pairing` | 配对权限 |

**错误示例**:
```
错误: missing scope: operator.read
原因: 连接成功但没有声明 operator 权限
解决: 在连接参数中添加 scopes 数组
```

## 连接流程

### 1. 建立 WebSocket 连接

```python
ws = await websockets.connect(
    gateway_url,
    max_size=10 * 1024 * 1024,  # 10MB
    ping_interval=30,
    ping_timeout=10,
    additional_headers={"Origin": gateway_url}  # 重要：设置 Origin header
)
```

**注意**: 必须设置 `Origin` header，否则会报 `origin not allowed` 错误。

### 2. 发送 connect 握手

```json
{
  "type": "req",
  "id": "1",
  "method": "connect",
  "params": {
    "client": {...},
    "role": "operator",
    "scopes": [...],
    "minProtocol": 3,
    "maxProtocol": 3
  }
}
```

### 3. 等待 hello-ok 响应

```json
{
  "type": "res",
  "id": "1",
  "ok": true,
  "payload": {
    "server": {
      "connId": "...",
      "version": "..."
    },
    "features": {...}
  }
}
```

## Gateway 方法调用

### 消息格式

**请求**:
```json
{
  "type": "req",
  "id": "2",
  "method": "config.get",
  "params": {}
}
```

**响应**:
```json
{
  "type": "res",
  "id": "2",
  "ok": true,
  "payload": {
    "config": {...}
  }
}
```

**错误响应**:
```json
{
  "type": "res",
  "id": "2",
  "ok": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "权限不足"
  }
}
```

### 可用方法列表

#### 配置管理

| 方法 | 说明 |
|------|------|
| `config.get` | 获取配置（含 hash 用于乐观锁） |
| `config.patch` | 部分更新配置（自动重启） |
| `config.apply` | 应用完整配置 |
| `config.schema` | 获取配置 Schema |

#### Agent 管理

| 方法 | 说明 |
|------|------|
| `agents.list` | 列出所有 Agent |
| `agents.create` | 创建 Agent |
| `agents.update` | 更新 Agent |
| `agents.delete` | 删除 Agent |

#### 文件操作

| 方法 | 说明 |
|------|------|
| `agents.files.list` | Agent 工作区文件列表 |
| `agents.files.get` | 读取文件内容 |
| `agents.files.set` | 写入文件内容 |

#### 模型管理

| 方法 | 说明 |
|------|------|
| `models.list` | 获取模型列表 |

## Gateway 配置

### 控制台 UI 认证配置

如果使用 `openclaw-control-ui` 作为 client.id，需要在 Gateway 配置中添加：

```json
{
  "gateway": {
    "controlUi": {
      "allowInsecureAuth": true
    }
  }
}
```

**错误示例**:
```
错误: control ui requires device identity
原因: openclaw-control-ui 客户端需要设备身份验证
解决: 在 Gateway 配置中添加 controlUi.allowInsecureAuth
```

### Token 认证

如果 Gateway 启用了 Token 认证：

```json
{
  "gateway": {
    "auth": {
      "mode": "token",
      "token": "your-token-here"
    }
  }
}
```

连接时需要在 params 中添加 auth：

```json
{
  "auth": {
    "token": "your-token-here"
  }
}
```

## Gateway 默认端口

| 环境 | 端口 | 说明 |
|------|------|------|
| 默认 | `18789` | 实际 Gateway 监听端口 |
| 文档示例 | `4444` | 文档中的示例端口（可能不准确） |

**注意**: 代码默认连接 `ws://127.0.0.1:4444`，实际 Gateway 可能监听在 `18789` 端口。需要根据实际配置调整。

## 源码定义位置

| 内容 | 位置 |
|------|------|
| 协议概述 | `docs/gateway/protocol.md` |
| 配置参考 | `docs/gateway/configuration-reference.md` |
| Schema 定义 | `src/gateway/protocol/schema/primitives.ts` |
| TypeScript 类型 | `dist/plugin-sdk/src/gateway/protocol/schema/primitives.d.ts` |
| 服务端方法实现 | `src/gateway/server-methods/*.ts` |

## Python 客户端实现

OpenClaw **没有官方 Python SDK**，需要自己实现 WebSocket 客户端：

```python
import websockets
import json

class GatewayClient:
    async def connect(self):
        self.ws = await websockets.connect(
            self.gateway_url,
            additional_headers={"Origin": self.gateway_url}
        )

        # 发送握手
        request = {
            "type": "req",
            "id": "1",
            "method": "connect",
            "params": {
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
                    "operator.admin"
                ],
                "minProtocol": 3,
                "maxProtocol": 3
            }
        }
        await self.ws.send(json.dumps(request))

    async def call(self, method: str, params: dict = None):
        request = {
            "type": "req",
            "id": str(self.request_id),
            "method": method,
            "params": params or {}
        }
        await self.ws.send(json.dumps(request))
        response = await self._wait_response()
        return response.get("payload", {})
```

## 错误排查指南

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `protocol mismatch` | 协议版本错误 | 使用 `PROTOCOL_VERSION = 3` |
| `invalid client.id` | client.id 不在允许列表 | 使用 `openclaw-control-ui` |
| `missing scope` | 未声明权限 | 添加 scopes 数组 |
| `origin not allowed` | WebSocket 缺少 Origin header | 设置 `additional_headers={"Origin": url}` |
| `control ui requires device identity` | 需要设备验证 | 配置 `controlUi.allowInsecureAuth: true` |
| `connection timeout` | 端口错误 | 检查 Gateway 实际监听端口 |

## 参考链接

- OpenClaw Gateway 源码: `src/gateway/`
- 协议类型定义: `src/gateway/protocol/`
- 本项目 WebSocket 客户端: `backend/gateway_client.py`