# Agent 群聊功能设计 - 方案 C（sessions_send）

## 1. 方案概述

**核心思路**：通过主持人 Agent 使用 `sessions_send` 工具与多个 Agent 通信，主持人汇总后回复用户。

**特点**：
- 利用 OpenClaw 现有能力，无需修改源码
- 主持人 Agent 负责协调和转发消息
- 支持多轮讨论（Ping-Pong）
- Token 消耗中等

---

## 2. 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                        Control UI 前端                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  群聊视图                                            │   │
│  │  - 参与者选择（勾选 Agent）                          │   │
│  │  - 消息列表（显示各 Agent 回复）                     │   │
│  │  - 用户输入框                                        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ chat.send API
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     OpenClaw Gateway                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  主持人 Session (host-agent)                         │   │
│  │                                                      │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │  sessions_send 工具                          │    │   │
│  │  │  - 向 Agent B 发消息                         │    │   │
│  │  │  - 向 Agent C 发消息                         │    │   │
│  │  │  - 转发其他 Agent 的回复                     │    │   │
│  │  └─────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────┘   │
│                              │                              │
│              ┌───────────────┼───────────────┐              │
│              ▼               ▼               ▼              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│  │ Agent B     │   │ Agent C     │   │ Agent D     │       │
│  │ Session     │   │ Session     │   │ Session     │       │
│  │ (分析师)     │   │ (顾问)      │   │ (审核)      │       │
│  └─────────────┘   └─────────────┘   └─────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 角色设计

### 3.1 主持人 Agent（Host Agent）

**职责**：
1. 接收用户消息
2. 决定调用哪些参与 Agent
3. 向参与 Agent 发送消息（使用 sessions_send）
4. 汇总各 Agent 回复
5. 综合回复用户

**System Prompt 模板**：

```
你是一个讨论主持人，负责协调多个专家 Agent 进行讨论。

## 可用工具
- sessions_send: 向其他 Agent 发送消息并获取回复

## 参与者 Agent
{{#each participants}}
- {{this.agentId}}: {{this.description}}
{{/each}}

## 工作流程
1. 分析用户问题，决定需要哪些 Agent 参与
2. 使用 sessions_send 向选中的 Agent 发送问题
3. 收集各 Agent 的回复
4. 如需深入讨论，可以向 Agent 转发其他 Agent 的观点
5. 综合所有回复，形成最终答案

## 注意事项
- 可以并行或串行调用多个 Agent
- 转发时说明"XXX 认为：..."，让其他 Agent 参考不同观点
- 最终回复要综合所有 Agent 的意见
- 如果某 Agent 的回复对当前问题帮助不大，可以忽略
```

### 3.2 参与 Agent

参与 Agent 是普通的 OpenClaw Agent，无需特殊配置。只需确保：
- 有合适的 System Prompt 定义其专业领域
- 配置在 OpenClaw 的 agents.list 中

---

## 4. 前端设计

### 4.1 群聊视图组件

```
┌─────────────────────────────────────────────────────────┐
│  群聊                                    [设置] [结束]   │
├─────────────────────────────────────────────────────────┤
│  参与者：☑️ 分析师  ☑️ 顾问  ☐ 审核  [+ 添加]          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [用户] 请分析这个技术方案的可行性                       │
│                                                         │
│  [主持人] 我来协调分析团队讨论这个问题...                │
│                                                         │
│  [分析师] 从技术角度看，这个方案有以下优点和风险...      │
│                                                         │
│  [顾问] 综合分析师的观点，我建议关注以下几点...          │
│                                                         │
│  [主持人] 综合各位专家的意见，我的总结如下：...          │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  [输入消息...]                                    [发送] │
└─────────────────────────────────────────────────────────┘
```

### 4.2 交互流程

```
用户输入消息
    │
    ▼
前端调用 chat.send（主持人 Session）
    │
    ▼
主持人 Agent 执行
    │
    ├─ sessions_send → Agent B
    │     └─ 返回回复 → 显示在消息列表
    │
    ├─ sessions_send → Agent C
    │     └─ 返回回复 → 显示在消息列表
    │
    └─ 主持人综合回复 → 显示在消息列表
```

### 4.3 消息来源识别

前端需要识别消息来源 Agent，可通过以下方式：

**方式 1：消息元数据**
```typescript
interface GroupChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sourceAgent?: string;  // 消息来源 Agent ID
  timestamp: number;
}
```

**方式 2：解析消息内容**
主持人 Agent 在回复中标记来源，如：
```
[分析师]: ...
[顾问]: ...
```

---

## 5. 数据结构

### 5.1 群聊配置

