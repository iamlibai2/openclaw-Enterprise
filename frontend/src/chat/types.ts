/**
 * Chat 模块类型定义
 */

// ==================== Agent ====================

export interface Agent {
  id: string
  name?: string
  modelName?: string
}

// ==================== Session ====================

export interface Session {
  sessionKey: string
  sessionId: string
  title?: string
  updatedAt?: number
}

// ==================== Message ====================

export interface TextContent {
  type: 'text'
  text: string
}

export interface ImageContent {
  type: 'image'
  source?: {
    type: 'base64'
    media_type: string
    data: string
  }
  url?: string
}

export type MessageContent = TextContent | ImageContent

export interface Message {
  role: 'user' | 'assistant' | 'tool'
  content: MessageContent[]
  timestamp: number
  usage?: {
    input?: number
    output?: number
    cacheRead?: number
    cacheWrite?: number
  }
  cost?: {
    total?: number
  }
  model?: string
}

// ==================== Chat State ====================

export interface ChatState {
  // Agent & Session
  agents: Agent[]
  selectedAgentId: string
  sessions: Session[]
  selectedSessionKey: string

  // Messages
  chatMessages: Message[]
  chatStream: string | null
  chatRunId: string | null
  chatSending: boolean
  chatStreamStartedAt: number | null

  // Error
  lastError: string | null
}

// ==================== Events ====================

export interface ChatEventPayload {
  runId: string
  sessionKey: string
  state: 'delta' | 'final' | 'aborted' | 'error'
  message?: unknown
  errorMessage?: string
}

// ==================== Slash Commands ====================

export type SlashCommandCategory = 'session' | 'model' | 'tools'

export interface SlashCommandDef {
  key: string
  name: string
  aliases?: string[]
  description: string
  args?: string
  category?: SlashCommandCategory
  executeLocal?: boolean
  argOptions?: string[]
  shortcut?: string
}

export interface ParsedSlashCommand {
  command: SlashCommandDef
  args: string
}