<template>
  <div class="group-chat">
    <!-- 背景装饰 -->
    <div class="bg-orb orb-1"></div>
    <div class="bg-orb orb-2"></div>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 顶部栏 -->
      <div class="top-bar">
        <div class="title-area">
          <h2>群聊讨论</h2>
          <span class="subtitle">多 Agent 协作讨论</span>
        </div>
        <div class="actions">
          <el-button type="primary" plain @click="showParticipantDialog = true">
            <el-icon><Setting /></el-icon>
            配置参与者
          </el-button>
          <el-button v-if="messages.length > 0" plain @click="handleClear">
            <el-icon><Delete /></el-icon>
            清空
          </el-button>
        </div>
      </div>

      <!-- 参与者面板 -->
      <div class="participants-bar">
        <span class="label">主持人：</span>
        <el-tag type="success" effect="plain">
          {{ hostAgent?.name || hostAgentId || '未选择' }}
        </el-tag>
        <span class="label" style="margin-left: 16px;">参与者：</span>
        <div class="participant-tags">
          <el-tag
            v-for="p in enabledParticipants"
            :key="p.agentId"
            :type="getAgentTagType(p.agentId)"
            effect="plain"
          >
            {{ p.name }}
          </el-tag>
          <span v-if="enabledParticipants.length === 0" class="no-participants">
            点击"配置参与者"添加
          </span>
        </div>
      </div>

      <!-- 消息区域 -->
      <div class="messages-area" ref="messagesContainer">
        <!-- 空状态 -->
        <div v-if="messages.length === 0 && !isStreaming" class="empty-state">
          <div class="empty-icon">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
            </svg>
          </div>
          <p class="empty-text">配置参与者后开始群聊</p>
          <p class="empty-hint">主持人将协调各 Agent 进行讨论</p>
        </div>

        <!-- 消息列表 -->
        <div v-else class="messages-list">
          <div
            v-for="msg in messages"
            :key="msg.id"
            :class="['message', msg.role, { 'from-agent': msg.sourceAgent }]"
          >
            <div v-if="msg.role === 'assistant' && msg.sourceAgent" class="avatar" :style="getAgentStyle(msg.sourceAgent)">
              {{ msg.sourceName?.charAt(0) || '?' }}
            </div>
            <div v-else-if="msg.role === 'assistant'" class="avatar host-avatar">
              {{ hostAgent?.name?.charAt(0) || 'H' }}
            </div>
            <div class="bubble">
              <div v-if="msg.sourceAgent && msg.role === 'assistant'" class="agent-label">
                {{ msg.sourceName }}
              </div>
              <div class="content" v-html="renderMarkdown(msg.content)"></div>
              <div class="time">{{ formatTime(msg.timestamp) }}</div>
            </div>
          </div>

          <!-- 流式输出 -->
          <div v-if="isStreaming && streamContent" class="message assistant streaming">
            <div class="avatar host-avatar">{{ hostAgent?.name?.charAt(0) || 'H' }}</div>
            <div class="bubble">
              <div class="content" v-html="renderMarkdown(streamContent)"></div>
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
            placeholder="输入消息，主持人将协调各 Agent 讨论..."
            rows="3"
            :disabled="!canChat"
            @keydown="handleKeydown"
          ></textarea>
          <button
            class="send-btn"
            :class="{ active: canSend }"
            :disabled="!canSend"
            @click="sendMessage"
          >
            <svg v-if="!isSending" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
            <span v-else class="btn-loading"></span>
          </button>
        </div>
        <p class="input-hint">{{ inputHint }}</p>
      </div>
    </div>

    <!-- 参与者配置弹窗 -->
    <el-dialog
      v-model="showParticipantDialog"
      title="配置群聊参与者"
      width="500px"
      :close-on-click-modal="false"
    >
      <div class="dialog-content">
        <!-- 主持人选择 -->
        <div class="config-section">
          <h4>主持人 Agent</h4>
          <p class="section-hint">主持人负责协调讨论，汇总各 Agent 的意见</p>
          <el-select v-model="hostAgentId" placeholder="选择主持人" style="width: 100%;">
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
        </div>

        <!-- 参与者选择 -->
        <div class="config-section">
          <h4>参与 Agent</h4>
          <p class="section-hint">勾选需要参与讨论的 Agent</p>
          <div class="participant-list">
            <div
              v-for="agent in agents.filter(a => a.id !== hostAgentId)"
              :key="agent.id"
              class="participant-item"
            >
              <el-checkbox
                :model-value="isParticipantEnabled(agent.id)"
                @change="toggleParticipant(agent.id, $event)"
              >
                <div class="participant-info">
                  <span class="participant-name">{{ agent.name || agent.id }}</span>
                  <span class="participant-model">{{ agent.modelName }}</span>
                </div>
              </el-checkbox>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showParticipantDialog = false">取消</el-button>
        <el-button type="primary" @click="saveParticipants">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting, Delete } from '@element-plus/icons-vue'
