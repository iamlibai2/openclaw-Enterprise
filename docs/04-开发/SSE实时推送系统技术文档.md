# SSE 实时推送系统技术文档

> 文档版本：1.0
> 更新时间：2026-04-05

---

## 一、系统概述

### 1.1 功能定位

SSE (Server-Sent Events) 实时推送系统用于将后端事件实时推送到前端，主要用于：

- 定时任务执行结果通知
- 系统告警推送
- Gateway 状态变更通知

### 1.2 技术选型

| 技术选型 | 原因 |
|----------|------|
| SSE (Server-Sent Events) | 单向推送、实现简单、自动重连、HTTP 协议 |
| EventSource API | 浏览器原生支持，无需额外库 |
| Flask Response Stream | Python 生成器实现 SSE 流 |

**为什么不用 WebSocket？**

SSE 是单向推送，定时任务通知场景只需服务器→客户端，不需要客户端→服务器。SSE 更轻量，自动重连更简单。

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SSE 实时推送系统架构                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│  │ 定时任务    │    │   Gateway   │    │    Agent    │            │
│  │  executor   │───>│  WebSocket  │───>│   执行任务  │            │
│  └─────────────┘    └─────────────┘    └─────────────┘            │
│                           │                                         │
│                           ↓ chat 事件                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│  │  listener   │───>│   router    │───>│ sse_manager │            │
│  │ 接收事件    │    │ 路由处理    │    │  广播推送   │            │
│  └─────────────┘    └─────────────┘    └─────────────┘            │
│                                                 │                   │
│                                                 ↓ SSE 流            │
│                                          ┌─────────────┐           │
│                                          │    前端     │           │
│                                          │ EventSource │           │
│                                          │ElNotification│          │
│                                          └─────────────┘           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
1. 任务执行
   executor.py → Gateway chat.send → Agent 处理

2. 结果回传
   Agent → Gateway → chat 事件 (state=final)

3. 事件监听
   listener.py 接收 chat 事件 → router.py 路由

4. 数据库更新
   router.py → 更新 task_executions 表

5. SSE 推送
   router.py → sse_manager.broadcast_to_admins()

6. 前端显示
   EventSource 接收 → ElNotification 弹窗
```

---

## 三、后端实现

### 3.1 SSE 管理器

**文件**：`backend/events/sse_manager.py`

```python
class SSEManager:
    """SSE 连接管理器"""

    def __init__(self):
        self._connections: Dict[int, queue.Queue] = {}  # user_id -> queue
        self._user_roles: Dict[int, Set[str]] = {}  # user_id -> roles
        self._lock = threading.Lock()

    def connect(self, user_id: int, roles: Set[str] = None) -> queue.Queue:
        """建立 SSE 连接"""
        q = queue.Queue(maxsize=100)
        with self._lock:
            self._connections[user_id] = q
            if roles:
                self._user_roles[user_id] = roles
        return q

    def broadcast(self, message: dict, require_roles: Set[str] = None):
        """广播消息"""
        with self._lock:
            for user_id, q in self._connections.items():
                # 角色过滤
                if require_roles:
                    user_roles = self._user_roles.get(user_id, set())
                    if not require_roles.intersection(user_roles):
                        continue
                try:
                    q.put_nowait(message)
                except queue.Full:
                    pass  # 队列满则跳过

    def stream(self, user_id: int, roles: Set[str] = None):
        """生成 SSE 流"""
        q = self.connect(user_id, roles)
        try:
            while True:
                try:
                    message = q.get(timeout=30)  # 30秒超时
                    if message is None:
                        break
                    yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    yield ": heartbeat\n\n"  # 心跳
        finally:
            self.disconnect(user_id)
```

### 3.2 SSE 端点

**文件**：`backend/app.py`

```python
@app.route('/api/events/stream')
def sse_stream():
    """SSE 事件流端点"""
    # 从 URL 参数获取 token（EventSource 不支持 header）
    token = request.args.get('token')

    # 验证 token
    payload = verify_access_token(token)
    user_id = payload.get('user_id')

    # 查询用户角色
    user = db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    role_id = user.get('role_id')
    roles = set()
    if role_id:
        role = db.fetch_one("SELECT name FROM roles WHERE id = ?", (role_id,))
        if role and role.get('name') == 'admin':
            roles.add('admin')

    # 返回 SSE 流
    def generate():
        for data in sse_manager.stream(user_id, roles):
            yield data

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )
```

### 3.3 事件路由器

**文件**：`backend/events/router.py`

```python
class EventRouter:
    """事件路由器"""

    async def _handle_chat_event(self, payload: dict):
        """处理 chat 事件"""
        session_key = payload.get('sessionKey', '')
        state = payload.get('state', '')

        # 检查是否是后台任务
        match = TASK_SESSION_PATTERN.match(session_key)
        if not match:
            return

        # 查找执行记录
        execution = db.fetch_one(
            "SELECT * FROM task_executions WHERE result LIKE ?",
            (f'%{session_key}%',)
        )

        if state == 'final':
            await self._handle_task_completed(execution, payload)

    async def _handle_task_completed(self, execution: dict, payload: dict):
        """处理任务完成"""
        # 更新数据库
        db.update('task_executions', {...})

        # SSE 推送
        event = EventPayload.task_result(
            task_id=task_id,
            status='completed',
            task_name=task_name
        )
        sse_manager.broadcast_to_admins(event)
