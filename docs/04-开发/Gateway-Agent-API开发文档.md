# Gateway Agent API 开发文档

## 概述

OpenClaw Gateway 提供 WebSocket API 用于管理 Agent。本文档描述 Agent 相关的所有 API、配置结构和工作流程。

---

## API 列表

### 1. agents.list - 获取 Agent 列表

```python
from gateway_sync import sync_call

result = sync_call('agents.list')
```

**返回值**：
```json
{
  "defaultId": "xiaomei",
  "mainKey": "main",
  "scope": "per-sender",
  "agents": [
    {"id": "main", "name": "Neo"},
    {"id": "xiaomei", "name": "小美"}
  ]
}
```

---

### 2. agents.create - 创建 Agent

```python
result = sync_call('agents.create', {
    'name': 'MyAgent',           # 必填：Agent 名称
    'workspace': '~/.openclaw/workspace-myagent'  # 必填：工作空间路径
})
```

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | Agent 名称（用于生成 agentId） |
| `workspace` | string | ✅ | 工作空间路径（支持 `~` 展开） |
| `emoji` | string | ❌ | 表情符号 |
| `avatar` | string | ❌ | 头像描述 |

**返回值**：
```json
{
  "ok": true,
  "agentId": "myagent",        // 自动生成（name 的 normalize 形式）
  "name": "MyAgent",
  "workspace": "/home/user/.openclaw/workspace-myagent"
}
```

**重要说明**：
- `agentId` 由 `name` 自动生成：小写 + 移除特殊字符 + 不能以数字开头
- 创建后会**自动重启 Gateway**
- 不支持 `id` 和 `model` 参数（需在创建后通过 `agents.update` 设置）

---

### 3. agents.update - 更新 Agent

```python
result = sync_call('agents.update', {
    'agentId': 'myagent',       # 必填
    'model': 'bailian/glm-5'    # 可选：模型 ID（字符串）
})
```

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `agentId` | string | ✅ | Agent ID |
| `name` | string | ❌ | 更新名称 |
| `workspace` | string | ❌ | 更新工作空间 |
| `model` | string | ❌ | 更新模型（**字符串**，不是 dict） |
| `avatar` | string | ❌ | 更新头像 |

**返回值**：
```json
{
  "ok": true,
  "agentId": "myagent"
}
```

**重要说明**：
- `model` 参数是**字符串**，不是 `{"primary": "xxx"}` 格式
- 更新后**热加载生效**，无需重启 Gateway

---

### 4. agents.delete - 删除 Agent

```python
result = sync_call('agents.delete', {
    'agentId': 'myagent',       # 必填
    'deleteFiles': True         # 可选：是否删除文件
})
```

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `agentId` | string | ✅ | Agent ID |
| `deleteFiles` | boolean | ❌ | 是否删除工作空间文件（默认 false） |

**返回值**：
```json
{
  "ok": true,
  "agentId": "myagent",
  "removedBindings": 0
}
```

**重要说明**：
- `main` Agent 不能被删除
- 删除后**热加载生效**，无需重启 Gateway

---

### 5. agents.files.get - 获取 Agent 文件

```python
result = sync_call('agents.files.get', {
    'agentId': 'myagent',
    'name': 'SOUL.md'
})
```

**支持的文件名**：
- `AGENTS.md` - 工作空间说明
- `SOUL.md` - 核心特质和行为准则
- `IDENTITY.md` - 身份定义
- `USER.md` - 用户偏好信息
- `TOOLS.md` - 工具相关说明
- `HEARTBEAT.md` - 心跳模板
- `BOOTSTRAP.md` - 初始化引导（首次运行后删除）
- `MEMORY.md` - 长期记忆
- `memory/YYYY-MM-DD.md` - 每日记

---

### 6. agents.files.set - 设置 Agent 文件

```python
result = sync_call('agents.files.set', {
    'agentId': 'myagent',
    'name': 'SOUL.md',
    'content': '# My Soul\n\n你是一个助手...'
})
```

---

## 配置结构

### Agent 配置示例

```json
{
  "id": "myagent",
  "name": "我的助手",
  "workspace": "/home/user/.openclaw/workspace-myagent",
  "agentDir": "/home/user/.openclaw/agents/myagent/agent",
  "model": {"primary": "bailian/glm-5"},
  "skills": ["acp-router", "feishu-bitable"],
  "tools": {
    "profile": "minimal",
    "alsoAllow": ["read", "web_search"]
  },
  "subagents": {"allowAgents": ["*"]},
  "default": false
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | Agent 唯一标识（自动生成） |
| `name` | string | Agent 显示名称 |
| `workspace` | string | 工作空间路径（存储身份、记忆等） |
| `agentDir` | string | Gateway 内部目录（存储 sessions 等） |
| `model` | object/string | 模型配置，`{"primary": "model-id"}` 或字符串 |
| `skills` | array | 技能列表 |
| `tools` | object | 工具配置 |
| `subagents` | object | 子 Agent 权限 |
| `default` | boolean | 是否为默认 Agent |

---

## 工作空间结构

创建 Agent 后，`workspace` 目录下自动生成以下文件：

```
~/.openclaw/workspace-myagent/
├── AGENTS.md          # 工作空间说明
├── BOOTSTRAP.md       # 初始化引导（首次对话后删除）
├── HEARTBEAT.md       # 心跳模板
├── IDENTITY.md        # Agent 身份定义
├── SOUL.md            # 核心特质和行为准则
├── TOOLS.md           # 工具相关说明
├── USER.md            # 用户偏好信息
├── MEMORY.md          # 长期记忆
├── memory/            # 每日记
│   └── 2026-04-09.md
└── .openclaw/         # OpenClaw 内部目录
    └── .git/          # Git 仓库（自动初始化）