import { agentApi } from '../api'
import {
  GatewayBrowserClient,
  GatewayHelloOk,
  extractText,
  createGatewayClient
} from '../utils/gateway-ws'
import { renderMessageContent } from '../utils/markdown'
import type { AgentInfo, Participant, GroupChatMessage } from './types'

// ==================== 状态 ====================

const STORAGE_KEY = 'groupchat_state'

const agents = ref<AgentInfo[]>([])
const hostAgentId = ref<string>('')
const participants = ref<Participant[]>([])
const showParticipantDialog = ref(false)

const messages = ref<GroupChatMessage[]>([])
const inputMessage = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)

const isSending = ref(false)
const isStreaming = ref(false)
const streamContent = ref('')
const runId = ref<string | null>(null)

// Gateway 客户端
let client: GatewayBrowserClient | null = null
let sessionKey = ref<string>('')
let isManualStop = false

// Agent 颜色映射
const agentColors: Record<string, string> = {}
const colorPalette = [
  'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
  'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)',
]

// ==================== 计算属性 ====================

const hostAgent = computed(() => agents.value.find(a => a.id === hostAgentId.value))

const enabledParticipants = computed(() =>
  participants.value.filter(p => p.enabled && p.agentId !== hostAgentId.value)
)

const canChat = computed(() =>
  hostAgentId.value && enabledParticipants.value.length > 0
)

const canSend = computed(() =>
  canChat.value &&
  inputMessage.value.trim() &&
  !isSending.value
)

const inputHint = computed(() => {
  if (!hostAgentId.value) return '请先选择主持人 Agent'
  if (enabledParticipants.value.length === 0) return '请添加参与 Agent'
  return 'Enter 发送 · Shift+Enter 换行'
})

// ==================== Agent 管理 ====================

async function loadAgents() {
  try {
    const res = await agentApi.list()
    if (res.data.success) {
      agents.value = res.data.data || []
      // 初始化颜色
      agents.value.forEach((agent, idx) => {
        agentColors[agent.id] = colorPalette[idx % colorPalette.length]
      })
    }
  } catch (err: any) {
    console.error('Failed to load agents:', err)
  }
}

function isParticipantEnabled(agentId: string): boolean {
  return participants.value.find(p => p.agentId === agentId)?.enabled ?? false
}

function toggleParticipant(agentId: string, enabled: boolean) {
  const agent = agents.value.find(a => a.id === agentId)
  if (!agent) return

  const existing = participants.value.find(p => p.agentId === agentId)
  if (existing) {
    existing.enabled = enabled
  } else {
    participants.value.push({
      agentId,
      name: agent.name || agentId,
      description: agent.description,
      enabled
    })
  }
}

function saveParticipants() {
  showParticipantDialog.value = false
  ElMessage.success(`已配置 ${enabledParticipants.value.length} 个参与 Agent`)
  saveState()  // 保存配置
}

// ==================== 样式辅助 ====================

function getAgentStyle(agentId: string): Record<string, string> {
  return {
    background: agentColors[agentId] || colorPalette[0]
  }
}

function getAgentTagType(agentId: string): string {
  const idx = agents.value.findIndex(a => a.id === agentId)
  const types = ['', 'success', 'warning', 'danger', 'info']
  return types[idx % types.length] || ''
}

// ==================== 消息处理 ====================

async function sendMessage() {
  if (!canSend.value || !client) return

  const content = inputMessage.value.trim()
  inputMessage.value = ''

  // 添加用户消息
  messages.value.push({
    id: crypto.randomUUID(),
    role: 'user',
    content,
    timestamp: Date.now()
  })
  scrollToBottom()

  // 构建带上下文的消息
  const participantInfo = enabledParticipants.value
    .map(p => `- ${p.name}(${p.agentId})`)
    .join('\n')

  const contextMessage = `【群聊上下文】
主持人：${hostAgent.value?.name || '主持人'}
参与者：
${participantInfo}

【用户问题】
${content}

请根据问题决定需要哪些 Agent 参与，并使用 sessions_send 工具与他们讨论。`

  isSending.value = true
  isStreaming.value = true
  streamContent.value = ''
  runId.value = crypto.randomUUID()

  try {
    // 发送消息到主持人 Session
    await client.request('chat.send', {
      sessionKey: sessionKey.value,
      message: contextMessage,
      deliver: false,
      idempotencyKey: runId.value
    })
  } catch (err: any) {
    console.error('Failed to send message:', err)
    isStreaming.value = false
    ElMessage.error('发送失败: ' + err.message)
  } finally {
    isSending.value = false
  }
}

