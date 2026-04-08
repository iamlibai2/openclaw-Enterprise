# SSE 事件推送系统设计

## 文档信息

| 项目 | 内容 |
|------|------|
| 文档编号 | DES-076 |
| 创建日期 | 2026-04-04 |
| 创建人 | Claude |
| 状态 | 待评审 |

## 1. 需求背景

### 1.1 现有问题

定时任务执行后，Admin UI 无法实时获取 Agent 执行结果：

```
当前流程：
1. 后端调用 chat.send 发送任务
2. Agent 执行（可能需要几秒到几分钟）
3. 结果无法回传给 Admin UI

问题：
- 用户无法及时看到任务执行结果
- 需要手动刷新或轮询检查
```

### 1.2 需求目标

- **实时性**：任务完成后立即通知前端
- **可配置**：推送间隔、开关等可配置
- **复用性**：支持未来更多事件类型
- **企业级**：稳定、可靠、可扩展

## 2. 技术选型

### 2.1 方案对比

| 方案 | 实时性 | 资源消耗 | 复杂度 | 复用性 |
|------|--------|---------|--------|--------|
| HTTP 轮询 | 低（延迟） | 高（频繁请求） | 低 | 低 |
| WebSocket | 高 | 中（长连接） | 高 | 高 |
| **SSE** | 高 | 低（单向推送） | 中 | 高 |

### 2.2 选择 SSE 的理由

1. **单向推送**：后端推送到前端，不需要双向通信
2. **自动重连**：浏览器原生支持断线重连
3. **HTTP 协议**：无需额外端口，穿透防火墙
4. **资源友好**：空闲时几乎零开销
5. **复用性强**：可扩展支持多种事件类型

### 2.3 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         Admin UI 后端                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  Gateway    │    │   Event     │    │   SSE       │        │
│  │  Listener   │───►│   Router    │───►│   Endpoint  │        │
│  │  (监听器)   │    │  (事件路由)  │    │  (推送端点)  │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│        │                  │                   ▲               │
│        ▼                  ▼                   │               │
│  ┌─────────────┐    ┌─────────────┐          │               │
│  │  Gateway    │    │  Database   │          │               │
│  │  WebSocket  │    │  (存储结果)  │          │               │
│  └─────────────┘    └─────────────┘          │               │
└─────────────────────────────────────────────│─────────────────┘
                                              │
                                              │ SSE 连接
                                              │
┌─────────────────────────────────────────────│─────────────────┐
│                         前端浏览器          ▼               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              EventSource (SSE 客户端)                │    │
│  │  - 自动重连                                          │    │
│  │  - 事件监听                                          │    │
│  │  - 通知显示                                          │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## 3. 模块设计

### 3.1 目录结构

```
backend/
├── events/                     # 事件模块（新增）
│   ├── __init__.py            # 模块入口
│   ├── listener.py            # Gateway 监听器
│   ├── router.py              # 事件路由器
│   ├── sse_manager.py         # SSE 连接管理
│   └── event_types.py         # 事件类型定义
├── gateway_client.py          # Gateway 客户端（修改）
└── app.py                     # Flask 应用（修改）

frontend/
├── src/
│   ├── utils/
│   │   └── sse-client.ts      # SSE 客户端（新增）
│   └── stores/
│       └── events.ts          # 事件状态管理（新增）
```

### 3.2 核心组件

#### 3.2.1 Gateway Listener（Gateway 监听器）

**职责**：建立到 Gateway 的持久 WebSocket 连接，监听事件

```python
# events/listener.py

class GatewayListener:
    """Gateway 事件监听器"""

    def __init__(self):
        self.client: Optional[GatewayClient] = None
        self.running = False
        self.event_callback: Callable[[dict], None] = None

    async def start(self):
        """启动监听"""
        self.client = GatewayClient(gateway_url, auth_token)
        await self.client.connect()
        self.running = True
        await self._listen_loop()

    async def _listen_loop(self):
        """监听循环"""
        while self.running:
            message = await self.client.receive()
            if message.get("type") == "event":
                await self._handle_event(message)

    async def _handle_event(self, event: dict):
        """处理事件"""
        event_name = event.get("event")
        payload = event.get("payload", {})

        # 调用事件路由
        if self.event_callback:
            await self.event_callback(event_name, payload)
```

#### 3.2.2 Event Router（事件路由器）

**职责**：根据事件类型路由到不同处理器

