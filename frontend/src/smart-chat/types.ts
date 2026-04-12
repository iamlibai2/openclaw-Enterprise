export interface Agent {
  id: string
  name: string
  model?: string
  lastMessage?: string
  lastTime?: number
  unread?: number
}

export interface Group {
  id: string
  name: string
  hostId: string
  hostName: string
  members: GroupMember[]
  lastMessage?: string
  lastTime?: number
}

export interface GroupMember {
  agentId: string
  name: string
  enabled: boolean
}

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  sourceAgent?: string
  sourceName?: string
  content: MessageContent[]
  timestamp: number
}

export interface MessageContent {
  type: 'text' | 'image'
  text?: string
  url?: string
}
