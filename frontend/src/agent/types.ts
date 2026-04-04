/**
 * Agent Profile 模块类型定义
 */

// Agent 档案完整信息
export interface AgentProfile {
  // 基本信息
  id: string
  name: string
  isDefault: boolean
  workspace: string

  // 人格组件
  soul: SoulConfig
  identity: IdentityConfig
  user: UserConfig
  memory: MemoryConfig

  // 能力组件
  skills: string[]
  tools: ToolsConfig
  model: ModelConfig
  subagents: SubagentsConfig

  // 统计
  stats: AgentStats
}

// 灵魂配置
export interface SoulConfig {
  content: string
  coreTruths: string[]
  boundaries: string[]
  vibe: string
}

// 身份配置
export interface IdentityConfig {
  content: string
  name: string
  creature: string
  vibe: string
  emoji: string
  avatar?: string
}

// 主人信息
export interface UserConfig {
  content: string
  name: string
  pronouns: string
  timezone: string
  notes: string
  context: string
}

// 记忆配置
export interface MemoryConfig {
  longTermMemory: string
  longTermMemorySize: number
  dailyMemories: DailyMemory[]
  totalSize: number
  lastUpdated: string
}

// 日期记忆
export interface DailyMemory {
  date: string
  content: string
  size: number
}

// 工具配置
export interface ToolsConfig {
  profile: string
  alsoAllow: string[]
  toolCount: number
}

// 模型配置
export interface ModelConfig {
  primary: string
  fallback?: string
}

// 子Agent配置
export interface SubagentsConfig {
  allowAgents: string[]
  denyAgents: string[]
}

// Agent 统计
export interface AgentStats {
  memoryCount: number
  memorySize: number
  skillCount: number
  toolCount: number
  lastActiveAt?: string
  conversationCount?: number
}

// Agent 列表项（简化版）
export interface AgentListItem {
  id: string
  name: string
  isDefault: boolean
  emoji?: string
  creature?: string
  vibe?: string
  workspace: string
  stats: {
    memoryCount: number
    skillCount: number
    toolCount: number
  }
}

// 导出配置
export interface ExportOptions {
  includeMemory: boolean
  includeHistory: boolean
}

// 克隆选项
export interface CloneOptions {
  name: string
  id: string
  cloneSoul: boolean
  cloneIdentity: boolean
  cloneMemory: boolean
  cloneUser: boolean
  cloneSkills: boolean
  cloneTools: boolean
}

// 编辑结果
export interface EditResult {
  success: boolean
  message?: string
  content?: string
}