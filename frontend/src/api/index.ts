import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

// 是否正在刷新 token
let isRefreshing = false
// 刷新失败后的重试队列
let failedQueue: { resolve: Function; reject: Function }[] = []

// 请求拦截器：添加 Token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：处理 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // 如果是登录或刷新请求失败，直接返回错误
    if (originalRequest.url?.includes('/auth/login') || originalRequest.url?.includes('/auth/refresh')) {
      return Promise.reject(error)
    }

    // 如果已经在登录页，不要跳转
    if (window.location.pathname === '/login') {
      return Promise.reject(error)
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      // 如果已经在刷新，加入队列等待
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(() => {
          originalRequest.headers.Authorization = `Bearer ${localStorage.getItem('access_token')}`
          return api.request(originalRequest)
        }).catch(err => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true

      const refreshToken = localStorage.getItem('refresh_token')

      if (refreshToken) {
        try {
          const res = await axios.post('/api/auth/refresh', {
            refresh_token: refreshToken
          })
          if (res.data.success) {
            const newToken = res.data.data.access_token
            localStorage.setItem('access_token', newToken)
            originalRequest.headers.Authorization = `Bearer ${newToken}`

            // 处理队列中的请求
            failedQueue.forEach(({ resolve }) => resolve())
            failedQueue = []

            return api.request(originalRequest)
          }
        } catch {
          // 刷新失败
        }
      }

      // 刷新失败或没有 refresh token，清除登录状态
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user_info')
      failedQueue.forEach(({ reject }) => reject())
      failedQueue = []
      window.location.href = '/login'
      return Promise.reject(error)
    }

    return Promise.reject(error)
  }
)

// ==================== 认证 API ====================
export const authApi = {
  login(username: string, password: string) {
    return api.post('/auth/login', { username, password })
  },

  logout() {
    return api.post('/auth/logout')
  },

  me() {
    return api.get('/auth/me')
  },

  changePassword(old_password: string, new_password: string) {
    return api.post('/auth/change-password', { old_password, new_password })
  }
}

// ==================== 用户管理 API ====================
export const userApi = {
  list() {
    return api.get('/users')
  },

  create(data: CreateUserParams) {
    return api.post('/users', data)
  },

  update(id: number, data: UpdateUserParams) {
    return api.put(`/users/${id}`, data)
  },

  delete(id: number) {
    return api.delete(`/users/${id}`)
  }
}

// ==================== 角色管理 API ====================
export const roleApi = {
  list() {
    return api.get('/roles')
  },

  update(id: number, data: { description?: string; permissions?: Record<string, string[]> }) {
    return api.put(`/roles/${id}`, data)
  }
}

// ==================== Agent API ====================
export const agentApi = {
  list() {
    return api.get('/agents')
  },

  get(id: string) {
    return api.get(`/agents/${id}`)
  },

  create(data: AgentConfig) {
    return api.post('/agents', data)
  },

  update(id: string, data: Partial<AgentConfig>) {
    return api.put(`/agents/${id}`, data)
  },

  delete(id: string) {
    return api.delete(`/agents/${id}`)
  },

  apply() {
    return api.post('/agents/apply')
  }
}

// ==================== Binding API ====================
export interface BindingMatch {
  channel?: string       // 频道名：feishu, dingtalk-connector
  accountId?: string     // 账号 ID：对应 channel.accounts 中的 key
  peer?: {
    kind?: 'direct' | 'group'  // 会话类型
    id?: string                 // 群ID 或 用户ID
  }
}

export interface BindingConfig {
  agentId: string
  match: BindingMatch
}

export const bindingApi = {
  list() {
    return api.get<{ success: boolean; data: BindingConfig[]; permissions?: { can_edit: boolean } }>('/bindings')
  },

  create(data: BindingConfig) {
    return api.post<{ success: boolean; data: BindingConfig; message: string }>('/bindings', data)
  },

  update(index: number, data: BindingConfig) {
    return api.put<{ success: boolean; data: BindingConfig; message: string }>(`/bindings/${index}`, data)
  },

  delete(index: number) {
    return api.delete<{ success: boolean; message: string }>(`/bindings/${index}`)
  },

  reorder(data: { fromIndex: number; toIndex: number } | { order: number[] }) {
    return api.put<{ success: boolean; message: string }>('/bindings/order', data)
  },

  getDefaultAgent() {
    return api.get<{ success: boolean; data: { agentId: string } }>('/bindings/default-agent')
  },

  setDefaultAgent(agentId: string) {
    return api.put<{ success: boolean; message: string }>('/bindings/default-agent', { agentId })
  },

  testMatch(data: { channel?: string; accountId?: string; peerKind?: 'direct' | 'group' }) {
    return api.post<{ success: boolean; data: {
      agentId: string
      agentName: string
      source: 'binding' | 'default'
      matchedBinding?: BindingConfig
      matchedIndex: number
    } }>('/bindings/test', data)
  }
}