function onChatEvent(evt: any) {
  if (evt.event !== 'chat' || !sessionKey.value) return

  const payload = evt.payload as any
  if (payload.sessionKey !== sessionKey.value) return

  if (payload.state === 'delta') {
    const next = extractText(payload.message)
    if (typeof next === 'string') {
      streamContent.value = next
    }
  } else if (payload.state === 'final') {
    const text = extractText(payload.message) || streamContent.value
    if (text?.trim()) {
      // 解析消息，提取各 Agent 的回复
      const parsed = parseAgentMessages(text)
      messages.value.push(...parsed)
      saveState()  // 保存消息历史
    }
    streamContent.value = ''
    isStreaming.value = false
    runId.value = null
    scrollToBottom()
  } else if (payload.state === 'aborted' || payload.state === 'error') {
    streamContent.value = ''
    isStreaming.value = false
    runId.value = null
    if (payload.state === 'error') {
      ElMessage.error(payload.errorMessage || '发生错误')
    }
  }
}

/**
 * 解析主持人回复，提取各 Agent 的消息
 */
function parseAgentMessages(text: string): GroupChatMessage[] {
  const messages: GroupChatMessage[] = []

  // 尝试匹配 [Agent名]: 内容 格式
  const agentPattern = /\[([^\]]+)\]:\s*([\s\S]*?)(?=\n\[|$)/g
  let match
  let hasAgentMessages = false

  while ((match = agentPattern.exec(text)) !== null) {
    hasAgentMessages = true
    const agentName = match[1].trim()
    const content = match[2].trim()

    if (content) {
      // 查找对应的 Agent
      const agent = agents.value.find(a =>
        a.name === agentName || a.id === agentName
      )

      messages.push({
        id: crypto.randomUUID(),
        role: 'assistant',
        content,
        sourceAgent: agent?.id,
        sourceName: agent?.name || agentName,
        timestamp: Date.now()
      })
    }
  }

  // 如果没有解析出 Agent 消息，整体作为主持人回复
  if (!hasAgentMessages && text.trim()) {
    messages.push({
      id: crypto.randomUUID(),
      role: 'assistant',
      content: text,
      sourceAgent: hostAgentId.value,
      sourceName: hostAgent.value?.name || '主持人',
      timestamp: Date.now()
    })
  }

  return messages
}

function handleClear() {
  messages.value = []
  streamContent.value = ''
  sessionKey.value = ''  // 清空 sessionKey
  clearState()  // 清除 localStorage
  ElMessage.success('已清空群聊记录')

  // 重新创建 session
  if (client?.connected && hostAgentId.value) {
    createHostSession()
  }
}

// ==================== Gateway 连接 ====================

