<template>
  <div class="feishu-chat">
    <!-- 左侧导航栏 -->
    <div class="sidebar">
      <!-- 顶部头像区 -->
      <div class="sidebar-header">
        <div class="user-avatar">
          <span>{{ userStore.user?.displayName?.charAt(0) || 'U' }}</span>
        </div>
      </div>

      <!-- 导航项 -->
      <div class="nav-items">
        <div
          :class="['nav-item', { active: activeNav === 'chat' }]"
          @click="activeNav = 'chat'"
          v-tooltip="'私信'"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
          <div class="nav-badge" v-if="unreadCount > 0">{{ unreadCount > 99 ? '99+' : unreadCount }}</div>
        </div>
        <div
          :class="['nav-item', { active: activeNav === 'group' }]"
          @click="activeNav = 'group'"
          v-tooltip="'群聊'"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
            <circle cx="9" cy="7" r="4"></circle>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
          </svg>
        </div>
      </div>

      <!-- 底部设置 -->
      <div class="sidebar-footer">
        <div class="nav-item" @click="showSettings = true" v-tooltip="'设置'">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
        </div>
      </div>
    </div>

    <!-- 会话列表 -->
    <div class="conversation-panel">
      <div class="panel-header">
        <div class="search-box">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input v-model="searchQuery" type="text" placeholder="搜索" />
        </div>
      </div>

      <div class="panel-tabs">
        <div :class="['tab', { active: activeNav === 'chat' }]" @click="activeNav = 'chat'">私信</div>
        <div :class="['tab', { active: activeNav === 'group' }]" @click="activeNav = 'group'">群聊</div>
      </div>

      <div class="conversation-list">
        <!-- 新建群聊按钮 -->
        <div v-if="activeNav === 'group'" class="create-group-btn" @click="showCreateGroup = true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          <span>创建群聊</span>
        </div>

        <!-- 单聊列表 -->
        <template v-if="activeNav === 'chat'">
          <div
            v-for="conv in filteredAgents"
            :key="conv.id"
            :class="['conversation-item', { active: selectedId === conv.id }]"
            @click="selectConversation('single', conv.id)"
          >
            <div class="conv-avatar" :style="getAvatarStyle(conv.id)">
              {{ conv.name?.charAt(0) || '?' }}
            </div>
            <div class="conv-info">
              <div class="conv-name">{{ conv.name }}</div>
              <div class="conv-preview">{{ conv.lastMessage || '开始聊天吧' }}</div>
            </div>
            <div class="conv-meta">
              <span class="conv-time" v-if="conv.lastTime">{{ formatShortTime(conv.lastTime) }}</span>
              <span class="conv-unread" v-if="conv.unread">{{ conv.unread }}</span>
            </div>
          </div>
        </template>

        <!-- 群聊列表 -->
        <template v-else>
          <div
            v-for="group in filteredGroups"
            :key="group.id"
            :class="['conversation-item', { active: selectedId === group.id }]"
            @click="selectConversation('group', group.id)"
          >
            <div class="conv-avatar group">
              <span class="group-icon">#</span>
            </div>
            <div class="conv-info">
              <div class="conv-name">{{ group.name }}</div>
              <div class="conv-preview">{{ group.lastMessage || `${group.participants.length} 人` }}</div>
            </div>
            <div class="conv-meta">
              <span class="conv-time" v-if="group.lastTime">{{ formatShortTime(group.lastTime) }}</span>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- 聊天主区域 -->
    <div class="chat-main">
      <template v-if="currentConversation">
        <!-- 顶部栏 -->
        <div class="chat-header">
          <div class="header-left">
            <div class="header-avatar" v-if="currentType === 'single'" :style="getAvatarStyle(currentAgent?.id)">
              {{ currentAgent?.name?.charAt(0) || '?' }}
            </div>
            <div class="header-avatar group" v-else>
              <span>#</span>
            </div>
            <div class="header-info">
              <div class="header-name">{{ currentTitle }}</div>
              <div class="header-desc" v-if="currentType === 'group' && currentGroup">
                {{ currentGroup.participants.map(p => p.name).join('、') }}
              </div>
            </div>
          </div>
          <div class="header-right">
            <button class="header-btn" @click="showDetail = !showDetail">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
            </button>
          </div>
        </div>

        <!-- 消息区域 -->
        <div class="messages-area" ref="messagesRef">
          <!-- 空状态欢迎 -->
          <div v-if="messages.length === 0" class="welcome">
            <div class="welcome-avatar" :style="currentType === 'single' ? getAvatarStyle(currentAgent?.id) : {}">
              <template v-if="currentType === 'single'">{{ currentAgent?.name?.charAt(0) }}</template>
              <template v-else>#</template>
            </div>
            <div class="welcome-title">{{ currentTitle }}</div>
            <div class="welcome-desc" v-if="currentType === 'single'">
              这是与 {{ currentAgent?.name }} 的对话，发送消息开始聊天
            </div>
            <div class="welcome-desc" v-else>
              这是群聊，主持人会协调各 Agent 参与讨论
            </div>
          </div>

          <!-- 消息列表 -->
          <div v-for="(msg, idx) in messages" :key="msg.id" :class="['message-row', msg.role]">
            <div class="msg-avatar" :style="getAvatarStyle(msg.sourceAgent || currentAgent?.id)">
              {{ getSenderName(msg)?.charAt(0) || '?' }}
            </div>
            <div class="msg-content">
              <div class="msg-header">
                <span class="msg-sender">{{ getSenderName(msg) }}</span>
                <span class="msg-time">{{ formatTime(msg.timestamp) }}</span>
              </div>
              <div class="msg-text" v-html="renderMarkdown(getMessageText(msg))"></div>
            </div>
          </div>

          <!-- 流式输出 -->
          <div v-if="isStreaming && streamContent" class="message-row assistant">
            <div class="msg-avatar" :style="getAvatarStyle(currentAgent?.id)">
              {{ currentAgent?.name?.charAt(0) || '?' }}
            </div>
            <div class="msg-content">
              <div class="msg-header">
                <span class="msg-sender">{{ currentAgent?.name }}</span>
                <span class="msg-time typing">
                  <span class="typing-dots"><i></i><i></i><i></i></span>
                </span>
              </div>
              <div class="msg-text" v-html="renderMarkdown(streamContent)"></div>
            </div>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="input-area">
          <div class="input-box">
            <div class="input-tools">
              <button class="tool-btn">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
                </svg>
              </button>
              <button class="tool-btn">
                <span style="font-size: 18px;">😊</span>
              </button>
            </div>
            <textarea
              ref="textareaRef"
              v-model="inputMessage"
              placeholder="发送消息..."
              rows="1"
              @keydown="handleKeydown"
              @input="autoResize"
            ></textarea>
            <button class="send-btn" :class="{ active: canSend }" @click="sendMessage">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            </button>
          </div>
        </div>
      </template>

      <!-- 空状态 -->
      <div v-else class="empty-chat">
        <div class="empty-icon">
          <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
        </div>
        <div class="empty-title">开始对话</div>
        <div class="empty-desc">选择左侧的联系人或群聊开始聊天</div>
      </div>
    </div>

    <!-- 右侧详情面板 -->
    <Transition name="slide-left">
      <div v-if="showDetail && currentGroup" class="detail-panel">
        <div class="detail-header">
          <span>群聊信息</span>
          <button class="close-btn" @click="showDetail = false">×</button>
        </div>
        <div class="detail-body">
          <div class="detail-section">
            <div class="section-title">主持人</div>
            <div class="member-item">
              <div class="member-avatar" :style="getAvatarStyle(currentGroup.hostAgentId)">
                {{ currentGroup.hostAgentName?.charAt(0) }}
              </div>
              <div class="member-name">{{ currentGroup.hostAgentName }}</div>
              <span class="member-tag">主持人</span>
            </div>
          </div>
          <div class="detail-section">
            <div class="section-title">参与者 · {{ currentGroup.participants.length }}</div>
            <div v-for="p in currentGroup.participants" :key="p.agentId" class="member-item">
              <div class="member-avatar" :style="getAvatarStyle(p.agentId)">
                {{ p.name?.charAt(0) }}
              </div>
              <div class="member-name">{{ p.name }}</div>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 新建群聊弹窗 -->
    <div v-if="showCreateGroup" class="modal-overlay" @click.self="showCreateGroup = false">
      <div class="modal">
        <div class="modal-header">
          <span>创建群聊</span>
          <button class="close-btn" @click="showCreateGroup = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-item">
            <label>群聊名称</label>
            <input v-model="newGroupName" type="text" placeholder="输入群聊名称" />
          </div>
          <div class="form-item">
            <label>选择主持人</label>
            <div class="agent-select">
              <div
                v-for="agent in agents"
                :key="agent.id"
                :class="['agent-option', { selected: newGroupHost === agent.id }]"
                @click="newGroupHost = agent.id"
              >
                <div class="agent-avatar" :style="getAvatarStyle(agent.id)">
                  {{ agent.name?.charAt(0) }}
                </div>
                <span>{{ agent.name }}</span>
              </div>
            </div>
          </div>
          <div class="form-item">
            <label>选择参与者</label>
            <div class="agent-select multi">
              <div
                v-for="agent in agents.filter(a => a.id !== newGroupHost)"
                :key="agent.id"
                :class="['agent-option', { selected: newGroupParticipants.includes(agent.id) }]"
                @click="toggleParticipant(agent.id)"
              >
                <div class="agent-avatar" :style="getAvatarStyle(agent.id)">
                  {{ agent.name?.charAt(0) }}
                </div>
                <span>{{ agent.name }}</span>
                <div v-if="newGroupParticipants.includes(agent.id)" class="check">✓</div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="showCreateGroup = false">取消</button>
          <button class="btn-confirm" :disabled="!canCreateGroup" @click="createGroup">创建</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'
