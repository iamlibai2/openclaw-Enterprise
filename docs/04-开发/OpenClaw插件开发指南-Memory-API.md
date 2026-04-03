# OpenClaw 插件开发指南 - Memory & Session API

## 概述

本文档记录了 Memory & Session API 插件的开发过程，作为 OpenClaw 插件开发的参考示例。

## 背景

Admin UI 改造为 WebSocket 架构后，需要远程访问 Agent 的记忆文件和会话记录。Gateway 内置的 `sessions.list` 和 `sessions.get` 方法只读取当前活跃的会话，而 sessions 目录下还有大量 `.jsonl.reset.*` 归档文件保存着历史聊天记录。因此开发了此插件，支持读取记忆文件、活跃会话和归档会话。

## 插件位置

```
~/.openclaw/extensions/memory-api/
├── package.json          # NPM 包配置
├── openclaw.plugin.json  # OpenClaw 插件元数据
├── index.ts              # 插件入口代码
├── tsconfig.json         # TypeScript 配置
├── dist/                 # 构建输出
│   ├── index.js
│   └── index.d.ts
└── README.md             # 使用文档
```

## 文件存储结构

### Memory 文件位置

```
~/.openclaw/
├── workspace/            # main agent
│   └── memory/
│       ├── 2026-03-28.md
│       └── 2026-03-29.md
├── workspace-aqiang/     # aqiang agent
│   └── memory/
│       └── ...
└── workspace-xiaomei/    # xiaomei agent
    └── memory/
        └── ...
```

### Session 文件位置

```
~/.openclaw/agents/{agentId}/sessions/
├── sessions.json                           # 会话索引
├── {sessionId}.jsonl                       # 活跃会话
├── {sessionId}.jsonl.reset.{timestamp}     # 归档会话
└── ...
```

**示例**：
```
~/.openclaw/agents/aqiang/sessions/
├── sessions.json
├── e004b058-0256-4c9b-b523-f55f674d36b5.jsonl          # 活跃
├── 9934c0ab-0e87-416d-8fc0-f4c337f29866.jsonl.reset.2026-03-31T10-16-41.215Z  # 归档
└── ...
```

## API 接口

### Memory API

#### memory.list

列出 Agent 的记忆文件：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| agentId | string | 是 | Agent ID（如 "main", "aqiang"） |

**返回**：
```json
{
  "files": [
    {
      "name": "2026-03-28.md",
      "path": "/home/user/.openclaw/workspace/memory/2026-03-28.md",
      "size": 1234,
      "modifiedAt": "2026-03-28T10:00:00.000Z"
    }
  ]
}
```

#### memory.get

获取指定记忆文件内容：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| agentId | string | 是 | Agent ID |
| name | string | 是 | 文件名（如 "2026-03-28.md"） |

**返回**：
```json
{
  "content": "# 2026-03-28\n\n今日工作...",
  "size": 1234,
  "modifiedAt": "2026-03-28T10:00:00.000Z"
}
```

### Session Files API

#### sessionFiles.list

列出所有会话文件（活跃 + 归档）：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| agentId | string | 是 | - | Agent ID |
| includeReset | boolean | 否 | true | 是否包含归档文件 |

**返回**：
```json
{
  "sessions": [
    {
      "key": "agent:aqiang:feishu:aqiang:direct:ou_xxx",
      "sessionId": "e004b058-0256-4c9b-b523-f55f674d36b5",
      "updatedAt": 1774985840056,
      "updatedAtISO": "2026-03-28T10:00:00.000Z",
      "chatType": "direct",
      "lastChannel": "feishu",
      "sessionFile": "/home/user/.openclaw/agents/aqiang/sessions/e004b058....jsonl",
      "status": "active"
    }
  ],
  "resetFiles": [
    {
      "filename": "9934c0ab-0e87-416d-8fc0-f4c337f29866.jsonl.reset.2026-03-31T10-16-41.215Z",
      "sessionId": "9934c0ab-0e87-416d-8fc0-f4c337f29866",
      "resetAt": "2026-03-31T10-16-41.215Z",
      "size": 700491,
      "modifiedAt": "2026-03-31T10:16:41.215Z",
      "status": "reset"
    }
  ],
  "totalActive": 4,
  "totalReset": 4
}
```

#### sessionFiles.listReset

只列出归档会话文件：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| agentId | string | 是 | Agent ID |

