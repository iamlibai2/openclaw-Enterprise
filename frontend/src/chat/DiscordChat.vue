<template>
  <div class="discord-chat">
    <!-- 左侧边栏 - 服务器/Agent 列表 -->
    <div class="sidebar-servers">
      <!-- 单聊 Agent 列表 -->
      <div class="server-list">
        <div
          v-for="agent in agents"
          :key="agent.id"
          :class="['server-icon', { active: isSelected('single', agent.id), online: true }]"
          :style="getAvatarStyle(agent.id)"
          @click="selectAgent(agent)"
          v-tooltip="agent.name || agent.id"
        >
          <span class="avatar-text">{{ agent.name?.charAt(0) || '?' }}</span>
          <div class="status-dot"></div>
          <div class="pill"></div>
        </div>
      </div>

      <div class="divider"></div>

      <!-- 新建群聊 -->
      <div class="server-icon add" @click="showCreateGroup = true" v-tooltip="'新建群聊'">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
      </div>

      <!-- 群聊列表 -->
      <div class="server-list">
        <div
          v-for="group in groups"
          :key="group.id"
          :class="['server-icon', 'group', { active: isSelected('group', group.id) }]"
          :style="getGroupStyle(group)"
          @click="selectGroup(group)"
          v-tooltip="group.name"
        >
          <span class="avatar-text">{{ group.name?.charAt(0) || '#' }}</span>
          <div class="pill"></div>
        </div>
      </div>
    </div>

    <!-- 中间频道列表 -->
    <div class="sidebar-channels">
      <div class="header">
        <span class="title">{{ currentTitle }}</span>
        <el-icon class="settings-icon" @click="showSettings = true"><Setting /></el-icon>
      </div>

      <!-- 单聊频道 -->
      <template v-if="currentType === 'single'">
        <div class="channel-section">
          <div class="section-header">私信</div>
          <div class="channel-item active">
            <el-icon><ChatDotRound /></el-icon>
            <span>{{ currentAgent?.name || '对话' }}</span>
          </div>
        </div>
      </template>

      <!-- 群聊频道 -->
      <template v-else-if="currentType === 'group' && currentGroup">
        <div class="channel-section">
          <div class="section-header">文字频道</div>
          <div class="channel-item active">
            <span class="hash">#</span>
            <span>聊天室</span>
          </div>
        </div>

        <div class="channel-section">
          <div class="section-header">参与者 · {{ currentGroup.participants.length }}</div>
          <div
            v-for="p in currentGroup.participants"
            :key="p.agentId"
            class="member-item"
          >
            <div class="member-avatar" :style="getAvatarStyle(p.agentId)">
              {{ p.name?.charAt(0) || '?' }}
            </div>
            <div class="member-info">
              <span class="member-name">{{ p.name }}</span>
              <span class="member-role" v-if="p.agentId === currentGroup.hostAgentId">主持人</span>
            </div>
          </div>
        </div>
      </template>

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <p>选择一个对话开始聊天</p>
      </div>
    </div>

    <!-- 主聊天区域 -->
    <div class="main-chat">
      <template v-if="currentType">
        <!-- 顶部栏 -->
        <div class="chat-header">
          <div class="header-left">
            <div class="channel-icon">
              <span v-if="currentType === 'single'">@</span>
              <span v-else>#</span>
            </div>
            <span class="channel-name">{{ currentTitle }}</span>
            <div class="channel-divider"></div>
            <span class="channel-desc" v-if="currentType === 'group' && currentGroup">
              {{ currentGroup.participants.map(p => p.name).join('、') }}
            </span>
          </div>
          <div class="header-right">
            <el-icon class="header-icon" @click="showMembers = !showMembers"><User /></el-icon>
          </div>
        </div>

        <!-- 消息区域 -->
        <div class="messages-area" ref="messagesRef">
          <div class="messages-wrapper">
            <!-- 欢迎消息 -->
            <div class="welcome-message" v-if="messages.length === 0">
              <div class="welcome-icon" :style="currentType === 'single' ? getAvatarStyle(currentAgent?.id || '') : getGroupStyle(currentGroup)">
                <span v-if="currentType === 'single'">{{ currentAgent?.name?.charAt(0) || '?' }}</span>
                <span v-else>{{ currentGroup?.name?.charAt(0) || '#' }}</span>
              </div>
              <h2>欢迎来到 #{{ currentTitle }}！</h2>
              <p v-if="currentType === 'single'">这是你与 {{ currentAgent?.name }} 的对话开始。</p>
              <p v-else>这是群聊的开始，主持人会协调各 Agent 参与讨论。</p>
            </div>

            <!-- 消息列表 -->
            <div
              v-for="(msg, idx) in messages"
              :key="msg.id"
              :class="['message', { 'has-avatar': shouldShowAvatar(idx) }]"
            >
              <div v-if="shouldShowAvatar(idx)" class="message-avatar" :style="getAvatarStyle(msg.sourceAgent || currentAgent?.id)">
                {{ getSenderName(msg)?.charAt(0) || '?' }}
              </div>
              <div v-else class="message-spacer"></div>

              <div class="message-content">
                <div v-if="shouldShowAvatar(idx)" class="message-header">
                  <span class="author" :style="{ color: getAuthorColor(msg.sourceAgent || currentAgent?.id) }">
                    {{ getSenderName(msg) }}
                  </span>
                  <span class="timestamp">{{ formatTime(msg.timestamp) }}</span>
                </div>
                <div class="message-text" v-html="renderMarkdown(getMessageText(msg))"></div>
              </div>
            </div>

            <!-- 流式输出 -->
            <div v-if="isStreaming && streamContent" class="message has-avatar">
              <div class="message-avatar" :style="getAvatarStyle(currentAgent?.id)">
                {{ currentAgent?.name?.charAt(0) || '?' }}
              </div>
              <div class="message-content">
                <div class="message-header">
                  <span class="author" :style="{ color: getAuthorColor(currentAgent?.id) }">
                    {{ currentAgent?.name }}
                  </span>
                  <span class="timestamp typing">正在输入...</span>
                </div>
                <div class="message-text" v-html="renderMarkdown(streamContent)"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="input-area">
          <div class="input-wrapper">
            <button class="input-btn attach">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm5 11h-4v4h-2v-4H7v-2h4V7h2v4h4v2z"/>
              </svg>
            </button>
            <textarea
              ref="textareaRef"
              v-model="inputMessage"
              placeholder="发送消息..."
              rows="1"
              @keydown="handleKeydown"
              @input="autoResize"
            ></textarea>
            <button class="input-btn emoji">
              <span>😊</span>
            </button>
            <button class="input-btn send" :class="{ active: canSend }" @click="sendMessage">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            </button>
          </div>
        </div>
      </template>

      <!-- 空状态 -->
      <div v-else class="no-chat">
        <div class="no-chat-icon">
          <svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
        </div>
        <h2>欢迎来到 OpenClaw</h2>
        <p>选择左侧的 Agent 开始对话，或创建群聊进行多 Agent 讨论</p>
      </div>
    </div>

    <!-- 右侧成员面板 -->
    <Transition name="slide">
      <div v-if="showMembers && currentGroup" class="sidebar-members">
        <div class="members-header">成员 — {{ currentGroup.participants.length }}</div>
        <div class="members-list">
          <div class="member-category">
            <div class="category-title">主持人</div>
            <div class="member-card">
              <div class="member-avatar" :style="getAvatarStyle(currentGroup.hostAgentId)">
                {{ currentGroup.hostAgentName?.charAt(0) || '?' }}
              </div>
              <div class="member-info">
                <span class="name">{{ currentGroup.hostAgentName }}</span>
                <span class="status">在线</span>
              </div>
            </div>
          </div>
          <div class="member-category">
            <div class="category-title">参与者</div>
            <div
              v-for="p in currentGroup.participants.filter(p => p.agentId !== currentGroup.hostAgentId)"
              :key="p.agentId"
              class="member-card"
            >
              <div class="member-avatar" :style="getAvatarStyle(p.agentId)">
                {{ p.name?.charAt(0) || '?' }}
              </div>
              <div class="member-info">
                <span class="name">{{ p.name }}</span>
                <span class="status">在线</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 新建群聊弹窗 -->
    <el-dialog
      v-model="showCreateGroup"
      title="创建群聊"
      width="440px"
      class="create-group-modal"
    >
      <div class="form-group">
        <label>群聊名称</label>
        <input v-model="newGroupName" type="text" placeholder="输入群聊名称" />
      </div>
      <div class="form-group">
        <label>主持人</label>
        <div class="agent-grid">
          <div
            v-for="agent in agents"
            :key="agent.id"
            :class="['agent-card', { selected: newGroupHost === agent.id }]"
            @click="newGroupHost = agent.id"
          >
            <div class="agent-avatar" :style="getAvatarStyle(agent.id)">
              {{ agent.name?.charAt(0) || '?' }}
            </div>
            <span class="agent-name">{{ agent.name }}</span>
          </div>
        </div>
      </div>
      <div class="form-group">
        <label>参与者</label>
        <div class="agent-grid">
          <div
            v-for="agent in agents.filter(a => a.id !== newGroupHost)"
            :key="agent.id"
            :class="['agent-card', { selected: newGroupParticipants.includes(agent.id) }]"
            @click="toggleParticipant(agent.id)"
          >
            <div class="agent-avatar" :style="getAvatarStyle(agent.id)">
              {{ agent.name?.charAt(0) || '?' }}
            </div>
            <span class="agent-name">{{ agent.name }}</span>
            <div v-if="newGroupParticipants.includes(agent.id)" class="check-mark">✓</div>
          </div>
        </div>
      </div>
      <template #footer>
        <button class="btn-cancel" @click="showCreateGroup = false">取消</button>
        <button class="btn-create" :disabled="!canCreateGroup" @click="createGroup">创建</button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting, ChatDotRound, User } from '@element-plus/icons-vue'
