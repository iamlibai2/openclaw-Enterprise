# Session Artifacts 插件技术文档

> 开发时间：2026-04-04
> 插件路径：`/home/iamlibai/workspace/github_code/openclaw/extensions/session-artifacts`

---

## 功能概述

会话文件追踪插件，用于追踪 Agent 在会话过程中生成的文件，并提供 Gateway API 查询接口。

### 功能特性

- **文件追踪**：自动检测 Agent 通过工具生成的文件（Word、Excel、PPT、PDF、TXT、MD 等）
- **会话关联**：将文件与会话（Session）关联，支持按会话查询
- **多 Agent 支持**：支持多 Agent 环境，每个 Agent 的 workspace 独立管理
- **实时查询**：通过 Gateway API 实时查询会话生成的文件列表

---

## 工作原理

### 文件检测方式

插件采用双重策略检测文件：

#### 1. Hook 监听（webchat 渠道）

- 监听 `after_tool_call` 事件
- 捕获工具调用中的文件路径信息
- 自动记录到会话的 artifacts 文件

**适用渠道**：仅 webchat 渠道生效

#### 2. 目录扫描（所有渠道）

- 扫描 Agent 的 workspace 目录
- 检测最近 24 小时内创建/修改的文件
- 支持的扩展名：`.docx`, `.doc`, `.xlsx`, `.xls`, `.pptx`, `.ppt`, `.pdf`, `.txt`, `.md`, `.csv`, `.json`

**适用渠道**：所有渠道（飞书、钉钉、webchat 等）

### 重要发现

`after_tool_call` hook **仅在 webchat 渠道生效**。飞书、钉钉等渠道使用独立的工具执行路径，不会触发 hook。

**解决方案**：必须实现目录扫描作为 fallback。

---

## 数据存储

```
{workspace}/.openclaw/artifacts/{sessionKey}.json
```

每个会话的 artifacts 记录存储在对应 Agent workspace 的 `.openclaw/artifacts/` 目录下。

### 文件结构

```json
{
  "sessionId": "agent:xiaomei:webchat:xxx",
  "agentId": "xiaomei",
  "artifacts": [
    {
      "name": "报告.docx",
      "path": "/home/user/.openclaw/workspace-xiaomei/报告.docx",
      "size": 12345,
      "createdAt": 1712198400000,
      "toolName": "write_file"
    }
  ],
  "updatedAt": 1712198400000
}
```

---

## API 接口

### artifacts.list

查询指定会话生成的文件列表。

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| sessionId | string | 是 | 会话标识（sessionKey） |
| agentId | string | 否 | Agent ID（可从 sessionId 解析） |

**响应**：

```json
{
  "ok": true,
  "sessionId": "agent:xiaomei:webchat:xxx",
  "artifacts": [
    {
      "name": "报告.docx",
      "path": "/home/user/.openclaw/workspace-xiaomei/报告.docx",
      "size": 12345,
      "createdAt": 1712198400000,
      "toolName": "write_file"
    }
  ]
}
```

**调用示例**：

```javascript
// 通过 Gateway WebSocket 调用
const result = await client.request('artifacts.list', {
  sessionId: 'agent:xiaomei:webchat:cd33178d-9665-4840-beb9-29427d076a1f'
});

console.log(result.artifacts);
```

### artifacts.sessions

查询所有包含 artifacts 的会话列表。

**请求参数**：无

**响应**：

```json
{
  "ok": true,
  "sessions": [
    {
      "sessionId": "agent:xiaomei:webchat:xxx",
      "agentId": "xiaomei",
      "artifactCount": 3,
      "updatedAt": 1712198400000
    }
  ]
}
```

---

## Gateway 方法响应格式

**重要**：Gateway 方法必须使用 `opts.respond()` 返回结果，不能使用 `return`。

```typescript
// ✅ 正确
api.registerGatewayMethod("artifacts.list", async (opts) => {
  opts.respond(true, { ok: true, artifacts: [...] });
});

// ❌ 错误 - 前端会收到 undefined
api.registerGatewayMethod("artifacts.list", async (params) => {
  return { ok: true, artifacts: [...] };
});
```

---

## 配置

### openclaw.json

```json
{
  "plugins": {
    "allow": ["session-artifacts"],
    "load": {
      "paths": ["/home/user/extensions/session-artifacts"]
    },
    "entries": {
      "session-artifacts": {
        "enabled": true
      }
    },
    "installs": {
      "session-artifacts": {
        "source": "path",
        "spec": "session-artifacts",
        "sourcePath": "/home/user/extensions/session-artifacts",
        "installPath": "/home/user/extensions/session-artifacts",
        "installedAt": "2026-04-04T00:00:00.000Z"
      }
    }
  }
}
```

### 插件配置（可选）

```json
{
  "outputDir": "/custom/path",
  "trackExtensions": [".docx", ".xlsx", ".pdf"]
}
```

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| outputDir | string | workspace/.openclaw/artifacts | artifacts 元数据存储目录 |
| trackExtensions | string[] | 见下方 | 要追踪的文件扩展名 |