**返回**：
```json
{
  "files": [
    {
      "filename": "9934c0ab-0e87-416d-8fc0-f4c337f29866.jsonl.reset.2026-03-31T10-16-41.215Z",
      "sessionId": "9934c0ab-0e87-416d-8fc0-f4c337f29866",
      "resetAt": "2026-03-31T10-16-41.215Z",
      "size": 700491,
      "modifiedAt": "2026-03-31T10:16:41.215Z"
    }
  ],
  "total": 4
}
```

#### sessionFiles.get

读取会话文件内容（支持活跃和归档文件）：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| agentId | string | 是 | - | Agent ID |
| filename | string | 是 | - | 文件名或 sessionId |
| format | string | 否 | "raw" | "raw" 或 "messages" |

**filename 格式**：
- sessionId（如 `e004b058-0256-4c9b-b523-f55f674d36b5`）→ 自动匹配 .jsonl 文件
- 完整文件名（如 `xxx.jsonl.reset.xxx`）→ 直接读取

**返回（raw 格式）**：
```json
{
  "lines": [
    {"type": "session", "version": 1, "id": "xxx", ...},
    {"type": "message", "role": "user", "content": "...", ...},
    {"type": "message", "role": "assistant", "content": "...", ...}
  ],
  "totalLines": 152,
  "size": 700491,
  "file": "xxx.jsonl.reset.xxx"
}
```

**返回（messages 格式）**：
```json
{
  "messages": [
    {"role": "user", "content": "...", "timestamp": "..."},
    {"role": "assistant", "content": "...", "timestamp": "..."}
  ],
  "totalLines": 152,
  "messageCount": 138,
  "size": 700491,
  "file": "xxx.jsonl.reset.xxx"
}
```

#### sessionFiles.search

搜索会话内容（包括归档文件）：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| agentId | string | 是 | - | Agent ID |
| query | string | 是 | - | 搜索关键词 |
| limit | number | 否 | 10 | 最大结果数 |
| searchReset | boolean | 否 | true | 是否搜索归档文件 |

**返回**：
```json
{
  "results": [
    {
      "filename": "e004b058-0256-4c9b-b523-f55f674d36b5.jsonl",
      "sessionId": "e004b058-0256-4c9b-b523-f55f674d36b5",
      "isReset": false,
      "resetAt": null,
      "size": 127393,
      "modifiedAt": "2026-04-01T03:37:00.000Z",
      "matchCount": 3,
      "matches": [...]
    },
    {
      "filename": "9934c0ab-0e87-416d-8fc0-f4c337f29866.jsonl.reset.2026-03-31T10-16-41.215Z",
      "sessionId": "9934c0ab-0e87-416d-8fc0-f4c337f29866",
      "isReset": true,
      "resetAt": "2026-03-31T10-16-41.215Z",
      "size": 700491,
      "modifiedAt": "2026-03-31T02:26:00.000Z",
      "matchCount": 5,
      "matches": [...]
    }
  ],
  "total": 2,
  "query": "飞书"
}
```

## 使用示例

### Python 调用

```python
from gateway_sync import sync_call

# 列出记忆文件
result = sync_call('memory.list', {'agentId': 'aqiang'})
for f in result['files']:
    print(f"{f['name']}: {f['size']} bytes")

# 列出归档会话
result = sync_call('sessionFiles.listReset', {'agentId': 'aqiang'})
for f in result['files']:
    print(f"{f['filename']}: {f['size']} bytes")

# 读取归档会话内容
result = sync_call('sessionFiles.get', {
    'agentId': 'aqiang',
    'filename': '9934c0ab-0e87-416d-8fc0-f4c337f29866.jsonl.reset.2026-03-31T10-16-41.215Z',
    'format': 'messages'
})
print(f"Found {result['messageCount']} messages")

# 搜索会话
result = sync_call('sessionFiles.search', {
    'agentId': 'aqiang',
    'query': '飞书',
    'limit': 10
})
for r in result['results']:
    print(f"{r['filename']}: {r['matchCount']} matches, isReset={r['isReset']}")
```

### 后端集成

```python
# backend/app.py

@app.route('/api/agents/<agent_id>/sessions/history')
def get_session_history(agent_id):
    """获取历史会话（包括归档）"""
    from gateway_sync import sync_call

    # 获取归档会话列表
    reset_result = sync_call('sessionFiles.listReset', {'agentId': agent_id})

    return jsonify({
        'success': True,
        'data': {
            'resetFiles': reset_result['files'],
            'total': reset_result['total']
        }
    })
```

