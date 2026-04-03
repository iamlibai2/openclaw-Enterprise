# Focus Clear 插件调试记录

> 日期：2026-04-02
> 插件：focus-clear
> 目标：实现当用户发送"专注模式"时清空上下文窗口

## 背景

开发了一个简单的 OpenClaw ContextEngine 插件，当用户消息包含"专注模式"时，清空当前上下文窗口。插件注册成功，但在实际测试中不触发。

## 问题排查过程

### 问题1：WebUI Dashboard 不触发

**现象**：在 WebUI Dashboard 中发送"专注模式"，插件没有反应。

**排查步骤**：

```bash
# 1. 检查插件是否注册成功
openclaw status | grep FocusClear
# 输出：FocusClear plugin registered - clears context on '专注模式'

# 2. 检查状态文件
cat ~/.openclaw/focus-clear-state.json
# 输出：{} (空，说明 ingest 没有被调用)

# 3. 检查 Gateway 日志
grep "FocusClear" /tmp/openclaw/openclaw-*.log
# 只有注册日志，没有 assemble/ingest 调用日志
```

**分析**：

检查配置发现：

```json
{
  "acp": {
    "enabled": true,
    "defaultAgent": "claude"
  }
}
```

WebUI Dashboard 默认使用 **ACP Agent**（如 claude），而不是 OpenClaw Agent（如 xiaomei、aqiang）。

**关键发现**：
- ACP Agents 的消息不经过 ContextEngine
- `plugins.slots.contextEngine` 只对 OpenClaw Agents 生效
- 需要通过飞书/钉钉等通道测试，这些通道使用 OpenClaw Agents

**结论**：转向飞书通道测试。

---

### 问题2：ingest 时机问题

**现象**：飞书发送消息后，日志显示 assemble 被调用，但没有检测到触发词。

**排查步骤**：

添加调试日志后查看：

```
FocusClear: assemble called for session agent:xiaomei:..., messages=7, shouldClear=undefined
```

**分析**：

阅读 OpenClaw 源码发现：

```javascript
// pi-embedded-CbCYZxIb.js:174605
// ingest 在 turn 结束后才调用
if (newMessages.length > 0) {
  await params.contextEngine.ingest?.({
    sessionId: params.sessionIdUsed,
    sessionKey: params.sessionKey,
    message: msg
  });
}
```

**消息处理流程**：

```
用户发送"专注模式"
    ↓
assemble() - 检查 shouldClear（此时为 false）
    ↓
AI 响应
    ↓
turn 结束 → ingest() - 检测到触发词 → 设置 shouldClear=true
    ↓
用户发送下一条消息
    ↓
assemble() - shouldClear=true → 清空上下文
```

**问题**：`ingest` 在 turn 结束后才调用，导致清空延迟到下一轮。

**解决方案**：在 `assemble` 中直接检查最新用户消息。

```typescript
async assemble(params) {
  // 检查最新的用户消息是否包含触发词
  if (params.messages && params.messages.length > 0) {
    for (let i = params.messages.length - 1; i >= 0; i--) {
      const msg = params.messages[i];
      if (msg?.role === "user") {
        const content = getMessageContent(msg);
        if (content.includes(this.config.triggerPhrase)) {
          return {
            messages: [],
            estimatedTokens: 0,
            systemPromptAddition: `\n[系统] ${this.config.responseMessage}\n`,
          };
        }
        break;
      }
    }
  }
}
```

---

### 问题3：消息格式解析错误

**现象**：修改后测试，日志显示检查了消息但没有检测到触发词。

**排查步骤**：

添加详细日志：

```typescript
console.log(`FocusClear: checking user message: "${content.substring(0, 100)}..."`);
```

查看日志：

```
FocusClear: checking user message [1]: "[{"type":"text","text":"Sender (untrusted metadata)..."
```

**分析**：

消息格式不是纯文本字符串，而是 JSON 数组：

```json
[
  {
    "type": "text",
    "text": "System: [2026-04-02 18:02:05 GMT+8] Feishu[xiaomei] DM | ou_995673adf1aa61ca8e5ae4e4571aff8e\n专注模式测试"
  }
]
```

原来的 `getMessageContent` 函数：

```typescript
function getMessageContent(message: any): string {
  if (typeof message.content === "string") return message.content;
  if (message.content?.text) return message.content.text;
  if (message.content && typeof message.content === "object") return JSON.stringify(message.content);
  return message.text || "";
}
```

当 `message.content` 是数组时，直接 `JSON.stringify` 了整个数组，导致无法正确提取文本内容。

**解决方案**：修复消息解析函数。

