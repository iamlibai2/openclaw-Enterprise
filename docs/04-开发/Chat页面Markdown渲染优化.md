# Chat 页面 Markdown 渲染优化

## 概述

在 Admin UI 的 Chat 页面中实现完整的 Markdown 渲染能力，支持表格、代码块、列表等常见格式。

**开发时间**: 2026-04-04

---

## 问题背景

### 初始状态

Chat 页面最初使用简单的文本显示，消息内容直接展示原始文本：

```vue
<div class="content">{{ getMessageText(msg) }}</div>
```

### 发现的问题

1. **Markdown 表格不渲染** - 发送 `| 列1 | 列2 |` 格式的表格，显示为原始文本
2. **代码块无样式** - 代码块没有语法高亮和复制按钮
3. **文本表格错位** - Unicode 字符画表格没有等宽字体，显示错乱

---

## 技术方案

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Vue 3 组件 (Chat.vue)                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ v-html="renderMarkdown(text)"                        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│               markdown.ts (渲染工具)                         │
│  ├── stripThinkingTags() - 移除 thinking 标签              │
│  ├── detectTextDirection() - 检测文本方向                   │
│  ├── isPlainTextTable() - 检测文本表格                      │
│  └── toSanitizedMarkdownHtml() - Markdown → HTML           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    第三方库                                  │
│  ├── marked - Markdown 解析器（支持 GFM 表格）              │
│  └── dompurify - HTML 安全清理（防 XSS）                    │
└─────────────────────────────────────────────────────────────┘
```

### 依赖库

| 库 | 版本 | 用途 |
|---|---|---|
| `marked` | ^17.0.5 | Markdown 解析，支持 GFM（GitHub Flavored Markdown） |
| `dompurify` | 最新 | HTML 安全清理，防止 XSS 攻击 |

---

## 实现细节

### 1. Markdown 渲染核心

**文件**: `frontend/src/utils/markdown.ts`

#### 1.1 基础渲染函数

```typescript
import DOMPurify from 'dompurify'
import { marked } from 'marked'

export function toSanitizedMarkdownHtml(markdown: string): string {
  const input = markdown.trim()
  if (!input) return ''

  // 解析 Markdown
  const rendered = marked.parse(input, {
    renderer: htmlEscapeRenderer,
    gfm: true,      // GitHub Flavored Markdown（支持表格）
    breaks: true    // 换行转 <br>
  }) as string

  // 安全清理
  return DOMPurify.sanitize(rendered, sanitizeOptions)
}
```

#### 1.2 自定义渲染器

```typescript
const htmlEscapeRenderer = new marked.Renderer()

// 代码块：添加语言标签 + 复制按钮
htmlEscapeRenderer.code = ({ text, lang }) => {
  const langLabel = lang ? `<span class="code-block-lang">${escapeHtml(lang)}</span>` : ''
  const copyBtn = `<button class="code-block-copy" data-code="${attrSafe}">复制</button>`
  const header = `<div class="code-block-header">${langLabel}${copyBtn}</div>`

  // JSON 自动折叠
  if (isJson) {
    return `<details class="json-collapse"><summary>JSON</summary>...</details>`
  }

  return `<div class="code-block-wrapper">${header}${codeBlock}</div>`
}