```typescript
interface GroupChatConfig {
  hostAgentId: string;           // 主持人 Agent ID
  participants: Participant[];   // 参与 Agent 列表
  maxTurns?: number;             // 最大讨论轮数
  parallelCall?: boolean;        // 是否并行调用
}

interface Participant {
  agentId: string;
  name: string;
  description: string;
  enabled: boolean;
}
```

### 5.2 群聊 Session

```typescript
interface GroupChatSession {
  id: string;
  hostSessionKey: string;        // 主持人 Session Key
  config: GroupChatConfig;
  messages: GroupChatMessage[];
  status: 'active' | 'ended';
  createdAt: number;
}
```

---

## 6. 实现步骤

### Phase 1：主持人 Agent 配置

1. 在 OpenClaw 配置中创建主持人 Agent
2. 编写主持人 System Prompt
3. 确保主持人有 `sessions_send` 工具权限

**配置示例**：
```json
{
  "agents": {
    "list": [
      {
        "id": "group-chat-host",
        "name": "群聊主持人",
        "model": { "primary": "bailian/qwen3.5-plus" },
        "tools": {
          "profile": "messaging",
          "alsoAllow": ["sessions_send"]
        }
      },
      {
        "id": "analyst",
        "name": "分析师",
        "model": { "primary": "bailian/glm-5" }
      },
      {
        "id": "advisor",
        "name": "顾问",
        "model": { "primary": "bailian/glm-5" }
      }
    ]
  }
}
```

### Phase 2：前端群聊视图

1. 创建 `GroupChat.vue` 组件
2. 实现参与者选择器
3. 实现消息列表（支持多 Agent 消息显示）
4. 实现输入框和发送逻辑

### Phase 3：消息解析

1. 解析主持人回复，提取各 Agent 的消息
2. 在消息列表中分别显示
3. 支持 Agent 头像、颜色区分

### Phase 4：优化体验

1. 显示 Agent 思考状态
2. 支持流式输出
3. 支持中途添加/移除参与者

---

## 7. 关键代码示例

### 7.1 主持人 Prompt（完整版）

```
你是一个讨论主持人，负责协调多个专家进行讨论。

## 可用工具
- sessions_send(label, agentId, message): 向指定 Agent 发送消息

## 当前参与者
{{participants}}

## 讨论规则
1. 收到用户问题后，分析需要哪些专家参与
2. 使用 sessions_send 向专家提问，格式：
   sessions_send(agentId="analyst", message="请分析：...")

3. 收到专家回复后，可以：
   - 继续追问同一专家
   - 向其他专家转发观点
   - 综合回复用户

4. 转发其他专家观点时，说明来源：
   "分析师认为：...，你怎么看？"

5. 最终回复用户时，使用格式：
   【综合意见】
   经过与各位专家讨论，总结如下：
   - 要点1
   - 要点2
   ...

## 示例对话

用户：这个技术方案可行吗？

主持人：让我咨询一下分析团队...

主持人调用：sessions_send(agentId="analyst", message="请从技术角度分析这个方案的可行性")

分析师回复：从技术角度看，这个方案有3个优点...

主持人调用：sessions_send(agentId="advisor", message="分析师认为有这些优点...，你有什么建议？")

顾问回复：建议关注风险点...

主持人：【综合意见】
经过讨论，团队认为：
- 分析师指出...
- 顾问建议...
- 我的建议是...
```

### 7.2 前端发送消息

```typescript
async function sendGroupMessage(content: string) {
  // 调用主持人的 chat.send
  const response = await gatewayClient.chat.send({
    agentId: groupChatConfig.hostAgentId,
    message: content,
    // 传递参与者信息作为上下文
    context: {
      participants: groupChatConfig.participants
        .filter(p => p.enabled)
        .map(p => `${p.agentId}(${p.name}): ${p.description}`)
        .join('\n')
    }
  });

  // 解析流式响应
  for await (const event of response.stream) {
    if (event.type === 'assistant') {
      // 解析消息，提取各 Agent 的回复
      const messages = parseAgentMessages(event.content);
      appendMessages(messages);
    }
  }
}
```

---

## 8. 局限与改进方向

### 当前局限

1. **Agent 互不可见**：主持人需要手动转发消息
2. **Token 消耗**：转发会增加额外 token
3. **延迟较高**：串行调用多个 Agent

### 改进方向

1. **并行调用**：主持人同时向多个 Agent 发送消息
2. **消息缓存**：避免重复转发相同内容
3. **智能转发**：主持人判断哪些观点值得转发

---

## 9. 测试计划

| 测试项 | 验证点 |
|--------|--------|
| 主持人调用 | sessions_send 正常工作 |
| 消息解析 | 前端正确显示各 Agent 消息 |
| 多轮讨论 | Ping-Pong 正常工作 |
| 错误处理 | Agent 不可用时的降级处理 |
| 性能 | 并行 vs 串行的响应时间 |

---

**文档版本**：v1.0
**创建日期**：2026-04-09