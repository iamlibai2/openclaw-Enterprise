<template>
  <div class="chat-page">
    <!-- 三栏布局 -->
    <div class="chat-layout">
      <!-- 左侧：Agent 选择 -->
      <div class="agent-panel">
        <div class="panel-header">
          <h3>Agent</h3>
        </div>
        <div class="agent-list" v-loading="loadingAgents">
          <div
            class="agent-item"
            v-for="agent in agents"
            :key="agent.id"
            :class="{ active: selectedAgent?.id === agent.id }"
            @click="selectAgent(agent)"
          >
            <div class="agent-avatar">{{ agent.name?.charAt(0) || agent.id.charAt(0) }}</div>
            <div class="agent-info">
              <div class="agent-name">{{ agent.name || agent.id }}</div>
              <div class="agent-model">{{ agent.modelName || agent.id }}</div>
            </div>
          </div>
          <div class="empty-tip" v-if="!loadingAgents && agents.length === 0">
            暂无 Agent
          </div>
        </div>
      </div>

      <!-- 中间：会话列表 -->
      <div class="session-panel">
        <div class="panel-header">
          <h3>会话</h3>
          <el-button type="primary" size="small" @click="createNewSession" :disabled="!selectedAgent">
            <el-icon><Plus /></el-icon>
            新对话
          </el-button>
        </div>
        <div class="session-list" v-loading="loadingSessions">
          <div
            class="session-item"
            v-for="session in sessions"
            :key="session.sessionKey"
            :class="{ active: currentSession?.sessionKey === session.sessionKey }"
            @click="selectSession(session)"
          >
            <div class="session-title">{{ session.title || '新对话' }}</div>
            <div class="session-time">{{ formatTime(session.updatedAt) }}</div>
          </div>
          <div class="empty-tip" v-if="!loadingSessions && sessions.length === 0">
            {{ selectedAgent ? '点击"新对话"开始聊天' : '请先选择 Agent' }}
          </div>
        </div>
      </div>

      <!-- 右侧：聊天面板 -->
      <div class="chat-panel">
        <template v-if="currentSession">
          <!-- 聊天头部 -->
          <div class="chat-header">
            <div class="chat-title">
              <span>{{ selectedAgent?.name || 'Agent' }}</span>
              <el-tag size="small" type="info" v-if="currentSession">{{ currentSession.sessionId?.slice(0, 8) }}</el-tag>
            </div>
            <div class="chat-actions">
              <el-button
                v-if="chatRunId"
                type="danger"
                size="small"
                @click="abortGeneration"
              >
                <el-icon><VideoPause /></el-icon>
                停止
              </el-button>
              <el-button
                v-if="messages.length > 0"
                type="default"
                size="small"
                @click="handleExport"
              >
                <el-icon><Download /></el-icon>
                导出
              </el-button>
            </div>
          </div>

          <!-- 消息列表 -->
          <div class="chat-messages" ref="messagesContainer" @click="handleMessageClick">
            <template v-for="(msg, idx) in messages" :key="idx">
              <!-- 用户消息：右侧紫色 -->
              <div class="message-row user" v-if="msg.role === 'user'">
                <div class="message-bubble user-bubble">
                  <div class="message-text" v-html="renderMarkdown(getMessageText(msg))"></div>
                  <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
                </div>
              </div>

              <!-- 助手消息：左侧绿色 -->
              <div class="message-row assistant" v-if="msg.role === 'assistant'">
                <div class="assistant-avatar" v-if="selectedAgent">
                  {{ selectedAgent.name?.charAt(0) || selectedAgent.id.charAt(0) }}
                </div>
                <div class="message-bubble assistant-bubble">
                  <div class="assistant-name">{{ selectedAgent?.name || 'Assistant' }}</div>
                  <div class="message-text" v-html="renderMarkdown(getMessageText(msg))"></div>
                  <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
                </div>
              </div>
            </template>

            <!-- 正在输入提示 -->
            <div class="message-row assistant typing" v-if="chatStream">
              <div class="assistant-avatar" v-if="selectedAgent">
                {{ selectedAgent.name?.charAt(0) || selectedAgent.id.charAt(0) }}
              </div>
              <div class="message-bubble assistant-bubble">
                <div class="assistant-name">{{ selectedAgent?.name || 'Assistant' }}</div>
                <div class="message-text" v-html="renderMarkdown(chatStream)"></div>
              </div>
            </div>
          </div>

          <!-- 输入区域 -->
          <div class="input-area">
            <el-input
              v-model="inputMessage"
              type="textarea"
              :rows="3"
              placeholder="输入消息，按 Enter 发送，Shift+Enter 换行"
              :disabled="!selectedAgent || chatSending"
              @keydown="handleKeydown"
            />
            <div class="input-actions">
              <span class="input-tip">{{ selectedAgent ? 'Enter 发送 · ↑↓ 历史记录' : '请先选择 Agent' }}</span>
              <el-button
                type="primary"
                @click="sendMessage"
                :disabled="!selectedAgent || !inputMessage.trim() || chatSending"
                :loading="chatSending"
              >
                发送
              </el-button>
            </div>
          </div>
        </template>

        <div class="empty-chat" v-else>
          <div class="empty-icon">💬</div>
          <div class="empty-text">选择一个 Agent 开始对话</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, VideoPause, Download } from '@element-plus/icons-vue'
