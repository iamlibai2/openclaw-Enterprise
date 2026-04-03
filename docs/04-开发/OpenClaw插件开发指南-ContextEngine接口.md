# OpenClaw ContextEngine 插件接口

> 来源：`/usr/lib/node_modules/openclaw/dist/plugin-sdk/src/context-engine/types.d.ts`

## 接口定义

```typescript
interface ContextEngine {
  /** 引擎标识和元信息 */
  readonly info: ContextEngineInfo;

  /** 初始化会话状态 */
  bootstrap?(params: BootstrapParams): Promise<BootstrapResult>;

  /** 运行转录维护 */
  maintain?(params: MaintainParams): Promise<ContextEngineMaintenanceResult>;

  /** 摄入单条消息 */
  ingest(params: IngestParams): Promise<IngestResult>;

  /** 摄入批量消息 */
  ingestBatch?(params: IngestBatchParams): Promise<IngestBatchResult>;

  /** 回合后处理 */
  afterTurn?(params: AfterTurnParams): Promise<void>;

  /** 组装模型上下文（核心方法） */
  assemble(params: AssembleParams): Promise<AssembleResult>;

  /** 压缩上下文 */
  compact(params: CompactParams): Promise<CompactResult>;

  /** 准备子 agent 启动 */
  prepareSubagentSpawn?(params: SubagentSpawnParams): Promise<SubagentSpawnPreparation>;

  /** 子 agent 结束通知 */
  onSubagentEnded?(params: SubagentEndedParams): Promise<void>;

  /** 释放资源 */
  dispose?(): Promise<void>;
}
```

## 类型定义

### ContextEngineInfo

```typescript
type ContextEngineInfo = {
  id: string;           // 引擎唯一标识
  name: string;         // 显示名称
  version?: string;     // 版本号
  ownsCompaction?: boolean;  // 是否管理自己的压缩生命周期
};
```

### AssembleResult（核心返回类型）

```typescript
type AssembleResult = {
  /** 发送给模型的对话消息列表 */
  messages: AgentMessage[];

  /** 估算的总 token 数 */
  estimatedTokens: number;

  /** 可选：追加到系统提示词前面的内容 */
  systemPromptAddition?: string;
};
```

### 其他返回类型

```typescript
type BootstrapResult = {
  bootstrapped: boolean;
  importedMessages?: number;
  reason?: string;
};

type IngestResult = {
  ingested: boolean;
};

type IngestBatchResult = {
  ingestedCount: number;
};

type CompactResult = {
  ok: boolean;
  compacted: boolean;
  reason?: string;
  result?: {
    summary?: string;
    firstKeptEntryId?: string;
    tokensBefore: number;
    tokensAfter?: number;
    details?: unknown;
  };
};
```

## 方法参数

### bootstrap

```typescript
{
  sessionId: string;
  sessionKey?: string;   // 完整的会话标识，如 "agent:xiaomei:feishu:..."
  sessionFile: string;   // 会话文件路径
}
```

### ingest

```typescript
{
  sessionId: string;
  sessionKey?: string;
  message: AgentMessage;
  isHeartbeat?: boolean;  // 是否来自心跳运行
}
```

### assemble

```typescript
{
  sessionId: string;
  sessionKey?: string;
  messages: AgentMessage[];  // 当前会话的所有消息
  tokenBudget?: number;       // token 预算
  model?: string;             // 当前模型 ID
  prompt?: string;            // 当前用户输入
}
```

### compact

```typescript
{
  sessionId: string;
  sessionKey?: string;
  sessionFile: string;
  tokenBudget?: number;
  force?: boolean;
  currentTokenCount?: number;
  compactionTarget?: "budget" | "threshold";
  customInstructions?: string;
  runtimeContext?: ContextEngineRuntimeContext;
}
```

## 生命周期

```
会话启动
    │
    ▼
bootstrap()     ← 初始化引擎状态
    │
    ▼
用户发送消息
    │
    ▼
assemble()      ← 组装发送给模型的上下文
    │
    ▼
AI 生成响应
    │
    ▼
afterTurn()     ← 回合后处理
    │
    ▼
ingest()        ← 摄入新消息（可选，也可在 afterTurn 中处理）
    │
    ▼
[下一轮对话]
    │
    ▼
compact()       ← 上下文压缩（按需触发）
    │
    ▼
会话结束
    │
    ▼
dispose()       ← 释放资源
```

## 重要设计

### 1. messages vs systemPrompt

ContextEngine **只能控制对话消息**，不能控制系统提示词。

| 内容 | 控制方 |
|------|--------|
| 对话历史 (`messages`) | ContextEngine |
| Agent 人格定义 | Agent 配置 |
| SOUL.md | Agent 配置 |
| 工具描述 | 系统自动生成 |
| 技能提示 | Skill 配置 |

### 2. systemPromptAddition 的作用