```typescript
function getMessageContent(message: any): string {
  if (!message) return "";

  // 处理字符串内容
  if (typeof message.content === "string") return message.content;

  // 处理 content 对象
  if (message.content) {
    // 数组格式: [{type: "text", text: "..."}]
    if (Array.isArray(message.content)) {
      const texts: string[] = [];
      for (const part of message.content) {
        if (part?.type === "text" && typeof part.text === "string") {
          texts.push(part.text);
        } else if (typeof part === "string") {
          texts.push(part);
        }
      }
      return texts.join("\n");
    }

    // 对象格式: {text: "..."} 或 {type: "text", text: "..."}
    if (message.content.text) return message.content.text;
    if (typeof message.content === "object") return JSON.stringify(message.content);
  }

  return message.text || "";
}
```

---

### 最终成功

重新构建并测试：

```bash
cd ~/.openclaw/extensions/focus-clear && npm run build
pkill -f openclaw-gateway  # 重启 Gateway
```

飞书发送"专注模式测试"，日志显示：

```
FocusClear: Detected "专注模式" in user message for session agent:xiaomei:feishu:xiaomei:direct:ou_995673adf1aa61ca8e5ae4e4571aff8e
```

AI 响应：

```
[系统] 已进入专注模式，上下文已清空。
```

### 问题4：退出专注模式后模型仍记得专注模式期间的对话

**现象**：在飞书测试中，发送"退出专注模式"后，机器人仍然记得专注模式期间说的"我感冒了"。

**排查步骤**：

查看日志时间线：

```
20:35:14 - ENTER focus mode, saving 3 messages
20:38:03 - in focus mode, adding marker (专注模式中对话："感冒了")
20:50:39 - EXIT focus mode, restoring saved context
```

退出时确实执行了，状态文件也被清空了，但模型仍然记得。

**分析**：

这是 **ContextEngine 的核心设计限制**：

```
ContextEngine.assemble() 返回值：
┌─────────────────────────────────────────────────┐
│  messages: []        ← 只控制发送给模型的消息     │
│  estimatedTokens: 0  ← token 估算                │
│  systemPromptAddition ← 系统提示词追加           │
└─────────────────────────────────────────────────┘

❌ 不能修改会话文件（session file）
❌ 不能删除已存储的消息
```

**消息流程分析**：

```
会话文件消息流：
[A, B, C] → 进入专注模式 → [A, B, C, "dudu", 回复, "感冒了", 回复]
                                         ↑
                                    会话文件记录

退出时 assemble() 返回 savedMessages [A, B, C]
    ↓
只影响当次请求发送给模型的消息
    ↓
会话文件中仍有 [A, B, C, "dudu", ..., "感冒了", ...]
    ↓
下次请求 params.messages 包含全部消息
    ↓
focusMode=false → 返回 params.messages（全部）
    ↓
模型看到了专注模式期间的对话！
```

**根本原因**：

| 操作 | ContextEngine 能做 | ContextEngine 不能做 |
|------|-------------------|---------------------|
| 过滤发送给模型的消息 | ✅ 返回 filtered messages | - |
| 删除会话文件中的消息 | ❌ | 无法修改 session file |
| 恢复上下文（持久） | ❌ | 只影响当次请求 |

**解决方案**：持续过滤专注模式期间的消息

退出专注模式后，保留状态，每次 assemble() 时持续过滤：

```typescript
interface SessionState {
  focusMode: boolean;
  savedMessages?: any[];
  // 新增：需要持续过滤的消息数量
  messagesToFilter?: number;  // 专注模式期间产生的消息数
  exitedAt?: string;          // 退出时间
}

// 退出时设置过滤数量
if (userContent.includes(this.config.exitPhrase)) {
  const focusModeMessagesCount = params.messages.length - savedMessages.length - 1;
  this.state[key] = {
    focusMode: false,
    savedMessages: savedMessages,
    messagesToFilter: focusModeMessagesCount,  // 持续过滤
  };
}

// 后续请求持续过滤
if (sessionState.messagesToFilter > 0) {
  const keepCount = params.messages.length - sessionState.messagesToFilter;
  const filteredMessages = params.messages.slice(0, keepCount);
  return { messages: filteredMessages, ... };
}
```

**修复后的完整流程**：

```
进入专注模式 (dudu):
    │
    ├─ 保存当前上下文 [A, B, C]
    ├─ 返回 messages: []
    └─ 会话文件写入："dudu", 回复
        ↓
专注模式中对话:
    │
    ├─ assemble() 返回 params.messages（添加标记）
    └─ 会话文件写入："感冒了", 回复
        ↓
退出专注模式:
    │
    ├─ 计算 messagesToFilter = 4 (dudu+回复+感冒了+回复)
    ├─ 返回 savedMessages [A, B, C]
    └─ 状态保留（不立即清除）
        ↓
后续请求:
    │
    ├─ params.messages = [A, B, C, "dudu", ..., "感冒了", ..., 新消息]
    ├─ 检测 messagesToFilter = 4
    ├─ keepCount = total - 4
    ├─ 返回 filteredMessages = [A, B, C, 新消息]
    └─ 模型不看到"感冒了"！
```