import { agentApi } from '../api'
import { createGatewayClient, extractText } from '../utils/gateway-ws'
import { renderMessageContent } from '../utils/markdown'
import type { Agent, Message, Participant } from '../chat/types'

// ==================== Types ====================

interface GroupChat {
  id: string
  name: string
  hostAgentId: string
  hostAgentName: string
  participants: Participant[]
  lastMessage?: string
  lastTime?: number
}

interface AgentConv {
  id: string
  name: string
  lastMessage?: string
  lastTime?: number
  unread?: number
}

// ==================== State ====================

const userStore = useUserStore()
const agents = ref<Agent[]>([])
const agentConvs = ref<AgentConv[]>([])
const groups = ref<GroupChat[]>([])

const activeNav = ref<'chat' | 'group'>('chat')
const searchQuery = ref('')
const currentType = ref<'single' | 'group' | null>(null)
const selectedId = ref<string>('')
const showDetail = ref(false)
const showCreateGroup = ref(false)
const showSettings = ref(false)

const messagesMap = ref<Map<string, Message[]>>(new Map())
const messages = ref<Message[]>([])

const isStreaming = ref(false)
const streamContent = ref('')
const inputMessage = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const messagesRef = ref<HTMLElement | null>(null)

const newGroupName = ref('')
const newGroupHost = ref('')
const newGroupParticipants = ref<string[]>([])

