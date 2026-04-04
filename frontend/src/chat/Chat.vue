<template>
  <div class="chat-studio" :class="{ 'with-panel': showFilesPanel }">
    <!-- 背景装饰 -->
    <div class="bg-orb orb-1"></div>
    <div class="bg-orb orb-2"></div>
    <div class="bg-orb orb-3"></div>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 顶部栏 -->
      <div class="top-bar">
        <div class="selectors">
          <el-select
            v-model="selectedAgentId"
            placeholder="选择 Agent"
            class="agent-select"
            @change="onAgentChange"
          >
            <el-option
              v-for="agent in agents"
              :key="agent.id"
              :label="agent.name || agent.id"
              :value="agent.id"
            >
              <div class="agent-option">
                <span class="agent-name">{{ agent.name || agent.id }}</span>
                <span class="agent-model">{{ agent.modelName }}</span>
              </div>
            </el-option>
          </el-select>

          <el-select
            v-model="selectedSessionKey"
            placeholder="选择会话"
            class="session-select"
            :disabled="!selectedAgentId"
            @change="onSessionChange"
          >
            <el-option
              v-for="session in sessions"
              :key="session.sessionKey"
              :label="session.title || '新对话'"
              :value="session.sessionKey"
            >
              <div class="session-option">
                <span>{{ session.title || '新对话' }}</span>
                <span class="session-time">{{ formatTime(session.updatedAt) }}</span>
              </div>
            </el-option>
          </el-select>
        </div>

        <div class="actions">
          <el-button
            type="primary"
            plain
            :disabled="!selectedAgentId"
            @click="createNewSession"
          >
            <el-icon><Plus /></el-icon>
            新对话
          </el-button>
          <el-button
            v-if="chatRunId"
            type="danger"
            plain
            @click="abortGeneration"
          >
            <el-icon><VideoPause /></el-icon>
            停止
          </el-button>
          <el-button
            v-if="chatMessages.length > 0"
            type="default"
            plain
            @click="handleExport"
          >
            <el-icon><Download /></el-icon>
            导出
          </el-button>
          <el-button
            type="default"
            plain
            :disabled="!selectedSessionKey"
            :class="{ 'is-active': showFilesPanel }"
            @click="toggleFilesPanel"
          >
            <el-icon><Folder /></el-icon>
            文件
          </el-button>
        </div>
      </div>

      <!-- 消息区域 -->
      <div class="messages-area" ref="messagesContainer" @click="handleMessageClick">
        <!-- 空状态 -->
        <div v-if="chatMessages.length === 0 && !chatStream" class="empty-state">
          <div class="empty-icon">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
          </div>
          <p class="empty-text">选择一个 Agent 开始对话</p>
          <p class="empty-hint">或创建新会话</p>
        </div>

        <!-- 消息列表 -->
        <div v-else class="messages-list">
          <div
            v-for="(msg, idx) in chatMessages"
            :key="idx"
            :class="['message', msg.role]"
          >
            <div v-if="msg.role === 'assistant'" class="avatar">
              {{ selectedAgent?.name?.charAt(0) || 'A' }}
            </div>
            <div class="bubble">
              <div class="content" v-html="renderMarkdown(getMessageText(msg))"></div>
              <div class="time">{{ formatTime(msg.timestamp) }}</div>
            </div>
          </div>

          <!-- 流式输出 -->
          <div v-if="chatStream" class="message assistant streaming">
            <div class="avatar">{{ selectedAgent?.name?.charAt(0) || 'A' }}</div>
            <div class="bubble">
              <div class="content" v-html="renderMarkdown(chatStream)"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="input-area">
        <div class="input-wrap">
          <textarea
            ref="textareaRef"
            v-model="inputMessage"
            class="chat-input"
            :placeholder="inputPlaceholder"
            rows="3"
            :disabled="!selectedSessionKey"
            @keydown="handleKeydown"
          ></textarea>
          <button
            class="send-btn"
            :class="{ active: canSend }"
            :disabled="!canSend"
            @click="sendMessage"
          >
            <svg v-if="!chatSending" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
            <span v-else class="btn-loading"></span>
          </button>
        </div>
        <p class="input-hint">{{ inputHint }}</p>
      </div>
    </div>

    <!-- 文件面板 -->
    <transition name="slide-panel">
      <div v-if="showFilesPanel" class="files-panel">
        <div class="panel-header">
          <h3>会话文件</h3>
          <button class="panel-close" @click="showFilesPanel = false">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="panel-content">
          <div v-if="filesLoading" class="files-loading">
            <span class="loading-spinner"></span>
            <span>加载中...</span>
          </div>
          <div v-else-if="filesError" class="files-error">
            {{ filesError }}
          </div>
          <div v-else-if="agentFiles.length === 0" class="files-empty">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
            </svg>
            <p>暂无文件</p>
          </div>
          <div v-else class="files-list">
            <div
              v-for="file in agentFiles"
              :key="file.name"
              class="file-item"
              @click="handleFileClick(file)"
            >
              <div class="file-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
              </div>
              <div class="file-info">
                <span class="file-name">{{ file.name }}</span>
                <span class="file-meta">
                  <span v-if="file.toolName" class="tool-tag">{{ file.toolName }}</span>
                  <span v-if="file.size">{{ formatFileSize(file.size) }}</span>
                  <span v-if="file.createdAt">{{ formatFileSizeDate(file.createdAt) }}</span>
                </span>
              </div>
            </div>
          </div>
        </div>
        <div class="panel-footer">
          <button class="refresh-btn" @click="loadAgentFiles" :disabled="filesLoading">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23 4 23 10 17 10"></polyline>
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
            </svg>
            刷新
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, VideoPause, Download, Folder } from '@element-plus/icons-vue'
import { agentApi, chatApi } from '../api'
import {
  GatewayBrowserClient,
  GatewayEventFrame,
  GatewayHelloOk,
  extractText,
  createGatewayClient
} from '../utils/gateway-ws'
import { renderMessageContent } from '../utils/markdown'
import { exportChatMarkdown } from './utils/chat-export'
import { InputHistory } from './utils/input-history'
import type { Agent, Session, Message } from './types'