import { agentApi } from '../api'
import { createGatewayClient, GatewayHelloOk, extractText } from '../utils/gateway-ws'
import { renderMessageContent } from '../utils/markdown'
import type { Agent, Message, Participant } from '../chat/types'

// ==================== Types ====================

interface GroupChat {
  id: string
  name: string
  hostAgentId: string
  hostAgentName: string
  participants: Participant[]
}

// ==================== State ====================

const agents = ref<Agent[]>([])
const groups = ref<GroupChat[]>([])

const currentType = ref<'single' | 'group' | null>(null)
const currentAgentId = ref<string>('')
const currentGroupId = ref<string>('')

const messagesMap = ref<Map<string, Message[]>>(new Map())
const messages = ref<Message[]>([])

const isStreaming = ref(false)
const streamContent = ref('')
const inputMessage = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const messagesRef = ref<HTMLElement | null>(null)

const showMembers = ref(false)
const showCreateGroup = ref(false)
const showSettings = ref(false)

const newGroupName = ref('')
const newGroupHost = ref('')
const newGroupParticipants = ref<string[]>([])

let client: ReturnType<typeof createGatewayClient> | null = null
const sessionMap = ref<Map<string, string>>(new Map())

// ==================== Computed ====================

const currentAgent = computed(() => agents.value.find(a => a.id === currentAgentId.value))
const currentGroup = computed(() => groups.value.find(g => g.id === currentGroupId.value))
const currentTitle = computed(() => {
  if (currentType.value === 'single') return currentAgent.value?.name || '对话'
  if (currentType.value === 'group') return currentGroup.value?.name || '群聊'
  return 'OpenClaw'
})

