/**
 * markdown.ts 单元测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  stripThinkingTags,
  extractThinking,
  toSanitizedMarkdownHtml,
  renderMessageContent,
  extractMessageText
} from '@/utils/markdown'

// Mock DOMPurify
vi.mock('dompurify', () => ({
  default: {
    sanitize: (html: string) => html,
    addHook: vi.fn()
  }
}))

// Mock marked - Renderer must be a class
vi.mock('marked', () => {
  class MockRenderer {
    html(...args: any[]) { return '' }
    image(...args: any[]) { return '' }
    code(...args: any[]) { return '' }
  }
  return {
    marked: {
      parse: (input: string) => '<p>' + input + '</p>',
      Renderer: MockRenderer
    }
  }
})

describe('stripThinkingTags', () => {
  it('移除 <think> 标签', () => {
    const input = '<think>internal thought</think>Hello world'
    expect(stripThinkingTags(input)).toBe('Hello world')
  })

  it('移除 <thinking> 标签', () => {
    const input = '<thinking>thinking...</thinking>Result'
    expect(stripThinkingTags(input)).toBe('Result')
  })

  it('移除多行 thinking 标签', () => {
    const input = '<think>\nline 1\nline 2\n</think>Output'
    expect(stripThinkingTags(input)).toBe('Output')
  })

  it('移除 relevant-memories 标签', () => {
    const input = '<relevant-memories>memories</relevant-memories>Content'
    expect(stripThinkingTags(input)).toBe('Content')
  })

  it('移除 relevant_memories 标签（下划线）', () => {
    const input = '<relevant_memories>memories</relevant_memories>Content'
    expect(stripThinkingTags(input)).toBe('Content')
  })

  it('无 thinking 标签时保持原样', () => {
    expect(stripThinkingTags('Hello world')).toBe('Hello world')
  })

  it('空字符串返回空', () => {
    expect(stripThinkingTags('')).toBe('')
  })
})

describe('extractThinking', () => {
  it('提取 thinking 内容', () => {
    const input = '<think>thought content</think>Result'
    expect(extractThinking(input)).toBe('thought content')
  })

  it('提取多个 thinking 内容', () => {
    const input = '<think>first</think><think>second</think>Result'
    expect(extractThinking(input)).toBe('first\nsecond')
  })

  it('无 thinking 时返回 null', () => {
    expect(extractThinking('No thinking here')).toBe(null)
  })

  it('空 thinking 标签返回 null', () => {
    expect(extractThinking('<think></think>')).toBe(null)
  })
})

describe('toSanitizedMarkdownHtml', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('空字符串返回空', () => {
    expect(toSanitizedMarkdownHtml('')).toBe('')
  })

  it('空白字符串返回空', () => {
    expect(toSanitizedMarkdownHtml('   ')).toBe('')
  })

  it('渲染简单文本', () => {
    const result = toSanitizedMarkdownHtml('test')
    expect(result).toContain('test')
  })
})

describe('renderMessageContent', () => {
  it('空文本返回空', () => {
    expect(renderMessageContent('')).toBe('')
  })

  it('空白文本返回空', () => {
    expect(renderMessageContent('   ')).toBe('')
  })

  it('渲染普通文本', () => {
    const result = renderMessageContent('Hello')
    expect(result).toContain('markdown-body')
    expect(result).toContain('dir="ltr"')
    expect(result).toContain('Hello')
  })

  it('移除 thinking 标签后渲染', () => {
    const result = renderMessageContent('<thinking>hidden</thinking>Result')
    expect(result).toContain('Result')
  })

  it('检测 RTL 文本', () => {
    // Arabic text
    const result = renderMessageContent('\u0645\u0631\u062d\u0628\u0627')
    expect(result).toContain('dir="rtl"')
  })

  it('检测纯文本表格添加样式', () => {
    // Unicode table characters: ┌───┐
    const tableText = '\u250C\u2500\u2500\u2500\u2510\n\u2502 A \u2502\n\u2514\u2500\u2500\u2500\u2518'
    const result = renderMessageContent(tableText)
    expect(result).toContain('text-table')
  })
})

describe('extractMessageText', () => {
  it('从 text 字段提取', () => {
    expect(extractMessageText({ text: 'hello' })).toBe('hello')
  })

  it('从 content 数组提取', () => {
    expect(extractMessageText({
      content: [{ type: 'text', text: 'array content' }]
    })).toBe('array content')
  })

  it('从 content 字符串提取', () => {
    expect(extractMessageText({ content: 'string content' })).toBe('string content')
  })

  it('无效输入返回 null', () => {
    expect(extractMessageText(null)).toBe(null)
    expect(extractMessageText(undefined)).toBe(null)
    expect(extractMessageText('string')).toBe(null)
    expect(extractMessageText({})).toBe(null)
    expect(extractMessageText({ content: [] })).toBe(null)
    expect(extractMessageText({ content: [{ type: 'image' }] })).toBe(null)
  })
})