```

### 文件用途

| 文件 | 用途 |
|------|------|
| `IDENTITY.md` | Agent 名称、头像等身份信息 |
| `SOUL.md` | Agent 的核心特质和行为准则 |
| `MEMORY.md` | 长期记忆（跨会话持久化） |
| `memory/YYYY-MM-DD.md` | 每日记（短期记忆） |
| `USER.md` | 用户偏好信息 |
| `BOOTSTRAP.md` | 初始化引导（首次对话时 Agent 会阅读并删除） |

---

## Skills/Tools 管理

Gateway 没有单独的 skills/tools API，需要通过 `config.set` 修改完整配置：

```python
from gateway_sync import sync_call
import json5

# 1. 获取当前配置
config = sync_call('config.get')
parsed = config.get('parsed', {})
hash_val = config.get('hash', '')

# 2. 修改 Agent 的 skills/tools
agents_list = parsed.get('agents', {}).get('list', [])
for a in agents_list:
    if a.get('id') == 'myagent':
        a['skills'] = ['acp-router', 'feishu-bitable']
        a['tools'] = {'profile': 'minimal', 'alsoAllow': ['read']}
        break

# 3. 写回配置（自动触发 Gateway 重启）
new_raw = json5.dumps(parsed, indent=2, quote_keys=True)
sync_call('config.set', {'raw': new_raw, 'baseHash': hash_val})
```

### tools.profile 可选值

| 值 | 说明 |
|------|------|
| `minimal` | 最小工具集 |
| `coding` | 编程工具集 |
| `messaging` | 消息处理工具集 |
| `full` | 完整工具集 |

---

## 典型工作流

### 创建 Agent 并设置模型

```python
from gateway_sync import sync_call

# Step 1: 创建 Agent（只能指定 name + workspace）
result = sync_call('agents.create', {
    'name': 'MyAgent',
    'workspace': '~/.openclaw/workspace-myagent'
})
agent_id = result['agentId']  # 自动生成，如 "myagent"

# Step 2: 设置 model（创建后单独调用）
sync_call('agents.update', {
    'agentId': agent_id,
    'model': 'bailian/glm-5'
})

# Step 3: 设置 SOUL（可选）
sync_call('agents.files.set', {
    'agentId': agent_id,
    'name': 'SOUL.md',
    'content': '# Who You Are\n\n你是一个助手...'
})
```

### 克隆 Agent

```python
# 1. 获取源 Agent 的配置
config = sync_call('config.get')
parsed = config.get('parsed', {})
source_agent = next(
    (a for a in parsed['agents']['list'] if a['id'] == 'source-id'),
    None
)

# 2. 创建新 Agent
result = sync_call('agents.create', {
    'name': source_agent['name'] + ' (副本)',
    'workspace': '~/.openclaw/workspace-new'
})

# 3. 复制配置
sync_call('agents.update', {
    'agentId': result['agentId'],
    'model': source_agent['model']['primary'] if isinstance(source_agent['model'], dict) else source_agent['model']
})
```

---

## 自动重启机制

| API | 重启行为 |
|-----|---------|
| `agents.create` | 自动重启 Gateway |
| `agents.update` | 热加载，无需重启 |
| `agents.delete` | 热加载，无需重启 |
| `config.set` | 自动触发 Gateway 重启 (SIGUSR1) |

---

## 错误处理

```python
from gateway_sync import sync_call, GatewayError

try:
    result = sync_call('agents.create', {'name': 'main'})
except GatewayError as e:
    print(f'Gateway 错误: {e.message}')
    # 错误示例: "main" is reserved
```

### 常见错误

| 错误 | 原因 |
|------|------|
| `"main" is reserved` | 不能创建名为 "main" 的 Agent |
| `agent "xxx" already exists` | Agent 已存在 |
| `must have required property 'workspace'` | 缺少必填参数 |
| `unexpected property 'id'` | 不支持该参数 |

---

## 源码参考

Gateway API 定义位于：
```
/usr/lib/node_modules/openclaw/dist/gateway-cli-Dsd9gHBa.js
```

Schema 定义位于：
```
/usr/lib/node_modules/openclaw/dist/method-scopes-BiEi0X2g.js
```