// ==================== 状态 ====================

const agents = ref<Agent[]>([])
const selectedAgentId = ref<string>('')
const selectedAgent = computed(() => agents.value.find(a => a.id === selectedAgentId.value))

const sessions = ref<Session[]>([])
const selectedSessionKey = ref<string>('')

const chatMessages = ref<Message[]>([])
const chatStream = ref<string | null>(null)
const chatRunId = ref<string | null>(null)
const chatSending = ref(false)
const lastError = ref<string | null>(null)

const inputMessage = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)

// 输入历史
const inputHistory = new InputHistory()

// Gateway 客户端
let client: GatewayBrowserClient | null = null
let isManualStop = false

// ==================== 文件面板状态 ====================

const showFilesPanel = ref(false)
const filesLoading = ref(false)
const filesError = ref<string | null>(null)

interface ArtifactFile {
  name: string
  path: string
  size?: number
  createdAt?: number
  toolName?: string
}
const agentFiles = ref<ArtifactFile[]>([])

// 计算属性
const canSend = computed(() =>
  selectedSessionKey.value &&
  inputMessage.value.trim() &&
  !chatSending.value
)

const inputPlaceholder = '输入消息，Enter 发送...'
const inputHint = computed(() =>
  !selectedSessionKey.value ? '请先选择或创建会话' : 'Enter 发送 · Shift+Enter 换行 · ↑↓ 历史记录'
)

// ==================== Agent 管理 ====================

async function loadAgents() {
  try {
    const res = await agentApi.list()
    if (res.data.success) {
      agents.value = res.data.data || []
    }
  } catch (err: any) {
    console.error('Failed to load agents:', err)
  }
}

