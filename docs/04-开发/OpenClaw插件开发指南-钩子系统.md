# OpenClaw 插件开发指南 - 钩子系统

本文档介绍 OpenClaw 插件系统中的钩子（Hooks）机制，帮助开发者理解和使用钩子来扩展 OpenClaw 功能。

## 概念总览

```
┌─────────────────────────────────────────────────────────────┐
│                        插件 (Plugin)                         │
│  一个独立模块，可注册命令、钩子、工具等                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   api.registerCommand()  ──→  注册 /命令                     │
│   api.registerTool()     ──→  注册 工具                       │
│   api.registerProvider() ──→  注册 模型提供商                  │
│   api.on()               ──→  注册 钩子处理器                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     钩子 (Hook)                              │
│  在特定时机被触发的回调函数                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   before_prompt_build  ──→  构建 prompt 前                  │
│   before_agent_start   ──→  Agent 启动前                     │
│   llm_input            ──→  发送给 LLM 前                    │
│   llm_output           ──→  LLM 返回后                       │
│   inbound_claim        ──→  收到消息时（最早）                 │
│   message_received     ──→  消息接收后                       │
│   agent_end            ──→  Agent 结束后                     │
│   ...                                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      事件 (Event)                            │
│  钩子回调函数的参数，包含当前上下文信息                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   // llm_input 事件示例                                      │
│   {                                                         │
│     runId: "...",                                           │
│     sessionId: "...",                                       │
│     provider: "bailian",                                    │
│     model: "glm-5",                                         │
│     systemPrompt: "You are a personal assistant...",        │
│     prompt: "用户消息...",                                    │
│     historyMessages: [...]                                  │
│   }                                                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 钩子执行顺序

```
用户消息
    │
    ▼
┌─────────────────────┐
│   inbound_claim     │  ← 最早，可拦截消息
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  message_received   │  ← 消息接收通知
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ before_model_resolve│  ← 可修改模型选择
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ before_agent_start  │  ← Agent 启动前，可修改 prompt/model
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ before_prompt_build │  ← 构建 prompt 前，可追加内容
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│     llm_input       │  ← 发送给 LLM 前，可读取完整 prompt
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│       [LLM]         │  ← 模型推理
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│    llm_output       │  ← LLM 返回后
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│     agent_end       │  ← Agent 结束
└─────────────────────┘
```

## 钩子类型

### 1. 观察型钩子（只读）

只能读取数据，不能修改。

| 钩子名 | 触发时机 | 事件数据 |
|--------|----------|----------|
| `llm_input` | 发送给 LLM 前 | `systemPrompt`, `prompt`, `historyMessages` |
| `llm_output` | LLM 返回后 | `assistantTexts`, `usage` |
| `agent_end` | Agent 结束后 | `messages`, `success`, `error` |
| `message_received` | 消息接收后 | `from`, `content` |
| `message_sent` | 消息发送后 | `to`, `content`, `success` |

### 2. 修改型钩子

可以返回数据修改后续流程。

| 钩子名 | 触发时机 | 可修改内容 |
|--------|----------|------------|
| `before_prompt_build` | 构建 prompt 前 | `systemPrompt`, `prependContext`, `prependSystemContext`, `appendSystemContext` |
| `before_agent_start` | Agent 启动前 | 上述 + `modelOverride`, `providerOverride` |
| `before_model_resolve` | 模型解析前 | `modelOverride`, `providerOverride` |

### 3. 拦截型钩子

可以阻断流程。

| 钩子名 | 触发时机 | 拦截方式 |
|--------|----------|----------|
| `inbound_claim` | 收到消息时 | 返回 `{ handled: true }` |
| `before_tool_call` | 工具调用前 | 返回 `{ block: true }` |
| `before_message_write` | 消息写入前 | 返回 `{ block: true }` |

## 钩子事件详解

### llm_input

**最常用的观察钩子**，可以读取完整的系统提示词。

```typescript
api.on("llm_input", (event, ctx) => {
  // event 参数
  const {
    runId,           // 运行 ID
    sessionId,       // 会话 ID
    provider,        // 提供商，如 "bailian"
    model,           // 模型，如 "glm-5"
    systemPrompt,    // ★ 完整的系统提示词
    prompt,          // 用户输入
    historyMessages, // 历史消息
    imagesCount      // 图片数量
  } = event;

  // ctx 上下文
  const {
    sessionKey,      // 会话标识
    agentId,         // Agent ID
    workspaceDir     // 工作目录
  } = ctx;

  console.log("System prompt:", systemPrompt);
});
```

### before_prompt_build

**修改型钩子**，可以追加内容到系统提示词。

```typescript
api.on("before_prompt_build", (event, ctx) => {
  // event 参数
  const {
    prompt,    // 用户输入
    messages   // 会话消息
  } = event;

  // 返回值可以修改后续流程
  return {
    // 追加到用户 prompt 前面
    prependContext: "这是前置上下文\n\n",

    // 追加到系统提示词前面（可被缓存）
    prependSystemContext: "[插件提示] 这是前置系统上下文\n\n",

    // 追加到系统提示词后面（可被缓存）
    appendSystemContext: "\n\n[插件提示] 这是后置系统上下文",

    // ⚠️ 注意：systemPrompt 只能覆盖为非空字符串
    // 空字符串 "" 不会被应用！
    // systemPrompt: "新的系统提示词"  // 仅非空时生效
  };
});
```

**重要限制**：`systemPrompt` 返回空字符串 `""` 不会被应用，OpenClaw 将其视为"不修改"。

**注意**：如果配置了 `contextEngine` slot，该 slot 的插件会完全接管消息处理流程，可能会覆盖 `before_prompt_build` 的 `systemPrompt` 返回值。如需使用 `systemPrompt` 替换功能，应移除 ContextEngine slot 配置。

### inbound_claim

**最早的拦截点**，可以完全接管消息处理。

```typescript
api.on("inbound_claim", (event, ctx) => {
  // event 参数
  const {
    content,          // 消息内容
    channel,          // 渠道，如 "feishu"
    senderId,         // 发送者 ID
    conversationId,   // 会话 ID
    isGroup,          // 是否群聊
    wasMentioned      // 是否被 @
  } = event;

  // 返回 { handled: true } 拦截消息
  if (content.startsWith("/my-command")) {
    // 处理自定义命令...
    return { handled: true };
  }

  // 返回空或 { handled: false } 放行
  return {};
});
```

### before_tool_call

拦截工具调用。

```typescript
api.on("before_tool_call", (event, ctx) => {
  const {
    toolName,   // 工具名称
    params,     // 工具参数
    runId,      // 运行 ID
    toolCallId  // 工具调用 ID
  } = event;

  // 阻止危险操作
  if (toolName === "exec" && params.command?.includes("rm -rf")) {
    return {
      block: true,
      blockReason: "禁止执行删除命令"
    };
  }

  // 修改参数
  return {
    params: { ...params, safe: true }
  };
});
```

## 插件模板

### 最小钩子插件

```typescript
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

