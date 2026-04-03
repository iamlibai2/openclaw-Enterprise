# OpenClaw 插件开发指南 - Focus Context Engine

## 概述

本文档记录了 Focus Context Engine 插件的开发过程，作为 OpenClaw ContextEngine 插件的参考示例。

## 背景

Admin UI 改造为 WebSocket 架构后，需要远程管理 Agent 的上下文。用户希望实现"专注模式"：
- 清理与当前任务无关的上下文
- 只保留与任务相关的消息
- 减少 token 使用，提高响应质量

## ContextEngine 接口

OpenClaw v2026.3.x 引入了 ContextEngine 插件接口，提供 7 个生命周期钩子：

```typescript
interface ContextEngine {
  readonly info: ContextEngineInfo;

  bootstrap?(params): Promise<BootstrapResult>;     // 初始化
  ingest(params): Promise<IngestResult>;            // 消息进入
  assemble(params): Promise<AssembleResult>;        // 组装上下文
  compact(params): Promise<CompactResult>;          // 压缩/清理
  afterTurn?(params): Promise<void>;                // 回合后处理
  maintain?(params): Promise<MaintenanceResult>;    // 维护
  dispose?(): Promise<void>;                        // 清理
}
```

## 技术架构

### 触发压缩的方式

```
┌─────────────────────────────────────────────────────────────────────┐
│                          触发压缩的方式                              │
└─────────────────────────────────────────────────────────────────────┘

方式 1: 用户在飞书发送 /compact 命令
┌──────────────┐     ┌──────────────────┐     ┌────────────────────┐
│   飞书消息    │ ──► │  Agent Runner    │ ──► │ compactEmbeddedPi  │
│  "/compact"  │     │  (pi-embedded)   │     │ SessionDirect()    │
└──────────────┘     └──────────────────┘     └─────────┬──────────┘
                                                       │
                                                       ▼
                                             ┌────────────────────┐
                                             │ resolveContextEngine│
                                             │ (读取 slots 配置)   │
                                             └─────────┬──────────┘
                                                       │
                                                       ▼
                                             ┌────────────────────┐
                                             │ contextEngine.compact│
                                             │  (Focus 插件)       │
                                             └────────────────────┘

方式 2: 上下文溢出时自动触发
┌──────────────┐     ┌──────────────────┐     ┌────────────────────┐
│  LLM 返回    │ ──► │  检测到 overflow │ ──► │ contextEngine.compact│
│  错误        │     │  自动恢复        │     │  (Focus 插件)       │
└──────────────┘     └──────────────────┘     └────────────────────┘

方式 3: Gateway sessions.compact (❌ 不使用 Focus 插件)
┌──────────────┐     ┌──────────────────┐     ┌────────────────────┐
│ Admin UI     │ ──► │ Gateway          │ ──► │ 简单截断文件        │
│ 调用 API     │     │ sessions.compact │     │ (保留最近 N 行)     │
└──────────────┘     └──────────────────┘     └────────────────────┘

方式 4: focus.compact (✅ 新增，使用 Focus 插件)
┌──────────────┐     ┌──────────────────┐     ┌────────────────────┐
│ Admin UI     │ ──► │ Gateway          │ ──► │ Focus 插件智能压缩  │
│ 调用 API     │     │ focus.compact    │     │ (按关键词过滤)      │
└──────────────┘     └──────────────────┘     └────────────────────┘
```

### 为什么 Gateway.sessions.compact 不调用 ContextEngine

因为 **Gateway 和 Agent Runner 是两个独立的组件**：
- Gateway：负责会话管理、消息路由
- Agent Runner (pi-embedded)：负责 LLM 交互、上下文管理

ContextEngine 是 Agent Runner 内部的概念，Gateway 无法直接调用。

### 解决方案：插件自己实现压缩

Focus 插件新增了 `focus.compact` Gateway 方法，自己实现智能压缩逻辑：
1. 直接读写 session 文件
2. 按关键词相关性过滤消息
3. 创建备份保证安全