// 图片：只允许 data:image 内联图片（安全考虑）
htmlEscapeRenderer.image = (token) => {
  if (/^data:image\//i.test(token.href)) {
    return `<img src="${token.href}" alt="${token.text}">`
  }
  return escapeHtml(token.text)  // 外部图片只显示 alt 文本
}
```

### 2. 消息内容处理

```typescript
export function renderMessageContent(text: string): string {
  if (!text.trim()) return ''

  // 1. 移除 thinking 标签（模型内部思考，不展示）
  const cleanedText = stripThinkingTags(text)

  // 2. 检测文本方向（RTL 语言支持）
  const dir = detectTextDirection(cleanedText)

  // 3. 检测是否为文本表格（Unicode 字符画）
  const isTable = isPlainTextTable(cleanedText)

  // 4. 渲染 Markdown
  const html = toSanitizedMarkdownHtml(cleanedText)

  // 5. 包装容器
  const wrapperClass = isTable ? 'markdown-body text-table' : 'markdown-body'
  return `<div class="${wrapperClass}" dir="${dir}">${html}</div>`
}
```

### 3. 文本表格检测

```typescript
function isPlainTextTable(text: string): boolean {
  const tableChars = ['─', '│', '┌', '┐', '└', '┘', '├', '┤', '┬', '┴', '┼',
                      '═', '║', '╔', '╗', '╚', '╝', '╠', '╣', '╦', '╩', '╬']
  let count = 0
  for (const char of text) {
    if (tableChars.includes(char)) count++
    if (count >= 5) return true
  }
  return false
}
```

### 4. RTL 文本方向检测

**文件**: `frontend/src/utils/text-direction.ts`

```typescript
const RTL_CHAR_REGEX =
  /\p{Script=Hebrew}|\p{Script=Arabic}|\p{Script=Syriac}|.../u

export function detectTextDirection(text: string | null): 'rtl' | 'ltr' {
  if (!text) return 'ltr'

  for (const char of text) {
    if (skipPattern.test(char)) continue
    return RTL_CHAR_REGEX.test(char) ? 'rtl' : 'ltr'
  }

  return 'ltr'
}
```

---

## 样式实现

### 关键问题：Vue scoped 样式与 v-html

**问题**：Vue 的 `scoped` 样式**不会应用到 `v-html` 渲染的动态内容**。

**错误做法**：
```vue
<template>
  <div class="content" v-html="html"></div>
</template>

<style scoped>
/* ❌ 这些样式不会应用到 v-html 内容 */
.content table { border-collapse: collapse; }
</style>
```

**解决方案**：使用非 scoped 的 `<style>` 块。

```vue
<style scoped>
/* 组件内部样式 */
.message { ... }
.bubble { ... }
</style>

<!-- 非 scoped：应用到动态内容 -->
<style>
/* Markdown 样式 */
.markdown-body table {
  margin: 12px 0;
  border-collapse: collapse;
  width: 100%;
}

.markdown-body th,
.markdown-body td {
  border: 1px solid #e0e0e0;
  padding: 8px 12px;
}

/* 文本表格：等宽字体 */
.text-table {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  white-space: pre;
}

/* 代码块 */
.code-block-wrapper {
  background: #1e1e1e;
  border-radius: 8px;
}

.code-block-copy {
  background: #404040;
  color: #ccc;
}

