/**
 * Markdown 渲染工具
 * 参考 OpenClaw Control UI 实现
 * 源码: /home/iamlibai/workspace/github_code/openclaw/ui/src/ui/markdown.ts
 */

import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { detectTextDirection } from './text-direction'

// 允许的 HTML 标签
const allowedTags = [
  'a', 'b', 'blockquote', 'br', 'button', 'code', 'del', 'div',
  'em', 'h1', 'h2', 'h3', 'h4', 'hr', 'i', 'li', 'ol', 'p',
  'pre', 'span', 'strong', 'summary', 'table', 'tbody', 'td',
  'th', 'thead', 'tr', 'ul', 'img', 'details'
]

// 允许的 HTML 属性
const allowedAttrs = [
  'class', 'href', 'rel', 'target', 'title', 'start', 'src',
  'alt', 'data-code', 'type', 'aria-label', 'dir'
]

const sanitizeOptions = {
  ALLOWED_TAGS: allowedTags,
  ALLOWED_ATTR: allowedAttrs,
  ADD_DATA_URI_TAGS: ['img']
}

// 缓存配置
const MARKDOWN_CACHE_LIMIT = 200
const MARKDOWN_CACHE_MAX_CHARS = 50000
const markdownCache = new Map<string, string>()

// 安装 DOMPurify 钩子
let hooksInstalled = false

function installHooks() {
  if (hooksInstalled) return
  hooksInstalled = true

  DOMPurify.addHook('afterSanitizeAttributes', (node) => {
    if (!(node instanceof HTMLAnchorElement)) return

    const href = node.getAttribute('href')
    if (!href) return

    // 阻止危险 URL 协议
    try {
      const url = new URL(href, window.location.href)
      if (url.protocol !== 'http:' && url.protocol !== 'https:' && url.protocol !== 'mailto:') {
        node.removeAttribute('href')
        return
      }
    } catch {
      // 相对 URL 是安全的
    }

    node.setAttribute('rel', 'noreferrer noopener')
    node.setAttribute('target', '_blank')
  })
}

function getCachedMarkdown(key: string): string | null {
  const cached = markdownCache.get(key)
  if (cached === undefined) return null

  // LRU: 移到最后
  markdownCache.delete(key)
  markdownCache.set(key, cached)
  return cached
}