## 插件位置

```
~/.openclaw/extensions/focus-context-engine/
├── package.json           # NPM 包配置
├── openclaw.plugin.json   # OpenClaw 插件元数据
├── index.ts               # 插件入口代码
├── tsconfig.json          # TypeScript 配置
├── dist/                  # 构建输出
│   ├── index.js
│   └── index.d.ts
└── README.md              # 使用文档
```

## 核心实现

### 1. 关键词提取

```typescript
function extractKeywords(text: string): string[] {
  // 移除中英文停用词
  const stopWords = new Set(["the", "a", "an", "is", ...]);

  // 统计词频，返回前 20 个高频词
  const words = text.toLowerCase()
    .replace(/[^\w\s\u4e00-\u9fff]/g, " ")
    .split(/\s+/)
    .filter(w => w.length > 2 && !stopWords.has(w));

  return Array.from(wordCount.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20)
    .map(([word]) => word);
}
```

### 2. 相关性计算

```typescript
function calculateRelevance(message: any, keywords: string[]): number {
  const content = getMessageContent(message).toLowerCase();
  const messageWords = content.split(/\s+/);
  const messageWordSet = new Set(messageWords);

  let matches = 0;
  for (const keyword of keywords) {
    if (messageWordSet.has(keyword) || content.includes(keyword)) {
      matches++;
    }
  }

  return keywords.length > 0 ? matches / keywords.length : 0.5;
}
```

### 3. 智能压缩 (compact)

```typescript
async compact(params): Promise<CompactResult> {
  // 1. 读取会话文件
  const messages = readSessionMessages(params.sessionFile);

  // 2. 提取任务关键词
  const keywords = focusStatus?.keywords || extractKeywords(recentMessages);

  // 3. 遍历历史消息，计算相关性
  for (const msg of messages) {
    const relevance = calculateRelevance(msg, keywords);
    // 保留: 最近消息 或 相关性高的消息
    if (isRecent || relevance >= threshold) {
      messagesToKeep.push(msg);
    }
  }

  // 4. 写回文件（创建备份）
  writeSessionMessages(sessionFile, messagesToKeep);

  // 5. 返回压缩结果
  return { ok: true, compacted: true, result: { ... } };
}
```

### 4. 会话文件路径解析

```typescript
// sessionKey 格式: agent:{agentId}:{channel}:{accountId}:{chatType}:{conversationId}
function resolveSessionFilePath(sessionKey: string) {
  const agentId = sessionKey.split(":")[1];
  const sessionsDir = path.join(openclawDir, "agents", agentId, "sessions");

  // 读取 sessions.json 查找 sessionFile
  const sessionsData = JSON.parse(fs.readFileSync(sessionsJsonPath, "utf-8"));
  return sessionsData[sessionKey]?.sessionFile;
}
```

### 5. 注册插件

```typescript
export default definePluginEntry({
  id: "focus-context-engine",
  name: "Focus Context Engine",

  register(api) {
    const engine = new FocusContextEngine();

    // 注册为 ContextEngine
    api.registerContextEngine("focus", () => engine);

    // 注册 Gateway 方法
    api.registerGatewayMethod("focus.compact", async (opts) => {
      const result = await engine.compactSession({
        sessionKey: opts.params.sessionKey,
        taskDescription: opts.params.taskDescription,
      });
      opts.respond(true, result);
    });
  },
});
```

## Gateway API

### focus.focus

启用专注模式。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| sessionKey | string | 是 | 会话键 |
| taskDescription | string | 否 | 任务描述 |
| keywords | string[] | 否 | 自定义关键词 |

**返回**:
```json
{
  "success": true,
  "status": {
    "enabled": true,
    "keywords": ["api", "认证", "用户"],
    "startedAt": "2026-04-02T10:00:00.000Z"
  },
  "message": "Focus mode enabled with 3 keywords"
}
```

