/**
 * 消息文本提取
 * 参考 OpenClaw: /home/iamlibai/workspace/github_code/openclaw/ui/src/ui/chat/message-extract.ts
 */

import type { Message, MessageContent } from '../types'

/**
 * 提取消息文本内容
 */
export function extractText(message: unknown): string | null {
  if (!message || typeof message !== 'object') {
    return null
  }

  const entry = message as Record<string, unknown>

  // 直接 text 字段
  if (typeof entry.text === 'string') {
    return entry.text
  }

  // content 数组
  const content = entry.content
  if (Array.isArray(content)) {
    const textBlock = content.find(
      (block) => block?.type === 'text' && typeof block.text === 'string'
    )
    if (textBlock) {
      return textBlock.text
    }
  }

  // content 字符串
  if (typeof content === 'string') {
    return content
  }

  return null
}

/**
 * 提取消息文本（带缓存）
 */
const textCache = new Map<unknown, string>()

export function extractTextCached(message: unknown): string | null {
  if (!message) {
    return null
  }

  const cached = textCache.get(message)
  if (cached !== undefined) {
    return cached
  }

  const text = extractText(message)
  textCache.set(message, text ?? '')
  return text
}

/**
 * 清空文本缓存
 */
export function clearTextCache(): void {
  textCache.clear()
}