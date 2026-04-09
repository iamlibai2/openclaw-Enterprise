/**
 * Chat 模块类型定义
 */

// ==================== Agent ====================

export interface Agent {
  id: string
  name?: string
  modelName?: string
  description?: string
}

// ==================== 会话类型 ====================

export type ConversationType = 'single' | 'group'

// 单聊会话
export interface SingleConversation {
  id: string
  type: 'single'
  agentId: string
  agentName: string
  lastMessage?: string
  lastMessageTime?: number
  unread?: number
  sessionKey: string
}

// 群聊会话
export interface GroupConversation {
  id: string
  type: 'group'
  name: string
  hostAgentId: string
  hostAgentName: string
  participants: Participant[]
  lastMessage?: string
  lastMessageTime?: number
  unread?: number
  sessionKey: string
}

export type Conversation = SingleConversation | GroupConversation

// 群聊参与者
export interface Participant {
  agentId: string
  name: string
  enabled: boolean
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
  id?: string
  role: 'user' | 'assistant' | 'tool'
  content: MessageContent[]
  timestamp: number
  sourceAgent?: string
  sourceName?: string
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