const canSend = computed(() => inputMessage.value.trim() && !isStreaming.value)
const canCreateGroup = computed(() => newGroupHost.value && newGroupParticipants.value.length > 0)

// ==================== Avatar Colors ====================

const avatarColors = [
  '#5865F2', '#57F287', '#FEE75C', '#EB459E', '#ED4245', '#9B59B6',
  '#3498DB', '#1ABC9C', '#F39C12', '#E74C3C', '#2ECC71', '#E91E63'
]

function getAvatarStyle(id?: string): Record<string, string> {
  if (!id) return { background: avatarColors[0] }
  const hash = id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  return { background: avatarColors[hash % avatarColors.length] }
}

function getGroupStyle(group?: GroupChat): Record<string, string> {
  if (!group) return { background: '#5865F2' }
  const hash = group.id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  return { background: avatarColors[hash % avatarColors.length] }
}

function getAuthorColor(id?: string): string {
  if (!id) return avatarColors[0]
  const hash = id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  return avatarColors[hash % avatarColors.length]
}

// ==================== Methods ====================

function isSelected(type: 'single' | 'group', id: string): boolean {
  return currentType.value === type &&
    (type === 'single' ? currentAgentId.value === id : currentGroupId.value === id)
}

function selectAgent(agent: Agent) {
  currentType.value = 'single'
  currentAgentId.value = agent.id
  currentGroupId.value = ''

  const key = `single-${agent.id}`
  if (sessionMap.value.has(key)) {
    // 已有 session，从 Gateway 加载历史消息
    loadMessagesFromGateway(key)
  } else {
    // 新对话
    messages.value = []
    ensureSession(key, agent.id)
  }
}

