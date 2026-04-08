# Admin UI 与 Control UI 的 Gateway 连接对比分析

> 文档版本：1.0
> 更新时间：2026-04-05

---

## 一、问题背景

Admin UI 是我们基于 OpenClaw Gateway 协议自主开发的管理界面，与 OpenClaw 官方提供的 Control UI 形成互补。本文档分析两者与 Gateway 的连接方式，解答"两者对 Gateway 来说是否地位相同"这一架构问题。

---

## 二、结论

**是的，对 Gateway 来说，Admin UI 和 Control UI 地位完全相同。**

Gateway 不区分客户端是官方开发还是第三方开发，只关心：
- 认证是否通过
- 权限范围是否合法
- API 请求是否正确

---

## 三、连接方式对比

### 3.1 技术层面对比

| 对比项 | Admin UI | OpenClaw Control UI |
|--------|----------|---------------------|
| 连接协议 | WebSocket 直连 | WebSocket 直连 |
| 认证方式 | Ed25519 挑战-响应 | Ed25519 挑战-响应 |
| 加密算法 | Ed25519 椭圆曲线 | Ed25519 椭圆曲线 |
| 角色 (role) | operator | operator |
| 模式 (mode) | ui | ui |
| 协议版本 | v3 | v3 |
| 数据格式 | JSON | JSON |

### 3.2 连接参数对比

**Admin UI 连接参数**：