import { agentApi, chatApi } from '../api'
import {
  GatewayBrowserClient,
  GatewayEventFrame,
  GatewayHelloOk,
  extractText,
  createGatewayClient
} from '../utils/gateway-ws'
import { renderMessageContent } from '../utils/markdown'
import { exportChatMarkdown } from '../chat/utils/chat-export'
import { InputHistory } from '../chat/utils/input-history'
import type { Agent, Session, Message } from '../chat/types'

// Agent 相关
interface AgentInfo {
  id: string
  name?: string
  modelName?: string
}
const agents = ref<AgentInfo[]>([])
const selectedAgent = ref<AgentInfo | null>(null)
const loadingAgents = ref(false)

// 会话相关
interface SessionInfo {
  sessionKey: string
  sessionId: string
  title?: string
  updatedAt?: number
}
const sessions = ref<SessionInfo[]>([])
const currentSession = ref<SessionInfo | null>(null)
const loadingSessions = ref(false)

// 消息相关
const messages = ref<Message[]>([])
const messagesContainer = ref<HTMLElement | null>(null)
const inputMessage = ref('')
const chatStream = ref<string | null>(null)
const chatRunId = ref<string | null>(null)
const chatSending = ref(false)

// 输入历史
const inputHistory = new InputHistory()

// Gateway 客户端
let client: GatewayBrowserClient | null = null
let isManualStop = false

// 加载 Agent 列表
async function loadAgents() {
  loadingAgents.value = true
  try {
    const res = await agentApi.list()
    if (res.data.success) {
      agents.value = res.data.data || []
    }
  } catch (err: any) {
    console.error('Failed to load agents:', err)
  } finally {
    loadingAgents.value = false
  }
}

// 选择 Agent
async function selectAgent(agent: AgentInfo) {
  selectedAgent.value = agent
  currentSession.value = null
  messages.value = []
  chatStream.value = null
  chatRunId.value = null
  await loadSessions()
}

