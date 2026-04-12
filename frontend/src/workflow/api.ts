/**
 * Workflow API
 */
import axios from 'axios'

const API_BASE = '/api/workflow'

export const workflowApi = {
  // 列出所有工作流
  async list() {
    const res = await axios.get(`${API_BASE}/list`)
    return res.data
  },

  // 获取工作流详情
  async get(name: string) {
    const res = await axios.get(`${API_BASE}/${name}`)
    return res.data
  },

  // 创建工作流
  async create(data: {
    name: string
    description?: string
    nodes?: any[]
    edges?: any[]
  }) {
    const res = await axios.post(`${API_BASE}/create`, data)
    return res.data
  },

  // 更新工作流
  async update(name: string, data: {
    nodes?: any[]
    edges?: any[]
    description?: string
  }) {
    const res = await axios.put(`${API_BASE}/${name}`, data)
    return res.data
  },

  // 删除工作流
  async delete(name: string) {
    const res = await axios.delete(`${API_BASE}/${name}`)
    return res.data
  },

  // 验证工作流
  async validate(name: string) {
    const res = await axios.get(`${API_BASE}/${name}/validate`)
    return res.data
  },

  // 执行工作流
  async execute(name: string, userInput: Record<string, any> = {}) {
    const res = await axios.post(`${API_BASE}/execute`, {
      name,
      user_input: userInput
    })
    return res.data
  },

  // 获取执行记录列表
  async listExecutions(name: string) {
    const res = await axios.get(`${API_BASE}/${name}/executions`)
    return res.data
  },

  // 获取执行记录详情
  async getExecution(name: string, filename: string) {
    const res = await axios.get(`${API_BASE}/${name}/executions/${filename}`)
    return res.data
  },

  // 获取节点输出
  async getNodeOutput(name: string, executionId: string, nodeId: string) {
    const res = await axios.get(`${API_BASE}/${name}/outputs/${executionId}/${nodeId}`)
    return res.data
  },

  // 与编排Agent对话
  async chat(message: string, context: Record<string, any> = {}) {
    const res = await axios.post(`${API_BASE}/chat`, {
      message,
      context
    })
    return res.data
  }
}