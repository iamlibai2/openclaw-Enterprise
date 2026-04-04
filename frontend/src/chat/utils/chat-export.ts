/**
 * 聊天导出功能
 * 参考 OpenClaw: /home/iamlibai/workspace/github_code/openclaw/ui/src/ui/chat/export.ts
 */

import type { Message } from '../types'

/**
 * 导出聊天记录为 Markdown 文件
 */
export function exportChatMarkdown(messages: Message[], assistantName: string): void {
  const markdown = buildChatMarkdown(messages, assistantName)
  if (!markdown) {
    return
  }
  const blob = new Blob([markdown], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `chat-${assistantName}-${Date.now()}.md`
  link.click()
  URL.revokeObjectURL(url)
}

/**
 * 构建聊天 Markdown 内容
 */
export function buildChatMarkdown(messages: Message[], assistantName: string): string | null {
  if (!Array.isArray(messages) || messages.length === 0) {
    return null
  }

  const lines: string[] = [`# Chat with ${assistantName}`, '']

  for (const msg of messages) {
    const role = msg.role === 'user' ? 'You' : msg.role === 'assistant' ? assistantName : 'Tool'
    const content = extractText(msg) ?? ''
    const ts = typeof msg.timestamp === 'number' ? new Date(msg.timestamp).toISOString() : ''
    lines.push(`## ${role}${ts ? ` (${ts})` : ''}`, '', content, '')
  }

  return lines.join('\n')
}

/**
 * 提取消息文本
 */
function extractText(message: Message): string | null {
  if (!message || typeof message !== 'object') {
    return null
  }

  // content 数组
  if (Array.isArray(message.content)) {
    const textBlock = message.content.find(
      (block) => block?.type === 'text' && typeof block.text === 'string'
    )
    if (textBlock) {
      return textBlock.text
    }
  }

  return null
}