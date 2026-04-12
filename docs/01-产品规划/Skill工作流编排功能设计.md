# Skill 工作流编排功能设计

> 状态：设计完成
> 优先级：P1
> 创建时间：2026-04-10
> 更新时间：2026-04-10

## 背景

当前的 Skill 都是独立运行的，但实际工作中经常需要将多个 Skill 串联完成一个完整任务。

**典型场景**：
```
搜索资料 → 生成文章 → 排版美化 → 发布公众号
```

**问题**：用户需要手动执行每个 Skill，并在之间传递数据，效率低、易出错。

**目标**：让用户用自然语言创建工作流，将多个 Skill 自动串联执行。

## 核心原则

### 原则一：自然语言操作，可视化只呈现

- 用户不需要拖拽节点、不需要写配置文件
- 所有操作通过 Agent 对话完成
- 可视化用于实时查看工作流结构和执行进度

### 原则二：人不在流程中，人在流程外

```
❌ 旧思路：人在流程里
流程 ──节点1──▶ 节点2 ──人工审批──▶ 节点3 ──人工发布──▶ 完成

✅ 新思路：人在流程外
流程 ──节点1──▶ 节点2 ──节点3──▶ 节点4──▶ 完成
                                      ↓
                             人查看结果、评估、提建议
```

**人的角色**：

| 角色 | 具体工作 |
|------|---------|
| 评估者 | 查看执行结果，判断质量 |
| 优化者 | 发现问题，提出改进建议 |
| 决策者 | 决定是否启用某个工作流 |
| 监督者 | 监控工作流执行情况 |

**人参与的是**：事后评估和优化，不是流程运转。

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                           用户界面层                                 │
│  ┌─────────────────────────┬───────────────────────────────────┐   │
│  │     Agent 对话面板       │         工作流可视化面板          │   │
│  │  (自然语言输入/输出)     │   (DAG图/执行状态/数据流向)       │   │
│  └─────────────────────────┴───────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      编排 Agent（系统级）                            │
│                                                                     │
│  职责：                                                             │
│  - 理解用户意图，创建/修改工作流                                    │
│  - 协助用户评估执行结果                                             │
│  - 根据用户反馈优化工作流                                           │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      工作流引擎（独立执行器）                        │
│                                                                     │
│  职责：                                                             │
│  - 读取工作流定义文件                                               │
│  - 按 DAG 顺序全自动执行                                            │
│  - 调用 Skill / Agent                                               │
│  - 数据传递、存储输出                                               │
│  - 记录执行历史                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      工作流定义文件（Markdown + JSON）               │
│                                                                     │
│  workflows/公众号发布/workflow.md                                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 两个核心问题

| 问题 | 答案 |
|------|------|
| **谁来编排？** | 编排 Agent（系统级服务），用户用自然语言交互 |
| **谁来执行？** | 工作流引擎（独立执行器），按文件定义全自动执行 |

## 界面设计

### 左右布局

```
┌────────────────────────┬──────────────────────────────────┐
│                        │                                  │
│   🤖 编排Agent对话     │      工作流可视化                 │
│                        │                                  │
│   用户: 创建工作流     │      [搜索]──▶[写文章]──▶[发布]  │
│   Agent: 已创建...     │                                  │
│                        │      实时更新：                   │
│   用户: 执行工作流     │      - 执行进度                   │
│   Agent: 开始执行...   │      - 数据流向                   │
│   Agent: 执行完成！    │      - 节点状态                   │
│                        │                                  │
│   用户: 搜索不够全面   │      执行结果：                   │
│   Agent: 已优化...     │      文章已发布: https://xxx      │
│                        │                                  │
│   [输入框]             │                                  │
│                        │                                  │
└────────────────────────┴──────────────────────────────────┘
     左侧 40%                     右侧 60%
```

### 交互流程

