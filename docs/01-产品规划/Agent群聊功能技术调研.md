# Agent 群聊功能技术调研

## 1. 需求背景

在 Control UI 中实现 Agent 群聊功能，让多个 Agent 能够协同讨论，共同解决复杂问题。

**核心诉求**：
- 多个 Agent 在同一个会话中协作
- Agent 之间能够互相看到消息
- 用户可以观察和干预讨论过程

---

## 2. 技术调研

### 2.1 行业解决方案

#### Microsoft Agent Framework

微软推出的多智能体框架，原生支持：

| 功能 | 说明 |
|------|------|
| GroupChat 模式 | 通过 GroupChatManager 选择下一个发言智能体 |
| 编排策略 | RoundRobin（轮询）、Prompt-based（基于提示选择） |
| Handoff 模式 | 智能体通过 function calling 实现控制权转移 |

#### A2A 协议（Google，2025年4月发布）

Agent-to-Agent Protocol，解决 Agent 间通信标准化问题：

```
┌─────────────────────────────────────────────────┐
│  A2A 协议核心概念                                │
├─────────────────────────────────────────────────┤
│  Agent Card    │ JSON 名片，托管在              │
│                 │ /.well-known/agent-card.json  │
├─────────────────────────────────────────────────┤
│  Task           │ 任务对象，有生命周期状态       │
│                 │ submitted → working →         │
│                 │ completed/failed              │
├─────────────────────────────────────────────────┤
│  Message        │ 消息，携带文本、文件、结构化数据│
├─────────────────────────────────────────────────┤
│  Artifact       │ 任务产物                       │
├─────────────────────────────────────────────────┤
│  通信方式       │ HTTP + JSON-RPC 2.0 + SSE     │
└─────────────────────────────────────────────────┘
```

**A2A 协议定位**：
- 解决**跨系统** Agent 通信问题
- 让不同框架（LangChain、CrewAI 等）的 Agent 能够互通
- 与 MCP 协议互补：MCP 解决 Agent 调工具，A2A 解决 Agent 间通信

#### ClaudeTalk 项目

GitHub: https://github.com/suyin58/claudetalk

在 IM 群聊中实现 Multi-Agent 协作的实践项目：

**核心问题**：IM 平台限制机器人发的消息其他机器人收不到

**解决方案**：用共享文件做消息队列
```
PM 机器人发消息 → 检测@标签 → 写入 bot_前端开发.json
    ↓
前端开发机器人轮询 → 发现新消息 → 回复 → 处理 → 删除消息
```

---

## 3. OpenClaw 现有能力分析

### 3.1 相关工具

| 工具 | 功能 | 适用场景 |
|------|------|----------|
| `sessions_send` | 向已存在的 Session 发消息 | Agent 间点对点通信 |
| `sessions_spawn` | 创建新的子 Session | 任务分发、子 Agent 创建 |

### 3.2 sessions_send 详解

**参数**：
```typescript
{
  sessionKey?: string,   // 目标 Session Key
  label?: string,        // 或通过 label 查找
  agentId?: string,      // 目标 Agent ID
  message: string,       // 发送的消息
  timeoutSeconds?: number
}
```

**工作流程**：
```
Agent A (主持人)
     │
     ├─ sessions_send → Agent B
     │     Ping-Pong 多轮对话（默认5轮）
     │
     └─ 收到 B 的回复
```

**通信模式**：**点对点**，非群聊

- Agent A 向 Agent B 发消息，只有 A 和 B 能看到
- Agent C 无法看到 A 和 B 的对话

### 3.3 sessions_spawn 详解

**参数**：
```typescript
{
  task: string,          // 任务描述
  runtime?: "subagent" | "acp",
  agentId?: string,      // 指定 Agent
  mode?: "run" | "session",
  // ...
}
```

**工作流程**：
```
Agent A (父)
     │
     ├─ sessions_spawn(task="...", agentId="B")
     │
     └─ 创建子 Session，B 执行任务
          │
          └─ SpawnedRunMetadata（groupId 等）
```

**通信模式**：**父子层级**

- 子 Agent 结果返回给父 Agent
- 子 Agent 之间互不可见

### 3.4 当前 A2A 配置状态

```json
{
  "tools": {
    "agentToAgent": {
      "enabled": true
    }
  },
  "session": {
    "visibility": "all"
  }
}
```

配置已启用 Agent 间通信，但仍为点对点模式。