function selectGroup(group: GroupChat) {
  currentType.value = 'group'
  currentGroupId.value = group.id
  currentAgentId.value = ''

  const key = `group-${group.id}`
  if (sessionMap.value.has(key)) {
    // 已有 session，从 Gateway 加载历史消息
    loadMessagesFromGateway(key)
  } else {
    // 新对话
    messages.value = []
    ensureSession(key, group.hostAgentId, true)
  }
}

function loadMessages(key: string) {
  messages.value = messagesMap.value.get(key) || []
  scrollToBottom()
}

async function ensureSession(key: string, agentId: string, isGroup = false) {
  if (!client?.connected) return

  let sessionKey = sessionMap.value.get(key)
  if (sessionKey) return

  const sessionId = crypto.randomUUID()
  sessionKey = isGroup
    ? `agent:${agentId}:groupchat:${sessionId}`
    : `agent:${agentId}:webchat:${sessionId}`

  sessionMap.value.set(key, sessionKey)

  try {
    await client.request('sessions.subscribe', { keys: [sessionKey] })
  } catch (err) {
    console.error('Failed to subscribe:', err)
  }
}

function shouldShowAvatar(idx: number): boolean {
  if (idx === 0) return true
  const prev = messages.value[idx - 1]
  const curr = messages.value[idx]
  return prev.role !== curr.role ||
    (prev.sourceAgent !== curr.sourceAgent) ||
    (curr.timestamp - prev.timestamp > 300000)
}

function getSenderName(msg: Message): string {
  if (msg.sourceName) return msg.sourceName
  if (msg.role === 'user') return '你'
  return currentAgent.value?.name || 'Assistant'
}

function getMessageText(msg: Message): string {
  const content = msg.content
  if (Array.isArray(content)) {
    const textBlock = content.find(c => c.type === 'text')
    return textBlock?.text || ''
  }
  return ''
}

function renderMarkdown(text: string): string {
  return renderMessageContent(text)
}

function formatTime(timestamp?: number): string {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  if (date.toDateString() === now.toDateString()) {
    return '今天 ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' }) + ' ' +
         date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function autoResize() {
  const textarea = textareaRef.value
  if (textarea) {
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px'
  }
}