let client: ReturnType<typeof createGatewayClient> | null = null
const sessionMap = ref<Map<string, string>>(new Map())

// ==================== Computed ====================

const unreadCount = computed(() => agentConvs.value.reduce((acc, c) => acc + (c.unread || 0), 0))

const filteredAgents = computed(() => {
  if (!searchQuery.value) return agentConvs.value
  const q = searchQuery.value.toLowerCase()
  return agentConvs.value.filter(a => a.name.toLowerCase().includes(q))
})

const filteredGroups = computed(() => {
  if (!searchQuery.value) return groups.value
  const q = searchQuery.value.toLowerCase()
  return groups.value.filter(g => g.name.toLowerCase().includes(q))
})

const currentAgent = computed(() => agents.value.find(a => a.id === selectedId.value))
const currentGroup = computed(() => groups.value.find(g => g.id === selectedId.value))
const currentConversation = computed(() => currentType.value !== null)
const currentTitle = computed(() => {
  if (currentType.value === 'single') return currentAgent.value?.name || '对话'
  if (currentType.value === 'group') return currentGroup.value?.name || '群聊'
  return ''
})

const canSend = computed(() => inputMessage.value.trim() && !isStreaming.value)
const canCreateGroup = computed(() => newGroupHost.value && newGroupParticipants.value.length > 0)

