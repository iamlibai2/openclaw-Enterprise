/**
 * Group Chat 模块类型定义
 */

// ==================== Participant ====================

export interface Participant {
  agentId: string
  name: string
  description?: string
  enabled: boolean
}

// ==================== Group Chat Message ====================

export interface GroupChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sourceAgent?: string  // 消息来源 Agent ID
  sourceName?: string   // 消息来源 Agent 名称
  timestamp: number
}

// ==================== Group Chat Session ====================

export interface GroupChatSession {
  id: string
  hostSessionKey: string
  hostAgentId: string
  participants: Participant[]
  messages: GroupChatMessage[]
  status: 'active' | 'ended'
  createdAt: number
}

// ==================== Group Chat Config ====================

export interface GroupChatConfig {
  hostAgentId: string
  participants: Participant[]
  maxTurns?: number
  parallelCall?: boolean
}

// ==================== Agent Info ====================

export interface AgentInfo {
  id: string
  name?: string
  description?: string
  modelName?: string
}