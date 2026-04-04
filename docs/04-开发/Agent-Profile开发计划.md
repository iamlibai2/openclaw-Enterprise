# Agent Profile 开发计划

> 创建时间：2026-04-04
> 更新时间：2026-04-04
> 状态：进行中

---

## 一、项目概述

将 Agent 视为"人"而非配置集合，提供可视化的档案管理界面。

### 核心组件

| 组件 | 文件 | 人格类比 |
|------|------|----------|
| SOUL.md | 灵魂文件 | 灵魂/性格 |
| IDENTITY.md | 身份文件 | 身份证 |
| USER.md | 主人信息 | 服务对象 |
| MEMORY.md | 记忆文件 | 大脑/记忆 |
| skills | 技能列表 | 经验/技能 |
| tools | 工具配置 | 工具箱 |
| model | 模型配置 | 大脑型号 |
| subagents | 子Agent配置 | 同事/伙伴 |

### 架构说明

**重要**：Admin UI 和 OpenClaw 很可能部署在不同服务器。

```
Admin UI 服务器                    OpenClaw 服务器
┌─────────────────┐              ┌─────────────────┐
│  Admin UI       │              │  OpenClaw       │
│  - templates/   │   Gateway    │  - ~/.openclaw/ │
│  - Flask API    │ ◄─────────► │  - workspace/   │
│  - Vue 前端     │    WebSocket │  - openclaw.json│
└─────────────────┘              └─────────────────┘
      不能直接访问文件系统              所有文件操作通过 API
```

**因此**：所有 Agent 创建、克隆、文件写入操作必须通过 Gateway API。

---

## 二、当前进度

### 已完成 ✅

| 任务 | 文件 | 完成日期 |
|------|------|----------|
| 模块结构设计 | `src/agent/` | 2026-04-04 |
| 类型定义 | `src/agent/types.ts` | 2026-04-04 |
| API 封装 | `src/agent/api.ts` | 2026-04-04 |
| Agent 列表页 | `src/agent/AgentGallery.vue` | 2026-04-04 |
| Agent 档案详情页 | `src/agent/AgentProfile.vue` | 2026-04-04 |
| 身份编辑器 | `src/agent/components/IdentityEditor.vue` | 2026-04-04 |
| 灵魂编辑器 | `src/agent/components/SoulEditor.vue` | 2026-04-04 |
| 主人信息编辑器 | `src/agent/components/UserEditor.vue` | 2026-04-04 |
| 记忆管理器 | `src/agent/components/MemoryManager.vue` | 2026-04-04 |
| 克隆对话框 UI | `src/agent/components/CloneDialog.vue` | 2026-04-04 |
| 导出对话框 UI | `src/agent/components/ExportDialog.vue` | 2026-04-04 |
| 后端 API（基础） | `backend/agent_profile.py` | 2026-04-04 |
| 路由和菜单集成 | `router/index.ts`, `App.vue` | 2026-04-04 |
| 克隆功能后端 | `backend/agent_profile.py` (AgentCloner) | 2026-04-04 |
| 导出功能后端 | `backend/agent_profile.py` (AgentExporter) | 2026-04-04 |
| 模板库 | `templates/` (4个预设模板) | 2026-04-04 |
| 模板 API | `backend/agent_profile.py` (list/create) | 2026-04-04 |
| 创建向导 UI | `src/agent/components/AgentBuilder.vue` | 2026-04-04 |
| 技能配置集成 | `AgentProfile.vue` (跳转 Skills 页面) | 2026-04-04 |
| 工具权限配置 | `components/ToolsEditor.vue` + API | 2026-04-04 |
| Agent 导入功能 | `components/ImportDialog.vue` + API | 2026-04-04 |

### 进行中 🚧

无

### 待开发 📋

所有计划功能已完成 ✅

---

## 三、功能设计

### 3.1 克隆 vs 创建向导 vs 模板创建

| 功能 | 入口 | 数据源 | 流程 | 场景 |
|------|------|--------|------|------|
| **克隆** | 档案页→克隆按钮 | 现有 Agent | 1步完成 | 快速复制成功的 Agent |
| **创建向导** | 列表页→创建按钮 | 模板库/空白 | 多步引导 | 创建新 Agent |
| **从模板创建** | 创建向导中的选项 | 模板库文件 | 选择模板→配置 | 基于预设创建 |

### 3.2 数据源依赖关系

```
克隆功能
└── 数据源: 现有 Agent（已有 xiaomei, main 等）✅

导出功能
└── 输出: .openclaw-agent 文件

模板库
└── 创建: 手动编写模板文件放入 templates/

从模板创建
└── 数据源: 模板库文件（依赖模板库先创建）
```

---

## 四、详细任务分解

### Phase 1: 克隆功能 (P1)

#### 实现方式

