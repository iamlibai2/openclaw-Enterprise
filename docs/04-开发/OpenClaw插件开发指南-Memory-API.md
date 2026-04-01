# OpenClaw 插件开发指南 - Memory API 示例

## 概述

本文档记录了 Memory API 插件的开发过程，作为 OpenClaw 插件开发的参考示例。

## 背景

Admin UI 改造为 WebSocket 架构后，需要远程访问 Agent 的记忆文件。Gateway 没有内置的 memory API，因此需要开发自定义插件。

## 插件结构

```
memory-api/
├── package.json          # NPM 包配置
├── openclaw.plugin.json  # OpenClaw 插件元数据
├── index.ts              # 插件入口代码
├── tsconfig.json         # TypeScript 配置
├── dist/                 # 构建输出
│   ├── index.js
│   └── index.d.ts
└── README.md             # 使用文档
```

## 关键文件内容

### package.json

```json
{
  "name": "openclaw-memory-api",
  "version": "1.0.0",
  "type": "module",
  "main": "dist/index.js",
  "dependencies": {
    "openclaw": "^2026.3.23-2"
  },
  "devDependencies": {
    "typescript": "^5.0.0"
  },
  "scripts": {
    "build": "tsc"
  }
}
```

### openclaw.plugin.json

```json
{
  "id": "memory-api",
  "name": "Memory API",
  "description": "Provides Gateway RPC methods for reading agent memory files",
  "configSchema": {
    "type": "object",
    "additionalProperties": false,
    "properties": {}
  }
}
```

### index.ts（核心代码）

```typescript
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import * as fs from "fs";
import * as path from "path";

const OPENCLAW_DIR = process.env.OPENCLAW_DIR || path.join(process.env.HOME || "", ".openclaw");

function getAgentWorkspace(agentId: string): string | null {
  const configPath = path.join(OPENCLAW_DIR, "openclaw.json");
  if (!fs.existsSync(configPath)) return null;

  try {
    const config = JSON.parse(fs.readFileSync(configPath, "utf-8"));
    const agents = config?.agents?.list || [];
    const agent = agents.find((a: any) => a.id === agentId);

    if (agent?.workspace) return agent.workspace;

    // Default workspace pattern
    if (agentId === "main") return path.join(OPENCLAW_DIR, "workspace");
    return path.join(OPENCLAW_DIR, `workspace-${agentId}`);
  } catch {
    return null;
  }
}

export default definePluginEntry({
  id: "memory-api",
  name: "Memory API",
  description: "Provides Gateway RPC methods for reading agent memory files",

  register(api) {
    // memory.list - 列出记忆文件
    api.registerGatewayMethod("memory.list", async (opts: any) => {
      const params = opts.params || {};
      const agentId = params.agentId;

      if (!agentId) {
        opts.respond(false, undefined, { message: "agentId is required" });
        return;
      }

      const workspace = getAgentWorkspace(agentId);
      if (!workspace) {
        opts.respond(false, undefined, { message: `Agent ${agentId} not found` });
        return;
      }

      const memoryDir = path.join(workspace, "memory");
      if (!fs.existsSync(memoryDir)) {
        opts.respond(true, { files: [] });
        return;
      }

      const files = fs.readdirSync(memoryDir)
        .filter(name => name.endsWith(".md"))
        .map(name => {
          const filePath = path.join(memoryDir, name);
          const stat = fs.statSync(filePath);
          return {
            name,
            path: filePath,
            size: stat.size,
            modifiedAt: stat.mtime.toISOString(),
          };
        })
        .sort((a, b) => b.modifiedAt.localeCompare(a.modifiedAt));

      opts.respond(true, { files });
    });

    // memory.get - 获取文件内容
    api.registerGatewayMethod("memory.get", async (opts: any) => {
      const params = opts.params || {};
      const agentId = params.agentId;
      const name = params.name;

      // 参数校验
      if (!agentId || !name) {
        opts.respond(false, undefined, { message: "agentId and name are required" });
        return;
      }

      // 安全检查：防止路径遍历
      if (!name.endsWith(".md") || name.includes("..") || name.includes("/")) {
        opts.respond(false, undefined, { message: "Invalid file name" });
        return;
      }

      const workspace = getAgentWorkspace(agentId);
      if (!workspace) {
        opts.respond(false, undefined, { message: `Agent ${agentId} not found` });
        return;
      }

      const filePath = path.join(workspace, "memory", name);
      if (!fs.existsSync(filePath)) {
        opts.respond(false, undefined, { message: `Memory file ${name} not found` });
        return;
      }

      const stat = fs.statSync(filePath);
      const content = fs.readFileSync(filePath, "utf-8");

      opts.respond(true, {
        content,
        size: stat.size,
        modifiedAt: stat.mtime.toISOString(),
      });
    });

    api.logger.info("Memory API plugin registered: memory.list, memory.get");
  },
});
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

`GatewayRequestHandler` 类型定义为：
```typescript
type GatewayRequestHandler = (opts: GatewayRequestHandlerOptions) => Promise<void> | void;