```
┌─────────────────────────────────────────────────────────────────┐
│ 阶段1：创建工作流                                                │
├─────────────────────────────────────────────────────────────────┤
│ 用户: "帮我创建公众号发布工作流"                                  │
│ 编排Agent: "已创建，包含搜索、生成文章、排版、发布四个步骤"       │
│            [右侧可视化展示 DAG]                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 阶段2：执行工作流（全自动，无人工干预）                           │
├─────────────────────────────────────────────────────────────────┤
│ 用户: "执行这个工作流，主题是AI发展趋势，风格正式"                 │
│ 编排Agent: "开始执行..."                                         │
│                                                                 │
│            [右侧实时显示执行进度]                                 │
│            [搜索 ✓]──▶[生成 ⏳]──▶[排版 ○]──▶[发布 ○]           │
│                                                                 │
│ 编排Agent: "执行完成，文章已发布：https://xxx"                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 阶段3：事后评估与优化（人在流程外）                               │
├─────────────────────────────────────────────────────────────────┤
│ 用户查看结果，发现问题：                                          │
│                                                                 │
│ 用户: "搜索结果不够全面"                                          │
│ 编排Agent: "我来优化搜索节点的配置..."                            │
│            "已增加国际资讯数据源，下次执行会更全面"                │
│                                                                 │
│ 用户: "文章风格太正式了"                                          │
│ 编排Agent: "已修改生成文章节点的默认风格参数"                     │
└─────────────────────────────────────────────────────────────────┘
```

## 数据结构设计

### 工作流定义

```typescript
interface Workflow {
  id: string
  name: string
  version: string
  nodes: Node[]
  edges: Edge[]
  userInputSchema?: { [key: string]: InputParam }
}

interface Node {
  id: string                // node_1
  name: string              // 搜索资料
  type: 'skill' | 'agent'   // 只有两种类型
  skill?: string            // skill 类型时：skill ID
  agent_id?: string         // agent 类型时：agent ID
  input: { [param: string]: string }  // 变量绑定
}

interface Edge {
  from: string
  to: string
}
```

### 节点类型（简化）

由于人不在流程中，节点类型只有两种：

| 类型 | 执行者 | 说明 |
|------|--------|------|
| `skill` | 系统调用 | 自动执行某个 Skill |
| `agent` | 指定 Agent | 调用某员工的 Agent 执行 |

**不需要**审批节点、人工节点。

## Skill 数据传递机制

### 变量绑定系统

每个节点执行后，输出存储在内存。下游节点通过**变量引用**获取数据：

```typescript
// 节点执行后的数据存储（内存）
nodeOutputs: Map<string, any> = {
  "node_1": {
    results: [{ title: "...", content: "..." }],
    summary: "AI发展趋势..."
  },
  "node_2": {
    article: "标题：AI发展趋势分析..."
  }
}

// 下游节点引用数据的方式
inputConfig: {
  // 方式1：引用整个输出
  material: "${node_1.output}"

  // 方式2：引用输出的某个字段
  topic: "${node_1.output.summary}"

  // 方式3：引用用户输入
  style: "${user_input.style}"

  // 方式4：固定值
  format: "wechat"
}
```

### 数据传递示例

**工作流：公众号文章发布**

| 节点 | Skill | 输入配置 | 输出 |
|------|-------|---------|------|
| node_1 | baidu-search | query: `${user_input.topic}` | { results: [...], summary: "..." } |
| node_2 | article-generator | material: `${node_1.output.results}`, style: `${user_input.style}` | { article: "..." } |
| node_3 | formatter | content: `${node_2.output.article}`, format: `wechat` | { formatted: "..." } |
| node_4 | wechat-publisher | content: `${node_3.output.formatted}` | { published: true, url: "..." } |

### 数据来源类型

| 来源 | 表达式 | 说明 |
|------|--------|------|
| 用户输入 | `${user_input.xxx}` | 工作流启动时用户提供 |
| 上游节点 | `${node_N.output.xxx}` | 引用已执行节点的输出 |
| 固定值 | `wechat` | 直接传入固定参数 |

### 执行时的数据流