.code-block-copy.copied {
  background: #22c55e;
  color: #fff;
}
</style>
```

---

## 功能清单

| 功能 | 实现 | 说明 |
|------|------|------|
| Markdown 表格 | ✅ | GFM 语法支持 |
| 文本表格 | ✅ | Unicode 字符画，等宽字体 |
| 代码块 | ✅ | 语法高亮 class + 复制按钮 |
| JSON 折叠 | ✅ | 纯 JSON 内容自动折叠 |
| 行内代码 | ✅ | \`code\` 格式 |
| 链接 | ✅ | 自动 `target="_blank"` + `rel="noopener"` |
| 图片 | ✅ | 仅支持 data:image 内联 |
| 列表 | ✅ | 有序/无序列表 |
| 引用 | ✅ | `>` 引用块 |
| 标题 | ✅ | h1-h4 |
| 分割线 | ✅ | `---` |
| RTL 支持 | ✅ | 阿拉伯语、希伯来语等 |
| Thinking 过滤 | ✅ | 移除模型内部思考标签 |
| XSS 防护 | ✅ | DOMPurify 安全清理 |
| 缓存优化 | ✅ | 渲染结果缓存 |

---

## 安全措施

### 1. HTML 标签白名单

```typescript
const allowedTags = [
  'a', 'b', 'blockquote', 'br', 'code', 'div', 'em', 'h1', 'h2',
  'h3', 'h4', 'hr', 'i', 'li', 'ol', 'p', 'pre', 'span', 'strong',
  'table', 'tbody', 'td', 'th', 'thead', 'tr', 'ul', 'img', 'details'
]
```

### 2. 属性白名单

```typescript
const allowedAttrs = [
  'class', 'href', 'rel', 'target', 'title', 'src', 'alt', 'dir', 'data-code'
]
```

### 3. 链接安全处理

```typescript
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node instanceof HTMLAnchorElement) {
    // 阻止危险协议（javascript:, data:, vbscript:）
    const url = new URL(node.getAttribute('href'), window.location.href)
    if (!['http:', 'https:', 'mailto:'].includes(url.protocol)) {
      node.removeAttribute('href')
      return
    }

    node.setAttribute('rel', 'noreferrer noopener')
    node.setAttribute('target', '_blank')
  }
})
```

### 4. 原始 HTML 转义

```typescript
// 用户粘贴的 HTML 标签会被转义显示，不会渲染
htmlEscapeRenderer.html = ({ text }) => escapeHtml(text)
```

---

## 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/utils/markdown.ts` | 新增 | Markdown 渲染工具 |
| `frontend/src/utils/text-direction.ts` | 新增 | RTL 文本方向检测 |
| `frontend/src/views/Chat.vue` | 修改 | 使用 Markdown 渲染 + 样式 |
| `frontend/package.json` | 修改 | 添加 dompurify 依赖 |

---

## 参考资料

### OpenClaw 源码

- `/home/iamlibai/workspace/github_code/openclaw/ui/src/ui/markdown.ts` - Markdown 渲染
- `/home/iamlibai/workspace/github_code/openclaw/ui/src/ui/text-direction.ts` - 文本方向检测
- `/home/iamlibai/workspace/github_code/openclaw/ui/src/ui/chat/grouped-render.ts` - 消息渲染
- `/home/iamlibai/workspace/github_code/openclaw/src/shared/text/assistant-visible-text.ts` - Thinking 标签处理

### 第三方文档

- [marked 文档](https://marked.js.org/) - Markdown 解析器
- [DOMPurify 文档](https://github.com/cure53/DOMPurify) - HTML 清理库
- [Vue scoped 样式](https://vuejs.org/api/sfc-css-features.html#scoped-css) - Vue CSS 特性

---

## 后续优化方向

1. **代码语法高亮** - 集成 Prism.js 或 highlight.js
2. **LaTeX 公式** - 支持 `$E=mc^2$` 数学公式
3. **Mermaid 图表** - 支持流程图、时序图
4. **图片上传** - 支持粘贴/拖拽图片
5. **消息操作** - 复制、重新生成、编辑
6. **暗色主题** - 适配暗色模式

---

## 调试技巧

### 查看渲染结果

在浏览器控制台添加日志：

```typescript
console.log('[Markdown] Input:', text.slice(0, 100))
console.log('[Markdown] Output:', html.slice(0, 200))
```

### 检查样式是否应用

1. 打开开发者工具 (F12)
2. 在 Elements 面板选择消息元素
3. 查看 Styles 面板中 `.markdown-body table` 等样式是否显示
4. 如果显示为删除线，说明样式未匹配或被覆盖

### 常见问题排查

| 现象 | 原因 | 解决 |
|------|------|------|
| 表格显示原始文本 | Markdown 未解析 | 检查 `marked.parse()` 是否正常 |
| 样式不生效 | scoped 样式不穿透 v-html | 使用非 scoped `<style>` |
| 代码块无样式 | CSS 选择器问题 | 检查 `.code-block-wrapper` 是否在非 scoped 样式中 |
| 表格被过滤 | DOMPurify 配置问题 | 检查 `allowedTags` 是否包含 `table` 系列标签 |