```

---

## 四、前端实现

### 4.1 SSE 客户端

**文件**：`frontend/src/utils/sse-client.ts`

```typescript
export class SSEClient {
  private eventSource: EventSource | null = null

  constructor(
    private url: string,
    private getToken: () => string | null = () => localStorage.getItem('access_token')
  ) {}

  connect(): void {
    const token = this.getToken()
    // EventSource 不支持 header，通过 URL 传 token
    const urlWithToken = `${this.url}?token=${encodeURIComponent(token)}`
    this.eventSource = new EventSource(urlWithToken)

    this.eventSource.onopen = () => {
      this.connected = true
      this.notifyStatusChange(true)
    }

    this.eventSource.onmessage = (event) => {
      const message = JSON.parse(event.data)
      this.dispatch(message.type, message.data)
    }

    this.eventSource.onerror = () => {
      this.connected = false
      this.reconnect()
    }
  }

  on(eventType: string, callback: SSEEventCallback): void {
    // 注册事件监听
  }
}

// 全局单例
export function getSSEClient(): SSEClient {
  if (!globalSSEClient) {
    globalSSEClient = new SSEClient('/api/events/stream')
  }
  return globalSSEClient
}
```

### 4.2 App.vue 集成

**文件**：`frontend/src/App.vue`

```typescript
import { getSSEClient, SSEEventTypes } from './utils/sse-client'

const isAdmin = computed(() => userStore.user?.role === 'admin')

function initSSE() {
  if (!isAdmin.value) return

  const sseClient = getSSEClient()

  // 监听任务结果
  sseClient.on(SSEEventTypes.TASK_RESULT, (data: any) => {
    const taskName = data.task_name || `任务 #${data.task_id}`

    if (data.status === 'completed') {
      ElNotification({
        title: '任务执行完成',
        message: `任务「${taskName}」已成功执行完成`,
        type: 'success',
        duration: 5000,
        position: 'top-right',
        onClick: () => router.push('/scheduled-tasks')
      })
    }
  })

  sseClient.connect()
}

onMounted(() => {
  userStore.loadFromStorage()  // 关键：先加载用户信息
  initSSE()
})
```

---

## 五、关键问题与解决方案

### 5.1 EventSource 认证问题

**问题**：EventSource API 不支持设置自定义 Header。

**解决方案**：通过 URL 参数传递 token：

```typescript
const urlWithToken = `${this.url}?token=${encodeURIComponent(token)}`
this.eventSource = new EventSource(urlWithToken)
```

后端从 query 参数获取：

```python
token = request.args.get('token')
```

### 5.2 用户角色判断问题

**问题**：users 表使用 `role_id` 字段，而非 `role` 字段。

**错误代码**：
```python
if user.get('role') == 'admin':  # 永远为 False
    roles.add('admin')
```

**正确代码**：
```python
role_id = user.get('role_id')
if role_id:
    role = db.fetch_one("SELECT name FROM roles WHERE id = ?", (role_id,))
    if role and role.get('name') == 'admin':
        roles.add('admin')
```

### 5.3 userStore 初始化问题

**问题**：App.vue onMounted 时 userStore.user 为 null，导致 isAdmin 为 false。

**原因**：Pinia store 的 `loadFromStorage()` 未在组件挂载时调用。

**解决方案**：
```typescript
onMounted(() => {
  userStore.loadFromStorage()  // 先加载
  initSSE()  // 再初始化 SSE
})
```

---

## 六、配置说明

### 6.1 连接参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| queue.maxsize | 100 | 每个用户的消息队列大小 |
| heartbeat interval | 30s | 心跳发送间隔 |
| max connections | 无限制 | 最大连接数（可按需限制） |

### 6.2 事件类型

```typescript
export const SSEEventTypes = {
  TASK_STARTED: 'task_started',
  TASK_RESULT: 'task_result',
  TASK_FAILED: 'task_failed',
  SYSTEM_NOTICE: 'system_notice',
  SYSTEM_ALERT: 'system_alert',
  GATEWAY_CONNECTED: 'gateway_connected',
  GATEWAY_DISCONNECTED: 'gateway_disconnect'
}
```

---

## 七、监控与调试

### 7.1 连接状态 API

```
GET /api/events/status
```

响应：
```json
{
  "success": true,
  "data": {
    "gateway": { "connected": true },
    "sse": {
      "current_connections": 1,
      "total_messages": 10
    }
  }
}
```

### 7.2 日志追踪

**后端日志关键字**：
- `[SSE] connect called` - 连接建立
- `[SSE] broadcast called` - 广播消息
- `[Router] Broadcasting SSE event` - 事件推送

**前端日志关键字**：
- `[SSE] Connected` - 连接成功
- `[SSE] Task result received` - 收到任务结果

---

## 八、后续优化

### 8.1 待优化项

| 优化项 | 优先级 | 说明 |
|--------|--------|------|
| 日志级别控制 | 高 | 生产环境移除调试日志 |
| 连接数限制 | 中 | 防止单用户多连接 |
| 消息持久化 | 低 | 用户离线时消息存储 |

### 8.2 扩展场景

- Agent 状态变更通知
- 审批请求推送
- 系统告警通知