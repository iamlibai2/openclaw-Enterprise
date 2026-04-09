# Chat 功能架构设计

## 文档信息

| 项目 | 内容 |
|------|------|
| 文档编号 | DEV-Chat-Arch |
| 创建日期 | 2026-04-09 |
| 更新日期 | 2026-04-09 |
| 状态 | 已完成 |

## 1. 概述

本文档描述 OpenClaw Control UI 的 Chat 对话功能架构设计，包括前端与 Gateway 的通信机制、后端监听器的作用，以及架构演进历史。

## 2. 架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Chat 功能架构                                      │
└─────────────────────────────────────────────────────────────────────────────┘

                              用户
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          前端 (Vue)                                          │
│                                                                             │
│  Chat.vue / DiscordChat.vue / FeishuChat.vue                                │
│       │                                                                     │
│       ▼                                                                     │
│  gateway-ws.ts ────────► WebSocket 连接 ──────────────┐                     │
│  (createGatewayClient)                                 │                     │
│                                                        │                     │
│  功能：                                                │                     │
│  - 发送消息 (chat.send)                                │                     │
│  - 接收流式响应 (chat 事件)                            │                     │
│  - 订阅事件 (sessions.subscribe)                       │                     │
└────────────────────────────────────────────────────────│─────────────────────┘
                                                         │
                                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Gateway (OpenClaw 核心)                               │
│                                                                             │
│  - 路由消息到对应 Agent                                                      │
│  - 管理 Session 生命周期                                                    │
│  - 广播事件给所有订阅者                                                      │
│  - 调用 LLM 生成回复                                                        │
│                                                                             │
│  WebSocket 端口: ws://127.0.0.1:18789                                       │
└─────────────────────────────────────────────────────────────────────────────┘
         │                                    │
         │ 消息/响应                          │ 事件广播
         ▼                                    ▼
┌──────────────────────────┐    ┌─────────────────────────────────────────────┐
│       Agent 进程          │    │           后端监听器                        │
│                          │    │   (events/listener.py)                     │
│  - 处理对话              │    │                                             │
│  - 调用工具              │    │   GatewayListener                           │
│  - 生成回复              │    │   - WebSocket 连接 Gateway                  │
│                          │    │   - 监听所有事件                            │
└──────────────────────────┘    │   - 转发给 EventRouter                      │
                                │                                             │
                                │   EventRouter                               │
                                │   - 处理 chat 事件                          │
                                │   - 后台任务结果通知                        │
                                │   - 朋友圈触发判断                          │
                                └─────────────────────────────────────────────┘
```

## 3. 两条 WebSocket 连接

系统中有两条独立的 WebSocket 连接，用途不同：

| 连接 | 用途 | 代码位置 | 启动时机 |
|------|------|----------|----------|
| **前端 → Gateway** | 用户聊天、接收回复 | `frontend/src/utils/gateway-ws.ts` | 用户打开聊天页面 |
| **后端 → Gateway** | 监听事件、触发任务 | `backend/events/listener.py` | 后端服务启动 |

### 3.1 前端 WebSocket 连接

```typescript
// frontend/src/utils/gateway-ws.ts

export function createGatewayClient(options: {
  url: string,           // Gateway WebSocket 地址
  token: string,         // 认证 Token
  onEvent: Function,     // 事件回调
  onClose: Function      // 连接关闭回调
}) {
  // 建立 WebSocket 连接
  const ws = new WebSocket(url)

  // 发送认证
  ws.send(JSON.stringify({
    type: 'hello',
    auth: { token }
  }))

  // 监听事件
  ws.onmessage = (event) => {
    const frame = JSON.parse(event.data)
    if (frame.type === 'event') {
      onEvent(frame)
    }
  }
}
```

### 3.2 后端 WebSocket 连接

```python
# backend/events/listener.py

class GatewayListener:
    """Gateway 事件监听器 - 维护到 Gateway 的持久连接"""

    def __init__(self):
        self.ws = None
        self._event_callback = None

    def set_event_callback(self, callback: Callable):
        """设置事件回调函数"""
        self._event_callback = callback

    async def connect(self):
        """建立 WebSocket 连接"""
        self.ws = await websockets.connect(gateway_url)

        # 发送认证
        await self.ws.send(json.dumps({
            'type': 'hello',
            'auth': {'token': gateway_token}
        }))

    async def listen(self):
        """监听事件"""
        async for message in self.ws:
            data = json.loads(message)
            if data.get('type') == 'event':
                await self._event_callback(data)
```

## 4. 消息流程

### 4.1 用户发送消息

```
1. 用户输入 → 前端
2. 前端 → Gateway (chat.send 请求)
   {
     "type": "req",
     "id": "uuid",
     "method": "chat.send",
     "params": {
       "sessionKey": "agent:xiaomei:webchat:user123",
       "message": "你好",
       "deliver": false,
       "idempotencyKey": "run-id"
     }
   }