async function onAgentChange() {
  // 重置会话
  selectedSessionKey.value = ''
  sessions.value = []
  chatMessages.value = []
  chatStream.value = null
  chatRunId.value = null

  if (selectedAgentId.value && client?.connected) {
    await loadSessions()
  }
}

// ==================== Session 管理 ====================

async function loadSessions() {
  if (!selectedAgentId.value || !client) return

  try {
    const result = await client.request<{ sessions: any[] }>('sessions.list', {
      agentId: selectedAgentId.value
    })
    const allSessions = result.sessions || []
    sessions.value = allSessions
      .filter((s: any) => s.key?.includes('webchat'))
      .map((s: any) => ({
        sessionKey: s.key,
        sessionId: s.sessionId,
        title: s.title || '新对话',
        updatedAt: s.updatedAt || Date.now()
      }))
      .sort((a: any, b: any) => b.updatedAt - a.updatedAt)
  } catch (err: any) {
    console.error('Failed to load sessions:', err)
    sessions.value = []
  }
}

function createNewSession() {
  if (!selectedAgentId.value) return

  const sessionId = crypto.randomUUID()
  const sessionKey = `agent:${selectedAgentId.value}:webchat:${sessionId}`

  const newSession: Session = {
    sessionKey,
    sessionId,
    title: '新对话',
    updatedAt: Date.now()
  }

  sessions.value.unshift(newSession)
  selectedSessionKey.value = sessionKey
  chatMessages.value = []
  chatStream.value = null
  chatRunId.value = null
}

async function onSessionChange() {
  if (selectedSessionKey.value) {
    await loadChatHistory()
  }
}

// ==================== Chat 功能 ====================

async function loadChatHistory() {
  if (!selectedSessionKey.value || !client) return

  try {
    const res = await client.request<{ messages?: any[] }>('chat.history', {
      sessionKey: selectedSessionKey.value,
      limit: 200
    })
    chatMessages.value = Array.isArray(res.messages) ? res.messages : []
    chatStream.value = null
    chatRunId.value = null
    scrollToBottom()
  } catch (err: any) {
    console.error('Failed to load messages:', err)
    ElMessage.error('加载消息失败: ' + err.message)
  }
}

async function sendMessage() {
  if (!selectedSessionKey.value || !inputMessage.value.trim() || !client) return

  const message = inputMessage.value.trim()

  // 保存到输入历史
  inputHistory.push(message)
  inputMessage.value = ''

  // 添加用户消息
  chatMessages.value = [
    ...chatMessages.value,
    {
      role: 'user' as const,
      content: [{ type: 'text', text: message }],
      timestamp: Date.now()
    }
  ]
  scrollToBottom()

  // 生成 runId
  const runId = crypto.randomUUID()
  chatRunId.value = runId
  chatStream.value = ''
  chatSending.value = true
  lastError.value = null

  try {
    await client.request('chat.send', {
      sessionKey: selectedSessionKey.value,
      message,
      deliver: false,
      idempotencyKey: runId
    })
  } catch (err: any) {
    console.error('Failed to send message:', err)
    chatRunId.value = null
    chatStream.value = null
    lastError.value = err.message
    chatMessages.value = [
      ...chatMessages.value,
      {
        role: 'assistant' as const,
        content: [{ type: 'text', text: 'Error: ' + err.message }],
        timestamp: Date.now()
      }
    ]
    scrollToBottom()
  } finally {
    chatSending.value = false
  }
}

async function abortGeneration() {
  if (!selectedSessionKey.value || !client) return

  try {
    await client.request('chat.abort', {
      sessionKey: selectedSessionKey.value,
      runId: chatRunId.value
    })
  } catch (err: any) {
    console.error('Failed to abort:', err)
  }
}