function setCachedMarkdown(key: string, value: string) {
  markdownCache.set(key, value)
  if (markdownCache.size <= MARKDOWN_CACHE_LIMIT) return

  const oldest = markdownCache.keys().next().value
  if (oldest) markdownCache.delete(oldest)
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

// 检测是否为纯文本表格（Unicode 字符画）
function isPlainTextTable(text: string): boolean {
  const tableChars = ['─', '│', '┌', '┐', '└', '┘', '├', '┤', '┬', '┴', '┼', '═', '║', '╔', '╗', '╚', '╝', '╠', '╣', '╦', '╩', '╬']
  let count = 0
  for (const char of text) {
    if (tableChars.includes(char)) count++
    if (count >= 5) return true
  }
  return false
}

/**
 * 移除 thinking 标签（模型内部思考过程，不展示给用户）
 * 支持 <think> 和 <thinking> 标签
 */
export function stripThinkingTags(text: string): string {
  // 移除 <think>...</think> 和 <thinking>...</thinking>
  return text
    .replace(/<\s*think(?:ing)?\s*>([\s\S]*?)<\s*\/\s*think(?:ing)?\s*>/gi, '')
    .replace(/<\s*relevant[-_]memories\b[^<>]*>[\s\S]*?<\s*\/\s*relevant[-_]memories\s*>/gi, '')
    .trimStart()
}

/**
 * 提取 thinking 内容（如果有）
 */
export function extractThinking(text: string): string | null {
  const matches = [...text.matchAll(/<\s*think(?:ing)?\s*>([\s\S]*?)<\s*\/\s*think(?:ing)?\s*>/gi)]
  const extracted = matches.map(m => (m[1] ?? '').trim()).filter(Boolean)
  return extracted.length > 0 ? extracted.join('\n') : null
}

// 自定义渲染器
const htmlEscapeRenderer = new marked.Renderer()

// HTML 原始内容转义显示
htmlEscapeRenderer.html = ({ text }: { text: string }) => escapeHtml(text)

// 图片处理
htmlEscapeRenderer.image = (token: { href?: string | null; text?: string | null }) => {
  const label = token.text?.trim() || 'image'
  const href = token.href?.trim() ?? ''

  // 只允许 data:image 内联图片
  if (/^data:image\/[a-z0-9.+-]+;base64,/i.test(href)) {
    return `<img class="markdown-inline-image" src="${escapeHtml(href)}" alt="${escapeHtml(label)}">`
  }

  // 外部图片只显示 alt 文本（安全考虑）
  return escapeHtml(label)
}

// 代码块处理
htmlEscapeRenderer.code = ({
  text,
  lang
}: {
  text: string
  lang?: string
  escaped?: boolean
}) => {
  const langClass = lang ? ` class="language-${escapeHtml(lang)}"` : ''
  const safeText = escapeHtml(text)
  const codeBlock = `<pre><code${langClass}>${safeText}</code></pre>`
  const langLabel = lang ? `<span class="code-block-lang">${escapeHtml(lang)}</span>` : ''

  // 复制按钮
  const attrSafe = text
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  const copyBtn = `<button type="button" class="code-block-copy" data-code="${attrSafe}" aria-label="复制代码"><span class="code-block-copy__idle">复制</span><span class="code-block-copy__done">已复制!</span></button>`
  const header = `<div class="code-block-header">${langLabel}${copyBtn}</div>`

  // JSON 自动折叠
  const trimmed = text.trim()
  const isJson =
    lang === 'json' ||
    (!lang && ((trimmed.startsWith('{') && trimmed.endsWith('}')) ||
               (trimmed.startsWith('[') && trimmed.endsWith(']'))))

  if (isJson) {
    const lineCount = text.split('\n').length
    const label = lineCount > 1 ? `JSON · ${lineCount} 行` : 'JSON'
    return `<details class="json-collapse"><summary>${label}</summary><div class="code-block-wrapper">${header}${codeBlock}</div></details>`
  }

  return `<div class="code-block-wrapper">${header}${codeBlock}</div>`
}

/**
 * 将 Markdown 转换为安全的 HTML
 */
export function toSanitizedMarkdownHtml(markdown: string): string {
  const input = markdown.trim()
  if (!input) return ''

  installHooks()

  // 检查缓存
  if (input.length <= MARKDOWN_CACHE_MAX_CHARS) {
    const cached = getCachedMarkdown(input)
    if (cached !== null) return cached
  }

  // 解析 Markdown
  let rendered: string
  try {
    rendered = marked.parse(input, {
      renderer: htmlEscapeRenderer,
      gfm: true,      // GitHub Flavored Markdown（支持表格）
      breaks: true    // 换行转 <br>
    }) as string
  } catch (err) {
    console.warn('[markdown] marked.parse failed, falling back to plain text:', err)
    rendered = `<pre class="code-block">${escapeHtml(input)}</pre>`
  }

  // 安全清理
  const sanitized = DOMPurify.sanitize(rendered, sanitizeOptions)

  // 缓存结果
  if (input.length <= MARKDOWN_CACHE_MAX_CHARS) {
    setCachedMarkdown(input, sanitized)
  }

  return sanitized
}

/**
 * 渲染消息内容
 * - 自动检测文本方向
 * - 检测纯文本表格，使用等宽字体
 * - Markdown 渲染
 */
export function renderMessageContent(text: string): string {
  if (!text.trim()) return ''

  // 移除 thinking 标签（不展示）
  const cleanedText = stripThinkingTags(text)

  // 检测文本方向
  const dir = detectTextDirection(cleanedText)

  // 检测是否为纯文本表格
  const isTable = isPlainTextTable(cleanedText)

  // 渲染 Markdown
  const html = toSanitizedMarkdownHtml(cleanedText)

  // 包装容器
  const wrapperClass = isTable ? 'markdown-body text-table' : 'markdown-body'
  return `<div class="${wrapperClass}" dir="${dir}">${html}</div>`
}

/**
 * 提取消息文本（支持多种格式）
 */
export function extractMessageText(message: unknown): string | null {
  if (!message || typeof message !== 'object') return null

  const entry = message as Record<string, unknown>

  // 直接 text 字段
  if (typeof entry.text === 'string') return entry.text

  // content 数组
  const content = entry.content
  if (Array.isArray(content)) {
    const textBlock = content.find(
      (block) => block?.type === 'text' && typeof block.text === 'string'
    )
    if (textBlock) return textBlock.text
  }

  // content 字符串
  if (typeof content === 'string') return content

  return null
}