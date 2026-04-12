# Workflow 功能完善 - 2026-04-11

## 一、状态持久化

### 背景

WorkflowPage 存在状态丢失问题：
1. 切换页面后对话历史丢失
2. 正在 streaming 时切换页面，回复中断
3. DAG 图消失

### 解决方案

参照 FeishuChat.vue 的成熟模式，实现状态持久化。

### 核心思路

```
┌─────────────────────────────────────────────────────────────┐
│                    Pinia Store + sessionStorage             │
│                                                             │
│  messages[]          ──对话历史                              │
│  currentWorkflow     ──当前工作流 DAG                        │
│  nodeStatus{}        ──节点执行状态                          │
│  thinking/streaming  ──正在进行的对话                        │
│  sessionKey          ──Gateway session                       │
│  pendingRequests{}   ──requestId 关联                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Gateway 连接复用                          │
│                                                             │
│  - WebSocket 单例，不随组件销毁停止                          │
│  - 切换回来时重新绑定事件监听器                               │
│  - 保持 sessionKey，继续接收 streaming                       │
└─────────────────────────────────────────────────────────────┘
```

### 修改的文件

| 文件 | 改动 |
|------|------|
| `frontend/src/workflow/stores.ts` | 新增 Pinia store，管理所有持久化状态 |
| `frontend/src/workflow/WorkflowPage.vue` | 改用 store 状态，Gateway 连接复用 |

### 验证结果

1. ✅ 切换页面后对话历史保持
2. ✅ 切换页面后 DAG 图保持
3. ✅ Streaming 时切换页面，回来后继续接收回复
4. ✅ 页面刷新后状态恢复

---

## 二、执行参数弹窗

### 背景

点击 Execute 按钮时，如果工作流定义了 `userInputSchema`，需要收集用户输入。

### 实现

```typescript
async function executeWorkflow() {
  const schema = currentWorkflow.value.userInputSchema || {}
  // 没有 default 值的字段就是必需参数
  const requiredParams = Object.entries(schema)
    .filter(([key, val]) => !val?.default)
    .map(([key]) => key)

  if (requiredParams.length > 0) {
    // 显示参数弹窗
    showExecuteDialog.value = true
  } else {
    // 无需参数，直接执行
    await sendExecutionRequest({})
  }
}
```

### 弹窗样式

添加了执行参数弹窗的完整 CSS，包括：
- 半透明遮罩层
- 弹窗卡片（圆角、阴影）
- 参数输入表单
- 取消/执行按钮

---

## 三、编排架构重构

### 背景

原设计问题：
- Backend 直接调用 Skill，但 Skill 在 Gateway 上运行
- 形成"Backend → Gateway → Skill"的循环调用

### 新架构

```
┌─────────────────────────────────────────────────────────────┐
│  Prometheus Agent (Gateway 上运行)                          │
│                                                             │
│  用户说"执行工作流 xxx"                                      │
│         ↓                                                    │
│  workflow-execute Skill                                     │
│         ↓                                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  编排循环：                                          │    │
│  │                                                     │    │
│  │  1. POST /orchestrate/start                         │    │
│  │     → Backend 返回第一个节点指令                     │    │
│  │                                                     │    │
│  │  2. 本地执行 Skill (Python 脚本)                    │    │
│  │                                                     │    │
│  │  3. POST /orchestrate/result                        │    │
│  │     → Backend 返回下一个节点指令                     │    │
│  │                                                     │    │
│  │  4. 循环直到 status == "completed"                  │    │
│  │                                                     │    │
│  │  5. 输出节点状态标记供前端解析                       │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  同时通过对话告诉用户进度                                    │
└─────────────────────────────────────────────────────────────┘

Backend (Flask API localhost:5001)
┌─────────────────────────────────────────────────────────────┐
│  OrchestrationEngine                                        │
│                                                             │
│  职责：                                                     │
│  - 拓扑排序                                                 │
│  - 解析变量绑定                                             │
│  - 返回"下一步执行什么"                                      │
│  - 存储节点输出                                             │
│  - 记录执行过程                                             │
│                                                             │
│  不执行 Skill，只编排                                        │
└─────────────────────────────────────────────────────────────┘
```

### 新增 API

| API | 说明 | 请求体 | 返回 |
|------|------|--------|------|
| `/orchestrate/start` | 开始执行 | `{name, user_input}` | 第一个节点指令 |
| `/orchestrate/result` | 提交节点结果 | `{execution_id, node_id, output}` | 下一个节点指令或完成状态 |
| `/orchestrate/error` | 提交节点错误 | `{execution_id, node_id, error}` | 失败状态 |
| `/orchestrate/status/<id>` | 获取执行状态 | - | 当前进度 |

### 编排指令格式