async function sendMessage() {
  if (!canSend.value || !client) return

  const content = inputMessage.value.trim()
  inputMessage.value = ''
  autoResize()

  const key = currentType.value === 'single'
    ? `single-${currentAgentId.value}`
    : `group-${currentGroupId.value}`

  // Add user message (本地显示，不需要保存到 localStorage)
  const userMsg: Message = {
    id: crypto.randomUUID(),
    role: 'user',
    content: [{ type: 'text', text: content }],
    timestamp: Date.now()
  }
  const msgs = messagesMap.value.get(key) || []
  msgs.push(userMsg)
  messagesMap.value.set(key, [...msgs])
  messages.value = [...msgs]

  // Get session key
  let sessionKey = sessionMap.value.get(key)
  if (!sessionKey) {
    await ensureSession(key, currentType.value === 'single' ? currentAgentId.value : currentGroup.value!.hostAgentId, currentType.value === 'group')
    sessionKey = sessionMap.value.get(key)
  }
  if (!sessionKey) return

  // Build message
  let messageToSend = content
  if (currentType.value === 'group' && currentGroup.value) {
    const group = currentGroup.value
    const participantInfo = group.participants
      .filter(p => p.enabled)
      .map(p => `- ${p.name}(${p.agentId})`)
      .join('\n')

    messageToSend = `【群聊上下文】
主持人：${group.hostAgentName}
参与者：
${participantInfo}

【用户问题】
${content}

请根据问题决定需要哪些 Agent 参与，并使用 sessions_send 工具与他们讨论。`
  }

  isStreaming.value = true
  streamContent.value = ''

  try {
    await client.request('chat.send', {
      sessionKey,
      message: messageToSend,
      deliver: false,
      idempotencyKey: crypto.randomUUID()
    })
  } catch (err: any) {
    console.error('Send failed:', err)
    isStreaming.value = false
    ElMessage.error('发送失败: ' + err.message)
  }
}

function scrollToBottom(smooth = true) {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTo({
        top: messagesRef.value.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto'
      })
    }
  })
}

function toggleParticipant(agentId: string) {
  const idx = newGroupParticipants.value.indexOf(agentId)
  if (idx >= 0) {
    newGroupParticipants.value.splice(idx, 1)
  } else {
    newGroupParticipants.value.push(agentId)
  }
}

function createGroup() {
  const host = agents.value.find(a => a.id === newGroupHost.value)
  const participants: Participant[] = newGroupParticipants.value.map(id => {
    const agent = agents.value.find(a => a.id === id)
    return { agentId: id, name: agent?.name || id, enabled: true }
  })

  const group: GroupChat = {
    id: `group-${crypto.randomUUID()}`,
    name: newGroupName.value || `${host?.name || '群'}的群`,
    hostAgentId: newGroupHost.value,
    hostAgentName: host?.name || newGroupHost.value,
    participants
  }

  groups.value.unshift(group)
  showCreateGroup.value = false
  newGroupName.value = ''
  newGroupHost.value = ''
  newGroupParticipants.value = []

  selectGroup(group)
  saveToStorage()
}

function saveToStorage() {
  // 保存群聊列表、session 映射、以及当前选择状态
  const data = {
    groups: groups.value,
    sessions: Object.fromEntries(sessionMap.value),
    // 保存当前选择
    currentType: currentType.value,
    currentAgentId: currentAgentId.value,
    currentGroupId: currentGroupId.value
  }
  localStorage.setItem('discord-chat-data', JSON.stringify(data))
}

function loadFromStorage() {
  try {
    const raw = localStorage.getItem('discord-chat-data')
    if (raw) {
      const data = JSON.parse(raw)
      groups.value = data.groups || []
      if (data.sessions) {
        sessionMap.value = new Map(Object.entries(data.sessions))
      }
      // 返回上次的选择状态
      return {
        currentType: data.currentType || null,
        currentAgentId: data.currentAgentId || '',
        currentGroupId: data.currentGroupId || ''
      }
    }
  } catch (e) {
    console.error('Failed to load:', e)
  }
  return { currentType: null, currentAgentId: '', currentGroupId: '' }
}

// 从 Gateway 加载历史消息
async function loadMessagesFromGateway(key: string) {
  if (!client?.connected) return

  const sessionKey = sessionMap.value.get(key)
  if (!sessionKey) return

  try {
    const res = await client.request<{ messages?: any[] }>('chat.history', {
      sessionKey,
      limit: 200
    })
    const msgs = Array.isArray(res.messages) ? res.messages : []
    messagesMap.value.set(key, msgs)
    messages.value = msgs
    scrollToBottom()
  } catch (err) {
    console.error('[DiscordChat] Failed to load history:', err)
  }
}