默认追踪的扩展名：
- 文档类：`.docx`, `.doc`, `.pdf`
- 表格类：`.xlsx`, `.xls`, `.csv`
- 演示类：`.pptx`, `.ppt`
- 文本类：`.txt`, `.md`, `.json`

---

## 技术细节

### SessionKey 解析

SessionKey 格式通常为 `agent:{agentId}:{channel}:{sessionId}`，插件会自动解析：

```typescript
function parseAgentIdFromSessionKey(sessionKey: string): string | null {
  const parts = sessionKey.split(":");
  if (parts.length >= 2 && parts[0] === "agent") {
    return parts[1];
  }
  return null;
}
```

### Workspace 定位

插件根据 agentId 查找对应的 workspace：

1. 从 `openclaw.json` 读取 agent 配置
2. 使用配置中的 `workspace` 字段
3. 若未配置，使用默认路径 `{OPENCLAW_DIR}/workspace-{agentId}`

### 时间过滤

目录扫描模式下，只返回最近 24 小时内创建/修改的文件，避免显示历史遗留文件。

```typescript
const maxAgeMs = 24 * 60 * 60 * 1000; // 24 小时
const now = Date.now();

if (now - stat.mtimeMs <= maxAgeMs) {
  // 包含该文件
}
```

---

## 前端集成示例

### Vue 3 组件

```vue
<template>
  <div class="files-panel">
    <div v-if="loading">加载中...</div>
    <div v-else-if="files.length === 0">暂无文件</div>
    <div v-else>
      <div v-for="file in files" :key="file.name" class="file-item">
        <span class="file-name">{{ file.name }}</span>
        <span class="file-size">{{ formatSize(file.size) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps(['sessionKey', 'client'])
const files = ref([])
const loading = ref(false)

async function loadFiles() {
  if (!props.sessionKey || !props.client) return

  loading.value = true
  try {
    const result = await props.client.request('artifacts.list', {
      sessionId: props.sessionKey
    })
    files.value = result?.artifacts || []
  } catch (err) {
    console.error('Failed to load artifacts:', err)
  } finally {
    loading.value = false
  }
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

defineExpose({ loadFiles })
</script>
```

---

## Admin UI 集成

### Chat.vue 文件面板

在 Chat 页面添加文件按钮和滑出面板：

```typescript
// 状态
const showFilesPanel = ref(false)
const agentFiles = ref<ArtifactFile[]>([])

// 加载文件列表
async function loadAgentFiles() {
  if (!client.value || !selectedSessionKey.value) return

  loadingFiles.value = true
  try {
    const result = await client.value.request<{ ok: boolean; artifacts: ArtifactFile[] }>(
      'artifacts.list',
      { sessionId: selectedSessionKey.value }
    )
    agentFiles.value = result?.artifacts || []
  } catch (err) {
    console.error('[Files] Failed:', err)
    agentFiles.value = []
  } finally {
    loadingFiles.value = false
  }
}

// 打开面板时自动加载
watch(showFilesPanel, (show) => {
  if (show && selectedSessionKey.value) {
    loadAgentFiles()
  }
})
```

### 后端下载 API

```python
# backend/app.py
@app.route('/api/chat/artifact/download', methods=['POST'])
@auth_required
def download_artifact():
    data = request.get_json()
    file_path = data.get('path', '')

    # 安全检查：只允许 workspace 目录内的文件
    workspace_dir = settings.OPENCLAW_WORKSPACE_DIR
    if not file_path.startswith(workspace_dir):
        return jsonify({'success': False, 'error': 'Invalid path'}), 403

    # 读取文件内容
    try:
        with open(file_path, 'rb') as f:
            content = base64.b64encode(f.read()).decode()
        return jsonify({
            'success': True,
            'data': {
                'content': content,
                'name': os.path.basename(file_path)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

---

## 限制与注意事项

1. **Hook 覆盖范围**：`after_tool_call` hook 仅在 webchat 渠道生效，其他渠道依赖目录扫描
2. **文件类型**：仅追踪预定义扩展名的文件，不追踪二进制文件或未知类型
3. **性能**：目录扫描在大 workspace 下可能有性能影响，建议控制文件数量
4. **并发**：多个会话同时生成文件时，artifacts 文件的写入可能存在竞争

---

## 文件清单

| 文件 | 说明 |
|------|------|
| `index.ts` | 插件主逻辑（~495 行） |
| `openclaw.plugin.json` | 插件配置清单 |
| `package.json` | NPM 包配置 |
| `README.md` | 技术文档 |

---

## 版本历史

### v1.0.0 (2026-04-04)

- 初始版本
- 支持 `artifacts.list` 和 `artifacts.sessions` API
- 支持 hook 监听和目录扫描双重检测
- 支持多 Agent 环境
- 集成到 Admin UI Chat 页面

---

## 许可证

MIT License