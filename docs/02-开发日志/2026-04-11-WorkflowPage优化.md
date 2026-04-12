# WorkflowPage 优化 - 2026-04-11

## 概述

今日主要完成了 WorkflowPage.vue 的界面重构和工作流创建功能的修复。

## 完成的工作

### 1. WorkflowPage.vue 界面重构

#### 字体统一
- 从 JetBrains Mono 等宽字体改为系统字体
- 使用 `-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif`
- 与 FeishuChat.vue 保持一致

#### CSS 变量系统
引入与飞书一致的变量系统：
```css
--bg-page: #f7f8fa;
--bg-card: #ffffff;
--bg-hover: #f0f2f5;
--bg-active: #e8f4ff;
--border-subtle: rgba(0, 0, 0, 0.06);
--border-light: rgba(0, 0, 0, 0.08);
--text-primary: #1a1a1a;
--text-secondary: #5c5c5c;
--text-tertiary: #8c8c8c;
--text-placeholder: #b3b3b3;
--accent: #3370ff;
--accent-soft: rgba(51, 112, 255, 0.08);
--accent-medium: rgba(51, 112, 255, 0.15);
--shadow-sm/md/lg;
--radius-sm/md/lg/xl;
```

#### 样式优化
- 输入框居中对齐：`align-items: center` + textarea `padding: 0`
- Focus 状态：蓝色边框 + 柔和阴影
- 消息内容：添加 `:deep(.markdown-body)` 样式统一字体
- 状态指示器：更柔和的动画效果

#### 新增功能
- 右侧空状态添加"加载测试数据"按钮
- DAG 工具栏添加 Test 按钮
- 添加调试日志便于排查问题

### 2. 工作流文件生成修复

#### io.py 修改

**问题**：生成的 workflow.md 缺少必要字段
- 缺少 `状态: ready`
- userInputSchema 为空
- 步骤说明是占位文本

**修复**：
```python
# 自动推断 userInputSchema
def _infer_input_schema(self, workflow: Workflow) -> dict:
    # 从 ${user_input.xxx} 表达式提取参数
    ...

# 参数描述映射
param_desc_map = {
    'topic': '搜索主题/文章主题',
    'query': '搜索关键词',
    'style': '文章风格',
    ...
}

# Skill 描述映射
SKILL_DESCRIPTIONS = {
    'baidu-search': '使用百度搜索，根据关键词搜索相关资料。',
    'article-generator': '根据输入素材，生成指定风格的文章。',
    'wordpress-publish': '发布文章到 WordPress 平台。',
    ...
}
```

#### routes.py 修改
- 接收并传递 `userInputSchema`
- 返回完整的 workflow 定义

**修复后效果**：
```markdown
# search-write-publish

创建时间: 2026-04-11 03:34
状态: ready

## 使用说明

执行工作流时需提供以下参数：
- **topic**: 搜索主题/文章主题
- **style**: 文章风格
- **platform**: 发布平台

## 步骤说明

### 第1步：搜索资料

使用百度搜索，根据关键词搜索相关资料。
输入参数：
  - query: 用户提供的 topic
```

### 3. 前端 DAG 显示修复

#### 问题
- Prometheus 返回表格文本，前端无法解析出 workflow 结构
- 右侧 DAG 不显示

#### 修复方案
改为从后端 API 获取真实 workflow 定义：

```typescript
// 解析成功消息，提取 workflow 名称
async function parseWorkflowResponse(text: string) {
  if (text.includes('工作流创建成功') || text.includes('✅')) {
    const nameMatch = text.match(/名称\s+(\S+)/i)
    if (nameMatch) {
      await fetchWorkflowFromApi(nameMatch[1])
    }
  }
}

// 调用后端 API 获取完整定义
async function fetchWorkflowFromApi(name: string) {
  const res = await axios.get(`/api/workflow/${name}`)
  // 转换 nodes 和 edges 格式
  // 设置 currentWorkflow
}
```

#### 节点 ID 转换
后端使用 `node_1`，前端使用 `node-0`：
```typescript
const nodes = workflow.nodes.map((n, i) => ({
  id: `node-${i}`,
  originalId: n.id,
  name: n.name,
  type: n.type,
  ...
}))

const edges = workflow.edges.map((e) => {
  const fromIdx = workflow.nodes.findIndex(n => n.id === e.from)
  const toIdx = workflow.nodes.findIndex(n => n.id === e.to)
  return { from: `node-${fromIdx}`, to: `node-${toIdx}` }
})
```

## 修改的文件

| 文件 | 改动 |
|------|------|
| `frontend/src/workflow/WorkflowPage.vue` | 界面重构、DAG 显示修复、字体统一 |
| `backend/workflow/io.py` | userInputSchema 推断、步骤说明生成 |
| `backend/workflow/routes.py` | 返回完整 workflow 定义 |

## 验证结果

1. ✅ 创建工作流后，右侧 DAG 正确显示
2. ✅ workflow.md 包含完整字段
3. ✅ 界面字体与飞书一致
4. ✅ 输入框内容居中

## 待办

- [ ] 删除调试日志和测试按钮（上线前）
- [ ] Prometheus 返回结构化 JSON（当前是表格文本）
- [ ] 工作流执行功能的真实实现