通过 Gateway API 实现，不直接访问文件系统。

**流程**:
```
1. config.get          → 获取当前配置
2. 读取源 Agent 信息   → 从配置中获取
3. skills.status       → 获取可用 skills（过滤不存在的）
4. 添加新 Agent 配置   → 修改 config
5. config.apply        → 应用配置
6. agents.files.get    → 读取源 Agent 文件
7. agents.files.set    → 写入新 Agent 文件
```

**使用的 Gateway API**:

| API | 用途 |
|-----|------|
| `config.get` | 获取配置 |
| `config.apply` | 应用配置变更 |
| `agents.files.get` | 读取文件内容 |
| `agents.files.set` | 写入文件内容 |
| `skills.status` | 获取可用 skills |

**文件**: `backend/agent_profile.py`

**API 设计**:
```
POST /api/agents/<agent_id>/clone

Body:
{
  "name": "小美_副本",
  "id": "xiaomei_2",
  "cloneSoul": true,
  "cloneIdentity": true,
  "cloneMemory": false,
  "cloneUser": true,
  "cloneSkills": true,
  "cloneTools": true
}

Response:
{
  "success": true,
  "data": {
    "id": "xiaomei_2",
    "name": "小美_副本"
  }
}
```

**任务清单**:
- [ ] 实现 config.get 调用
- [ ] 构建新 Agent 配置
- [ ] 实现 config.apply 调用
- [ ] 实现 agents.files.get/set 循环写入文件
- [ ] 处理 skills 过滤（只保留已存在的）
- [ ] 错误处理和提示

**预估工时**: 3-4 小时

---

### Phase 2: 导出功能 (P1)

#### 实现方式

读取 Agent 数据，打包为 .openclaw-agent 文件。

**流程**:
```
1. config.get              → 获取 Agent 配置
2. agents.files.get        → 读取各文件内容
3. 构建 manifest.json      → 元数据
4. 打包为 zip 文件         → .openclaw-agent
5. 返回文件流              → 下载
```

**导出格式**:
```
{agent_name}_{date}.openclaw-agent (实际为 zip)
├── manifest.json        # 元数据
├── soul.md             # 灵魂文件
├── identity.md         # 身份文件
├── user.md             # 主人信息
├── skills.json         # 技能配置
├── tools.json          # 工具配置
├── model.json          # 模型配置
└── memory.json         # 记忆文件（可选）
```

**manifest.json 格式**:
```json
{
  "name": "小美",
  "id": "xiaomei",
  "version": "1.0.0",
  "exportedAt": "2026-04-04T12:00:00Z",
  "description": "私人助理",
  "components": {
    "soul": true,
    "identity": true,
    "user": true,
    "skills": true,
    "tools": true,
    "model": true,
    "memory": false
  }
}
```

**文件**: `backend/agent_profile.py`

**任务清单**:
- [ ] 实现 agents.files.get 读取文件
- [ ] 构建 manifest.json
- [ ] 打包为 zip 文件
- [ ] 返回文件下载流
- [ ] 前端触发下载

**预估工时**: 2-3 小时

---

### Phase 3: 模板库 (P2)

#### 目录结构

```
openclaw-control-ui/
├── templates/
│   ├── README.md                    # 模板说明
│   ├── 行政助理.openclaw-agent
│   ├── 代码助手.openclaw-agent
│   ├── 客服代表.openclaw-agent
│   └── 写作助手.openclaw-agent
```

#### 预设模板

| 模板名 | 灵魂风格 | 技能 | 工具 | 适用场景 |
|--------|----------|------|------|----------|
| 行政助理 | 专业严谨 | 日程、文档 | messaging | 安排会议、整理文件 |
| 代码助手 | 技术导向 | 编程、调试 | full | 开发、代码审查 |
| 客服代表 | 热情耐心 | 问答、工单 | messaging | 客户服务 |
| 写作助手 | 创意活泼 | 写作、编辑 | 文档工具 | 内容创作 |

**任务清单**:
- [ ] 创建 templates 目录
- [ ] 编写行政助理模板
- [ ] 编写代码助手模板
- [ ] 编写客服代表模板
- [ ] 编写写作助手模板
- [ ] 后端 API 读取模板列表

**预估工时**: 2-3 小时

---

### Phase 4: 创建向导 (P2)

#### 流程设计