// ==================== Config API ====================
export const configApi = {
  get() {
    return api.get('/config')
  }
}

// ==================== Channel API ====================
export interface ChannelAccount {
  id: string
  config: Record<string, any>
  enabled: boolean
}

export interface Channel {
  name: string
  displayName: string
  enabled: boolean
  accounts: ChannelAccount[]
  defaultAccount?: string
  threadSession?: boolean
  requireMention?: boolean
  sharedMemoryAcrossConversations?: boolean
  separateSessionByConversation?: boolean
  dmPolicy?: string
  groupPolicy?: string
}

export const channelApi = {
  list() {
    return api.get<{ success: boolean; data: Channel[]; permissions?: { can_edit: boolean } }>('/channels')
  },

  get(channelName: string) {
    return api.get<{ success: boolean; data: Channel; permissions?: { can_edit: boolean } }>(`/channels/${channelName}`)
  },

  update(channelName: string, data: Partial<Channel>) {
    return api.put<{ success: boolean; message: string }>(`/channels/${channelName}`, data)
  },

  createAccount(channelName: string, accountId: string, config: Record<string, any>) {
    return api.post<{ success: boolean; message: string }>(`/channels/${channelName}/accounts`, { accountId, config })
  },

  updateAccount(channelName: string, accountId: string, config: Record<string, any>) {
    return api.put<{ success: boolean; message: string }>(`/channels/${channelName}/accounts/${accountId}`, { config })
  },

  deleteAccount(channelName: string, accountId: string) {
    return api.delete<{ success: boolean; message: string }>(`/channels/${channelName}/accounts/${accountId}`)
  }
}

// ==================== Gateway API ====================
export const gatewayApi = {
  status() {
    return api.get('/gateway/status')
  },
  restart() {
    return api.post('/gateway/restart')
  },
  reload() {
    return api.post('/gateway/reload')
  }
}

// ==================== 操作日志 API ====================
export const logApi = {
  operations(page: number = 1, limit: number = 50) {
    return api.get('/logs/operations', { params: { page, limit } })
  }
}

// ==================== 任务统计 API（仪表盘） ====================
export const taskApi = {
  overview() {
    return api.get('/tasks/overview')
  },

  trend(days: number = 7) {
    return api.get('/tasks/trend', { params: { days } })
  },

  ranking(days: number = 7, limit: number = 5) {
    return api.get('/tasks/ranking', { params: { days, limit } })
  },

  typeDistribution(days: number = 7) {
    return api.get('/tasks/type-distribution', { params: { days } })
  },

  recent(limit: number = 10) {
    return api.get('/tasks/recent', { params: { limit } })
  },

  report(data: TaskReportParams) {
    return api.post('/tasks/report', data)
  },

  generateDemo() {
    return api.post('/tasks/demo')
  }
}

// ==================== 配置文件管理 API ====================
export const configFileApi = {
  list() {
    return api.get('/config-files')
  },

  get(fileId: string) {
    return api.get(`/config-files/${fileId}`)
  },

  update(fileId: string, content: string) {
    return api.put(`/config-files/${fileId}`, { content })
  },

  templates(fileType?: string) {
    const params = fileType ? { fileType } : {}
    return api.get('/config-templates', { params })
  },

  getTemplate(templateId: string) {
    return api.get(`/config-templates/${templateId}`)
  },

  createTemplate(data: TemplateParams) {
    return api.post('/config-templates', data)
  },

  updateTemplate(templateId: string, data: Partial<TemplateParams>) {
    return api.put(`/config-templates/${templateId}`, data)
  },

  deleteTemplate(templateId: string) {
    return api.delete(`/config-templates/${templateId}`)
  },

  inject(data: InjectParams) {
    return api.post('/soul-inject', data)
  }
}

export interface TemplateParams {
  id: string
  name: string
  description: string
  fileType: string
  content: string
}

export interface InjectParams {
  fileType: string
  content: string
  mode: 'append' | 'prepend'
  agents?: string[]
}

