/**
 * Agent Profile API
 */

import api from '../api'
import type { AgentProfile, AgentListItem, CloneOptions, ExportOptions } from './types'

// 获取 Agent 列表（简化版）
export async function getAgentList(): Promise<AgentListItem[]> {
  const res = await api.get<{ success: boolean; data: AgentListItem[] }>('/agents/list')
  return res.data.data || []
}

// 获取 Agent 完整档案
export async function getAgentProfile(agentId: string): Promise<AgentProfile | null> {
  try {
    const res = await api.get<{ success: boolean; data: AgentProfile }>(`/agents/${agentId}/profile`)
    return res.data.data || null
  } catch {
    return null
  }
}

// 更新灵魂
export async function updateAgentSoul(agentId: string, content: string): Promise<boolean> {
  try {
    const res = await api.put<{ success: boolean }>(`/agents/${agentId}/soul`, { content })
    return res.data.success
  } catch {
    return false
  }
}

// 更新身份
export async function updateAgentIdentity(
  agentId: string,
  data: { name?: string; creature?: string; vibe?: string; emoji?: string; avatar?: string }
): Promise<boolean> {
  try {
    const res = await api.put<{ success: boolean }>(`/agents/${agentId}/identity`, data)
    return res.data.success
  } catch {
    return false
  }
}

// 更新主人信息
export async function updateAgentUser(
  agentId: string,
  data: { name?: string; pronouns?: string; timezone?: string; notes?: string; context?: string }
): Promise<boolean> {
  try {
    const res = await api.put<{ success: boolean }>(`/agents/${agentId}/user`, data)
    return res.data.success
  } catch {
    return false
  }
}

// 更新记忆
export async function updateAgentMemory(agentId: string, content: string): Promise<boolean> {
  try {
    const res = await api.put<{ success: boolean }>(`/agents/${agentId}/memory`, { content })
    return res.data.success
  } catch {
    return false
  }
}

// 获取日期记忆
export async function getDailyMemory(agentId: string, date: string): Promise<string | null> {
  try {
    const res = await api.get<{ success: boolean; data: { content: string } }>(
      `/agents/${agentId}/memory/daily/${date}`
    )
    return res.data.data?.content || null
  } catch {
    return null
  }
}

// 克隆 Agent
export async function cloneAgent(agentId: string, options: CloneOptions): Promise<{ success: boolean; newId?: string; message?: string }> {
  try {
    const res = await api.post<{ success: boolean; data?: { id: string }; error?: string }>(
      `/agents/${agentId}/clone`,
      options
    )
    return {
      success: res.data.success,
      newId: res.data.data?.id,
      message: res.data.error
    }
  } catch (e: any) {
    return { success: false, message: e.message }
  }
}

// 导出 Agent
export async function exportAgent(agentId: string, options: ExportOptions): Promise<Blob | null> {
  try {
    const res = await api.post<Blob>(
      `/agents/${agentId}/export`,
      options,
      { responseType: 'blob' }
    )
    return res.data
  } catch {
    return null
  }
}

// 导入 Agent
export async function importAgent(file: File): Promise<{ success: boolean; agentId?: string; message?: string }> {
  try {
    const formData = new FormData()
    formData.append('file', file)

    const res = await api.post<{ success: boolean; data?: { id: string }; error?: string }>(
      '/agents/import',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    return {
      success: res.data.success,
      agentId: res.data.data?.id,
      message: res.data.error
    }
  } catch (e: any) {
    return { success: false, message: e.message }
  }
}

// 删除 Agent
export async function deleteAgent(agentId: string): Promise<boolean> {
  try {
    const res = await api.delete<{ success: boolean }>(`/agents/${agentId}`)
    return res.data.success
  } catch {
    return false
  }
}

// 获取工具目录
export async function getToolsCatalog(): Promise<{ profiles: any[]; groups: any[] }> {
  const res = await api.get<{ success: boolean; data: { profiles: any[]; groups: any[] } }>('/agents/tools-catalog')
  return res.data.data || { profiles: [], groups: [] }
}

// 获取 Agent 工具配置
export async function getAgentTools(agentId: string): Promise<{ profile: string; alsoAllow: string[] }> {
  const res = await api.get<{ success: boolean; data: { profile: string; alsoAllow: string[] } }>(`/agents/${agentId}/tools`)
  return res.data.data || { profile: 'default', alsoAllow: [] }
}

// 更新 Agent 工具配置
export async function updateAgentTools(
  agentId: string,
  data: { profile: string; alsoAllow: string[] }
): Promise<boolean> {
  try {
    const res = await api.put<{ success: boolean }>(`/agents/${agentId}/tools`, data)
    return res.data.success
  } catch {
    return false
  }
}

// 获取模板列表
export async function getTemplates(): Promise<any[]> {
  const res = await api.get<{ success: boolean; data: any[] }>('/agents/templates')
  return res.data.data || []
}

// 从模板创建 Agent
export async function createFromTemplate(
  templateId: string,
  options: { name: string; id: string; tools?: any }
): Promise<{ success: boolean; agentId?: string; message?: string }> {
  try {
    const res = await api.post<{ success: boolean; data?: { id: string }; error?: string }>(
      '/agents/create',
      { templateId, ...options }
    )
    return {
      success: res.data.success,
      agentId: res.data.data?.id,
      message: res.data.error
    }
  } catch (e: any) {
    return { success: false, message: e.message }
  }
}