// ==================== Gateway Events ====================

function onChatEvent(evt: any) {
  if (evt.event !== 'chat') return
  const payload = evt.payload
  const sessionKey = payload.sessionKey

  // Find conversation
  let convKey: string | null = null
  for (const [key, sk] of sessionMap.value.entries()) {
    if (sk === sessionKey) {
      convKey = key
      break
    }
  }
  if (!convKey) return

  if (payload.state === 'delta') {
    const text = extractText(payload.message)
    if (typeof text === 'string') {
      streamContent.value = text
      scrollToBottom()
    }
  } else if (payload.state === 'final') {
    const text = extractText(payload.message) || streamContent.value
    if (text?.trim()) {
      const msg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: [{ type: 'text', text }],
        timestamp: Date.now()
      }
      const msgs = messagesMap.value.get(convKey) || []
      msgs.push(msg)
      messagesMap.value.set(convKey, [...msgs])
      if (convKey === (currentType.value === 'single' ? `single-${currentAgentId.value}` : `group-${currentGroupId.value}`)) {
        messages.value = [...msgs]
      }
    }
    streamContent.value = ''
    isStreaming.value = false
    scrollToBottom()
    // 只保存 session，消息由 Gateway 保存
    saveToStorage()
  } else if (payload.state === 'error') {
    streamContent.value = ''
    isStreaming.value = false
    ElMessage.error(payload.errorMessage || '发生错误')
  }
}

// ==================== Lifecycle ====================

onMounted(async () => {
  try {
    const res = await agentApi.list()
    if (res.data.success) {
      agents.value = res.data.data || []
    }
  } catch (e) {
    console.error('Failed to load agents:', e)
  }

  loadFromStorage()

  // Connect Gateway
  try {
    const res = await (await import('../api')).chatApi.getConfig()
    if (res.data.success) {
      const { gatewayUrl, gatewayToken } = res.data.data
      client = createGatewayClient({
        url: gatewayUrl,
        token: gatewayToken,
        onHello: async () => {
          console.log('[DiscordChat] Connected')
          // 重新订阅所有已保存的 session
          if (sessionMap.value.size > 0) {
            const sessionKeys = Array.from(sessionMap.value.values())
            console.log('[DiscordChat] Re-subscribing to sessions:', sessionKeys.length)
            try {
              await client?.request('sessions.subscribe', { keys: sessionKeys })
              console.log('[DiscordChat] Sessions re-subscribed')
            } catch (err) {
              console.error('[DiscordChat] Failed to re-subscribe:', err)
            }
          }
        },
        onEvent: onChatEvent,
        onClose: () => console.log('[DiscordChat] Disconnected')
      })
      client.start()
    }
  } catch (e) {
    console.error('Failed to connect gateway:', e)
  }
})

onUnmounted(() => {
  saveToStorage()
  client?.stop()
})

watch(messages, () => scrollToBottom())
</script>

<style scoped>
.discord-chat {
  display: flex;
  height: 100%;
  background: #313338;
  color: #dbdee1;
  font-family: 'Whitney', 'Helvetica Neue', Helvetica, Arial, sans-serif;
}

/* 左侧服务器列表 */
.sidebar-servers {
  width: 72px;
  background: #1e1f22;
  padding: 12px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.server-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.server-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease-out;
  position: relative;
  color: #dbdee1;
  font-size: 18px;
  font-weight: 600;
}

.server-icon:hover {
  border-radius: 16px;
}

.server-icon.active {
  border-radius: 16px;
}

.server-icon .avatar-text {
  transition: transform 0.2s ease;
}

.server-icon:hover .avatar-text {
  transform: scale(1.1);
}

.server-icon .status-dot {
  position: absolute;
  bottom: -2px;
  right: -2px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #23a55a;
  border: 3px solid #1e1f22;
  opacity: 0;
  transition: opacity 0.2s;
}

.server-icon.online .status-dot {
  opacity: 1;
}

.server-icon .pill {
  position: absolute;
  left: -12px;
  width: 8px;
  height: 0;
  border-radius: 0 4px 4px 0;
  background: #fff;
  transition: height 0.2s ease;
}

