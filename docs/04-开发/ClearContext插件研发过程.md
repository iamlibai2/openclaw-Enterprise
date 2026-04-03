# Clear Context 插件研发过程文档

## 项目背景

用户需要一个插件，能够在飞书对话中执行 `/clear-context` 命令后，清空当前会话的上下文和系统提示词，让模型以全新状态响应后续消息。

## 需求分析

### 原始需求
1. 用户发送命令（如 `/clear-context`）
2. 系统跳过 LLM 调用，直接返回确认消息
3. 后续消息中，模型不再受之前的上下文和系统提示词影响

### 技术约束
- OpenClaw 插件框架
- 飞书渠道集成
- 会话隔离（不同用户独立状态）

## 技术探索过程

### 阶段一：调研插件机制

首先调研 OpenClaw 插件 SDK 提供的能力：

```
可用接口：
├── registerCommand()  → 注册命令，跳过 LLM，直接响应
├── registerHook()     → 注册钩子，在特定时机触发回调
├── api.on()           → 简化的钩子注册方式
├── registerGatewayMethod() → 注册 Gateway API 方法
└── ContextEngine      → 上下文引擎接口（需独占 slot）
```

### 阶段二：选择实现方案

#### 方案 A：ContextEngine
- **优点**：可以控制发送给模型的消息
- **缺点**：
  - 需要独占 `contextEngine` slot
  - 只能控制消息，无法修改系统提示词
  - 实现复杂度高

#### 方案 B：`registerCommand` + `before_prompt_build` 钩子
- **优点**：
  - 命令可跳过 LLM，直接响应
  - 钩子可修改 prompt 相关内容
  - 不需要独占 slot
- **缺点**：需验证是否能清空系统提示词

**选择方案 B**，因为更简单且不独占资源。

### 阶段三：实现初版

```typescript
// 核心实现
export default definePluginEntry({
  id: "clear-context",

  register(api) {
    // 注册命令
    api.registerCommand({
      name: "clear-context",
      handler: (ctx) => {
        // 设置清空状态
        state[userKey] = { cleared: true };
        return { type: "text", text: "已清空上下文" };
      }
    });

    // 注册钩子
    api.on("before_prompt_build", (event, ctx) => {
      if (state[userKey]?.cleared) {
        return {
          systemPrompt: "",      // 尝试清空系统提示词
          prependContext: ""     // 清空前置上下文
        };
      }
    });
  }
});
```

### 阶段四：发现问题

测试发现 `systemPrompt: ""` **无法清空系统提示词**。

深入分析 OpenClaw 源码发现：

```javascript
// OpenClaw 内部实现（简化）
const legacySystemPrompt = hookResult?.systemPrompt?.trim() || "";
if (legacySystemPrompt) {  // ← 只有非空才会应用！
  applySystemPromptOverride(session, legacySystemPrompt);
}
```

**结论**：OpenClaw 将空字符串视为"不修改"，而非"清空"。这是设计限制，不允许插件清空系统提示词。

### 阶段五：尝试替代方案

#### 方案 1：`prependSystemContext`
```typescript
return {
  prependSystemContext: "[清空模式] 之前的系统提示已无效。\n\n"
};
```
**结果**：只是在系统提示词前追加了内容，原有提示词仍然存在。

#### 方案 2：`llm_input` 钩子
```typescript
api.on("llm_input", (event, ctx) => {
  // event.systemPrompt 包含完整系统提示词
  // 但这是只读的，无法修改
});
```
**结果**：`llm_input` 是观察型钩子，只能读取，不能修改。

#### 方案 3：尝试 `inbound_claim`
这是最早的拦截点，但只能拦截消息，无法修改系统提示词。

### 阶段六：最终方案

**承认限制**：OpenClaw 设计上不允许插件清空系统提示词。

**妥协方案**：使用 `prependContext` 在用户消息前追加提示，告知模型忽略之前的上下文：

```typescript
api.on("before_prompt_build", (event, ctx) => {
  if (state[userKey]?.cleared) {
    return {
      prependContext: `【清空提示】
这是一个全新的对话开始。之前的历史消息已被忽略。
请以全新的状态回应当前用户消息，不要引用之前的对话内容。

