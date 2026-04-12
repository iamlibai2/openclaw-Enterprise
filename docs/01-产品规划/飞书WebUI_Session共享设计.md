# 飞书与 WebUI Session 共享设计

> 状态：规划中
> 优先级：P2
> 创建时间：2026-04-10

## 背景

当前 FeishuChat（Web UI）和飞书客户端的对话使用不同的 session，导致：

- 用户在 Web UI 的对话记录，飞书客户端看不到
- 用户在飞书客户端的对话，Web UI 也无法继续

**目标**：同一用户在飞书客户端和 Web UI 共享同一个 session。

## 核心概念

### Session Key 格式

```
agent:{agentId}:{channel}:{peerKind}:{peerId}

# 示例
agent:main:feishu:direct:ou_xxxx     # 飞书私聊
agent:main:webchat:uuid-xxx           # Web UI（当前）
```

### identityLinks 机制

OpenClaw 提供的身份映射配置：

```yaml
session:
  dmScope: per-peer
  identityLinks:
    "zhangsan":                 # canonical id（统一身份）
      - "feishu:ou_xxxx"        # 飞书身份
      - "webchat:zhangsan"      # WebUI 身份
```

## 问题分析

### 当前 Web UI 的问题

```javascript
// FeishuChat.vue 当前实现
sessionKey = `agent:${agentId}:webchat:${crypto.randomUUID()}`  // 随机 UUID
```

问题：
1. 每次创建会话都是新的 UUID
2. 与飞书客户端的 `agent:${agentId}:feishu:direct:${openId}` 不匹配

### 用户使用顺序问题

```
场景：用户先用 Web UI，再用飞书

1. WebUI 阶段：
   登录用户 → Employee → Agent
   Session: agent:assistant:webchat:uuid-xxx
   ❌ 此时不知道 feishu_open_id

2. 飞书阶段：
   飞书消息(open_id="ou_xxx") → ?
   Session: agent:assistant:feishu:direct:ou_xxx
   ❌ 不知道 ou_xxx 对应哪个 Employee

结果：两个独立 session，无法共享
```

## 解决方案

### 数据结构变更

```python
# Employee 表新增字段
class Employee:
    # 现有字段
    name: str
    phone: str
    agent_ids: list  # 关联的 Agent（一对一或一对多）
    user_id: int     # 关联 User 表

    # 新增字段
    feishu_open_id: str  # 飞书用户身份
```

### 自动绑定流程

```
┌─────────────────────────────────────────────────────────────┐
│                      飞书消息到达                             │
│                   sender: ou_xxxx                           │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  1. 查找 Employee.feishu_open_id = 'ou_xxxx'                │
│                                                             │
│     找到 → 直接使用该员工的 Agent                            │
│     未找到 → 尝试自动绑定                                    │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  2. 自动绑定流程                                             │
│                                                             │
│     a. 调用飞书 API 获取 ou_xxxx 的手机号                    │
│     b. 在 Employee 表查找 phone 匹配的员工                   │
│     c. 找到 → 更新 Employee.feishu_open_id = 'ou_xxxx'      │
│     d. 未找到 → 提示用户到 WebUI 绑定                        │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  3. 生成 Session                                             │
│                                                             │
│     peerId = employee.id 或 employee.username               │
│     session key = agent:{agentId}:direct:{peerId}           │
└─────────────────────────────────────────────────────────────┘
```

### 简化方案（不用 identityLinks）

如果两边使用相同的 peerId，就不需要 identityLinks：

```python
# 飞书消息处理
open_id = message.sender.open_id
employee = Employee.query.filter(feishu_open_id=open_id).first()
peer_id = employee.id  # 或 employee.username

# session key
session_key = f"agent:{agent_id}:direct:{peer_id}"
```

```javascript
// Web UI 消息处理
const userId = currentUser.id
const employee = await getEmployeeByUserId(userId)
const peerId = employee.id  // 与飞书相同！

// session key
const sessionKey = `agent:${agentId}:direct:${peerId}`
```

**两边 peerId 相同 → session 相同**

### 备选方案：绑定码

如果无法自动匹配手机号，提供手动绑定方式：

```
1. 用户登录 WebUI
2. 点击"绑定飞书账号"
3. 系统生成绑定码：BIND-XXXX
4. 用户在飞书客户端发送绑定码给机器人
5. 机器人识别绑定码，建立 open_id → Employee 映射
```

## 实现步骤

### Phase 1：数据准备

1. Employee 表新增 `feishu_open_id` 字段
2. 提供管理界面手动绑定飞书账号

### Phase 2：自动绑定

1. 飞书消息到达时，检查 `feishu_open_id` 是否已绑定
2. 未绑定则尝试通过手机号自动匹配
3. 匹配成功则自动绑定

### Phase 3：Session 共享

1. 修改 FeishuChat.vue 的 session key 生成逻辑
2. 使用 employee.id 作为 peerId
3. 测试 WebUI 和飞书客户端 session 共享

## 注意事项

### `/new` 命令

`/new` 会创建新 session，但不影响共享：

```
用户在飞书发 /new → session key = "agent:main:direct:zhangsan:new_xxx"
用户在 WebUI 发 /new → session key = "agent:main:direct:zhangsan:new_xxx"

两边还是共享的！
```

### 多 Agent 场景

每个 Agent 只分配给一个用户，Agent 之间隔离：

```
Employee A → Agent "assistant_a"
Employee B → Agent "assistant_b"

Session 不会混淆
```

## 参考文档

- OpenClaw Session 文档：`/openclaw/docs/zh-CN/concepts/session.md`
- 飞书用户身份：open_id（应用维度）、user_id（企业维度）、union_id（开发者维度）
- identityLinks 实现代码：`/openclaw/src/routing/session-key.ts`