function handleExport() {
  if (chatMessages.value.length === 0) return
  exportChatMarkdown(chatMessages.value, selectedAgent.value?.name || 'Agent')
}

// ==================== 文件面板 ====================

function toggleFilesPanel() {
  showFilesPanel.value = !showFilesPanel.value
  if (showFilesPanel.value && selectedSessionKey.value) {
    loadAgentFiles()
  }
}

async function loadAgentFiles() {
  if (!selectedSessionKey.value || !client) {
    console.log('[Files] No session or client:', { sessionKey: selectedSessionKey.value, client: !!client })
    return
  }

  filesLoading.value = true
  filesError.value = null

  console.log('[Files] Requesting artifacts.list for session:', selectedSessionKey.value)

  try {
    // 使用 artifacts.list 获取会话生成的文件
    // 添加超时保护
    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => reject(new Error('请求超时')), 5000)
    })

    const result = await Promise.race([
      client.request<{ ok: boolean; artifacts: ArtifactFile[] }>('artifacts.list', {
        sessionId: selectedSessionKey.value
      }),
      timeoutPromise
    ])
    console.log('[Files] artifacts.list result:', result)
    agentFiles.value = result?.artifacts || []
  } catch (err: any) {
    console.error('[Files] Failed to load session artifacts:', err)
    filesError.value = err.message || '加载失败'
  } finally {
    filesLoading.value = false
  }
}