---

`
    };
  }
});
```

**效果**：
- 系统提示词仍然存在
- 用户历史消息仍然存在
- 但模型被告知忽略它们，以全新状态响应

这是在框架限制下的最佳妥协。

## 最终实现

### 功能清单

| 功能 | 类型 | 作用 |
|------|------|------|
| `/clear-context` | 命令 | 设置清空状态 |
| `/restore-context` | 命令 | 恢复正常状态 |
| `before_prompt_build` | 钩子 | 追加清空提示 |
| `clearContext.status` | Gateway 方法 | 查询状态 |
| `clearContext.setCleared` | Gateway 方法 | 设置状态 |

### 会话隔离

不同用户的状态独立存储：

```
状态文件：~/.openclaw/clear-context-state.json

{
  "ou_995673adf1aa61ca8e5ae4e4571aff8e": {
    "cleared": true,
    "clearedAt": "2026-04-03T01:14:39.291Z"
  },
  "ou_another_user": {
    "cleared": false
  }
}
```

### 完整代码

```typescript
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

interface PluginState {
  [sessionKey: string]: { cleared: boolean; clearedAt?: string; };
}

const state: PluginState = {};

function getStateFilePath(): string {
  return (process.env.OPENCLAW_DIR || process.env.HOME + "/.openclaw") + "/clear-context-state.json";
}

function loadState(): PluginState { /* ... */ }
function saveState(s: PluginState): void { /* ... */ }

function extractUserKey(sessionKey: string | undefined): string {
  if (!sessionKey) return "default";
  const parts = sessionKey.split(":");
  const lastPart = parts[parts.length - 1];
  if (lastPart.startsWith("ou_") || lastPart.startsWith("user_") || lastPart.startsWith("uid_")) {
    return lastPart;
  }
  return sessionKey;
}

const CLEAR_PROMPT = `【清空提示】
这是一个全新的对话开始。之前的历史消息已被忽略。
请以全新的状态回应当前用户消息，不要引用之前的对话内容。

---

`;

export default definePluginEntry({
  id: "clear-context",
  name: "Clear Context",
  description: "Clear context with /clear-context command",

  register(api) {
    Object.assign(state, loadState());
    api.logger.info("ClearContext plugin registered");

    // /clear-context 命令
    api.registerCommand({
      name: "clear-context",
      description: "清空上下文",
      handler: (ctx) => {
        const userKey = extractUserKey(ctx.senderId || ctx.from || "default");
        state[userKey] = { cleared: true, clearedAt: new Date().toISOString() };
        saveState(state);
        return { type: "text", text: "已清空上下文。" };
      }
    });

    // /restore-context 命令
    api.registerCommand({
      name: "restore-context",
      description: "恢复正常上下文状态",
      handler: (ctx) => {
        const userKey = extractUserKey(ctx.senderId || ctx.from || "default");
        delete state[userKey];
        saveState(state);
        return { type: "text", text: "已恢复正常上下文状态。" };
      }
    });

    // before_prompt_build 钩子
    api.on("before_prompt_build", (event, ctx) => {
      const userKey = extractUserKey(ctx.sessionKey);
      if (state[userKey]?.cleared) {
        return { prependContext: CLEAR_PROMPT };
      }
      return {};
    });

    // Gateway 方法
    api.registerGatewayMethod("clearContext.status", async (opts) => { /* ... */ });
    api.registerGatewayMethod("clearContext.setCleared", async (opts) => { /* ... */ });
  }
});
```

### 阶段七：发现 systemPrompt 可以替换

进一步测试发现，`systemPrompt: "新内容"` **可以替换**系统提示词：

```typescript
const SIMPLE_SYSTEM_PROMPT = `你是一个助手。请简洁地回答用户问题。`;

api.on("before_prompt_build", (event, ctx) => {
  if (state[userKey]?.cleared) {
    return {
      systemPrompt: SIMPLE_SYSTEM_PROMPT,  // ✅ 非空字符串可以替换
      prependContext: CLEAR_PROMPT,
    };
  }
});
```