async function connectGateway() {
  isManualStop = false
  try {
    const res = await (await import('../api')).chatApi.getConfig()
    if (res.data.success) {
      const { gatewayUrl, gatewayToken } = res.data.data

      client = createGatewayClient({
        url: gatewayUrl,
        token: gatewayToken,
        onHello: (hello: GatewayHelloOk) => {
          console.log('[GroupChat] Gateway hello:', hello)
          // 创建主持人 Session
          createHostSession()
        },
        onEvent: onChatEvent,
        onClose: (info) => {
          console.log('[GroupChat] Gateway closed:', info)
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

async function createHostSession() {
  if (!client || !hostAgentId.value) return

  // 如果已有 sessionKey 且属于当前 hostAgent，则复用
  if (sessionKey.value && sessionKey.value.startsWith(`agent:${hostAgentId.value}:`)) {
    console.log('[GroupChat] Reusing session:', sessionKey.value)
    // 订阅 session 以接收事件
    await subscribeSession()
    return
  }

  // 创建主持人 Session
  const sessionId = crypto.randomUUID()
  sessionKey.value = `agent:${hostAgentId.value}:groupchat:${sessionId}`
  console.log('[GroupChat] Created session:', sessionKey.value)
  saveState()

  // 订阅 session 以接收事件
  await subscribeSession()
}

async function subscribeSession() {
  if (!client || !sessionKey.value) return

  try {
    await client.request('sessions.subscribe', {
      keys: [sessionKey.value]
    })
    console.log('[GroupChat] Subscribed to session:', sessionKey.value)
  } catch (err: any) {
    console.error('[GroupChat] Failed to subscribe session:', err)
  }
}

// ==================== 工具函数 ====================

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
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

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

// ==================== 生命周期 ====================

// 持久化状态
interface SavedState {
  sessionKey: string
  hostAgentId: string
  participants: Participant[]
  messages: GroupChatMessage[]
}

function saveState() {
  const state: SavedState = {
    sessionKey: sessionKey.value,
    hostAgentId: hostAgentId.value,
    participants: participants.value,
    messages: messages.value.slice(-50) // 只保存最近 50 条消息
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}

function loadState(): SavedState | null {
  try {
    const data = localStorage.getItem(STORAGE_KEY)
    if (data) {
      return JSON.parse(data)
    }
  } catch (e) {
    console.error('[GroupChat] Failed to load state:', e)
  }
  return null
}

function clearState() {
  localStorage.removeItem(STORAGE_KEY)
}

onMounted(async () => {
  await loadAgents()

  // 恢复之前的状态
  const saved = loadState()
  if (saved) {
    hostAgentId.value = saved.hostAgentId
    participants.value = saved.participants
    messages.value = saved.messages
    sessionKey.value = saved.sessionKey
    console.log('[GroupChat] Restored state from localStorage')
  }

  await connectGateway()
})

onUnmounted(() => {
  // 保存状态到 localStorage
  if (sessionKey.value && messages.value.length > 0) {
    saveState()
    console.log('[GroupChat] Saved state to localStorage')
  }

  if (client) {
    isManualStop = true
    client.stop()
  }
})

// 监听主持人变化，重新创建 Session
import { watch } from 'vue'
watch(hostAgentId, (newVal, oldVal) => {
  if (newVal && client?.connected) {
    // 如果主持人变化，清空旧消息，创建新 session
    if (oldVal && newVal !== oldVal) {
      messages.value = []
      clearState()
    }
    createHostSession()
  }
})
</script>

<style scoped>
.group-chat {
  min-height: calc(100vh - 120px);
  padding: 24px 32px;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 16px;
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
  background: radial-gradient(circle, #667eea, transparent);
  top: -100px;
  right: -100px;
  animation: float 8s ease-in-out infinite;
}

.orb-2 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, #f093fb, transparent);
  bottom: 0;
  left: -80px;
  animation: float 10s ease-in-out infinite reverse;
}

/* 顶部栏 */
.top-bar {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  backdrop-filter: blur(10px);
}

.title-area h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.title-area .subtitle {
  font-size: 13px;
  color: #999;
}

.actions {
  display: flex;
  gap: 10px;
}

/* 参与者面板 */
.participants-bar {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 10px;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.participants-bar .label {
  font-size: 13px;
  color: #666;
}

.participant-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.no-participants {
  font-size: 13px;
  color: #999;
  font-style: italic;
}

/* 消息区域 */
.messages-area {
  position: relative;
  z-index: 1;
  flex: 1;
  min-height: 300px;
  max-height: calc(100vh - 340px);
  overflow-y: auto;
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
}

.message.user .avatar {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
}

.host-avatar {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
}

.bubble {
  max-width: min(900px, 75%);
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

.agent-label {
  font-size: 12px;
  font-weight: 600;
  color: #6366f1;
  margin-bottom: 6px;
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

/* 流式输出 */
.message.streaming .bubble {
  animation: pulsing-border 1.5s ease-out infinite;
}

@keyframes pulsing-border {
  0%, 100% { box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05); }
  50% { box-shadow: 0 2px 16px rgba(99, 102, 241, 0.2); }
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

/* 弹窗样式 */
.dialog-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.config-section h4 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.section-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: #999;
}

.participant-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;
}

.participant-item {
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  transition: all 0.15s ease;
}

.participant-item:hover {
  background: rgba(99, 102, 241, 0.05);
  border-color: rgba(99, 102, 241, 0.15);
}

.participant-info {
  display: flex;
  flex-direction: column;
}

.participant-name {
  font-size: 14px;
  color: #333;
}

.participant-model {
  font-size: 12px;
  color: #999;
}

.agent-option {
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

<!-- Markdown 样式 -->
<style>
.message .bubble .content p { margin: 0 0 8px; }
.message .bubble .content p:last-child { margin-bottom: 0; }
.message .bubble .content code {
  padding: 2px 6px;
  background: rgba(99, 102, 241, 0.1);
  border-radius: 4px;
  font-size: 0.9em;
  color: #6366f1;
}
.message.user .bubble .content code {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}
</style>