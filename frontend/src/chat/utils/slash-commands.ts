/**
 * Slash 命令支持
 * 参考 OpenClaw: /home/iamlibai/workspace/github_code/openclaw/ui/src/ui/chat/slash-commands.ts
 */

import type { SlashCommandDef, SlashCommandCategory, ParsedSlashCommand } from '../types'

// ==================== 命令定义 ====================

/**
 * 企业场景常用命令
 */
export const SLASH_COMMANDS: SlashCommandDef[] = [
  // Session 命令
  {
    key: 'new',
    name: 'new',
    description: '创建新会话',
    category: 'session',
    executeLocal: true,
    shortcut: 'Ctrl+N'
  },
  {
    key: 'clear',
    name: 'clear',
    description: '清空当前会话消息',
    category: 'session',
    executeLocal: true,
    shortcut: 'Ctrl+L'
  },
  {
    key: 'export',
    name: 'export',
    description: '导出聊天记录为 Markdown',
    category: 'session',
    executeLocal: true,
    shortcut: 'Ctrl+E'
  },

  // Tools 命令
  {
    key: 'help',
    name: 'help',
    description: '显示命令帮助',
    category: 'tools',
    executeLocal: true
  }
]

// ==================== 分类 ====================

export const CATEGORY_ORDER: SlashCommandCategory[] = ['session', 'model', 'tools']

export const CATEGORY_LABELS: Record<SlashCommandCategory, string> = {
  session: '会话',
  model: '模型',
  tools: '工具'
}

// ==================== 工具函数 ====================

/**
 * 获取命令补全列表
 */
export function getSlashCommandCompletions(filter: string): SlashCommandDef[] {
  const lower = filter.toLowerCase()
  const commands = lower
    ? SLASH_COMMANDS.filter(
        (cmd) =>
          cmd.name.startsWith(lower) ||
          cmd.aliases?.some((alias) => alias.toLowerCase().startsWith(lower)) ||
          cmd.description.toLowerCase().includes(lower)
      )
    : SLASH_COMMANDS

  return commands.toSorted((a, b) => {
    const ai = CATEGORY_ORDER.indexOf(a.category ?? 'session')
    const bi = CATEGORY_ORDER.indexOf(b.category ?? 'session')
    if (ai !== bi) {
      return ai - bi
    }
    if (lower) {
      const aExact = a.name.startsWith(lower) ? 0 : 1
      const bExact = b.name.startsWith(lower) ? 0 : 1
      if (aExact !== bExact) {
        return aExact - bExact
      }
    }
    return 0
  })
}

/**
 * 解析 Slash 命令
 */
export function parseSlashCommand(text: string): ParsedSlashCommand | null {
  const trimmed = text.trim()
  if (!trimmed.startsWith('/')) {
    return null
  }

  const body = trimmed.slice(1)
  const firstSeparator = body.search(/[\s:]/)
  const name = firstSeparator === -1 ? body : body.slice(0, firstSeparator)
  let remainder = firstSeparator === -1 ? '' : body.slice(firstSeparator).trimStart()
  if (remainder.startsWith(':')) {
    remainder = remainder.slice(1).trimStart()
  }
  const args = remainder.trim()

  if (!name) {
    return null
  }

  const normalizedName = name.toLowerCase()
  const command = SLASH_COMMANDS.find(
    (cmd) =>
      cmd.name === normalizedName ||
      cmd.aliases?.some((alias) => alias.toLowerCase() === normalizedName)
  )
  if (!command) {
    return null
  }

  return { command, args }
}

/**
 * 判断是否为本地命令
 */
export function isLocalCommand(name: string): boolean {
  const cmd = SLASH_COMMANDS.find(
    (c) => c.name === name || c.aliases?.some((a) => a.toLowerCase() === name)
  )
  return cmd?.executeLocal ?? false
}