.server-icon:hover .pill {
  height: 20px;
}

.server-icon.active .pill {
  height: 40px;
}

.server-icon.add {
  background: transparent;
  color: #23a55a;
  border-radius: 50%;
}

.server-icon.add:hover {
  background: #23a55a;
  color: #fff;
  border-radius: 16px;
}

.divider {
  width: 32px;
  height: 2px;
  background: #35363c;
  border-radius: 1px;
  margin: 4px 0;
}

/* 中间频道列表 */
.sidebar-channels {
  width: 240px;
  background: #2b2d31;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-channels .header {
  height: 48px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 2px solid #1e1f22;
  font-weight: 600;
}

.sidebar-channels .title {
  font-size: 15px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.settings-icon {
  cursor: pointer;
  opacity: 0.6;
  transition: opacity 0.15s;
}

.settings-icon:hover {
  opacity: 1;
}

.channel-section {
  padding: 16px 8px 8px;
}

.section-header {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  color: #949ba4;
  padding: 0 8px;
  margin-bottom: 4px;
}

.channel-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
  color: #949ba4;
  font-size: 15px;
  transition: all 0.15s;
}

.channel-item:hover {
  background: #35373c;
  color: #dbdee1;
}

.channel-item.active {
  background: #404249;
  color: #fff;
}

.channel-item .hash {
  font-size: 20px;
  opacity: 0.6;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.member-item:hover {
  background: #35373c;
}

.member-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}

.member-info {
  display: flex;
  flex-direction: column;
}

.member-name {
  font-size: 14px;
  color: #949ba4;
}

.member-role {
  font-size: 11px;
  color: #f0b232;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #949ba4;
}

/* 主聊天区域 */
.main-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-header {
  height: 48px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #313338;
  border-bottom: 1px solid #1e1f22;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.channel-icon {
  font-size: 24px;
  color: #80848e;
}

.channel-name {
  font-weight: 600;
  font-size: 16px;
}

.channel-divider {
  width: 1px;
  height: 24px;
  background: #3f4147;
  margin: 0 8px;
}

.channel-desc {
  font-size: 14px;
  color: #949ba4;
}

.header-icon {
  font-size: 24px;
  cursor: pointer;
  color: #b5bac1;
  transition: color 0.15s;
}

.header-icon:hover {
  color: #dbdee1;
}

/* 消息区域 */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.messages-wrapper {
  max-width: 100%;
}

.welcome-message {
  text-align: center;
  padding: 32px 0;
}

.welcome-icon {
  width: 68px;
  height: 68px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: 600;
  color: #fff;
  margin: 0 auto 8px;
}

.welcome-message h2 {
  font-size: 32px;
  font-weight: 700;
  margin: 8px 0;
}

.welcome-message p {
  color: #949ba4;
  font-size: 16px;
}

.message {
  display: flex;
  gap: 16px;
  padding: 2px 48px 2px 72px;
  position: relative;
  margin-top: 17px;
}

.message:hover {
  background: #2e3035;
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  flex-shrink: 0;
  position: absolute;
  left: 16px;
}

.message-spacer {
  width: 40px;
  flex-shrink: 0;
}

.message-content {
  flex: 1;
  min-width: 0;
}

.message-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 4px;
}

.author {
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
}

.author:hover {
  text-decoration: underline;
}

.timestamp {
  font-size: 12px;
  color: #949ba4;
}

.timestamp.typing {
  color: #f0b232;
}

.message-text {
  font-size: 16px;
  line-height: 1.375;
  color: #dbdee1;
  word-wrap: break-word;
}

.message-text :deep(p) {
  margin: 0 0 8px;
}

.message-text :deep(code) {
  background: #2b2d31;
  padding: 2px 4px;
  border-radius: 4px;
  font-size: 14px;
}

/* 输入区域 */
.input-area {
  padding: 0 16px 24px;
  flex-shrink: 0;
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: #383a40;
  border-radius: 8px;
  padding: 0 16px;
}