### focus.compact ⭐ 新增

执行智能压缩，可远程触发。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| sessionKey | string | 是 | 会话键 |
| taskDescription | string | 否 | 任务描述（用于提取关键词） |
| keywords | string[] | 否 | 自定义关键词 |
| tokenBudget | number | 否 | 目标 token 预算 |

**返回**:
```json
{
  "success": true,
  "compacted": true,
  "result": {
    "tokensBefore": 50000,
    "tokensAfter": 25000,
    "summary": "Removed 15 irrelevant messages, saved ~25000 tokens",
    "details": {
      "messagesRemoved": 15,
      "messagesKept": 35,
      "keywords": ["api", "认证", "用户"],
      "focusMode": true
    }
  }
}
```

### focus.getStatus

获取专注模式状态。

### focus.clearStatus

清除专注模式。

## 配置安装

### openclaw.json 配置

```json
{
  "plugins": {
    "allow": ["focus-context-engine"],
    "slots": {
      "contextEngine": "focus"
    },
    "load": {
      "paths": ["~/.openclaw/extensions/focus-context-engine"]
    },
    "entries": {
      "focus-context-engine": {
        "enabled": true
      }
    }
  }
}
```

### 构建和重启

```bash
cd ~/.openclaw/extensions/focus-context-engine
npm install
npm run build
openclaw gateway restart
```

## 使用示例

### Python 调用

```python
from gateway_sync import sync_call

# 方式 1: 设置专注模式 + Agent 对话时自动生效
result = sync_call('focus.focus', {
    'sessionKey': 'agent:aqiang:feishu:aqiang:direct:ou_xxx',
    'taskDescription': '开发用户认证 API'
})
# 之后每次对话，assemble() 会按关键词相关性排序消息

# 方式 2: 远程触发智能压缩
result = sync_call('focus.compact', {
    'sessionKey': 'agent:aqiang:feishu:aqiang:direct:ou_xxx',
    'taskDescription': '开发用户认证 API'
})
print(f"已清理 {result['result']['details']['messagesRemoved']} 条消息")
print(f"节省 {result['result']['tokensBefore'] - result['result']['tokensAfter']} tokens")

# 查看状态
status = sync_call('focus.getStatus', {
    'sessionKey': 'agent:aqiang:feishu:aqiang:direct:ou_xxx'
})

# 清除专注模式
sync_call('focus.clearStatus', {
    'sessionKey': 'agent:aqiang:feishu:aqiang:direct:ou_xxx'
})
```

### 后端集成

```python
# backend/app.py

@app.route('/api/sessions/<session_key>/focus', methods=['POST'])
def set_focus_mode(session_key):
    """设置专注模式"""
    from gateway_sync import sync_call

    data = request.json
    result = sync_call('focus.focus', {
        'sessionKey': session_key,
        'taskDescription': data.get('taskDescription'),
        'keywords': data.get('keywords')
    })

    return jsonify({
        'success': result.get('success', False),
        'data': result.get('status')
    })

@app.route('/api/sessions/<session_key>/compact', methods=['POST'])
def compact_session(session_key):
    """智能压缩会话"""
    from gateway_sync import sync_call

    data = request.json
    result = sync_call('focus.compact', {
        'sessionKey': session_key,
        'taskDescription': data.get('taskDescription'),
        'keywords': data.get('keywords')
    })

    return jsonify({
        'success': result.get('success', False),
        'compacted': result.get('compacted', False),
        'data': result.get('result')
    })
```

## 重要技术点

### 1. ContextEngine 插件槽位

配置中使用 `slots.contextEngine` 指定活动的 ContextEngine：

```json
{
  "plugins": {
    "slots": {
      "contextEngine": "focus"  // 使用 focus 引擎
    }
  }
}
```

### 2. 消息保留策略

- **保留窗口**: 最近 20 条消息始终保留
- **相关性阈值**: 相关性 > 20% 的消息保留
- **最少保留**: 最少保留 10 条消息