export default definePluginEntry({
  id: "my-hook-plugin",
  name: "My Hook Plugin",
  description: "一个简单的钩子插件",

  register(api) {
    // 监听 llm_input 钩子
    api.on("llm_input", (event, ctx) => {
      console.log(`[${ctx.sessionKey}] System prompt length: ${event.systemPrompt?.length || 0}`);
    });
  }
});
```

### 完整插件示例

```typescript
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

interface PluginState {
  [key: string]: {
    enabled: boolean;
    enabledAt?: string;
  };
}

const state: PluginState = {};

export default definePluginEntry({
  id: "example-plugin",
  name: "Example Plugin",
  description: "示例插件，展示各种功能",
  version: "1.0.0",

  register(api) {
    api.logger.info("Example plugin registered");

    // 注册命令
    api.registerCommand({
      name: "example-toggle",
      description: "切换示例模式",
      handler: (ctx) => {
        const userId = ctx.senderId || "default";
        state[userId] = {
          enabled: !state[userId]?.enabled,
          enabledAt: new Date().toISOString()
        };
        return {
          type: "text",
          text: state[userId].enabled ? "已启用" : "已禁用"
        };
      }
    });

    // 注册钩子
    api.on("llm_input", (event, ctx) => {
      const userId = ctx.sessionKey?.split(":").pop() || "default";
      if (state[userId]?.enabled) {
        console.log(`[Example] Processing for user ${userId}`);
        console.log(`[Example] Model: ${event.provider}/${event.model}`);
      }
    });

    // 注册 Gateway 方法
    api.registerGatewayMethod("example.status", async (opts) => {
      const userId = opts.params?.userId || "default";
      opts.respond(true, {
        enabled: state[userId]?.enabled || false,
        enabledAt: state[userId]?.enabledAt
      });
    });
  }
});
```

## 内置钩子包

OpenClaw 自带一组内置钩子包（bundled hooks），它们是特殊类型的插件。

```bash
# 查看内置钩子包
openclaw hooks list
```

| 钩子包 | 功能 |
|--------|------|
| 🚀 boot-md | Gateway 启动时自动运行 BOOT.md |
| 📎 bootstrap-extra-files | 注入额外的 workspace 引导文件 |
| 📝 command-logger | 记录所有命令事件到审计日志 |
| 💾 session-memory | `/new` 或 `/reset` 时保存会话上下文 |

**注意**：`openclaw hooks install` 已废弃，请使用 `openclaw plugins install`。

## 插件来源分类

| 来源 | 标识 | 目录 |
|------|------|------|
| 内置 | `openclaw-bundled` | `/usr/lib/node_modules/openclaw/dist/extensions/` |
| 全局 | `global` | `~/.openclaw/extensions/` |
| 工作空间 | `workspace` | `<workspace>/.openclaw/extensions/` |

## 常见问题

### Q: 如何读取完整的系统提示词？

使用 `llm_input` 钩子，它的 `event.systemPrompt` 包含完整内容。

### Q: 为什么 `before_prompt_build` 返回空 `systemPrompt` 无效？

OpenClaw 的实现中，空字符串被视为"不修改"而非"清空"。这是设计限制。

### Q: 如何阻止某条消息被处理？

在 `inbound_claim` 钩子中返回 `{ handled: true }`。

### Q: 钩子可以单独存在吗？

不可以。钩子必须通过插件注册，依赖插件框架的调度机制。

### Q: 如何调试钩子？

1. 使用 `console.log()` 输出到 Gateway 日志
2. 使用 `api.logger.info()` 记录日志
3. 写入文件进行持久化调试

## 参考资源

- OpenClaw 官方文档：https://docs.openclaw.ai/cli/hooks
- 插件 SDK 类型定义：`/usr/lib/node_modules/openclaw/dist/plugin-sdk/src/plugins/types.d.ts`