// ==================== Colors ====================

const avatarColors = [
  'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
  'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)',
  'linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)',
  'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)',
]

function getAvatarStyle(id?: string): Record<string, string> {
  if (!id) return { background: avatarColors[0] }
  const hash = id.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0)
  return { background: avatarColors[hash % avatarColors.length] }
}

// ==================== Methods ====================

function selectConversation(type: 'single' | 'group', id: string) {
  currentType.value = type
  selectedId.value = id

  const key = type === 'single' ? `single-${id}` : `group-${id}`
  messages.value = messagesMap.value.get(key) || []
  scrollToBottom(false)

  ensureSession(key, type === 'single' ? id : currentGroup.value!.hostAgentId, type === 'group')
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
  } catch (e) {
    console.error('Subscribe failed:', e)
  }
}

function getSenderName(msg: Message): string {
  if (msg.sourceName) return msg.sourceName
  if (msg.role === 'user') return userStore.user?.displayName || '你'
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
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function formatShortTime(timestamp?: number): string {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function autoResize() {
  const ta = textareaRef.value
  if (ta) {
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 150) + 'px'
  }
}

async function sendMessage() {
  if (!canSend.value || !client) return

  const content = inputMessage.value.trim()
  inputMessage.value = ''
  autoResize()

  const key = currentType.value === 'single' ? `single-${selectedId.value}` : `group-${selectedId.value}`

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

  // Update conversation preview
  if (currentType.value === 'single') {
    const conv = agentConvs.value.find(c => c.id === selectedId.value)
    if (conv) {
      conv.lastMessage = content.slice(0, 30)
      conv.lastTime = Date.now()
    }
  } else if (currentGroup.value) {
    currentGroup.value.lastMessage = content.slice(0, 30)
    currentGroup.value.lastTime = Date.now()
  }

  let sessionKey = sessionMap.value.get(key)
  if (!sessionKey) {
    await ensureSession(key, currentType.value === 'single' ? selectedId.value : currentGroup.value!.hostAgentId, currentType.value === 'group')
    sessionKey = sessionMap.value.get(key)
  }
  if (!sessionKey) return

  let messageToSend = content
  if (currentType.value === 'group' && currentGroup.value) {
    const group = currentGroup.value
    const participantInfo = group.participants.filter(p => p.enabled).map(p => `- ${p.name}(${p.agentId})`).join('\n')
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
  } catch (e: any) {
    console.error('Send failed:', e)
    isStreaming.value = false
    ElMessage.error('发送失败: ' + e.message)
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
  if (idx >= 0) newGroupParticipants.value.splice(idx, 1)
  else newGroupParticipants.value.push(agentId)
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

  selectConversation('group', group.id)
  saveToStorage()
}

function saveToStorage() {
  const data = { groups: groups.value, messages: Object.fromEntries(messagesMap.value) }
  localStorage.setItem('feishu-chat-data', JSON.stringify(data))
}

function loadFromStorage() {
  try {
    const raw = localStorage.getItem('feishu-chat-data')
    if (raw) {
      const data = JSON.parse(raw)
      groups.value = data.groups || []
      if (data.messages) messagesMap.value = new Map(Object.entries(data.messages))
    }
  } catch (e) {
    console.error('Load failed:', e)
  }
}

function onChatEvent(evt: any) {
  if (evt.event !== 'chat') return
  const payload = evt.payload
  const sessionKey = payload.sessionKey

  let convKey: string | null = null
  for (const [key, sk] of sessionMap.value.entries()) {
    if (sk === sessionKey) { convKey = key; break }
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

      const currentKey = currentType.value === 'single' ? `single-${selectedId.value}` : `group-${selectedId.value}`
      if (convKey === currentKey) {
        messages.value = [...msgs]
      }

      // Update preview
      if (convKey.startsWith('single-')) {
        const agentId = convKey.replace('single-', '')
        const conv = agentConvs.value.find(c => c.id === agentId)
        if (conv) {
          conv.lastMessage = text.slice(0, 30)
          conv.lastTime = Date.now()
        }
      } else {
        const groupId = convKey.replace('group-', '')
        const group = groups.value.find(g => g.id === groupId)
        if (group) {
          group.lastMessage = text.slice(0, 30)
          group.lastTime = Date.now()
        }
      }
    }
    streamContent.value = ''
    isStreaming.value = false
    scrollToBottom()
    saveToStorage()
  } else if (payload.state === 'error') {
    streamContent.value = ''
    isStreaming.value = false
    ElMessage.error(payload.errorMessage || '错误')
  }
}

// ==================== Lifecycle ====================

onMounted(async () => {
  try {
    const res = await agentApi.list()
    if (res.data.success) {
      agents.value = res.data.data || []
      agentConvs.value = agents.value.map(a => ({
        id: a.id,
        name: a.name || a.id,
        lastMessage: '',
        lastTime: 0,
        unread: 0
      }))
    }
  } catch (e) {
    console.error('Load agents failed:', e)
  }

  loadFromStorage()

  try {
    const res = await (await import('../api')).chatApi.getConfig()
    if (res.data.success) {
      const { gatewayUrl, gatewayToken } = res.data.data
      client = createGatewayClient({
        url: gatewayUrl,
        token: gatewayToken,
        onHello: () => console.log('[FeishuChat] Connected'),
        onEvent: onChatEvent,
        onClose: () => console.log('[FeishuChat] Disconnected')
      })
      client.start()
    }
  } catch (e) {
    console.error('Connect gateway failed:', e)
  }
})

onUnmounted(() => {
  saveToStorage()
  client?.stop()
})

watch(messages, () => scrollToBottom())
</script>

<style scoped>
.feishu-chat {
  display: flex;
  height: 100%;
  background: #f5f6f7;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

/* 左侧导航栏 */
.sidebar {
  width: 64px;
  background: linear-gradient(180deg, #3370ff 0%, #2b5fe8 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0;
}

.sidebar-header {
  margin-bottom: 24px;
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
}

.nav-items {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-item {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.nav-item.active {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.nav-badge {
  position: absolute;
  top: 0;
  right: 0;
  min-width: 18px;
  height: 18px;
  border-radius: 9px;
  background: #ff4d4f;
  color: #fff;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 5px;
}

.sidebar-footer {
  margin-top: auto;
}

/* 会话列表 */
.conversation-panel {
  width: 260px;
  background: #fff;
  border-right: 1px solid #e5e6e8;
  display: flex;
  flex-direction: column;
}

.panel-header {
  padding: 16px;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f5f6f7;
  border-radius: 8px;
}

.search-box svg {
  color: #8f959e;
  flex-shrink: 0;
}

.search-box input {
  flex: 1;
  border: none;
  background: none;
  font-size: 14px;
  color: #1f2329;
}

.search-box input::placeholder {
  color: #8f959e;
}

.search-box input:focus {
  outline: none;
}

.panel-tabs {
  display: flex;
  padding: 0 16px;
  border-bottom: 1px solid #e5e6e8;
}

.tab {
  padding: 12px 16px;
  font-size: 14px;
  color: #8f959e;
  cursor: pointer;
  position: relative;
  transition: color 0.2s;
}

.tab:hover {
  color: #1f2329;
}

.tab.active {
  color: #3370ff;
  font-weight: 500;
}

.tab.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 16px;
  right: 16px;
  height: 2px;
  background: #3370ff;
  border-radius: 1px;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.create-group-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  margin: 4px 8px;
  border-radius: 8px;
  color: #3370ff;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.create-group-btn:hover {
  background: #f5f6f7;
}

.conversation-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.conversation-item:hover {
  background: #f5f6f7;
}

.conversation-item.active {
  background: #e8f3ff;
}

.conv-avatar {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  flex-shrink: 0;
}

.conv-avatar.group {
  background: linear-gradient(135deg, #3370ff 0%, #2b5fe8 100%);
}

.group-icon {
  font-size: 22px;
  font-weight: 400;
}

.conv-info {
  flex: 1;
  min-width: 0;
}

.conv-name {
  font-size: 15px;
  font-weight: 500;
  color: #1f2329;
  margin-bottom: 4px;
}

.conv-preview {
  font-size: 13px;
  color: #8f959e;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.conv-time {
  font-size: 12px;
  color: #8f959e;
}

.conv-unread {
  min-width: 18px;
  height: 18px;
  border-radius: 9px;
  background: #3370ff;
  color: #fff;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 5px;
}

/* 聊天主区域 */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-header {
  height: 60px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e5e6e8;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
}

.header-avatar.group {
  background: linear-gradient(135deg, #3370ff 0%, #2b5fe8 100%);
}

.header-info {
  display: flex;
  flex-direction: column;
}

.header-name {
  font-size: 16px;
  font-weight: 600;
  color: #1f2329;
}

.header-desc {
  font-size: 12px;
  color: #8f959e;
  margin-top: 2px;
}

.header-btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8f959e;
  transition: all 0.2s;
}

.header-btn:hover {
  background: #f5f6f7;
  color: #1f2329;
}

/* 消息区域 */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.welcome {
  text-align: center;
  padding: 60px 20px;
}

.welcome-avatar {
  width: 72px;
  height: 72px;
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  color: #fff;
  font-size: 28px;
  font-weight: 600;
}

.welcome-title {
  font-size: 20px;
  font-weight: 600;
  color: #1f2329;
  margin-bottom: 8px;
}

.welcome-desc {
  font-size: 14px;
  color: #8f959e;
}

.message-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  animation: fadeIn 0.3s ease;
}

.message-row.user {
  flex-direction: row-reverse;
}

.msg-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.msg-content {
  max-width: 70%;
}

.message-row.user .msg-content {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.msg-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.message-row.user .msg-header {
  flex-direction: row-reverse;
}

.msg-sender {
  font-size: 13px;
  font-weight: 500;
  color: #1f2329;
}

.msg-time {
  font-size: 12px;
  color: #8f959e;
}

.typing-dots {
  display: inline-flex;
  gap: 3px;
}

.typing-dots i {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #8f959e;
  animation: typing 1s ease infinite;
}

.typing-dots i:nth-child(2) { animation-delay: 0.2s; }
.typing-dots i:nth-child(3) { animation-delay: 0.4s; }

.msg-text {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
}

.message-row.assistant .msg-text {
  background: #fff;
  color: #1f2329;
  border-top-left-radius: 4px;
}

.message-row.user .msg-text {
  background: linear-gradient(135deg, #3370ff 0%, #2b5fe8 100%);
  color: #fff;
  border-top-right-radius: 4px;
}

/* 输入区域 */
.input-area {
  padding: 16px 20px;
  background: #fff;
  border-top: 1px solid #e5e6e8;
}

.input-box {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 8px 12px;
  background: #f5f6f7;
  border-radius: 12px;
}

.input-tools {
  display: flex;
  gap: 4px;
}

.tool-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8f959e;
  transition: all 0.2s;
}

.tool-btn:hover {
  background: #e5e6e8;
  color: #1f2329;
}

.input-box textarea {
  flex: 1;
  border: none;
  background: none;
  font-size: 14px;
  line-height: 1.5;
  color: #1f2329;
  resize: none;
  min-height: 24px;
  max-height: 150px;
  font-family: inherit;
}

.input-box textarea::placeholder {
  color: #8f959e;
}

.input-box textarea:focus {
  outline: none;
}

.send-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: #e5e6e8;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8f959e;
  transition: all 0.2s;
}

.send-btn.active {
  background: linear-gradient(135deg, #3370ff 0%, #2b5fe8 100%);
  color: #fff;
}

.send-btn.active:hover {
  transform: scale(1.05);
}

/* 空状态 */
.empty-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #8f959e;
}

.empty-icon {
  opacity: 0.3;
  margin-bottom: 16px;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2329;
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 14px;
}

/* 右侧详情面板 */
.detail-panel {
  width: 280px;
  background: #fff;
  border-left: 1px solid #e5e6e8;
  display: flex;
  flex-direction: column;
}

.detail-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e5e6e8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  color: #1f2329;
}

.close-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 20px;
  color: #8f959e;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background: #f5f6f7;
}

.detail-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.detail-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 12px;
  font-weight: 500;
  color: #8f959e;
  margin-bottom: 12px;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
}

.member-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
}

.member-name {
  flex: 1;
  font-size: 14px;
  color: #1f2329;
}

.member-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: #e8f3ff;
  color: #3370ff;
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

.modal {
  width: 420px;
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  animation: slideUp 0.3s ease;
}

.modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid #e5e6e8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 16px;
  font-weight: 600;
  color: #1f2329;
}