```python
# events/router.py

class EventRouter:
    """事件路由器"""

    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = {}

    def register(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    async def route(self, event_type: str, payload: dict):
        """路由事件"""
        handlers = self.handlers.get(event_type, [])
        for handler in handlers:
            await handler(payload)


# 内置处理器
async def handle_task_result(payload: dict):
    """处理任务结果事件"""
    session_key = payload.get("sessionKey", "")

    # 检查是否是后台任务
    if ":backend:task-" in session_key:
        # 更新数据库
        update_task_execution(session_key, payload)

        # 通过 SSE 推送给前端
        await sse_manager.broadcast({
            "type": "task_result",
            "data": {
                "sessionKey": session_key,
                "status": "completed" if payload.get("state") == "final" else "running"
            }
        })
```

#### 3.2.3 SSE Manager（SSE 连接管理器）

**职责**：管理 SSE 连接、推送消息

```python
# events/sse_manager.py

import queue
from typing import Dict, Queue
from flask import Response

class SSEManager:
    """SSE 连接管理器"""

    def __init__(self):
        self.connections: Dict[str, Queue] = {}  # user_id -> queue
        self._lock = threading.Lock()

    def connect(self, user_id: int) -> Queue:
        """建立 SSE 连接"""
        q = queue.Queue()
        with self._lock:
            self.connections[user_id] = q
        return q

    def disconnect(self, user_id: int):
        """断开 SSE 连接"""
        with self._lock:
            self.connections.pop(user_id, None)

    async def send(self, user_id: int, message: dict):
        """发送消息给特定用户"""
        q = self.connections.get(user_id)
        if q:
            q.put(message)

    async def broadcast(self, message: dict, role: str = None):
        """广播消息给所有连接（可选：按角色过滤）"""
        with self._lock:
            for user_id, q in self.connections.items():
                # 可以根据角色过滤
                q.put(message)

    def stream(self, user_id: int):
        """生成 SSE 流"""
        q = self.connect(user_id)
        try:
            while True:
                try:
                    message = q.get(timeout=30)  # 30秒超时
                    yield f"data: {json.dumps(message)}\n\n"
                except queue.Empty:
                    # 发送心跳
                    yield ": heartbeat\n\n"
        except GeneratorExit:
            self.disconnect(user_id)


sse_manager = SSEManager()
```

#### 3.2.4 SSE Endpoint（SSE 端点）

```python
# app.py

from events.sse_manager import sse_manager

@app.route('/api/events/stream')
@require_auth
def sse_stream():
    """SSE 事件流端点"""
    user_id = get_current_user()['id']

    def generate():
        for data in sse_manager.stream(user_id):
            yield data

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'  # 禁用 Nginx 缓冲
        }
    )
```

### 3.3 事件类型定义

```python
# events/event_types.py

class EventType:
    """事件类型定义"""

    # 任务相关
    TASK_RESULT = "task_result"          # 任务执行结果
    TASK_STARTED = "task_started"        # 任务开始执行
    TASK_FAILED = "task_failed"          # 任务执行失败

    # 系统相关
    SYSTEM_NOTICE = "system_notice"      # 系统通知
    SYSTEM_ALERT = "system_alert"        # 系统告警

    # 未来扩展
    # AGENT_STATUS = "agent_status"      # Agent 状态变化
    # GATEWAY_STATUS = "gateway_status"  # Gateway 状态变化


class EventPayload:
    """事件载荷格式"""

    @staticmethod
    def task_result(session_key: str, status: str, result: dict = None) -> dict:
        return {
            "type": EventType.TASK_RESULT,
            "timestamp": datetime.now().isoformat(),
            "data": {
                "sessionKey": session_key,
                "status": status,  # running/completed/failed
                "result": result
            }
        }
```

## 4. 数据库设计

### 4.1 系统配置表

```sql
CREATE TABLE IF NOT EXISTS system_settings (
    key VARCHAR(50) PRIMARY KEY,
    value TEXT NOT NULL,
    value_type VARCHAR(20) DEFAULT 'string',
    description VARCHAR(200),
    category VARCHAR(50),
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER
);

-- 初始配置
INSERT INTO system_settings (key, value, value_type, description, category) VALUES
('sse_enabled', 'true', 'boolean', '启用 SSE 事件推送', 'events'),
('sse_heartbeat_interval', '30', 'number', 'SSE 心跳间隔(秒)', 'events'),
('task_notification_enabled', 'true', 'boolean', '启用任务完成通知', 'notification');
```