通过 `llm_input` 钩子验证：
```typescript
api.on("llm_input", (event, ctx) => {
  console.log(`systemPrompt = "${event.systemPrompt}"`);
});
// 输出: systemPrompt = "你是一个助手。请简洁地回答用户问题。"
```

**关键发现**：
| 返回值 | 效果 |
|--------|------|
| `systemPrompt: ""` | ❌ 不生效，被视为"不修改" |
| `systemPrompt: "新内容"` | ✅ 替换为新内容 |

### 阶段八：发现 ContextEngine slot 会覆盖 systemPrompt

测试中发现，即使返回 `systemPrompt: "新内容"`，模型仍然使用了原有的系统提示词。

经排查发现：配置中 `"contextEngine": "focus-clear"` 导致 **focus-clear 插件占据了 ContextEngine slot**。

**ContextEngine slot 的影响**：
- ContextEngine 是独占 slot，完全接管消息处理流程
- 它只能通过 `systemPromptAddition` **追加**内容
- 它**不能替换**原有的系统提示词
- `before_prompt_build` 钩子的 `systemPrompt` 返回值会被 ContextEngine 流程覆盖或忽略

**解决方案**：移除 ContextEngine 配置：
```json
// 删除 plugins.slots 中的 contextEngine 配置
{
  "plugins": {
    "slots": {
      // "contextEngine": "focus-clear"  ← 删除这行
    }
  }
}
```

移除后，`systemPrompt` 替换正常生效。

### 阶段九：最终验证（2026-04-03）

通过 `llm_input` 钩子记录的日志验证实际发送给模型的内容：

**清空前**：
```
[07:51:43] userKey=ou_xxx cleared=false
--- SYSTEM PROMPT (length=19533) ---
You are a personal assistant running inside OpenClaw.
...
# Project Context
## SOUL.md - Who You Are
你是小美，博士的专属秘书...
```

**清空后**：
```
[07:55:43] userKey=ou_xxx cleared=true
--- SYSTEM PROMPT (length=18) ---
你是一个助手。请简洁地回答用户问题。
```

**验证结果**：
- ✅ 系统提示词成功替换（19533 → 18 字符）
- ✅ Project Context（SOUL.md、IDENTITY.md）不再出现
- ✅ 会话历史消息仍存在（不受 `before_prompt_build` 控制）

### 阶段十：CLEAR_PROMPT 置空（2026-04-03）

用户要求将用户消息前的提示置空：

```typescript
// 原来
const CLEAR_PROMPT = `【清空提示】
这是一个全新的对话开始。之前的历史消息已被忽略。
请以全新的状态回应当前用户消息，不要引用之前的对话内容。
`;

// 修改后
const CLEAR_PROMPT = "";
```

**效果**：用户消息前不再追加任何提示内容，模型直接收到用户原始消息。

### 阶段十一：用户对 `/context detail` 的疑问

用户报告 `/context detail` 仍显示完整系统提示词。

**分析**：

| 命令/钩子 | 测量内容 | 是否经过钩子 |
|-----------|----------|--------------|
| `/context detail` | 配置状态（Agent 原始配置） | ❌ 不经过 |
| `llm_input` 钩子 | 实际发送给模型的内容 | ✅ 经过钩子处理 |

**结论**：`/context detail` 显示的是"配置文件里有什么"，不是"模型实际收到什么"。这是预期行为，不是问题。验证实际内容应查看 `llm_input` 日志。

## 最终版本

### 插件代码（最终版）