// ==================== 会话记录 API ====================
export const sessionApi = {
  agents() {
    return api.get('/session-agents')
  },

  list(agentId: string) {
    return api.get(`/sessions/${agentId}`)
  },

  messages(agentId: string, sessionId: string, options?: { isReset?: boolean; filename?: string }) {
    const params = new URLSearchParams()
    if (options?.isReset) {
      params.append('isReset', 'true')
    }
    if (options?.filename) {
      params.append('filename', options.filename)
    }
    const query = params.toString()
    return api.get(`/sessions/${agentId}/${sessionId}/messages${query ? '?' + query : ''}`)
  }
}

// ==================== Focus Mode API ====================
export const focusApi = {
  // 启用专注模式
  enable(sessionKey: string, options?: {
    taskDescription?: string
    keywords?: string[]
    compactNow?: boolean
  }) {
    return api.post<{ success: boolean; data: FocusStatus; message: string }>('/focus/focus', {
      sessionKey,
      ...options
    })
  },

  // 执行智能压缩
  compact(sessionKey: string, options?: {
    taskDescription?: string
    keywords?: string[]
    tokenBudget?: number
  }) {
    return api.post<{ success: boolean; compacted: boolean; data: FocusCompactResult }>('/focus/compact', {
      sessionKey,
      ...options
    })
  },

  // 获取专注模式状态
  getStatus(sessionKey: string) {
    return api.get<{ success: boolean; data: FocusStatus }>('/focus/status', {
      params: { sessionKey }
    })
  },

  // 清除专注模式
  clear(sessionKey: string) {
    return api.post<{ success: boolean; message: string }>('/focus/clear', {
      sessionKey
    })
  }
}

export interface FocusStatus {
  enabled: boolean
  taskDescription?: string
  keywords?: string[]
  startedAt?: string
  messagesRemoved?: number
  tokensSaved?: number
}

export interface FocusCompactResult {
  tokensBefore: number
  tokensAfter: number
  summary: string
  details: {
    messagesRemoved: number
    messagesKept: number
    keywords: string[]
    focusMode: boolean
  }
}

// ==================== 记忆文件 API ====================
export const memoryApi = {
  list(agentId: string) {
    return api.get(`/memory/${agentId}`)
  },

  get(agentId: string, date: string) {
    return api.get(`/memory/${agentId}/${date}`)
  }
}

// ==================== 搜索 API ====================
export const searchApi = {
  sessions(agentId: string, keyword: string) {
    return api.get(`/search/sessions/${agentId}`, { params: { q: keyword } })
  },

  memory(agentId: string, keyword: string) {
    return api.get(`/search/memory/${agentId}`, { params: { q: keyword } })
  }
}

// ==================== 类型定义 ====================
export interface AgentConfig {
  id: string
  name: string
  model?: { primary: string; secondary?: string }
  workspace?: string
  subagents?: { allowAgents: string[] }
  tools?: { profile: string; alsoAllow?: string[] }
  default?: boolean
  modelName?: string
}

export interface Model {
  id: string
  name: string
  provider: string
  contextWindow?: number
  maxTokens?: number
}

export interface CreateUserParams {
  username: string
  password: string
  email?: string
  display_name?: string
  role_id?: number
}

export interface UpdateUserParams {
  display_name?: string
  email?: string
  role_id?: number
  is_active?: boolean
  password?: string
}

export interface User {
  id: number
  username: string
  email: string
  display_name: string
  is_active: boolean
  last_login: string
  created_at: string
  role_name: string
}

export interface Role {
  id: number
  name: string
  description: string
  permissions: Record<string, string[]>
  created_at: string
}

export interface TaskOverview {
  todayTotal: number
  todayChange: number
  completionRate: number
  avgDuration: number
  inProgress: number
}

export interface TaskTrend {
  labels: string[]
  values: number[]
  total: number
  change: number
}

export interface TaskRanking {
  agentId: string
  agentName: string
  taskCount: number
  successRate: number
}

export interface TaskTypeDistribution {
  type: string
  icon: string
  count: number
  percent: number
}

export interface TaskRecent {
  id: number
  agentId: string
  agentName: string
  title: string
  status: string
  taskType: string
  completedAt: string
  createdAt: string
}

export interface TaskReportParams {
  agentId: string
  title: string
  taskType?: string
  status?: string
  deliverableType?: string
  deliverablePath?: string
  durationSeconds?: number
  userId?: string
  sessionId?: string
  details?: string
}