async function handleFileClick(file: ArtifactFile) {
  // 文件路径是绝对路径，需要通过后端下载
  try {
    const res = await chatApi.downloadArtifact({ path: file.path })
    if (res.data.success && res.data.data?.content) {
      // 下载文件
      const blob = new Blob([res.data.data.content], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = file.name
      a.click()
      URL.revokeObjectURL(url)
    }
  } catch (err: any) {
    console.error('Failed to download artifact:', err)
    // 如果后端不支持，显示文件路径提示
    ElMessage.info(`文件路径: ${file.path}`)
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatFileSizeDate(ms: number): string {
  const date = new Date(ms)
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

// ==================== 输入处理 ====================

function handleKeydown(e: KeyboardEvent) {
  // Enter 发送
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
    return
  }

  // 上箭头：历史记录
  if (e.key === 'ArrowUp' && !e.shiftKey) {
    const target = e.target as HTMLTextAreaElement
    if (target.selectionStart === 0) {
      e.preventDefault()
      const prev = inputHistory.up()
      if (prev) inputMessage.value = prev
    }
    return
  }

  // 下箭头：历史记录
  if (e.key === 'ArrowDown' && !e.shiftKey) {
    const target = e.target as HTMLTextAreaElement
    if (target.selectionStart === target.value.length) {
      e.preventDefault()
      const next = inputHistory.down()
      inputMessage.value = next || ''
    }
    return
  }
}

// ==================== 事件处理 ====================

function onChatEvent(evt: GatewayEventFrame) {
  if (evt.event !== 'chat' || !selectedSessionKey.value) return

  const payload = evt.payload as any

  if (payload.sessionKey !== selectedSessionKey.value) {
    return
  }

  if (payload.state === 'delta') {
    const next = extractText(payload.message)
    if (typeof next === 'string') {
      chatStream.value = next
    }
  } else if (payload.state === 'final') {
    const text = extractText(payload.message) || chatStream.value
    if (text?.trim()) {
      chatMessages.value = [
        ...chatMessages.value,
        {
          role: 'assistant',
          content: [{ type: 'text', text }],
          timestamp: Date.now()
        }
      ]
    }
    chatStream.value = null
    chatRunId.value = null
  } else if (payload.state === 'aborted') {
    const text = chatStream.value
    if (text?.trim()) {
      chatMessages.value = [
        ...chatMessages.value,
        {
          role: 'assistant',
          content: [{ type: 'text', text }],
          timestamp: Date.now()
        }
      ]
    }
    chatStream.value = null
    chatRunId.value = null
  } else if (payload.state === 'error') {
    chatStream.value = null
    chatRunId.value = null
    lastError.value = payload.errorMessage ?? 'chat error'
    ElMessage.error(lastError.value)
  }

  scrollToBottom()
}

// ==================== 工具函数 ====================

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

function getMessageText(msg: Message): string {
  return extractText(msg) || ''
}

function formatTime(timestamp?: number): string {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function renderMarkdown(text: string): string {
  return renderMessageContent(text)
}

function handleMessageClick(e: Event) {
  const target = e.target as HTMLElement
  const copyBtn = target.closest('.code-block-copy') as HTMLButtonElement | null
  if (!copyBtn) return

  const code = copyBtn.dataset.code ?? ''
  navigator.clipboard.writeText(code).then(
    () => {
      copyBtn.classList.add('copied')
      setTimeout(() => copyBtn.classList.remove('copied'), 1500)
    },
    () => {
      ElMessage.error('复制失败')
    }
  )
}

// ==================== Gateway 连接 ====================

async function connectGateway() {
  isManualStop = false
  try {
    const res = await chatApi.getConfig()
    if (res.data.success) {
      const { gatewayUrl, gatewayToken } = res.data.data
      console.log('[Chat] Connecting to Gateway:', gatewayUrl)

      client = createGatewayClient({
        url: gatewayUrl,
        token: gatewayToken,
        onHello: (hello: GatewayHelloOk) => {
          console.log('[Chat] Gateway hello:', hello)
        },
        onEvent: onChatEvent,
        onClose: (info) => {
          console.log('[Chat] Gateway closed:', info)
          if (!isManualStop) {
            ElMessage.warning('Gateway 连接已断开')
          }
        }
      })

      client.start()
    }
  } catch (err: any) {
    console.error('Failed to connect gateway:', err)
    ElMessage.error('连接 Gateway 失败: ' + err.message)
  }
}

// ==================== 生命周期 ====================

onMounted(async () => {
  await loadAgents()
  await connectGateway()
})

onUnmounted(() => {
  if (client) {
    isManualStop = true
    client.stop()
  }
})
</script>

<style scoped>
.chat-studio {
  min-height: calc(100vh - 120px);
  padding: 24px 32px;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 背景光晕 */
.bg-orb {
  position: fixed;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.12;
  pointer-events: none;
  z-index: 0;
}

.orb-1 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, #6366f1, transparent);
  top: -100px;
  right: -100px;
  animation: float 8s ease-in-out infinite;
}

.orb-2 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, #ec4899, transparent);
  bottom: 0;
  left: -80px;
  animation: float 10s ease-in-out infinite reverse;
}

.orb-3 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, #06b6d4, transparent);
  top: 40%;
  left: 40%;
  animation: float 12s ease-in-out infinite 3s;
}

/* 顶部选择器 */
.top-bar {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  backdrop-filter: blur(10px);
}

.selectors {
  display: flex;
  gap: 16px;
  align-items: center;
}

.agent-select,
.session-select {
  width: 200px;
}

.agent-select :deep(.el-input__wrapper),
.session-select :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.8);
  border-radius: 10px;
  box-shadow: none;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.agent-option,
.session-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.agent-name {
  font-weight: 500;
}

.agent-model {
  font-size: 12px;
  color: #999;
}

.session-time {
  font-size: 12px;
  color: #999;
}

.actions {
  display: flex;
  gap: 10px;
}

/* 消息区域 */
.messages-area {
  position: relative;
  z-index: 1;
  flex: 1;
  min-height: 300px;
  max-height: calc(100vh - 320px);
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 16px;
}

.empty-icon {
  color: #ddd;
}

.empty-text {
  font-size: 16px;
  color: #999;
  margin: 0;
}

.empty-hint {
  font-size: 13px;
  color: #bbb;
  margin: 0;
}

/* 消息列表 */
.messages-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.message.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
}