type GatewayRequestHandlerOptions = {
  req: RequestFrame;
  params: Record<string, unknown>;
  client: GatewayClient | null;
  respond: RespondFn;
  context: GatewayRequestContext;
};

type RespondFn = (ok: boolean, payload?: unknown, error?: ErrorShape) => void;
```

### 2. 参数获取

参数在 `opts.params` 中，而不是直接传入：
```typescript
const params = opts.params || {};
const agentId = params.agentId;
```

### 3. 安全考虑

- **路径遍历防护**：禁止 `..` 和 `/` 在文件名中
- **文件类型限制**：只允许 `.md` 文件
- **只读访问**：不支持写入操作

### 4. Agent Workspace 解析

从 `openclaw.json` 配置获取 agent 的 workspace：
- 如果 agent 有显式配置 `workspace`，使用配置值
- 否则使用默认模式：`workspace-{agentId}` 或 `workspace`（main agent）

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
    "allow": [
      "memory-api"
    ],
    "load": {
      "paths": [
        "/home/user/.openclaw/extensions/memory-api"
      ]
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

## API 使用

### memory.list

列出 Agent 的记忆文件：

```python
from gateway_sync import sync_call

result = sync_call('memory.list', {'agentId': 'main'})
# 返回: {'files': [{'name', 'path', 'size', 'modifiedAt'}, ...]}
```

### memory.get

获取指定记忆文件内容：

```python
result = sync_call('memory.get', {
    'agentId': 'main',
    'name': '2026-03-28.md'
})
# 返回: {'content': '...', 'size': 1234, 'modifiedAt': '...'}
```

## 调试技巧

### 检查插件是否加载

```bash
# 查看 Gateway 日志
journalctl -u openclaw-gateway -f | grep plugin
```

### 测试 API 方法

```python
# Python 测试
from gateway_sync import sync_call
result = sync_call('memory.list', {'agentId': 'main'})
print(result)
```

### 常见错误

| 错误 | 原因 | 解决方案 |
|-----|-----|---------|
| `unknown method: memory.list` | 插件未加载 | 检查 `load.paths` 配置 |
| TypeScript 类型错误 | handler 返回值 | 使用 `opts.respond()` |
| `Agent not found` | agentId 错误 | 检查 openclaw.json 中 agents.list |

## 扩展建议

### 添加更多方法

```typescript
// memory.search - 搜索记忆内容
api.registerGatewayMethod("memory.search", async (opts: any) => {
  const { agentId, query } = opts.params || {};
  // 实现搜索逻辑...
  opts.respond(true, { results: [...] });
});

// memory.stats - 记忆统计
api.registerGatewayMethod("memory.stats", async (opts: any) => {
  const { agentId } = opts.params || {};
  // 实现统计逻辑...
  opts.respond(true, { totalFiles, totalSize, ... });
});
```

### 配置化

可以通过 `configSchema` 支持插件配置：

```json
{
  "configSchema": {
    "type": "object",
    "properties": {
      "maxFileSize": {
        "type": "number",
        "default": 100000
      }
    }
  }
}
```

在代码中使用：
```typescript
const maxFileSize = api.pluginConfig?.maxFileSize || 100000;
```

## 总结

Memory API 插件展示了 OpenClaw 插件开发的关键要点：

1. **使用 `definePluginEntry`** 定义插件
2. **使用 `opts.respond()`** 发送响应
3. **从 `opts.params`** 获取参数
4. **安全防护** 路径遍历和文件类型
5. **配置注册** 在 openclaw.json 中启用插件

此插件使 Admin UI 能够远程访问 Agent 记忆文件，实现了远程部署能力。