// ==================== Skill 类型定义 ====================
export interface Skill {
  slug: string
  name: string
  description: string
  level: 'workspace' | 'shared' | 'bundled'
  path: string
  version?: string
  enabled: boolean
  userInvocable: boolean
  metadata?: {
    openclaw?: {
      requires?: {
        bins?: string[]
        env?: string[]
        config?: string[]
      }
      install?: any[]
      os?: string[]
    }
    clawdbot?: {
      requires?: {
        bins?: string[]
        env?: string[]
      }
    }
  }
  config?: SkillConfig
  files?: SkillFile[]
  skillMdContent?: string
  canEdit?: boolean
  canDelete?: boolean
  agentId?: string
  agentName?: string
}

export interface AgentSkills {
  id: string
  name: string
  skills: Skill[]
}

export interface SkillsData {
  agents: AgentSkills[]
  sharedSkills: Skill[]
  bundledSkills: Skill[]
}

export interface SkillConfig {
  enabled?: boolean
  apiKey?: string | { source: string; provider: string; id: string }
  env?: Record<string, string>
  config?: Record<string, any>
}

export interface SkillFile {
  name: string
  type: 'file' | 'directory'
  size?: number
}

export interface CreateSkillParams {
  name: string
  description?: string
  content: string
  location: 'workspace' | 'shared'
  agentId?: string
}

export const skillApi = {
  list() {
    return api.get<SkillListResponse>('/skills')
  },

  get(skillSlug: string) {
    return api.get<SkillDetailResponse>(`/skills/${skillSlug}`)
  },

  toggle(skillSlug: string, enabled: boolean) {
    return api.post<BaseResponse>(`/skills/${skillSlug}/toggle`, { enabled })
  },

  updateConfig(skillSlug: string, config: { env?: Record<string, string>; config?: Record<string, any> }) {
    return api.put<BaseResponse>(`/skills/${skillSlug}/config`, config)
  },

  create(data: CreateSkillParams) {
    return api.post<BaseResponse & { data: { name: string; path: string } }>('/skills', data)
  },

  update(skillSlug: string, content: string) {
    return api.put<BaseResponse>(`/skills/${skillSlug}`, { content })
  },

  delete(skillSlug: string) {
    return api.delete<BaseResponse>(`/skills/${skillSlug}`)
  }
}

interface SkillListResponse {
  success: boolean
  data: SkillsData
  permissions?: { can_edit: boolean; can_delete: boolean }
}

interface SkillDetailResponse {
  success: boolean
  data: Skill
}

// ==================== 员工管理 API ====================
export interface Department {
  id: number
  name: string
  parent_id: number | null
  leader_id: number | null
  sort_order: number
  children?: Department[]
  created_at: string
}

export interface Employee {
  id: number
  name: string
  email: string | null
  phone: string | null
  avatar: string | null
  department_id: number | null
  department_name: string | null
  manager_id: number | null
  manager_name: string | null
  agent_id: string | null
  agent_name: string | null
  agent_model: string | null
  user_id: number | null
  status: string
  created_at: string
}

export interface UnboundAgent {
  id: string
  name: string
  model?: { primary: string }
}

export const departmentApi = {
  list() {
    return api.get<{ success: boolean; data: Department[] }>('/departments')
  },

  create(data: { name: string; parent_id?: number; leader_id?: number; sort_order?: number }) {
    return api.post<BaseResponse & { data: { id: number; name: string } }>('/departments', data)
  },

  update(id: number, data: Partial<{ name: string; parent_id: number | null; leader_id: number | null; sort_order: number }>) {
    return api.put<BaseResponse>(`/departments/${id}`, data)
  },

  delete(id: number) {
    return api.delete<BaseResponse>(`/departments/${id}`)
  }
}

export const employeeApi = {
  list() {
    return api.get<{
      success: boolean
      data: Employee[]
      unbound_agents: UnboundAgent[]
      permissions: { can_edit: boolean; can_delete: boolean }
    }>('/employees')
  },

  get(id: number) {
    return api.get<{ success: boolean; data: Employee; subordinates: Employee[] }>(`/employees/${id}`)
  },

  create(data: { name: string; email?: string; phone?: string; department_id?: number; manager_id?: number; agent_id?: string }) {
    return api.post<BaseResponse & { data: { id: number; name: string } }>('/employees', data)
  },

  update(id: number, data: Partial<{ name: string; email: string; phone: string; department_id: number | null; manager_id: number | null; agent_id: string | null; status: string }>) {
    return api.put<BaseResponse>(`/employees/${id}`, data)
  },

  delete(id: number) {
    return api.delete<BaseResponse>(`/employees/${id}`)
  },

  bindAgent(id: number, agentId: string) {
    return api.post<BaseResponse>(`/employees/${id}/bind-agent`, { agent_id: agentId })
  },

  unbindAgent(id: number) {
    return api.post<BaseResponse>(`/employees/${id}/unbind-agent`)
  }
}