```
Step 1: 选择来源
┌─────────────────────────────────────┐
│  创建 Agent                          │
│                                     │
│  ○ 从模板创建（推荐）                │
│  ○ 从空白创建                        │
│                                     │
│              [下一步]                │
└─────────────────────────────────────┘

Step 2: 选择模板（仅模板创建）
┌─────────────────────────────────────┐
│  选择模板                            │
│                                     │
│  ┌─────────┐ ┌─────────┐            │
│  │ 行政助理 │ │ 代码助手 │            │
│  └─────────┘ └─────────┘            │
│                                     │
│         [上一步]  [下一步]           │
└─────────────────────────────────────┘

Step 3: 配置身份
┌─────────────────────────────────────┐
│  配置身份                            │
│                                     │
│  名字:     [我的助手    ]            │
│  ID:       [my_assistant]           │
│  Emoji:    [🤖          ]            │
│  身份:     [AI 助手     ]            │
│                                     │
│         [上一步]  [下一步]           │
└─────────────────────────────────────┘

Step 4: 配置技能和工具
┌─────────────────────────────────────┐
│  技能配置                            │
│  ☑ acp-router                       │
│  ☐ feishu-bitable                   │
│                                     │
│  工具权限                            │
│  Profile: [messaging ▼]             │
│                                     │
│         [上一步]  [创建]             │
└─────────────────────────────────────┘

Step 5: 完成
┌─────────────────────────────────────┐
│  ✅ 创建成功                         │
│                                     │
│  Agent: 我的助手                     │
│  ID: my_assistant                   │
│                                     │
│  [查看档案]  [返回列表]              │
└─────────────────────────────────────┘
```

**文件**:
- `frontend/src/agent/components/AgentBuilder.vue`
- `backend/agent_profile.py` (create_from_template API)

**任务清单**:
- [x] 创建 AgentBuilder.vue 组件
- [x] 实现多步表单
- [x] 后端 create_from_template API
- [x] 读取模板文件
- [x] 通过 Gateway API 创建 Agent

**预估工时**: 4-6 小时

---

### Phase 5: 技能配置集成 (P1)

#### 方案

在 Agent 档案页添加"配置技能"按钮，跳转到现有 Skills 页面。

**任务清单**:
- [ ] 档案页添加"配置技能"按钮
- [ ] 跳转到 /skills-list 页面
- [ ] （可选）带参数过滤显示相关技能

**预估工时**: 1 小时

---

### Phase 6: 工具权限配置 (P2)

#### 功能

可视化编辑 Agent 的工具权限。

**任务清单**:
- [ ] 获取工具列表 (tools.catalog)
- [ ] 分类展示工具
- [ ] 支持搜索过滤
- [ ] 保存配置 (config.apply)

**预估工时**: 3-4 小时

---

## 五、里程碑计划

| 里程碑 | 目标日期 | 交付物 |
|--------|----------|--------|
| M1: 克隆导出 | 2026-04-05 | 克隆、导出功能完成 |
| M2: 模板创建 | 2026-04-07 | 模板库 + 创建向导 |
| M3: 完整体验 | 2026-04-10 | 工具配置、导入功能 |

---

## 六、Gateway API 参考

### 已确认可用的 API

| API | 功能 | 用途 |
|-----|------|------|
| `config.get` | 获取配置 | 读取 openclaw.json |
| `config.apply` | 应用配置 | 更新 openclaw.json |
| `agents.files.list` | 列出文件 | 查看 Agent 文件列表 |
| `agents.files.get` | 获取文件 | 读取 SOUL.md 等 |
| `agents.files.set` | 写入文件 | 创建/更新文件 |
| `skills.status` | 获取技能状态 | 查看可用技能 |
| `skills.update` | 更新技能 | 启用/禁用技能 |

### 限制

| 操作 | 支持情况 |
|------|----------|
| 创建 Skill 内容 | ❌ 不支持（只能安装已有 skill） |
| 直接文件系统访问 | ❌ 跨服务器不支持 |
| Workspace 路径 | 必须从配置读取 |

---

## 七、风险与注意事项

### 风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Gateway API 变更 | 高 | 使用稳定 API，做好版本兼容 |
| Skills 不存在 | 中 | 克隆时过滤不存在的 skill |
| ID 冲突 | 中 | 创建前检查 ID 是否已存在 |
| 配置冲突 | 中 | 使用 baseHash 乐观锁 |

### 注意事项

1. **所有文件操作必须通过 Gateway API**
   - 不假设可以直接访问文件系统
   - Admin UI 和 OpenClaw 可能部署在不同服务器

2. **Skills 只能引用，不能创建**
   - 克隆时检查 skill 是否存在
   - 不存在的 skill 跳过或提示用户先安装

3. **配置操作需要 baseHash**
   - 使用 `config.get` 获取 hash
   - `config.apply` 时传入 baseHash

---

## 八、变更记录

| 日期 | 变更 | 操作人 |
|------|------|--------|
| 2026-04-04 | 创建开发计划 | Claude |
| 2026-04-04 | 完成基础模块 | Claude |
| 2026-04-04 | 更新架构说明（跨服务器） | Claude |
| 2026-04-04 | 明确开发顺序和依赖关系 | Claude |