```
1. 用户启动工作流
   user_input = { topic: "AI发展趋势", style: "正式" }

2. 执行 node_1 (baidu-search)
   解析输入: query = "AI发展趋势" (从 user_input)
   执行 Skill: baidu-search("AI发展趋势")
   存储输出: node_outputs["node_1"] = { results: [...], summary: "..." }

3. 执行 node_2 (article-generator)
   解析输入:
     material = node_outputs["node_1"].results (从内存取)
     style = user_input.style (从用户输入取)
   执行 Skill: article-generator(material, style)
   存储输出: node_outputs["node_2"] = { article: "..." }

4. 继续执行后续节点...
```

## 文件存储方案

采用 **Markdown + 内嵌 JSON** 存储工作流定义，不依赖数据库。

**设计原则**：
- **JSON 部分**：核心结构数据（节点、边、变量绑定），规范化、防篡改
- **Markdown 部分**：人类可读的描述、说明、文档，供大模型直接阅读理解

### 文件格式

```markdown
# 公众号文章发布

创建时间: 2026-04-10
状态: ready

## 目标

搜索 AI 相关资料，生成正式风格文章，发布到公众号。

## 使用说明

1. 输入搜索主题
2. 选择文章风格
3. 执行工作流

---

<!-- WORKFLOW_DEFINITION
{
  "id": "wf_001",
  "name": "公众号文章发布",
  "version": "1.0",
  "nodes": [
    {
      "id": "node_1",
      "name": "搜索资料",
      "type": "skill",
      "skill": "baidu-search",
      "input": { "query": "${user_input.topic}" }
    },
    {
      "id": "node_2",
      "name": "生成文章",
      "type": "skill",
      "skill": "article-generator",
      "input": {
        "material": "${node_1.output.results}",
        "style": "${user_input.style}"
      }
    },
    {
      "id": "node_3",
      "name": "排版",
      "type": "skill",
      "skill": "formatter",
      "input": {
        "content": "${node_2.output.article}",
        "format": "wechat"
      }
    },
    {
      "id": "node_4",
      "name": "发布",
      "type": "skill",
      "skill": "wechat-publisher",
      "input": { "content": "${node_3.output.formatted}" }
    }
  ],
  "edges": [
    { "from": "node_1", "to": "node_2" },
    { "from": "node_2", "to": "node_3" },
    { "from": "node_3", "to": "node_4" }
  ],
  "userInputSchema": {
    "topic": { "type": "string", "description": "搜索主题" },
    "style": { "type": "string", "description": "文章风格", "enum": ["正式", "轻松"] }
  }
}
WORKFLOW_DEFINITION -->

## 步骤说明

### 第一步：搜索资料

使用百度搜索，根据用户提供的主题搜索相关资料。

### 第二步：生成文章

根据搜索结果，按照指定风格生成文章。

### 第三步：排版

将文章排版为公众号格式。

### 第四步：发布

发布到微信公众号。
```

### 格式说明

| 部分 | 格式 | 用途 | 可编辑 |
|------|------|------|--------|
| 标题、元信息 | Markdown | 基本信息 | ✅ 用户可编辑 |
| 目标、说明 | Markdown | 人类可读文档 | ✅ 用户可编辑 |
| `<!-- WORKFLOW_DEFINITION ... -->` | JSON 注释块 | 核心结构定义 | ⚠️ 仅 Agent 修改 |
| 步骤说明 | Markdown | 辅助说明 | ✅ 用户可编辑 |

**JSON 块保护机制**：
- 使用 HTML 注释 `<!-- -->` 包裹，普通 Markdown 编辑器不会渲染
- Agent 修改时只更新 JSON 块内部，不影响其他 Markdown 内容
- 用户如果误改 JSON 块，Agent 会检测并修复

### 文件目录结构

```
.openclaw/
└── workflows/
    ├── README.md                   # 工作流索引
    │
    ├── 公众号文章发布/
    │   ├── workflow.md             # 工作流定义
    │   └── executions/
    │       ├── 2026-04-10-14-30.md # 执行记录
    │       └── 2026-04-10-15-00.md
    │
    ├── 数据分析报告/
    │   └── workflow.md
    │
    └── templates/
        └── 公众号发布模板.md        # 可复用模板
```