// ==================== 模型管理 API ====================

export interface ModelProvider {
  id: string
  name: string
  api_base: string
  models: string[]
  auth_type: string
  description: string
}

export interface ModelConfig {
  id: string
  name: string
  provider: string
  model_type: string
  api_base: string
  model_name: string
  parameters: Record<string, any>
  api_key_masked: string
  enabled: boolean
  created_at: string
  updated_at: string
  testing?: boolean  // 前端状态，用于测试按钮 loading
}

export interface ModelTestResult {
  connected: boolean
  response_time?: number
  model?: string
  error?: string
  status_code?: number
}

export const modelApi = {
  // 获取提供商模板
  getProviders() {
    return api.get<{ success: boolean; data: ModelProvider[] }>('/models/providers')
  },

  // 获取指定提供商的模型列表
  getProviderModels(providerId: string) {
    return api.get<{ success: boolean; data: string[] }>(`/models/providers/${providerId}/models`)
  },

  // 获取所有模型配置
  list() {
    return api.get<{ success: boolean; data: ModelConfig[] }>('/models')
  },

  // 获取单个模型
  get(modelId: string) {
    return api.get<{ success: boolean; data: ModelConfig }>(`/models/${modelId}`)
  },

  // 创建模型
  create(data: {
    name: string
    provider: string
    model_name: string
    api_key: string
    api_base?: string
    model_type?: string
    parameters?: Record<string, any>
    enabled?: boolean
  }) {
    return api.post<{ success: boolean; data: ModelConfig }>('/models', data)
  },

  // 更新模型
  update(modelId: string, data: Partial<{
    name: string
    provider: string
    model_name: string
    api_key: string
    api_base: string
    model_type: string
    parameters: Record<string, any>
    enabled: boolean
  }>) {
    return api.put<{ success: boolean; data: ModelConfig }>(`/models/${modelId}`, data)
  },

  // 删除模型
  delete(modelId: string) {
    return api.delete<BaseResponse>(`/models/${modelId}`)
  },

  // 测试模型连接
  testConnection(modelId: string) {
    return api.post<{ success: boolean; data: ModelTestResult }>(`/models/${modelId}/test`)
  },

  // 获取 Gateway 模型列表（用于同步）
  getGatewayModels() {
    return api.get<{ success: boolean; data: any[] }>('/models/gateway')
  }
}

// ==================== Channel 配置 API ====================

export interface ChannelType {
  id: string
  name: string
  description: string
  config_fields: string[]
  required_fields: string[]
}

export interface ChannelConfig {
  id: string
  channel_type: string
  channel_name: string
  enabled: boolean
  app_id?: string
  app_id_masked?: string
  app_secret_masked?: string
  app_key?: string
  app_key_masked?: string
  event_url?: string
  callback_url?: string
  bot_name?: string
  agent_id?: string
  created_at: string
  updated_at: string
}

export const channelConfigApi = {
  // 获取 Channel 类型
  getTypes() {
    return api.get<{ success: boolean; data: ChannelType[] }>('/channel-config/types')
  },

  // 获取所有配置
  list() {
    return api.get<{ success: boolean; data: ChannelConfig[] }>('/channel-config')
  },

  // 获取指定 Channel 配置
  get(channelType: string) {
    return api.get<{ success: boolean; data: ChannelConfig | null }>(`/channel-config/${channelType}`)
  },

  // 保存配置
  save(channelType: string, data: Record<string, any>) {
    return api.post<{ success: boolean; data: ChannelConfig; warnings?: string[] }>(`/channel-config/${channelType}`, data)
  },

  // 删除配置
  delete(channelType: string) {
    return api.delete<BaseResponse>(`/channel-config/${channelType}`)
  },

  // 验证配置
  validate(channelType: string, data: Record<string, any>) {
    return api.post<{ success: boolean; data: { valid: boolean; errors: string[]; warnings: string[] } }>(`/channel-config/${channelType}/validate`, data)
  }
}

// ==================== 图片生成 API ====================

export interface ImageGenerateResult {
  images: { url: string; b64_json?: string }[]
  created: number
}

export const imageGeneratorApi = {
  /**
   * 文生图 - 根据提示词生成图片
   */
  generate(prompt: string, options?: { size?: string; n?: number }) {
    return api.post<{ success: boolean; data: ImageGenerateResult; error?: string }>(
      '/image-generator/generate',
      {
        prompt,
        size: options?.size || '2k',
        n: options?.n || 1
      }
    )
  }
}

export default api