### 3. 状态持久化

专注模式状态保存在 `~/.openclaw/focus-context-engine-state.json`：

```json
{
  "agent:aqiang:feishu:...": {
    "enabled": true,
    "taskDescription": "开发 API",
    "keywords": ["api", "认证", "用户"],
    "startedAt": "2026-04-02T10:00:00.000Z",
    "messagesRemoved": 15,
    "tokensSaved": 12000
  }
}
```

### 4. 文件安全

压缩时创建备份：
```
session.jsonl → session.jsonl.bak-{timestamp}
```

### 5. Session Key 格式

```
agent:{agentId}:{channel}:{accountId}:{chatType}:{conversationId}
```

示例：
```
agent:aqiang:feishu:aqiang:direct:ou_xxx
agent:xiaomei:feishu:xiaomei:group:oc_xxx
```

## 调试技巧

### 检查插件加载

```bash
# 查看 Gateway 日志
journalctl -u openclaw-gateway -f | grep "Focus"
```

### 测试 API 方法

```python
from gateway_sync import sync_call

# 测试 focus.compact
result = sync_call('focus.compact', {
    'sessionKey': 'agent:aqiang:feishu:aqiang:direct:ou_xxx',
    'taskDescription': '测试任务'
})
print(f"Result: {result}")
```

### 查看压缩结果

```python
# 查看统计数据
result = sync_call('focus.getStatus', {
    'sessionKey': 'agent:aqiang:feishu:aqiang:direct:ou_xxx'
})
print(f"已清理 {result['status']['messagesRemoved']} 条消息")
print(f"节省 {result['status']['tokensSaved']} tokens")
```

## 未来增强

1. **LLM 智能评分**: 使用 LLM 判断消息相关性
2. **向量检索 (RAG)**: 将消息向量化，按相似度检索
3. **多任务切换**: 支持保存和恢复不同任务的上下文
4. **压缩历史**: 记录每次压缩的详情，支持回滚
5. **自动触发**: 在 afterTurn 中检测 token 使用，自动触发压缩

## 版本历史

### v1.0.0 (2026-04-02)

- 初始版本
- 实现专注模式核心功能
- 支持 Gateway API 调用
- 基础关键词提取和相关性评分
- 新增 `focus.compact` 方法支持远程触发

### v1.1.0 (2026-04-02)

- Admin UI 集成完成
- 新增前端专注模式界面
- 新增后端 REST API 端点

## Admin UI 集成

### 后端 API 端点

在 `backend/app.py` 中新增了 4 个 REST API 端点：

```python
# ==================== Focus Mode API ====================

@app.route('/api/focus/focus', methods=['POST'])
@require_permission('sessions', 'edit')
def focus_mode():
    """启用专注模式并可选触发压缩"""
    data = request.json
    session_key = data.get('sessionKey')
    task_description = data.get('taskDescription')
    keywords = data.get('keywords')
    compact_now = data.get('compactNow', False)

    # 通过 Gateway WebSocket 调用 Focus 插件
    result = sync_call('focus.focus', {
        'sessionKey': session_key,
        'taskDescription': task_description,
        'keywords': keywords,
        'compactNow': compact_now
    })
    return jsonify({'success': result.get('success'), 'data': result.get('status')})


@app.route('/api/focus/compact', methods=['POST'])
@require_permission('sessions', 'edit')
def focus_compact():
    """执行智能压缩"""
    result = sync_call('focus.compact', params)
    return jsonify({
        'success': result.get('success'),
        'compacted': result.get('compacted'),
        'data': result.get('result')
    })


@app.route('/api/focus/status', methods=['GET'])
@require_permission('sessions', 'read')
def focus_get_status():
    """获取专注模式状态"""
    session_key = request.args.get('sessionKey')
    result = sync_call('focus.getStatus', {'sessionKey': session_key})
    return jsonify({'success': True, 'data': result.get('status')})


@app.route('/api/focus/clear', methods=['POST'])
@require_permission('sessions', 'edit')
def focus_clear():
    """清除专注模式"""
    result = sync_call('focus.clearStatus', {'sessionKey': session_key})
    return jsonify({'success': result.get('success')})
```