### 执行记录文件格式

执行记录也采用 Markdown + JSON 格式：

```markdown
# 执行记录: 2026-04-10 14:30

工作流: 公众号文章发布
状态: 完成
耗时: 45秒

## 用户输入

- 主题: AI发展趋势
- 风格: 正式

---

<!-- EXECUTION_DATA
{
  "workflowId": "wf_001",
  "executionId": "exec_202604101430",
  "status": "completed",
  "startedAt": "2026-04-10T14:30:00",
  "completedAt": "2026-04-10T14:30:45",
  "userInput": {
    "topic": "AI发展趋势",
    "style": "正式"
  },
  "nodeExecutions": [
    {
      "nodeId": "node_1",
      "status": "completed",
      "duration": 3,
      "outputFile": "outputs/exec_202604101430/node_1.json"
    },
    {
      "nodeId": "node_2",
      "status": "completed",
      "duration": 25,
      "outputFile": "outputs/exec_202604101430/node_2.json"
    },
    {
      "nodeId": "node_3",
      "status": "completed",
      "duration": 5,
      "outputFile": "outputs/exec_202604101430/node_3.json"
    },
    {
      "nodeId": "node_4",
      "status": "completed",
      "duration": 12,
      "outputFile": "outputs/exec_202604101430/node_4.json"
    }
  ],
  "finalOutput": {
    "published": true,
    "url": "https://mp.weixin.qq.com/xxx"
  }
}
EXECUTION_DATA -->

## 执行过程

### 第一步：搜索资料 (3秒) ✅

搜索完成，找到 5 条相关结果。

### 第二步：生成文章 (25秒) ✅

文章已生成，标题：AI发展趋势深度分析

### 第三步：排版 (5秒) ✅

已排版为公众号格式。

### 第四步：发布 (12秒) ✅

文章已发布到公众号。

## 最终结果

文章已成功发布，链接: https://mp.weixin.qq.com/xxx
```

### 节点输出文件

各节点的详细输出数据存为 JSON 文件（数据可能很大，不适合嵌入 Markdown）：

```
workflows/公众号文章发布/
└── outputs/
    └── exec_202604101430/
        ├── node_1.json    # 搜索结果（大数组）
        ├── node_2.json    # 生成的文章内容
        ├── node_3.json    # 排版后的 HTML
        └── node_4.json    # 发布结果
```

## 数据存储策略