---

## 经验总结

### 1. OpenClaw Agent vs ACP Agent

| 类型 | 说明 | ContextEngine 支持 |
|------|------|-------------------|
| OpenClaw Agent | 飞书、钉钉等通道使用 | ✅ 支持 |
| ACP Agent | WebUI Dashboard 默认使用 | ❌ 不支持 |

测试 ContextEngine 插件需要通过飞书/钉钉通道。

### 2. ContextEngine 生命周期

```
bootstrap() → 会话启动时
    ↓
assemble() → 每次生成响应前（检查消息的最佳时机）
    ↓
AI 响应
    ↓
ingest() → turn 结束后（不适合做触发检测）
    ↓
afterTurn() → turn 完成后
```

**关键点**：触发词检测应在 `assemble()` 中进行，而不是 `ingest()`。

### 3. 消息格式多样性

不同通道的消息格式可能不同：

```javascript
// 字符串格式
{ "content": "用户消息" }

// 对象格式
{ "content": { "text": "用户消息" } }

// 数组格式（飞书）
{ "content": [{ "type": "text", "text": "用户消息" }] }
```

解析消息内容时需要处理所有情况。

### 4. 调试技巧

1. **添加详细日志**：在关键方法入口打印参数
2. **检查状态文件**：确认状态是否正确保存
3. **阅读源码**：了解框架的实际调用时机
4. **隔离变量**：先确认通道类型，再确认消息格式

### 5. ContextEngine 核心限制（重要！）

**ContextEngine 只能控制发送给模型的消息，不能修改会话文件！**

这是 ContextEngine 接口设计的根本限制：

```typescript
interface AssembleResult {
  messages: AgentMessage[];      // ← 只控制本次请求的消息
  estimatedTokens: number;       // ← token 估算
  systemPromptAddition?: string; // ← 系统提示词追加
}
```

**不能做的事情**：
- ❌ 删除会话文件中的消息
- ❌ 修改已持久化的对话历史
- ❌ 持久化上下文恢复（除非每次 assemble() 都过滤）

**解决方案**：
- ✅ 在每次 assemble() 中持续过滤不需要的消息
- ✅ 保存状态（messagesToFilter）并在后续请求中应用

### 6. 专注模式期间对话的处理方式

| 方案 | 行为 | 适用场景 |
|------|------|----------|
| 当前实现 | 丢弃专注模式对话 | 专注模式用于临时任务，不需要保留 |
| 方案A | 追加专注模式对话到恢复的上下文后 | 专注模式对话有价值，需要保留 |
| 方案B | 专注模式对话单独保存，可查询 | 需要审计或回顾专注模式任务 |
| 方案C | 退出时询问用户是否保留 | 用户自主决定 |

当前实现采用"丢弃"方案，通过持续过滤实现。

## 完整代码

最终版本的插件代码位于：`~/.openclaw/extensions/focus-clear/index.ts`

关键修复点：
1. 在 `assemble()` 中检测触发词（而不是 `ingest()`）
2. 正确解析数组格式的消息内容（飞书格式）
3. 从后向前遍历，找到最新的用户消息
4. 退出后持续过滤专注模式期间的消息（ContextEngine 无法删除会话文件）

## Gateway API

### focusClear.status

获取会话的状态。

```python
from gateway_sync import sync_call

result = sync_call('focusClear.status', {'sessionKey': 'agent:xiaomei:...'})
print(result)  # { status: { focusMode: false, messagesToFilter: 4 } }
```

### focusClear.setFocusMode

手动设置专注模式状态。

```python
result = sync_call('focusClear.setFocusMode', {'sessionKey': 'agent:xiaomei:...', 'enabled': True})
```

### focusClear.clearFilterState

完全清除过滤状态（不再过滤专注模式期间的消息）。

```python
result = sync_call('focusClear.clearFilterState', {'sessionKey': 'agent:xiaomei:...'})
```

## 版本历史

### v1.0.0 (2026-04-02)

- 初始版本
- 支持触发词检测和上下文清空
- 支持飞书等多通道消息格式

### v1.2.0 (2026-04-02)

- 新增：保存进入专注模式前的上下文
- 新增：退出时恢复保存的上下文
- 新增：专注模式标记

### v1.3.0 (2026-04-02)

- **关键修复**：退出后持续过滤专注模式期间的消息
- 新增：`messagesToFilter` 状态字段
- 新增：`clearFilterState` Gateway 方法
- 解决 ContextEngine 无法修改会话文件的限制