// 加载会话列表
async function loadSessions() {
  if (!selectedAgent.value || !client) return

  loadingSessions.value = true
  try {
    const result = await client.request<{ sessions: any[] }>('sessions.list', {
      agentId: selectedAgent.value.id
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
  } finally {
    loadingSessions.value = false
  }
}

// 选择会话
async function selectSession(session: SessionInfo) {
  currentSession.value = session
  await loadMessages()
}

// 加载消息
async function loadMessages() {
  if (!currentSession.value || !client) return

  try {
    const res = await client.request<{ messages?: any[] }>('chat.history', {
      sessionKey: currentSession.value.sessionKey,
      limit: 200
    })
    messages.value = Array.isArray(res.messages) ? res.messages : []
    chatStream.value = null
    chatRunId.value = null
    scrollToBottom()
  } catch (err: any) {
    console.error('Failed to load messages:', err)
    ElMessage.error('加载消息失败: ' + err.message)
  }
}

// 创建新会话
function createNewSession() {
  if (!selectedAgent.value) return

  const sessionId = crypto.randomUUID()
  const sessionKey = `agent:${selectedAgent.value.id}:webchat:${sessionId}`

  const newSession: SessionInfo = {
    sessionKey,
    sessionId,
    title: '新对话',
    updatedAt: Date.now()
  }

  sessions.value.unshift(newSession)
  currentSession.value = newSession
  messages.value = []
  chatStream.value = null
  chatRunId.value = null
}

// 发送消息
async function sendMessage() {
  if (!currentSession.value || !inputMessage.value.trim() || !client) return

  const messageText = inputMessage.value.trim()
  inputHistory.push(messageText)
  inputMessage.value = ''

  // 添加用户消息
  messages.value = [
    ...messages.value,
    {
      role: 'user' as const,
      content: [{ type: 'text', text: messageText }],
      timestamp: Date.now()
    }
  ]
  scrollToBottom()

  // 生成 runId
  const runId = crypto.randomUUID()
  chatRunId.value = runId
  chatStream.value = ''
  chatSending.value = true

  try {
    await client.request('chat.send', {
      sessionKey: currentSession.value.sessionKey,
      message: messageText,
      deliver: false,
      idempotencyKey: runId
    })
  } catch (err: any) {
    console.error('Failed to send message:', err)
    chatRunId.value = null
    chatStream.value = null
    messages.value = [
      ...messages.value,
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

// 中止生成
async function abortGeneration() {
  if (!currentSession.value || !client) return

  try {
    await client.request('chat.abort', {
      sessionKey: currentSession.value.sessionKey,
      runId: chatRunId.value
    })
  } catch (err: any) {
    console.error('Failed to abort:', err)
  }
}

// 导出
function handleExport() {
  if (messages.value.length === 0) return
  exportChatMarkdown(messages.value, selectedAgent.value?.name || 'Agent')
}

// 处理 chat 事件
function onChatEvent(evt: GatewayEventFrame) {
  if (evt.event !== 'chat' || !currentSession.value) return

  const payload = evt.payload as any

  if (payload.sessionKey !== currentSession.value.sessionKey) {
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
      messages.value = [
        ...messages.value,
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
      messages.value = [
        ...messages.value,
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
    ElMessage.error(payload.errorMessage ?? 'chat error')
  }

  scrollToBottom()
}

// 处理键盘事件
function handleKeydown(e: KeyboardEvent) {
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

// 处理消息点击（复制代码）
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

// 滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 获取消息文本
function getMessageText(msg: Message): string {
  return extractText(msg) || ''
}

// 格式化时间
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

// 渲染 Markdown
function renderMarkdown(text: string): string {
  return renderMessageContent(text)
}

// 连接 Gateway
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
.chat-page {
  height: calc(100vh - 60px);
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.chat-layout {
  display: flex;
  height: 100%;
}

/* 左侧 Agent 面板 */
.agent-panel {
  width: 220px;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.panel-header {
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.agent-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.agent-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.agent-item:hover {
  background: #f5f7fa;
}

.agent-item.active {
  background: #ecf5ff;
}

.agent-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 16px;
}

.agent-info {
  flex: 1;
  min-width: 0;
}

.agent-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.agent-model {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

/* 中间会话面板 */
.session-panel {
  width: 280px;
  background: #fafafa;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.session-item {
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: all 0.2s;
}

.session-item:hover {
  background: #e9ecf0;
}

.session-item.active {
  background: #e6f0ff;
}

.session-title {
  font-size: 14px;
  color: #303133;
  margin-bottom: 4px;
}

.session-time {
  font-size: 12px;
  color: #909399;
}

/* 右侧聊天面板 */
.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.chat-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 500;
}

.chat-actions {
  display: flex;
  gap: 8px;
}

/* 消息列表 */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f9fafb;
}

.message-row {
  display: flex;
  margin-bottom: 16px;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
  gap: 12px;
}

.message-bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  position: relative;
}

.user-bubble {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.assistant-bubble {
  background: #fff;
  color: #303133;
  border-bottom-left-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.assistant-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 14px;
  flex-shrink: 0;
}

.assistant-name {
  font-size: 13px;
  font-weight: 500;
  color: #11998e;
  margin-bottom: 4px;
}

.message-text {
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.message-time {
  font-size: 11px;
  opacity: 0.7;
  margin-top: 4px;
  text-align: right;
}

/* 输入区域 */
.input-area {
  padding: 16px 20px;
  border-top: 1px solid #e4e7ed;
  background: #fff;
}

.input-area :deep(.el-textarea__inner) {
  resize: none;
  border-radius: 8px;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
}

.input-tip {
  font-size: 12px;
  color: #909399;
}

/* 空状态 */
.empty-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-text {
  font-size: 16px;
}

.empty-tip {
  text-align: center;
  padding: 20px;
  color: #909399;
  font-size: 14px;
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
  border-left: 4px solid #667eea;
  background: rgba(102, 126, 234, 0.05);
  color: #666;
}

.markdown-body a {
  color: #667eea;
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

/* 行内代码 */
.markdown-body code:not(pre code) {
  padding: 2px 6px;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 4px;
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.9em;
  color: #667eea;
}

/* 用户消息内的代码样式调整 */
.user-bubble .markdown-body code:not(pre code) {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.user-bubble .markdown-body blockquote {
  border-left-color: rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.9);
}

.user-bubble .markdown-body a {
  color: #fff;
  text-decoration: underline;
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
</style>