### 3.5 OpenClaw A2A vs Google A2A 协议

| 项目 | OpenClaw sessions_send | Google A2A 协议 |
|------|------------------------|-----------------|
| 范围 | 系统内部 | 跨系统 |
| Agent Card | 无 | 有（.well-known/） |
| 标准端点 | 无 | tasks/send, message/stream |
| 数据结构 | 内部格式 | Task/Message/Artifact |
| 通信协议 | Gateway 内部调用 | HTTP + JSON-RPC + SSE |

**结论**：OpenClaw 的 `sessions_send` 是内部 Agent 间通信机制，借鉴了 A2A 概念，但不是 Google A2A 协议的完整实现。

---

## 4. 可行方案对比

### 方案 A：前端模拟群聊

**原理**：前端管理多个 Agent Session，并行发送消息，合并显示

**实现**：
```
用户输入 "讨论这个问题"
    │
    ├── Agent 1: chat.send → SSE 流 → 响应 1
    ├── Agent 2: chat.send → SSE 流 → 响应 2
    └── Agent 3: chat.send → SSE 流 → 响应 3
    │
前端合并显示：响应1 + 响应2 + 响应3
```

**特点**：
| 优点 | 缺点 |
|------|------|
| 完全前端实现 | Agent 之间看不到彼此回复 |
| 无需后端改动 | 不是真正讨论，只是并行回答 |
| 灵活控制参与者 | 无法协调 |

### 方案 B：使用 sessions_spawn

**原理**：主持人 Agent 派发子任务给其他 Agent

**实现**：
```
用户消息 → 主持人 Agent
              │
              ├── sessions_spawn(task="分析", agentId="分析师")
              │       → 子 Agent 执行 → 返回结果
              │
              └── 主持人综合回复
```

**特点**：
| 优点 | 缺点 |
|------|------|
| 有上下文继承（groupId） | 层级结构，非平级 |
| 主持人可见子 Agent 结果 | 子 Agent 之间互不可见 |
| OpenClaw 原生支持 | 不是群聊，是任务分发 |

### 方案 C：使用 sessions_send

**原理**：Agent 间点对点通信

**实现**：
```
Agent A (主持人)
     │
     ├─ sessions_send → Agent B (分析师)
     │     Ping-Pong 多轮讨论
     │
     ├─ sessions_send → Agent C (顾问)
     │     Ping-Pong 多轮讨论
     │
     └─ A 综合回复
```

**特点**：
| 优点 | 缺点 |
|------|------|
| 配置已就绪 | 点对点，非群聊 |
| 支持多轮讨论 | Agent B 和 C 看不到彼此消息 |
| 无需开发新功能 | 需要主持人转发消息 |

### 方案 D：开发真正的群聊功能

**需要实现**：
1. 群聊 Session 机制
2. 消息广播到所有参与者
3. 群聊状态管理
4. 前端群聊 UI

**工作量**：较大，需要修改 OpenClaw 核心或 Control UI 后端

---

## 5. 结论与建议

### 当前限制

**OpenClaw 目前不支持真正的 Agent 群聊**（所有 Agent 在同一会话中互相看到消息）。

### 推荐方案

| 阶段 | 方案 | 说明 |
|------|------|------|
| 短期 | 方案 A（前端模拟） | 快速实现，满足"多 Agent 并行回答"场景 |
| 中期 | 方案 C（sessions_send） | 利用现有能力，主持人协调讨论 |
| 长期 | 方案 D（开发群聊） | 实现真正的 Agent 群聊功能 |

### 下一步行动

1. **确认需求场景**：是需要"多 Agent 并行回答"还是"多 Agent 协作讨论"？
2. **选择方案**：根据场景选择短期或长期方案
3. **原型验证**：先用方案 A 或 C 做原型，验证用户需求

---

## 6. 参考资料

- [A2A 协议规范](https://a2a-protocol.org/latest/specification/)
- [A2A GitHub](https://github.com/google/A2A)
- [ClaudeTalk 项目](https://github.com/suyin58/claudetalk)
- [Microsoft Agent Framework](https://learn.microsoft.com/en-us/dotnet/api/microsoft.agents)
- OpenClaw 源码：`src/agents/tools/sessions-send-tool.ts`
- OpenClaw 源码：`src/agents/tools/sessions-spawn-tool.ts`

---

**文档版本**：v1.0
**创建日期**：2026-04-09
**作者**：Claude（基于讨论整理）