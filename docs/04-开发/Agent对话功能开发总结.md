# Agent 对话功能开发总结

## 概述

在 Admin UI 中实现了 Agent 对话功能，用户可以通过 Web 界面直接与 Agent 进行交互。

**开发时间**: 2026-04-04

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                 前端 Vue 3 (Admin UI)                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ gateway-ws.ts                                        │   │
│  │ - GatewayBrowserClient                               │   │
│  │ - Ed25519 设备身份管理                                │   │
│  │ - 挑战-响应认证流程                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Chat.vue                                             │   │
│  │ - Agent/Session 选择器                               │   │
│  │ - 消息显示与流式输出                                  │   │
│  │ - 消息发送与停止控制                                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │ WebSocket (直连 Gateway)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   OpenClaw Gateway                          │
│  端点: ws://127.0.0.1:18789                                 │
│  方法: connect, chat.history, chat.send, chat.abort         │
│  事件: connect.challenge, chat                             │
└─────────────────────────────────────────────────────────────┘
                          │ HTTP (获取配置)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   后端 Flask                                │
│  GET /api/chat/config → { gatewayUrl, gatewayToken }       │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈对比

| 组件 | Admin UI (本项目) | OpenClaw Control UI |
|------|------------------|---------------------|
| 框架 | Vue 3 | Lit (Web Components) |
| 语言 | TypeScript | TypeScript |
| 构建工具 | Vite | Vite |
| 状态管理 | Vue Composition API (ref/computed) | Lit reactive properties |
| 后端通信 | WebSocket Gateway Client | WebSocket Gateway Client |

## 核心实现

### 1. Gateway WebSocket 客户端 (`gateway-ws.ts`)

完全参考 OpenClaw 官方实现，核心流程：

```typescript
// 连接流程
1. WebSocket.open → queueConnect()
2. queueConnect() → 延迟 750ms → sendConnect()
3. 收到 connect.challenge 事件 → 提取 nonce → 立即 sendConnect()
4. sendConnect():
   - 构建 device 认证对象 (Ed25519 签名)
   - 发送 connect 请求
5. 收到 hello-ok → 连接成功
```

### 2. 设备身份认证

使用 Ed25519 椭圆曲线加密：

```typescript
// 密钥生成 (v3 API)
const { secretKey, publicKey } = await ed.keygenAsync()
const deviceId = SHA256(publicKey) → hex string

// 签名
const signature = await ed.signAsync(data, secretKey)
```

### 3. 认证载荷格式

```typescript
// v2 格式
payload = [
  "v2",
  deviceId,
  clientId,        // "openclaw-control-ui"
  clientMode,      // "ui"
  role,            // "operator"
  scopes.join(","), // "operator.admin,operator.read,..."
  String(signedAtMs),
  token,           // Gateway token
  nonce            // 从 challenge 事件获取
].join("|")
```

### 4. Chat API

| 方法 | 参数 | 说明 |
|------|------|------|
| `chat.history` | `{sessionKey, limit}` | 加载历史消息 |
| `chat.send` | `{sessionKey, message, idempotencyKey}` | 发送消息（非阻塞） |
| `chat.abort` | `{sessionKey, runId?}` | 中止运行 |

### 5. Chat 事件处理

```typescript
// 事件格式
{
  runId: string,
  sessionKey: string,
  state: 'delta' | 'final' | 'aborted' | 'error',
  message?: unknown,
  errorMessage?: string
}

// 状态处理
delta → 流式更新 chatStream
final → 保存消息到 chatMessages
aborted → 保存已输出内容
error → 显示错误信息
```

## 遇到的问题及解决方案

### 问题 1: client ID 无效

**错误**: `invalid connect params: at /client/id: must be equal to constant`

**原因**: 使用了 `admin-ui` 作为 client ID，但 Gateway 只接受预定义的常量值。

**解决**: 查看 `openclaw/src/gateway/protocol/client-info.ts`，改为 `openclaw-control-ui`。

```typescript
// 有效值
GATEWAY_CLIENT_IDS = {
  WEBCHAT_UI: "webchat-ui",
  CONTROL_UI: "openclaw-control-ui",
  WEBCHAT: "webchat",
  CLI: "cli",
  // ...
}
```

### 问题 2: clientMode 无效

**解决**: `webchat` → `ui`（对应 `GATEWAY_CLIENT_MODES.UI`）

### 问题 3: Gateway Token 不匹配

**错误**: `unauthorized: gateway token mismatch`

**原因**: 后端返回了 Device Token 而不是 Gateway Token。

**解决**: 修改 `settings.py`，优先从 `openclaw.json` 读取 Gateway token：

```python
def _get_gateway_token() -> str:
    # 1. 环境变量
    # 2. openclaw.json → gateway.auth.token
    # 3. device-auth.json (fallback)
```

### 问题 4: Ed25519 API 变更

**错误**: `ed.utils.randomPrivateKey is not a function`

**原因**: `@noble/ed25519` v3 改了 API。

**解决**:
```typescript
// 旧 API (v2)
const privateKey = ed.utils.randomPrivateKey()
const publicKey = await ed.getPublicKeyAsync(privateKey)

// 新 API (v3)
const { secretKey, publicKey } = await ed.keygenAsync()
```

### 问题 5: Vue 响应式更新不生效

**原因**: `handleChatEvent` 函数修改的是普通对象，不是 Vue 的响应式 ref。

**解决**: 在 Vue 组件中直接操作 ref，不通过外部函数：

```typescript
// 错误做法
handleChatEvent({ chatMessages: chatMessages.value, ... }, payload)

// 正确做法
if (payload.state === 'delta') {
  chatStream.value = next  // 直接操作 ref
}
```

## 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/utils/gateway-ws.ts` | 新增 | Gateway WebSocket 客户端 |
| `frontend/src/views/Chat.vue` | 新增 | 对话页面组件 |
| `frontend/src/api/index.ts` | 修改 | 添加 `chatApi` |
| `frontend/src/router/index.ts` | 修改 | 添加 `/chat` 路由 |
| `frontend/src/App.vue` | 修改 | 添加"对话"菜单项 |
| `backend/app.py` | 修改 | 添加 `/api/chat/config` 端点 |
| `backend/settings.py` | 修改 | 修复 Gateway Token 读取逻辑 |

## 参考资料

- OpenClaw 源码: `/home/iamlibai/workspace/github_code/openclaw/`
  - `ui/src/ui/gateway.ts` - WebSocket 客户端核心
  - `ui/src/ui/device-identity.ts` - 设备身份管理
  - `ui/src/ui/controllers/chat.ts` - Chat 控制器
  - `src/gateway/device-auth.ts` - 认证载荷构建
- OpenClaw 文档: `/usr/lib/node_modules/openclaw/docs/web/`
  - `control-ui.md` - Control UI 使用说明
  - `webchat.md` - WebChat 行为说明

## 后续优化建议

1. **Markdown 渲染** - 支持消息中的 Markdown 格式
2. **代码高亮** - 支持代码块的语法高亮
3. **图片附件** - 支持粘贴/拖拽图片
4. **Slash Commands** - 支持 `/help`、`/new` 等快捷命令
5. **会话管理** - 支持重命名、删除会话
6. **消息操作** - 支持复制、重新生成等