## 重要技术点

### 1. GatewayRequestHandler 签名

**错误写法**（直接返回值）：
```typescript
api.registerGatewayMethod("memory.list", async (params: { agentId: string }) => {
  return { files: [...] };  // ❌ 类型错误
});
```

**正确写法**（使用 respond 函数）：
```typescript
api.registerGatewayMethod("memory.list", async (opts: any) => {
  const params = opts.params || {};
  opts.respond(true, { files: [...] });  // ✅ 正确
});
```

### 2. 安全防护

- **路径遍历防护**：禁止 `..` 和 `/` 在文件名中
- **文件类型限制**：Memory 只允许 `.md` 文件
- **Session ID 格式校验**：必须是 UUID 格式
- **路径解析校验**：使用 `path.resolve` 验证路径在允许目录内

```typescript
// 路径遍历防护
if (name.includes("..") || name.includes("/")) {
  opts.respond(false, undefined, { message: "Invalid file name" });
  return;
}

// 路径解析校验
const resolvedPath = path.resolve(sessionFile);
if (!resolvedPath.startsWith(sessionsDir)) {
  opts.respond(false, undefined, { message: "Invalid file path" });
  return;
}
```

### 3. Reset 文件名解析

Reset 文件命名格式：`{sessionId}.jsonl.reset.{ISO-timestamp}`

```typescript
function parseResetFilename(filename: string): { sessionId: string; resetAt: string } | null {
  const match = filename.match(
    /^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.jsonl\.reset\.(.+)$/i
  );
  if (match) {
    return {
      sessionId: match[1],
      resetAt: match[2],
    };
  }
  return null;
}
```

### 4. 避免方法名冲突

Gateway 内置了 `sessions.list` 和 `sessions.get` 方法，因此本插件使用 `sessionFiles.*` 前缀避免覆盖：

| 插件方法 | Gateway 内置方法 |
|---------|-----------------|
| `sessionFiles.list` | `sessions.list` |
| `sessionFiles.get` | `sessions.get` |
| `sessionFiles.listReset` | - |
| `sessionFiles.search` | - |

## 安装配置

### 1. 构建插件

```bash
cd ~/.openclaw/extensions/memory-api
npm install
npm run build
```

### 2. 配置 openclaw.json

```json
{
  "plugins": {
    "allow": ["memory-api"],
    "load": {
      "paths": ["/home/user/.openclaw/extensions/memory-api"]
    },
    "entries": {
      "memory-api": {
        "enabled": true
      }
    },
    "installs": {
      "memory-api": {
        "source": "path",
        "installPath": "/home/user/.openclaw/extensions/memory-api"
      }
    }
  }
}
```

### 3. 重启 Gateway

```bash
openclaw gateway restart
```

## 调试技巧

### 检查插件是否加载

```bash
# 查看 Gateway 日志
journalctl -u openclaw-gateway -f | grep "Memory"
# 或
tail -f /tmp/gateway.log | grep plugin
```

### 测试 API 方法

```python
from gateway_sync import sync_call

# 测试 memory.list
result = sync_call('memory.list', {'agentId': 'main'})
print(f"Memory files: {len(result.get('files', []))}")

# 测试 sessionFiles.listReset
result = sync_call('sessionFiles.listReset', {'agentId': 'aqiang'})
print(f"Reset files: {result.get('total', 0)}")
```

### 常见错误

| 错误 | 原因 | 解决方案 |
|-----|-----|---------|
| `unknown method: memory.list` | 插件未加载 | 检查 `load.paths` 配置 |
| `unknown method: sessionFiles.list` | 使用了旧版本插件 | 重新构建插件 |
| TypeScript 类型错误 | handler 返回值 | 使用 `opts.respond()` |
| `Agent not found` | agentId 错误 | 检查 openclaw.json 中 agents.list |
| `Invalid file path` | 路径遍历攻击 | 检查 filename 参数 |

## 总结

Memory & Session API 插件展示了 OpenClaw 插件开发的关键要点：

1. **使用 `definePluginEntry`** 定义插件
2. **使用 `opts.respond()`** 发送响应
3. **从 `opts.params`** 获取参数
4. **安全防护** 路径遍历和文件类型校验
5. **避免冲突** 使用不同前缀区分内置方法
6. **配置注册** 在 openclaw.json 中启用插件

此插件使 Admin UI 能够远程访问 Agent 记忆文件和历史会话记录（包括归档），实现了完整的会话历史查询能力。