### 4.2 任务执行表（已有，补充字段）

```sql
-- task_executions 表补充
ALTER TABLE task_executions ADD COLUMN session_key VARCHAR(100);
ALTER TABLE task_executions ADD COLUMN notified BOOLEAN DEFAULT 0;
```

## 5. 前端实现

### 5.1 SSE 客户端

```typescript
// src/utils/sse-client.ts

export interface SSEEvent {
  type: string
  timestamp: string
  data: any
}

export class SSEClient {
  private eventSource: EventSource | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private listeners: Map<string, Set<(data: any) => void>> = new Map()

  constructor(url: string) {
    this.url = url
  }

  connect() {
    this.eventSource = new EventSource(this.url)

    this.eventSource.onopen = () => {
      console.log('[SSE] Connected')
      this.reconnectAttempts = 0
    }

    this.eventSource.onmessage = (event) => {
      try {
        const message: SSEEvent = JSON.parse(event.data)
        this.dispatch(message.type, message.data)
      } catch (e) {
        // 心跳消息，忽略
      }
    }

    this.eventSource.onerror = () => {
      console.error('[SSE] Connection error')
      this.reconnect()
    }
  }

  on(eventType: string, callback: (data: any) => void) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set())
    }
    this.listeners.get(eventType)!.add(callback)
  }

  off(eventType: string, callback: (data: any) => void) {
    this.listeners.get(eventType)?.delete(callback)
  }

  private dispatch(type: string, data: any) {
    const callbacks = this.listeners.get(type)
    callbacks?.forEach(cb => cb(data))
  }

  private reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[SSE] Max reconnect attempts reached')
      return
    }

    this.reconnectAttempts++
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000)

    setTimeout(() => {
      console.log(`[SSE] Reconnecting (attempt ${this.reconnectAttempts})...`)
      this.connect()
    }, delay)
  }

  disconnect() {
    this.eventSource?.close()
    this.eventSource = null
  }
}
```

### 5.2 使用示例

```typescript
// 在 App.vue 中

import { SSEClient } from '@/utils/sse-client'

const sseClient = new SSEClient('/api/events/stream')

// 监听任务结果
sseClient.on('task_result', (data) => {
  // 显示通知
  ElNotification({
    title: '任务完成',
    message: `任务 ${data.sessionKey} 已完成`,
    type: 'success'
  })

  // 更新通知中心
  store.fetchUnreadCount()
})

onMounted(() => {
  sseClient.connect()
})

onUnmounted(() => {
  sseClient.disconnect()
})
```

## 6. 配置管理

### 6.1 配置 API

```
GET  /api/settings              # 获取所有配置
GET  /api/settings/:key         # 获取单个配置
PUT  /api/settings/:key         # 更新配置（需 admin 权限）
```

### 6.2 配置界面

在"系统设置"中添加"事件推送"配置项：
- SSE 开关
- 心跳间隔
- 任务通知开关

## 7. 安全考虑

### 7.1 认证

- SSE 连接需要登录认证
- 使用 Cookie 或 Token 验证

### 7.2 权限

- 不同角色可能接收不同事件
- 敏感事件只推送给管理员

### 7.3 限流

- 单用户最多 1 个 SSE 连接
- 超时自动断开

## 8. 实现计划

| 阶段 | 任务 | 预估工时 |
|------|------|---------|
| **Phase 1** | 数据库配置表 + API | 1h |
| **Phase 2** | Gateway Listener | 2h |
| **Phase 3** | SSE Manager + Endpoint | 2h |
| **Phase 4** | 前端 SSE 客户端 | 1h |
| **Phase 5** | 集成测试 | 1h |
| **总计** | | **7h** |

## 9. 测试要点

1. **连接测试**：SSE 连接建立、断开、重连
2. **推送测试**：任务完成后前端收到通知
3. **并发测试**：多用户同时连接
4. **异常测试**：Gateway 断开后重连
5. **配置测试**：配置修改后生效

## 10. 后续扩展

### 10.1 可扩展事件类型

- Agent 状态变化
- Gateway 连接状态
- 系统告警
- 审批通知

### 10.2 可扩展功能

- 事件订阅（用户选择接收哪些事件）
- 事件历史记录
- 事件过滤规则