3. Gateway → Agent (调用 LLM)
4. Agent → Gateway (流式响应)
5. Gateway → 前端 (delta/final 事件)
6. Gateway → 后端监听器 (广播 chat 事件)
```

### 4.2 前端接收响应

```typescript
// Chat.vue
function onChatEvent(evt: GatewayEventFrame) {
  if (evt.event !== 'chat') return

  const payload = evt.payload

  switch (payload.state) {
    case 'delta':
      // 流式输出，实时更新
      chatStream.value = extractText(payload.message)
      break

    case 'final':
      // 完成，添加到消息列表
      chatMessages.value.push({
        role: 'assistant',
        content: extractText(payload.message)
      })
      chatStream.value = null
      break

    case 'error':
      // 错误处理
      lastError.value = payload.errorMessage
      break
  }
}
```

### 4.3 后端监听事件

```python
# events/router.py
async def _handle_chat_event(self, payload: dict):
    session_key = payload.get('sessionKey', '')
    state = payload.get('state', '')

    # 检查是否是后台任务
    if TASK_SESSION_PATTERN.match(session_key):
        await self._handle_backend_task(payload)
        return

    # 检查是否需要发朋友圈
    if state == 'final':
        await self._handle_moment_generation(payload)
```

## 5. Gateway API

### 5.1 请求方法

| 方法 | 说明 |
|------|------|
| `chat.send` | 发送消息到 Agent |
| `chat.abort` | 中止当前生成 |
| `sessions.list` | 获取会话列表 |
| `sessions.subscribe` | 订阅会话事件 |
| `sessions.create` | 创建新会话 |
| `artifacts.list` | 获取会话生成的文件 |

### 5.2 事件类型

| 事件 | state | 说明 |
|------|-------|------|
| `chat` | `delta` | 流式输出片段 |
| `chat` | `final` | 完成，最终消息 |
| `chat` | `aborted` | 被中止 |
| `chat` | `error` | 出错 |

## 6. Session Key 格式

Session Key 用于标识会话，格式如下：

```
agent:{agent_id}:{channel}:{user_id}

示例：
- agent:xiaomei:webchat:user123      # 网页聊天
- agent:xiaomei:feishu:user456        # 飞书聊天
- agent:aqiang:backend:task-{uuid}    # 后台任务
- agent:main:groupchat:group789       # 群聊
```

**解析 Session Key**：

```python
def extract_agent_id_from_session(session_key: str) -> Optional[str]:
    """从 session key 中提取 Agent ID"""
    parts = session_key.split(':')
    if len(parts) >= 2 and parts[0] == 'agent':
        return parts[1]
    return None
```

## 7. 架构演进历史

### 7.1 第一阶段：原始 Chat（2026-03 底 ~ 04 初）

```
┌──────────────────────────────────────────────────────────┐
│  前端 ──WebSocket──► Gateway ──► Agent                   │
│                                                          │
│  后端不参与聊天流程                                        │
└──────────────────────────────────────────────────────────┘
```

**特点**：
- 前端直连 Gateway
- 后端只提供 REST API（用户管理、配置等）
- 简单、高效

**局限**：
- 后端无法感知聊天事件
- 定时任务结果无法通知前端

### 7.2 第二阶段：添加后端监听器（2026-04-04 ~ 05）

**问题**：

```
定时任务执行后，Admin UI 无法实时获取 Agent 执行结果：

1. 后端调用 chat.send 发送任务
2. Agent 执行（可能需要几秒到几分钟）
3. 结果无法回传给 Admin UI ❌
```

**解决方案**：

```
┌──────────────────────────────────────────────────────────┐
│  后端添加:                                               │
│  - GatewayListener (监听器)                              │
│  - EventRouter (事件路由)                                │
│  - SSE Endpoint (推送给前端)                             │
└──────────────────────────────────────────────────────────┘
```

**用途**：
- 定时任务结果实时通知
- 后台任务状态更新

### 7.3 第三阶段：朋友圈功能（2026-04-09）

**复用后端监听器**：

```
后端监听 chat final 事件
    │
    ▼
LLM 判断是否值得发朋友圈
    │
    ▼
生成动态内容 + 配图
    │
    ▼
保存到数据库
```

## 8. 三种 Chat 页面对比

| 页面 | 用途 | 特点 |
|------|------|------|
| `Chat.vue` | 原始对话页面 | 选择 Agent → 选择 Session → 对话 |
| `DiscordChat.vue` | Discord 风格对话 | 左侧会话列表，右侧聊天区，支持群聊 |
| `FeishuChat.vue` | 飞书风格对话 | 类似 Discord，UI 风格不同 |

**核心代码一致**：三者都使用 `gateway-ws.ts` 建立 WebSocket 连接，消息处理逻辑相同。

## 9. 职责分离

| 组件 | 职责 |
|------|------|
| **前端** | 用户交互、消息展示、WebSocket 连接 |
| **Gateway** | 消息路由、Session 管理、事件广播 |
| **Agent** | 对话处理、工具调用、LLM 调用 |
| **后端监听器** | 事件监听、任务通知、朋友圈触发 |

**核心原则**：前端负责交互，Gateway 负责路由，Agent 负责生成，后端负责旁路监听。

## 10. 相关文档

- [SSE 事件推送系统设计](../03-详细设计/SSE事件推送系统设计.md)
- [OpenClaw WebSocket 协议](./OpenClaw-WebSocket协议.md)
- [Gateway 连接对比](./AdminUI与ControlUI的Gateway连接对比.md)