```typescript
// 最终系统提示词 = systemPromptAddition + 原始系统提示词
function prependSystemPromptAddition(params) {
  return `${params.systemPromptAddition}\n\n${params.systemPrompt}`;
}
```

`systemPromptAddition` 只能在系统提示词**前面追加**内容，不能删除或替换原有内容。

### 3. 清空上下文的实现

```typescript
async assemble(params): Promise<AssembleResult> {
  // 清空对话历史
  return {
    messages: [],  // 空数组 = 清空对话历史
    estimatedTokens: 0,
    systemPromptAddition: "\n[系统] 上下文已清空\n",  // 提示用户
  };
}
```

**注意**：`messages: []` 只清空对话历史，不会清空系统提示词。

### 4. ⚠️ ContextEngine 核心限制（非常重要）

**ContextEngine 只能控制发送给模型的消息，不能修改会话文件！**

```typescript
assemble() 返回的 messages:
┌─────────────────────────────────────────────┐
│  只影响本次请求发送给模型的消息                │
│  不影响会话文件中持久化的消息                  │
│  不删除已存储的对话历史                       │
└─────────────────────────────────────────────┘
```

**问题场景**：

```
会话文件: [A, B, C]
assemble() 返回 [A, B]  ← 过滤掉 C
模型看到: [A, B]
会话文件仍: [A, B, C]  ← C 没被删除！

下次请求:
params.messages = [A, B, C, D]  ← 从会话文件读取
assemble() 返回 params.messages（全部）
模型看到: [A, B, C, D]  ← C 又出现了！
```

**解决方案**：

如果需要持续过滤某些消息，必须在每次 assemble() 中都进行过滤：

```typescript
// 持续过滤方案
interface SessionState {
  messagesToFilter: number;  // 需要过滤的消息数量
}

async assemble(params): Promise<AssembleResult> {
  const state = this.state[sessionKey];

  // 每次都过滤
  if (state.messagesToFilter > 0) {
    const keepCount = params.messages.length - state.messagesToFilter;
    const filteredMessages = params.messages.slice(0, keepCount);
    return {
      messages: filteredMessages,
      estimatedTokens: estimateTokens(filteredMessages),
    };
  }

  // 正常返回
  return { messages: params.messages, ... };
}
```

**参考实现**：`focus-clear` 插件（v1.3.0）使用持续过滤方案。

### 5. 调用时机

| 方法 | 调用时机 | 用途 |
|------|----------|------|
| `bootstrap` | 会话启动时 | 初始化状态，导入历史 |
| `assemble` | 每次生成响应前 | **检测触发词的最佳时机** |
| `ingest` | turn 结束后 | 记录消息（不适合做触发检测） |
| `afterTurn` | turn 完成后 | 后处理，状态持久化 |

## 消息格式

不同通道的消息格式可能不同：

```typescript
// 字符串格式
{ role: "user", content: "用户消息" }

// 对象格式
{ role: "user", content: { text: "用户消息" } }

// 数组格式（飞书）
{ role: "user", content: [{ type: "text", text: "用户消息" }] }
```

解析消息内容的示例：

```typescript
function getMessageContent(message: any): string {
  if (!message) return "";

  if (typeof message.content === "string") {
    return message.content;
  }

  if (Array.isArray(message.content)) {
    return message.content
      .filter(part => part?.type === "text")
      .map(part => part.text)
      .join("\n");
  }

  if (message.content?.text) {
    return message.content.text;
  }

  return message.text || "";
}
```

## 注册插件

```typescript
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

export default definePluginEntry({
  id: "my-context-engine",
  name: "My Context Engine",
  description: "...",

  register(api) {
    // 从配置获取参数
    const config = api.pluginConfig || {};

    // 创建引擎实例
    const engine = new MyContextEngine(config);

    // 注册 ContextEngine
    api.registerContextEngine("my-context-engine", () => engine);
  },
});
```

## 配置

在 `~/.openclaw/openclaw.json` 中配置：

```json
{
  "plugins": {
    "slots": {
      "contextEngine": "my-context-engine"
    },
    "entries": {
      "my-context-engine": {
        "enabled": true,
        "config": {
          "customOption": "value"
        }
      }
    }
  }
}
```

## 示例：Focus Clear 插件

完整示例见：`~/.openclaw/extensions/focus-clear/index.ts`

核心逻辑：

```typescript
async assemble(params): Promise<AssembleResult> {
  const userContent = getLatestUserMessage(params.messages);

  // 检测触发词
  if (userContent.includes(this.config.triggerPhrase)) {
    return {
      messages: [],  // 清空对话历史
      estimatedTokens: 0,
      systemPromptAddition: `\n[系统] ${this.config.enterMessage}\n`,
    };
  }

  // 正常返回
  return {
    messages: params.messages,
    estimatedTokens: estimateTokens(params.messages),
  };
}
```