.message.user .avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.bubble {
  max-width: min(900px, 68%);
  padding: 12px 16px;
  border-radius: 12px;
  position: relative;
}

.message.user .bubble {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}

.message.assistant .bubble {
  background: #fff;
  color: #303133;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.content {
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.time {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.7);
  margin-top: 6px;
  text-align: right;
}

.message.assistant .time {
  color: #999;
  text-align: left;
}

/* 流式输出动画 */
.message.streaming .bubble {
  animation: pulsing-border 1.5s ease-out infinite;
}

@keyframes pulsing-border {
  0%, 100% { box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05); }
  50% { box-shadow: 0 2px 16px rgba(99, 102, 241, 0.2); }
}

/* 淡入动画 */
.message {
  animation: fade-in 0.2s ease-out;
}

@keyframes fade-in {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 输入区域 */
.input-area {
  position: relative;
  z-index: 1;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 12px;
  padding: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  backdrop-filter: blur(10px);
}

.input-wrap {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  font-size: 14px;
  line-height: 1.45;
  color: #333;
  background: transparent;
  font-family: inherit;
  min-height: 40px;
  max-height: 150px;
  padding: 9px 0;
}

.chat-input::placeholder {
  color: #999;
}

.send-btn {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: #888;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.send-btn.active {
  background: #6366f1;
  border-color: #6366f1;
}

.send-btn.active:hover {
  background: #5855e5;
}

.send-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.btn-loading {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.input-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: #999;
}

/* 主内容区（支持面板展开时的过渡） */
.main-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  flex: 1;
  min-width: 0;
  transition: margin-right 0.3s ease;
}

.with-panel .main-content {
  margin-right: 0;
}

/* 文件面板 */
.files-panel {
  position: absolute;
  top: 0;
  right: 0;
  width: 320px;
  height: 100%;
  background: rgba(255, 255, 255, 0.95);
  border-left: 1px solid rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  z-index: 10;
  backdrop-filter: blur(10px);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.panel-close {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: #666;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.panel-close:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #333;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.files-loading,
.files-error,
.files-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #999;
  gap: 12px;
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(99, 102, 241, 0.2);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.files-error {
  color: #ef4444;
}

.files-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid transparent;
}

.file-item:hover {
  background: rgba(99, 102, 241, 0.06);
  border-color: rgba(99, 102, 241, 0.15);
}

.file-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: rgba(99, 102, 241, 0.1);
  color: #6366f1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  display: block;
  font-size: 14px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}