.input-btn {
  width: 32px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  cursor: pointer;
  color: #b5bac1;
  transition: color 0.15s;
}

.input-btn:hover {
  color: #dbdee1;
}

.input-btn.attach {
  transform: rotate(45deg);
}

.input-btn.emoji span {
  font-size: 22px;
}

.input-btn.send {
  color: #949ba4;
}

.input-btn.send.active {
  color: #fff;
}

.input-wrapper textarea {
  flex: 1;
  background: none;
  border: none;
  color: #dbdee1;
  font-size: 16px;
  line-height: 1.375;
  padding: 12px 0;
  resize: none;
  font-family: inherit;
  max-height: 200px;
}

.input-wrapper textarea::placeholder {
  color: #6d6f78;
}

.input-wrapper textarea:focus {
  outline: none;
}

/* 空状态 */
.no-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #949ba4;
}

.no-chat-icon {
  opacity: 0.3;
  margin-bottom: 16px;
}

.no-chat h2 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #dbdee1;
}

/* 右侧成员面板 */
.sidebar-members {
  width: 240px;
  background: #2b2d31;
  flex-shrink: 0;
  overflow-y: auto;
}

.members-header {
  padding: 12px 16px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  color: #949ba4;
}

.members-list {
  padding: 0 8px;
}

.member-category {
  margin-bottom: 16px;
}

.category-title {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  color: #949ba4;
  padding: 8px;
}

.member-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.member-card:hover {
  background: #35373c;
}

.member-card .member-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}

.member-card .member-info {
  display: flex;
  flex-direction: column;
}

.member-card .name {
  font-size: 14px;
  color: #949ba4;
}

.member-card .status {
  font-size: 12px;
  color: #23a55a;
}

/* 滑入动画 */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

/* 新建群聊弹窗 */
.create-group-modal :deep(.el-dialog__header) {
  padding: 16px 20px;
  background: #313338;
  border-bottom: 1px solid #1e1f22;
}

.create-group-modal :deep(.el-dialog__title) {
  color: #fff;
  font-weight: 600;
}

.create-group-modal :deep(.el-dialog__body) {
  padding: 20px;
  background: #313338;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  color: #949ba4;
  margin-bottom: 8px;
}

.form-group input {
  width: 100%;
  padding: 10px;
  background: #1e1f22;
  border: none;
  border-radius: 4px;
  color: #dbdee1;
  font-size: 16px;
}

.form-group input::placeholder {
  color: #6d6f78;
}

.form-group input:focus {
  outline: none;
  box-shadow: 0 0 0 2px #5865f2;
}

.agent-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.agent-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px;
  background: #2b2d31;
  border-radius: 8px;
  cursor: pointer;
  min-width: 70px;
  transition: all 0.15s;
  position: relative;
}

.agent-card:hover {
  background: #35373c;
}

.agent-card.selected {
  background: #404249;
  box-shadow: inset 0 0 0 2px #5865f2;
}

.agent-card .agent-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

.agent-card .agent-name {
  font-size: 13px;
  color: #949ba4;
}

.agent-card .check-mark {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 18px;
  height: 18px;
  background: #5865f2;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #fff;
}

.btn-cancel {
  padding: 8px 16px;
  background: #4e5058;
  border: none;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
  font-size: 14px;
}

.btn-cancel:hover {
  background: #6d6f78;
}

.btn-create {
  padding: 8px 16px;
  background: #5865f2;
  border: none;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
  font-size: 14px;
  margin-left: 8px;
}

.btn-create:hover {
  background: #4752c4;
}

.btn-create:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 滚动条 */
.messages-area::-webkit-scrollbar,
.sidebar-members::-webkit-scrollbar {
  width: 8px;
}

.messages-area::-webkit-scrollbar-thumb,
.sidebar-members::-webkit-scrollbar-thumb {
  background: #1e1f22;
  border-radius: 4px;
}

.messages-area::-webkit-scrollbar-thumb:hover,
.sidebar-members::-webkit-scrollbar-thumb:hover {
  background: #2b2d31;
}
</style>