```json
{
  "client": {
    "id": "openclaw-control-ui",
    "displayName": "Admin UI Backend",
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

**Control UI 连接参数**（推测）：

```json
{
  "client": {
    "id": "control-ui",
    "displayName": "OpenClaw Control UI",
    "platform": "node",
    "mode": "ui",
    "version": "x.x.x"
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

**差异仅在于**：
- `client.id` - 客户端标识符
- `client.displayName` - 显示名称
- `client.version` - 版本号

---

## 四、认证流程对比

两者使用完全相同的认证流程：

```
┌─────────────┐                              ┌─────────────┐
│   客户端     │                              │   Gateway   │
│(Admin/UI)   │                              │             │
└──────┬──────┘                              └──────┬──────┘
       │                                            │
       │  1. WebSocket Connect                      │
       │───────────────────────────────────────────>│
       │                                            │
       │  2. connect request (含 deviceId, scopes)  │
       │───────────────────────────────────────────>│
       │                                            │
       │  3. challenge (nonce)                      │
       │<───────────────────────────────────────────│
       │                                            │
       │  4. challenge response (签名)              │
       │───────────────────────────────────────────>│
       │                                            │
       │  5. connect success                        │
       │<───────────────────────────────────────────│
       │                                            │
       │  6. API 调用 (chat.send, agent.list, ...)  │
       │<──────────────────────────────────────────>│
       │                                            │
```

### 4.1 设备身份生成

两者都使用 Ed25519 密钥对：

```typescript
// 密钥生成
const { secretKey, publicKey } = await ed.keygenAsync()

// 设备 ID = 公钥指纹
const deviceId = await fingerprintPublicKey(publicKey)

// 存储
localStorage.setItem('device_identity', JSON.stringify({
  deviceId,
  publicKey: base64UrlEncode(publicKey),
  privateKey: base64UrlEncode(secretKey)
}))
```

### 4.2 挑战-响应认证

两者签名逻辑相同：

```typescript
// 认证载荷
const payload = `v2|${deviceId}|${clientId}|${clientMode}|${role}|${scopes}|${signedAtMs}|${token}|${nonce}`

// Ed25519 签名
const signature = await ed.signAsync(payload, secretKey)
```

---

## 五、Gateway 视角

### 5.1 Gateway 关心的信息

Gateway 在处理连接时，只验证：

| 验证项 | 说明 |
|--------|------|
| protocol | 协议版本是否兼容 |
| deviceId | 设备身份是否有效 |
| signature | 挑战签名是否正确 |
| token | 认证令牌是否有效（如配置） |
| scopes | 权限范围是否合法 |

### 5.2 Gateway 不关心的信息

Gateway 不关心：

| 不关心项 | 说明 |
|----------|------|
| client.id | 客户端标识（仅用于日志） |
| displayName | 显示名称 |
| UI 实现 | 界面长什么样 |
| 额外功能 | 客户端自己的业务逻辑 |

---

## 六、架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        客户端层                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────┐        ┌─────────────────────┐        │
│  │      Admin UI       │        │     Control UI      │        │
│  │    (第三方开发)      │        │     (官方开发)      │        │
│  │                     │        │                     │        │
│  │  • 用户管理          │        │  • 对话管理         │        │
│  │  • 权限管理          │        │  • Agent 控制       │        │
│  │  • 定时任务          │        │  • 工具调用         │        │
│  │  • 灵魂管理          │        │  • 审批处理         │        │
│  │  • 对话功能          │        │                     │        │
│  └──────────┬──────────┘        └──────────┬──────────┘        │
│             │                              │                    │
│             │    WebSocket + Ed25519 Auth  │                    │
│             │                              │                    │
└─────────────┼──────────────────────────────┼────────────────────┘
              │                              │
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌─────────────────────────┐
              │        Gateway          │
              │                         │
              │  • 协议验证             │
              │  • 认证授权             │
              │  • 请求路由             │
              │  • 事件广播             │
              │                         │
              │  (对两个客户端无差别)    │
              └─────────────────────────┘
                             │
                             ▼
              ┌─────────────────────────┐
              │        Agent            │
              └─────────────────────────┘
```

---

## 七、实际区别

### 7.1 客户端标识不同

每个客户端有独立的 `clientId`：

```typescript
// Admin UI
const clientId = 'openclaw-control-ui'

// Control UI
const clientId = 'control-ui'  // 或其他官方标识
```

### 7.2 设备身份独立

每个客户端生成自己的密钥对，deviceId 唯一：

```typescript
// Admin UI 的设备身份
{
  deviceId: "SHA256:abc123...",
  publicKey: "...",
  privateKey: "..."  // 存储在 localStorage
}

// Control UI 的设备身份（不同）
{
  deviceId: "SHA256:def456...",
  publicKey: "...",
  privateKey: "..."
}
```

### 7.3 功能范围不同

| 功能 | Admin UI | Control UI |
|------|----------|------------|
| 用户管理 | ✅ | ❌ |
| 权限管理 | ✅ | ❌ |
| 部门管理 | ✅ | ❌ |
| 定时任务 | ✅ | ❌ |
| 灵魂管理 | ✅ | ❌ |
| 会话管理 | ✅ | ✅ |
| 对话功能 | ✅ | ✅ |
| Agent 控制 | ✅ | ✅ |

**注意**：功能差异是客户端自己的业务逻辑，Gateway 不参与。

---

## 八、安全考虑

### 8.1 多客户端场景

当同时使用 Admin UI 和 Control UI 时：

1. **设备身份独立** - 每个客户端有自己的密钥对
2. **会话独立** - 每个客户端维护自己的 WebSocket 连接
3. **事件独立** - 每个客户端独立接收 Gateway 事件

### 8.2 权限控制

两者使用相同的 scopes 机制：

```json
{
  "scopes": [
    "operator.read",
    "operator.write",
    "operator.admin",
    "operator.approvals",
    "operator.pairing"
  ]
}
```

如果配置了 Gateway 认证令牌，两者都需要提供有效的 token。

---

## 九、总结

| 问题 | 答案 |
|------|------|
| 连接方式是否相同？ | ✅ 是，都使用 WebSocket + Ed25519 认证 |
| 对 Gateway 来说地位是否相同？ | ✅ 是，Gateway 不区分客户端来源 |
| 认证流程是否相同？ | ✅ 是，相同的挑战-响应流程 |
| 权限机制是否相同？ | ✅ 是，相同的 scopes 机制 |
| API 调用方式是否相同？ | ✅ 是，相同的 JSON-RPC 风格 |

**核心结论**：对 Gateway 来说，Admin UI 就是另一个 Control UI 客户端，两者地位完全平等，都通过相同的协议和认证方式连接。

---

## 十、参考文档

- [OpenClaw WebSocket 协议](./OpenClaw-WebSocket协议.md)
- [Agent 对话功能开发总结](./Agent对话功能开发总结.md)
- [SSE 实时推送系统技术文档](./SSE实时推送系统技术文档.md)