```typescript
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

const state: PluginState = {};

// 简化的系统提示词（替换原有的）
const SIMPLE_SYSTEM_PROMPT = `你是一个助手。请简洁地回答用户问题。`;

// 清空提示内容（置空）
const CLEAR_PROMPT = "";

export default definePluginEntry({
  id: "clear-context",
  name: "Clear Context",
  description: "Clear context with /clear-context command or trigger keywords",

  register(api) {
    Object.assign(state, loadState());

    // /clear-context 命令
    api.registerCommand({
      name: "clear-context",
      handler: (ctx) => {
        state[userKey] = { cleared: true, clearedAt: new Date().toISOString() };
        saveState(state);
        return { type: "text", text: "已清空上下文。" };
      },
    });

    // /restore-context 命令
    api.registerCommand({
      name: "restore-context",
      handler: (ctx) => {
        delete state[userKey];
        saveState(state);
        return { type: "text", text: "已恢复正常上下文状态。" };
      },
    });

    // before_prompt_build 钩子 - 替换系统提示词
    api.on("before_prompt_build", (event, ctx) => {
      if (state[userKey]?.cleared) {
        return {
          systemPrompt: SIMPLE_SYSTEM_PROMPT,
          prependContext: CLEAR_PROMPT,  // 置空
        };
      }
      return {};
    });

    // llm_input 钩子 - 调试日志
    api.on("llm_input", (event, ctx) => {
      // 记录完整信息到 ~/.openclaw/llm-input-debug.log
    });

    // Gateway 方法
    api.registerGatewayMethod("clearContext.status", async (opts) => { /* ... */ });
    api.registerGatewayMethod("clearContext.setCleared", async (opts) => { /* ... */ });
  },
});
```

### 功能清单（最终版）

| 功能 | 类型 | 作用 |
|------|------|------|
| `/clear-context` | 命令 | 设置清空状态，直接响应 |
| `/restore-context` | 命令 | 恢复正常状态 |
| `before_prompt_build` | 钩子 | 替换系统提示词为简化版本 |
| `llm_input` | 钩子 | 记录调试日志，验证实际内容 |
| `clearContext.status` | Gateway 方法 | 查询状态 |
| `clearContext.setCleared` | Gateway 方法 | 设置状态 |

## 经验总结

### 技术发现

1. **systemPrompt 替换规则**
   - `systemPrompt: ""` → 不生效（视为"不修改"）
   - `systemPrompt: "新内容"` → ✅ 可以替换
   - **但如果有 ContextEngine slot 占用，会被覆盖**

2. **ContextEngine slot 的优先级**
   - ContextEngine 完全接管消息流程
   - 它会覆盖 `before_prompt_build` 的 `systemPrompt` 返回值
   - 如需使用 `systemPrompt` 替换功能，必须移除 ContextEngine slot

3. **钩子能力边界（修正）**
   - `before_prompt_build`：
     - 无 ContextEngine：可追加内容，**可替换**系统提示词
     - 有 ContextEngine：修改可能被覆盖
   - `llm_input`：只读，可获取完整系统提示词（用于验证）
   - `inbound_claim`：可拦截，不可修改系统提示词

3. **sessionKey 格式差异**
   - 命令 handler：`feishu:ou_xxx` 或 `ctx.senderId`
   - 钩子 handler：`agent:xiaomei:feishu:xiaomei:direct:ou_xxx`
   - 需要统一提取用户标识

### 设计决策

| 决策 | 理由 |
|------|------|
| 使用 `registerCommand` | 跳过 LLM，直接响应，节省 token |
| 使用状态文件持久化 | Gateway 重启后状态保留 |
| 提取 `ou_xxx` 作为用户标识 | 支持多渠道，统一用户标识 |
| 使用 `systemPrompt` 替换 | 真正替换系统提示词（需移除 ContextEngine slot） |
| 使用 `llm_input` 验证 | 观察实际发送给模型的系统提示词 |

### 替代方案建议

如果需要真正的清空效果，可考虑：

1. **使用 `/reset` 或 `/new` 命令**
   - 这是 OpenClaw 内置功能，真正清空会话
   - 缺点：无法自定义触发方式

2. **创建无系统提示词的 Agent**
   - 配置一个"干净"的 Agent
   - 通过路由将特定请求导向该 Agent

3. **等待 OpenClaw 官方支持**
   - 提交 Feature Request
   - 等待 `systemPrompt: ""` 被支持

## 参考资料

- OpenClaw 插件 SDK 类型定义：`/usr/lib/node_modules/openclaw/dist/plugin-sdk/src/plugins/types.d.ts`
- OpenClaw 钩子文档：`/usr/lib/node_modules/openclaw/docs/concepts/agent-loop.md`
- 本项目钩子系统教程：`docs/04-开发/OpenClaw插件开发指南-钩子系统.md`