```json
{
  "status": "running",
  "execution_id": "exec_20260411132638_search-write-publish",
  "next_action": "execute_node",
  "node_id": "node_1",
  "node_name": "搜索资料",
  "type": "skill",
  "skill": "baidu-search",
  "input": {"query": "AI技术"},
  "progress": {
    "completed": [],
    "running": "node_1",
    "pending": ["node_2", "node_3"]
  }
}
```

### 修改的文件

| 文件 | 改动 |
|------|------|
| `backend/workflow/orchestration.py` | 新增编排引擎 |
| `backend/workflow/routes.py` | 新增编排 API 路由 |
| `workspace-prometheus/skills/workflow-execute/scripts/execute.py` | 改为编排循环 |

---

## 四、节点状态实时更新

### 背景

执行节点时，前端不知道实时状态，无法更新 DAG。

### 解决方案

通过对话输出节点状态标记，前端解析标记实时更新 DAG。

### 标记格式

```
[WORKFLOW_START: workflow-name]     # 开始执行
[NODE_START: node_id]               # 节点开始
[NODE_COMPLETE: node_id]            # 节点完成
[NODE_ERROR: node_id]               # 节点失败
[EXECUTION_COMPLETE: workflow-name] # 执行完成
[EXECUTION_ERROR: error-msg]        # 执行失败
```

### 前端解析

```typescript
async function parseWorkflowResponse(text: string) {
  // 解析节点状态标记
  const nodeStartMatches = text.matchAll(/\[NODE_START:\s+(\S+)\]/g)
  const nodeCompleteMatches = text.matchAll(/\[NODE_COMPLETE:\s+(\S+)\]/g)
  const nodeErrorMatches = text.matchAll(/\[NODE_ERROR:\s+(\S+)\]/g)

  for (const match of nodeStartMatches) {
    const nodeId = convertNodeId(match[1])  // node_1 → node-0
    workflowStore.updateNodeStatus(nodeId, 'running')
  }

  for (const match of nodeCompleteMatches) {
    const nodeId = convertNodeId(match[1])
    workflowStore.updateNodeStatus(nodeId, 'completed')
  }

  // ...
}

// 节点 ID 转换：后端 node_1 → 前端 node-0
function convertNodeId(backendNodeId: string): string {
  const match = backendNodeId.match(/node_(\d+)/)
  if (match) {
    const index = parseInt(match[1]) - 1
    return `node-${index}`
  }
  return backendNodeId
}
```

### DAG 状态显示

| 状态 | 样式 |
|------|------|
| pending | 灰色，无动画 |
| running | 蓝色边框，背景高亮，动画 |
| completed | 绿色边框，绿色背景 |
| failed | 红色边框，红色背景 |

### 修改的文件

| 文件 | 改动 |
|------|------|
| `frontend/src/workflow/WorkflowPage.vue` | 解析节点状态标记，添加 convertNodeId 函数 |
| `workspace-prometheus/skills/workflow-execute/scripts/execute.py` | 输出节点状态标记 |

---

## 五、工作流创建解析改进

### 背景

Prometheus 返回的 `[WORKFLOW_CREATED: xxx]` 标记中的名称可能截断或不匹配。

### 改进

增加多种解析方式：

1. 精确匹配 `[WORKFLOW_CREATED: name]`
2. 表格匹配 `\| 名称 \| name \|`
3. requestId 关联查询 workflow list
4. 成功关键词触发获取最新工作流

### 修改的文件

| 文件 | 改动 |
|------|------|
| `frontend/src/workflow/WorkflowPage.vue` | 改进 parseWorkflowResponse |
| `workspace-prometheus/SOUL.md` | 强调标记名称必须精确匹配 |

---

## 六、修改的文件汇总

| 文件 | 改动说明 |
|------|---------|
| `frontend/src/workflow/stores.ts` | Pinia store，状态持久化 |
| `frontend/src/workflow/WorkflowPage.vue` | 状态管理、执行弹窗、节点状态解析 |
| `backend/workflow/orchestration.py` | 新增编排引擎 |
| `backend/workflow/routes.py` | 新增编排 API |
| `workspace-prometheus/skills/workflow-execute/scripts/execute.py` | 编排循环 + 状态标记 |
| `workspace-prometheus/SOUL.md` | 执行输出规范 |

---

## 七、完成状态

| 功能 | 状态 |
|------|------|
| 创建工作流 | ✅ 完成 |
| DAG 显示 | ✅ 完成 |
| 状态持久化 | ✅ 完成 |
| 执行参数弹窗 | ✅ 完成 |
| 编排 API | ✅ 完成 |
| 编排循环 | ✅ 完成 |
| 节点状态实时更新 | ✅ 完成 |
| Agent 节点执行 | ⏳ 待实现 |
| 真实 Skill 调用 | ⏳ 待实现（目前是 mock） |

---

## 八、后续优化

- [ ] Agent 节点执行实现
- [ ] 真实 Skill 调用（替换 mock）
- [ ] 添加状态清理按钮
- [ ] 执行历史查看
- [ ] 工作流模板功能