| 数据类型 | 存储位置 | 格式 | 存储时机 |
|---------|---------|------|---------|
| 工作流定义（结构） | workflow.md 内 JSON 块 | JSON 注释块 | 创建/修改时 |
| 工作流说明（文档） | workflow.md | Markdown | 随时可编辑 |
| 用户输入 | executions/*.md 内 JSON 块 | JSON 注释块 | 启动时 |
| 节点输出（大数据） | outputs/*.json | JSON 文件 | 每节点执行完 |
| 执行记录（结构） | executions/*.md 内 JSON 块 | JSON 注释块 | 执行完成时 |
| 执行说明（文档） | executions/*.md | Markdown | 执行完成时 |

### 文件职责划分

```
workflow.md
├── Markdown 部分（用户/Agent 都可编辑）
│   ├── 标题、元信息
│   ├── 目标描述
│   ├── 使用说明
│   └── 步骤说明
│
└── JSON 块（仅 Agent 修改，存储核心结构）
    ├── nodes: 节点定义
    ├── edges: 边定义
    └── userInputSchema: 输入参数定义
```

### JSON 块保护机制

```python
class WorkflowFile:
    MARKER_START = "<!-- WORKFLOW_DEFINITION"
    MARKER_END = "WORKFLOW_DEFINITION -->"

    def read_json_block(self, content: str) -> dict:
        """提取 JSON 块"""
        start = content.find(self.MARKER_START)
        end = content.find(self.MARKER_END)
        if start == -1 or end == -1:
            return None
        json_str = content[start + len(self.MARKER_START):end].strip()
        return json.loads(json_str)

    def write_json_block(self, content: str, data: dict) -> str:
        """更新 JSON 块，保留其他 Markdown 内容"""
        new_json = json.dumps(data, ensure_ascii=False, indent=2)
        new_block = f"{self.MARKER_START}\n{new_json}\n{self.MARKER_END}"

        start = content.find(self.MARKER_START)
        end = content.find(self.MARKER_END) + len(self.MARKER_END)

        if start == -1:
            # 没有 JSON 块，追加到文件末尾
            return content + "\n\n---\n\n" + new_block + "\n"
        else:
            # 替换现有 JSON 块
            return content[:start] + new_block + content[end:]

    def validate_json_block(self, content: str) -> bool:
        """验证 JSON 块是否有效"""
        try:
            data = self.read_json_block(content)
            required = ['id', 'name', 'nodes', 'edges']
            return all(k in data for k in required)
        except:
            return False
```

**核心逻辑**：
- **Markdown 部分**：人类可读、可编辑，Agent 也能理解
- **JSON 块部分**：结构化数据，Agent 修改时精确定位、不污染其他内容
- **节点输出**：单独 JSON 文件，因为数据量大

## 执行引擎设计

```python
class WorkflowEngine:
    """工作流执行引擎 - 全自动执行，无人工干预"""

    def __init__(self):
        self.workflow_io = WorkflowIO()
        self.output_io = OutputIO()
        self.node_outputs = {}      # 内存缓存
        self.user_input = {}        # 用户输入

    async def execute(self, workflow_name: str, user_input: dict) -> dict:
        """执行工作流 - 一气呵成，不暂停"""
        self.user_input = user_input
        self.node_outputs = {}

        # 1. 读取工作流定义
        _, data = self.workflow_io.read(workflow_name)
        nodes = data['nodes']
        edges = data['edges']

        # 2. 拓扑排序确定执行顺序
        order = self._topological_sort(nodes, edges)

        # 3. 生成执行 ID
        execution_id = datetime.now().strftime('%Y%m%d%H%M%S')

        # 4. 逐节点执行（全部自动，无等待）
        for node_id in order:
            node = next(n for n in nodes if n['id'] == node_id)
            await self._execute_node(workflow_name, execution_id, node)

        # 5. 返回最终输出
        last_node = nodes[-1]
        return self.node_outputs.get(last_node['id'])

    async def _execute_node(self, workflow_name: str, execution_id: str, node: dict):
        """执行单个节点"""
        # 1. 解析输入
        input_data = self._resolve_inputs(node.get('input', {}))

        # 2. 根据节点类型调用
        if node['type'] == 'skill':
            output = await self._invoke_skill(node['skill'], input_data)
        elif node['type'] == 'agent':
            output = await self._invoke_agent(node['agent_id'], input_data)

        # 3. 存到内存（供下游节点使用）
        self.node_outputs[node['id']] = output

        # 4. 存到文件（持久化，用于历史追溯）
        self.output_io.save(execution_id, node['id'], output)

    def _resolve_inputs(self, input_config: dict) -> dict:
        """解析输入变量绑定"""
        result = {}
        for param, expr in input_config.items():
            result[param] = self._evaluate_expression(expr)
        return result

    def _evaluate_expression(self, expr: str) -> any:
        """解析 ${node_1.output.results} 等表达式"""
        if not isinstance(expr, str) or not expr.startswith('${'):
            return expr  # 固定值

        path = expr[2:-1]  # 去掉 ${ }
        parts = path.split('.')

        if parts[0] == 'user_input':
            return self.user_input.get(parts[1])
        else:
            # ${node_1.output.results}
            node_id = parts[0]
            value = self.node_outputs.get(node_id, {})
            for field in parts[1:]:
                if isinstance(value, dict):
                    value = value.get(field)
            return value
```

**关键特点**：
- 没有等待、没有暂停
- 全自动一气呵成执行完
- 节点类型只有 skill 和 agent

## 自然语言命令

### 编排相关

| 用户输入 | 编排Agent 动作 |
|---------|---------------|
| "创建一个XX工作流" | 解析意图，生成完整工作流定义 |
| "添加一个搜索步骤" | 在指定位置插入节点 |
| "删除第X步" | 删除节点，调整边 |
| "把第X步改成..." | 修改节点配置 |
| "用搜索到的结果作为素材" | 自动建立变量绑定关系 |

### 执行相关

| 用户输入 | 编排Agent 动作 |
|---------|---------------|
| "执行这个工作流" | 调用引擎开始执行 |
| "执行工作流，主题是XX" | 带参数执行 |
| "最近执行效果怎么样？" | 分析执行记录，给出统计 |

### 评估优化相关

| 用户输入 | 编排Agent 动作 |
|---------|---------------|
| "搜索结果不够全面" | 优化搜索节点配置 |
| "文章风格太正式了" | 修改生成节点参数 |
| "排版换成XX格式" | 更新排版节点 |
| "加一个数据分析步骤" | 插入新节点 |

## 功能实现优先级

| 阶段 | 功能 | 说明 |
|------|------|------|
| **P0** | 文件操作层 | Markdown + JSON 读写 |
| **P0** | 执行引擎（基础） | 串行全自动执行 |
| **P0** | 编排Agent（创建） | 自然语言创建工作流 |
| **P0** | 可视化展示 | DAG 图渲染，执行状态 |
| **P1** | 执行记录 | Markdown + JSON 记录 |
| **P1** | 编排Agent（修改） | 自然语言修改工作流 |
| **P1** | 编排Agent（评估） | 分析执行结果，接受优化建议 |
| **P2** | 并行执行 | 多节点同时运行 |
| **P2** | 工作流模板 | 保存、复用、分享 |
| **P2** | 条件分支 | if/else 路径 |
| **P3** | 断点续执行 | 从失败节点重新执行 |

## 数据格式适配

当上游输出格式与下游输入不匹配时：

### 方式1：Skill 自带适配能力

```yaml
# article-generator skill 定义
inputSchema:
  material:
    type: string | array
    description: "素材内容"
```

Skill 内部处理不同格式的输入。

### 方式2：Agent 自动转换

Agent 检测格式不匹配，自动添加转换节点或配置：

```
用户: "用搜索结果生成文章"

Agent 检测:
  - baidu-search 输出: array[{title, content}]
  - article-generator 输入: string

Agent: "我会把搜索结果提取成文本再传给文章生成"
自动配置: material = ${node_1.output.results.map(r => r.content).join('\n')}
```

### 方式3：显式转换节点

```yaml
nodes:
  - id: transform_1
    type: transform
    input: ${node_1.output.results}
    transform: "map(r => r.content).join('\n')"
```

## 可视化展示内容

右侧可视化展示以下信息（只展示，不操作）：

1. **DAG 结构图**：节点和连接关系
2. **节点状态**：pending(灰) / running(蓝动画) / done(绿) / failed(红)
3. **数据流向动画**：节点间箭头流动效果
4. **执行进度**：当前节点、已执行节点数
5. **实时输出预览**：点击节点查看输出数据

## 技术栈选择

| 功能 | 技术选型 |
|------|---------|
| 文件解析 | Python YAML + Markdown 解析库 |
| DAG 可视化 | Vue + D3.js / Vue Flow |
| 执行引擎 | Python asyncio |
| 数据存储 | 内存 dict + 文件系统 |

## 参考案例

- **n8n**：可视化工作流编排（但我们用自然语言操作）
- **Dify**：LLM 工作流编排
- **Coze**：字节的工作流编排产品
- **LangGraph**：LangChain 的 DAG 执行框架

## 后续讨论

1. 条件分支的具体语法设计
2. 并行节点的依赖关系处理
3. 工作流模板的管理方式
4. 与现有 Skill 系统的集成方式