### 前端 API 客户端

在 `frontend/src/api/index.ts` 中新增 `focusApi`：

```typescript
// ==================== Focus Mode API ====================
export const focusApi = {
  // 启用专注模式
  enable(sessionKey: string, options?: {
    taskDescription?: string
    keywords?: string[]
    compactNow?: boolean
  }) {
    return api.post<{ success: boolean; data: FocusStatus; message: string }>('/focus/focus', {
      sessionKey,
      ...options
    })
  },

  // 执行智能压缩
  compact(sessionKey: string, options?: {
    taskDescription?: string
    keywords?: string[]
    tokenBudget?: number
  }) {
    return api.post<{ success: boolean; compacted: boolean; data: FocusCompactResult }>('/focus/compact', {
      sessionKey,
      ...options
    })
  },

  // 获取专注模式状态
  getStatus(sessionKey: string) {
    return api.get<{ success: boolean; data: FocusStatus }>('/focus/status', {
      params: { sessionKey }
    })
  },

  // 清除专注模式
  clear(sessionKey: string) {
    return api.post<{ success: boolean; message: string }>('/focus/clear', {
      sessionKey
    })
  }
}

export interface FocusStatus {
  enabled: boolean
  taskDescription?: string
  keywords?: string[]
  startedAt?: string
  messagesRemoved?: number
  tokensSaved?: number
}

export interface FocusCompactResult {
  tokensBefore: number
  tokensAfter: number
  summary: string
  details: {
    messagesRemoved: number
    messagesKept: number
    keywords: string[]
    focusMode: boolean
  }
}
```

### 前端 UI 实现

在 `frontend/src/views/Sessions.vue` 中添加专注模式功能：

#### 1. 会话详情面板按钮

```vue
<div class="panel-header">
  <h3>对话记录</h3>
  <div class="header-actions">
    <span v-if="selectedSession">{{ selectedSession.updatedAt }}</span>
    <el-button
      v-if="selectedSession"
      size="small"
      :type="focusStatus?.enabled ? 'warning' : 'default'"
      @click="showFocusDialog"
    >
      {{ focusStatus?.enabled ? '专注模式已启用' : '专注模式' }}
    </el-button>
  </div>
</div>
```

#### 2. 专注模式对话框

```vue
<el-dialog v-model="focusDialogVisible" title="专注模式" width="500px">
  <!-- 状态显示（已启用时） -->
  <el-alert type="success" v-if="focusStatus?.enabled">
    <template #title>
      <div class="status-header">
        <span>专注模式已启用</span>
        <el-tag size="small">{{ focusStatus.keywords?.length || 0 }} 个关键词</el-tag>
      </div>
    </template>
    <div class="status-details">
      <div v-if="focusStatus.taskDescription">
        <strong>任务：</strong>{{ focusStatus.taskDescription }}
      </div>
      <div v-if="focusStatus.messagesRemoved">
        <strong>已清理：</strong>{{ focusStatus.messagesRemoved }} 条消息
      </div>
      <div v-if="focusStatus.tokensSaved">
        <strong>节省：</strong>{{ focusStatus.tokensSaved }} tokens
      </div>
    </div>
  </el-alert>

  <!-- 配置表单（未启用时） -->
  <el-form v-if="!focusStatus?.enabled">
    <el-form-item label="任务描述">
      <el-input
        v-model="focusTaskDescription"
        type="textarea"
        placeholder="描述当前任务，系统会自动提取关键词..."
      />
    </el-form-item>
    <el-form-item label="关键词">
      <el-select
        v-model="focusKeywords"
        multiple
        filterable
        allow-create
        placeholder="自定义关键词（可选）"
      />
    </el-form-item>
    <el-form-item label="立即压缩">
      <el-switch v-model="focusCompactNow" />
    </el-form-item>
  </el-form>

  <!-- 操作按钮 -->
  <div class="focus-actions">
    <el-button v-if="focusStatus?.enabled" type="danger" @click="clearFocus">
      清除专注模式
    </el-button>
    <el-button v-if="focusStatus?.enabled" type="primary" @click="compactNow">
      执行压缩
    </el-button>
    <el-button v-if="!focusStatus?.enabled" type="primary" @click="enableFocus">
      启用专注模式
    </el-button>
  </div>
</el-dialog>
```