.tool-tag {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.panel-footer {
  padding: 12px 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.refresh-btn {
  width: 100%;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid rgba(99, 102, 241, 0.3);
  background: rgba(99, 102, 241, 0.08);
  color: #6366f1;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.15s ease;
}

.refresh-btn:hover:not(:disabled) {
  background: rgba(99, 102, 241, 0.15);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 文件按钮激活状态 */
.actions .is-active {
  background: rgba(99, 102, 241, 0.15);
  border-color: #6366f1;
  color: #6366f1;
}

/* 面板滑入动画 */
.slide-panel-enter-active,
.slide-panel-leave-active {
  transition: all 0.3s ease;
}

.slide-panel-enter-from,
.slide-panel-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

/* 动画 */
@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(20px, -20px) scale(1.05); }
  66% { transform: translate(-10px, 10px) scale(0.95); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>

<!-- 非 scoped 样式：用于 v-html 渲染的动态内容 -->
<style>
/* Markdown 样式 */
.markdown-body {
  overflow-x: auto;
}

.markdown-body p {
  margin: 0 0 12px;
}

.markdown-body p:last-child {
  margin-bottom: 0;
}

.markdown-body h1,
.markdown-body h2,
.markdown-body h3,
.markdown-body h4 {
  margin: 16px 0 8px;
  font-weight: 600;
  line-height: 1.3;
}

.markdown-body h1:first-child,
.markdown-body h2:first-child,
.markdown-body h3:first-child {
  margin-top: 0;
}

.markdown-body h1 { font-size: 1.5em; }
.markdown-body h2 { font-size: 1.3em; }
.markdown-body h3 { font-size: 1.15em; }
.markdown-body h4 { font-size: 1em; }

.markdown-body ul,
.markdown-body ol {
  margin: 8px 0;
  padding-left: 24px;
}

.markdown-body li {
  margin: 4px 0;
}

.markdown-body blockquote {
  margin: 12px 0;
  padding: 8px 16px;
  border-left: 4px solid #6366f1;
  background: rgba(99, 102, 241, 0.05);
  color: #666;
}

.markdown-body a {
  color: #6366f1;
  text-decoration: none;
}

.markdown-body a:hover {
  text-decoration: underline;
}

/* 表格样式 */
.markdown-body table {
  margin: 12px 0;
  border-collapse: collapse;
  width: 100%;
  font-size: 13px;
}

.markdown-body th,
.markdown-body td {
  border: 1px solid #e0e0e0;
  padding: 8px 12px;
  text-align: left;
}

.markdown-body th {
  background: rgba(0, 0, 0, 0.03);
  font-weight: 600;
}

.markdown-body tr:nth-child(even) {
  background: rgba(0, 0, 0, 0.02);
}

/* 代码块样式 */
.code-block-wrapper {
  margin: 12px 0;
  border-radius: 8px;
  overflow: hidden;
  background: #1e1e1e;
}

.code-block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 12px;
  background: #2d2d2d;
  font-size: 12px;
}

.code-block-lang {
  color: #888;
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
}

.code-block-copy {
  padding: 4px 10px;
  border: none;
  border-radius: 4px;
  background: #404040;
  color: #ccc;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
}

.code-block-copy:hover {
  background: #505050;
  color: #fff;
}

.code-block-copy.copied {
  background: #22c55e;
  color: #fff;
}

.code-block-wrapper pre {
  margin: 0;
  padding: 12px;
  overflow-x: auto;
}

.code-block-wrapper code {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 13px;
  color: #d4d4d4;
  background: transparent;
}

/* JSON 折叠 */
.json-collapse {
  margin: 12px 0;
}

.json-collapse > summary {
  cursor: pointer;
  padding: 8px 12px;
  background: rgba(99, 102, 241, 0.08);
  border-radius: 6px;
  font-size: 13px;
  color: #6366f1;
  list-style: none;
}

.json-collapse > summary::-webkit-details-marker {
  display: none;
}

.json-collapse[open] > summary {
  border-radius: 6px 6px 0 0;
}

/* 行内代码 */
.markdown-body code:not(pre code) {
  padding: 2px 6px;
  background: rgba(99, 102, 241, 0.1);
  border-radius: 4px;
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.9em;
  color: #6366f1;
}

/* 用户消息内的代码样式 */
.message.user .bubble .markdown-body code:not(pre code) {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.message.user .bubble .markdown-body a {
  color: #fff;
}

.message.user .bubble .markdown-body blockquote {
  border-left-color: rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.9);
}

/* 分割线 */
.markdown-body hr {
  margin: 16px 0;
  border: none;
  border-top: 1px solid #e0e0e0;
}

/* 图片 */
.markdown-body img {
  max-width: 100%;
  border-radius: 8px;
}

/* 文本表格 */
.text-table {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  white-space: pre;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.4;
}

.text-table p {
  margin: 0;
  white-space: pre;
}

.message.assistant .bubble .text-table {
  background: rgba(0, 0, 0, 0.02);
  padding: 8px 12px;
  border-radius: 6px;
}

.message.user .bubble .text-table {
  background: rgba(255, 255, 255, 0.1);
  padding: 8px 12px;
  border-radius: 6px;
}
</style>