.modal-body {
  padding: 24px;
}

.form-item {
  margin-bottom: 20px;
}

.form-item label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #1f2329;
  margin-bottom: 8px;
}

.form-item input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #e5e6e8;
  border-radius: 8px;
  font-size: 14px;
  color: #1f2329;
  transition: border-color 0.2s;
}

.form-item input:focus {
  outline: none;
  border-color: #3370ff;
}

.agent-select {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.agent-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid #e5e6e8;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.agent-option:hover {
  border-color: #3370ff;
}

.agent-option.selected {
  border-color: #3370ff;
  background: #e8f3ff;
}

.agent-option .agent-avatar {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}

.agent-option span {
  font-size: 13px;
  color: #1f2329;
}

.agent-option .check {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #3370ff;
  color: #fff;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid #e5e6e8;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn-cancel {
  padding: 8px 20px;
  border: none;
  border-radius: 8px;
  background: #f5f6f7;
  color: #1f2329;
  font-size: 14px;
  cursor: pointer;
}

.btn-cancel:hover {
  background: #e5e6e8;
}

.btn-confirm {
  padding: 8px 20px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #3370ff 0%, #2b5fe8 100%);
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}

.btn-confirm:hover {
  opacity: 0.9;
}

.btn-confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 动画 */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

@keyframes typing {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

.slide-left-enter-active,
.slide-left-leave-active {
  transition: all 0.3s ease;
}

.slide-left-enter-from,
.slide-left-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

/* 滚动条 */
.messages-area::-webkit-scrollbar,
.conversation-list::-webkit-scrollbar,
.detail-body::-webkit-scrollbar {
  width: 6px;
}

.messages-area::-webkit-scrollbar-thumb,
.conversation-list::-webkit-scrollbar-thumb,
.detail-body::-webkit-scrollbar-thumb {
  background: #d8d8d8;
  border-radius: 3px;
}

.messages-area::-webkit-scrollbar-thumb:hover,
.conversation-list::-webkit-scrollbar-thumb:hover,
.detail-body::-webkit-scrollbar-thumb:hover {
  background: #bbb;
}
</style>