#### 3. 核心逻辑

```typescript
// Focus Mode 相关状态
const focusDialogVisible = ref(false)
const focusStatus = ref<FocusStatus | null>(null)
const focusTaskDescription = ref('')
const focusKeywords = ref<string[]>([])
const focusCompactNow = ref(true)
const focusLoading = ref(false)

// 选择会话时加载 Focus 状态
async function selectSession(session: Session) {
  selectedSession.value = session
  focusStatus.value = null
  loadFocusStatus(session.sessionKey)  // 自动加载状态
  // ... 加载消息
}

// 显示对话框
function showFocusDialog() {
  focusDialogVisible.value = true
  loadFocusStatus(selectedSession.value.sessionKey)
}

// 启用专注模式
async function enableFocus() {
  const res = await focusApi.enable(sessionKey, {
    taskDescription: focusTaskDescription.value,
    keywords: focusKeywords.value,
    compactNow: focusCompactNow.value
  })
  if (res.data.success) {
    focusStatus.value = res.data.data
    // 如果执行了压缩，刷新消息列表
    if (focusCompactNow.value) {
      await loadSessions()
      await selectSession(selectedSession.value)
    }
  }
}

// 执行压缩
async function compactNow() {
  const res = await focusApi.compact(sessionKey)
  if (res.data.compacted) {
    ElMessage.success(`已清理 ${result.details.messagesRemoved} 条消息`)
    await loadFocusStatus(sessionKey)
    await selectSession(selectedSession.value)
  }
}

// 清除专注模式
async function clearFocus() {
  await focusApi.clear(sessionKey)
  focusStatus.value = null
  focusDialogVisible.value = false
}
```

### 使用流程

1. **进入 Sessions 页面**
   - 左侧选择 Agent
   - 中间选择会话

2. **点击"专注模式"按钮**
   - 对话框显示当前状态
   - 未启用时显示配置表单
   - 已启用时显示统计信息

3. **启用专注模式**
   - 输入任务描述（可选）
   - 添加自定义关键词（可选）
   - 选择是否立即压缩
   - 点击"启用专注模式"

4. **执行压缩**
   - 系统自动提取关键词
   - 按相关性过滤消息
   - 保留最近消息和相关消息
   - 显示压缩结果

5. **清除专注模式**
   - 点击"清除专注模式"
   - 状态重置

### UI 效果

```
┌─────────────────────────────────────────────────────────────────────┐
│  会话详情                                                            │
├─────────────────────────────────────────────────────────────────────┤
│  对话记录                    2026-04-02 14:30  [专注模式] 按钮        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  点击按钮后弹出对话框：                                               │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  专注模式                                                      │  │
│  ├───────────────────────────────────────────────────────────────┤  │
│  │  ✓ 专注模式已启用                            [3 个关键词]      │  │
│  │    任务：开发用户认证 API                                      │  │
│  │    已清理：15 条消息                                           │  │
│  │    节省：12000 tokens                                          │  │
│  ├───────────────────────────────────────────────────────────────┤  │
│  │  [清除专注模式]  [执行压缩]  [关闭]                            │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 权限要求

- **读取状态**: 需要 `sessions.read` 权限
- **启用/压缩/清除**: 需要 `sessions.edit` 权限