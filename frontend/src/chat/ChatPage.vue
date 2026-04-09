<template>
  <div class="chat-page">
    <!-- 左侧会话列表 -->
    <ConversationList
      :agents="agents"
      :selected-id="selectedConversationId"
      :single-conversations="singleConversations"
      :group-conversations="groupConversations"
      @select="handleSelectConversation"
      @create-group="showCreateGroupDialog = true"
    />

    <!-- 右侧聊天区域 -->
    <ChatArea
      :conversation="currentConversation"
      :messages="currentMessages"
      :is-streaming="isStreaming"
      :stream-content="streamContent"
      :is-sending="isSending"
      @send="handleSendMessage"
    />

    <!-- 新建群聊弹窗 -->
    <el-dialog
      v-model="showCreateGroupDialog"
      title="新建群聊"
      width="480px"
      :close-on-click-modal="false"
      class="create-group-dialog"
    >
      <div class="create-group-form">
        <div class="form-item">
          <label>群聊名称</label>
          <el-input v-model="newGroupName" placeholder="输入群聊名称" />
        </div>

        <div class="form-item">
          <label>选择主持人</label>
          <el-select v-model="newGroupHost" placeholder="选择主持人" style="width: 100%;">
            <el-option
              v-for="agent in agents"
              :key="agent.id"
              :label="agent.name || agent.id"
              :value="agent.id"
            >
              <div class="agent-option">
                <div class="agent-avatar" :style="getAvatarStyle(agent.id)">
                  {{ agent.name?.charAt(0) || '?' }}
                </div>
                <div class="agent-info">
                  <span class="name">{{ agent.name || agent.id }}</span>
                  <span class="model">{{ agent.modelName }}</span>
                </div>
              </div>
            </el-option>
          </el-select>
        </div>

        <div class="form-item">
          <label>选择参与者</label>
          <div class="participant-select">
            <div
              v-for="agent in agents.filter(a => a.id !== newGroupHost)"
              :key="agent.id"
              :class="['participant-card', { selected: newGroupParticipants.includes(agent.id) }]"
              @click="toggleParticipant(agent.id)"
            >
              <div class="agent-avatar" :style="getAvatarStyle(agent.id)">
                {{ agent.name?.charAt(0) || '?' }}
              </div>
              <span class="name">{{ agent.name || agent.id }}</span>
              <el-icon v-if="newGroupParticipants.includes(agent.id)" class="check-icon"><Check /></el-icon>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="showCreateGroupDialog = false">取消</el-button>
        <el-button type="primary" @click="createGroup" :disabled="!canCreateGroup">
          创建群聊
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Check } from '@element-plus/icons-vue'
import ConversationList from './components/ConversationList.vue'
import ChatArea from './components/ChatArea.vue'
import { agentApi } from '../api'
import {
  GatewayBrowserClient,
  GatewayHelloOk,
  extractText,
  createGatewayClient
} from '../utils/gateway-ws'
import { renderMessageContent } from '../utils/markdown'
import type { Agent, SingleConversation, GroupConversation, Conversation, Message, Participant } from './types'

// ==================== State ====================

const agents = ref<Agent[]>([])
const selectedConversationId = ref<string>('')

// 单聊会话
const singleConversations = ref<SingleConversation[]>([])
// 群聊会话
const groupConversations = ref<GroupConversation[]>([])

// 消息存储
const messagesMap = ref<Map<string, Message[]>>(new Map())

// 当前会话的消息
const currentMessages = ref<Message[]>([])

// 流式输出
const isStreaming = ref(false)
const streamContent = ref('')
const isSending = ref(false)

// Gateway 客户端
let client: GatewayBrowserClient | null = null
let sessionKeyMap = ref<Map<string, string>>(new Map())
let isManualStop = false

// 新建群聊
const showCreateGroupDialog = ref(false)
const newGroupName = ref('')
const newGroupHost = ref('')
const newGroupParticipants = ref<string[]>([])

// ==================== Computed ====================

const currentConversation = computed(() => {
  const single = singleConversations.value.find(c => c.id === selectedConversationId.value)
  if (single) return single
  return groupConversations.value.find(c => c.id === selectedConversationId.value) || null
})

const canCreateGroup = computed(() => {
  return newGroupHost.value && newGroupParticipants.value.length > 0
})

// ==================== 头像颜色 ====================

const avatarColors: Record<string, string> = {}
const colorPalette = [
  'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
]

function getAvatarStyle(agentId: string): Record<string, string> {
  if (!avatarColors[agentId]) {
    const idx = Object.keys(avatarColors).length
    avatarColors[agentId] = colorPalette[idx % colorPalette.length]
  }
  return { background: avatarColors[agentId] }
}

// ==================== 初始化 ====================

onMounted(async () => {
  await loadAgents()
  await connectGateway()
  loadConversationsFromStorage()
})

onUnmounted(() => {
  saveConversationsToStorage()
  if (client) {
    isManualStop = true
    client.stop()
  }
})

async function loadAgents() {
  try {
    const res = await agentApi.list()
    if (res.data.success) {
      agents.value = res.data.data || []
      // 初始化单聊会话
      singleConversations.value = agents.value.map(agent => ({
        id: `single-${agent.id}`,
        type: 'single' as const,
        agentId: agent.id,
        agentName: agent.name || agent.id,
        sessionKey: '',
        lastMessage: '',
        lastMessageTime: 0
      }))
    }
  } catch (err) {
    console.error('Failed to load agents:', err)
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
          console.log('[ChatPage] Gateway connected')
        },
        onEvent: onChatEvent,
        onClose: (info) => {
          console.log('[ChatPage] Gateway closed:', info)
          if (!isManualStop) {
            ElMessage.warning('Gateway 连接已断开')
          }
        }
      })

      client.start()
    }
  } catch (err: any) {
    console.error('Failed to connect gateway:', err)
  }
}

// ==================== 会话管理 ====================

function handleSelectConversation(conv: Conversation) {
  selectedConversationId.value = conv.id

  // 加载该会话的消息
  const messages = messagesMap.value.get(conv.id) || []
  currentMessages.value = messages

  // 确保 session 已创建
  ensureSession(conv)
}

async function ensureSession(conv: Conversation) {
  if (!client?.connected) return

  let sessionKey = sessionKeyMap.value.get(conv.id)
  if (sessionKey) return

  if (conv.type === 'single') {
    const sessionId = crypto.randomUUID()
    sessionKey = `agent:${conv.agentId}:webchat:${sessionId}`
  } else {
    const sessionId = crypto.randomUUID()
    sessionKey = `agent:${conv.hostAgentId}:groupchat:${sessionId}`
  }

  sessionKeyMap.value.set(conv.id, sessionKey)

  // 订阅 session
  try {
    await client.request('sessions.subscribe', {
      keys: [sessionKey]
    })
    console.log('[ChatPage] Subscribed to session:', sessionKey)
  } catch (err) {
    console.error('[ChatPage] Failed to subscribe:', err)
  }
}

// ==================== 发送消息 ====================

async function handleSendMessage(content: string) {
  if (!currentConversation.value || !client) return

  const conv = currentConversation.value

  // 添加用户消息
  const userMessage: Message = {
    id: crypto.randomUUID(),
    role: 'user',
    content: [{ type: 'text', text: content }],
    timestamp: Date.now()
  }

  const messages = messagesMap.value.get(conv.id) || []
  messages.push(userMessage)
  messagesMap.value.set(conv.id, [...messages])
  currentMessages.value = [...messages]

  // 更新会话最后消息
  if (conv.type === 'single') {
    const singleConv = singleConversations.value.find(c => c.id === conv.id)
    if (singleConv) {
      singleConv.lastMessage = content.slice(0, 30)
      singleConv.lastMessageTime = Date.now()
    }
  } else {
    const groupConv = groupConversations.value.find(c => c.id === conv.id)
    if (groupConv) {
      groupConv.lastMessage = content.slice(0, 30)
      groupConv.lastMessageTime = Date.now()
    }
  }

  // 获取 sessionKey
  let sessionKey = sessionKeyMap.value.get(conv.id)
  if (!sessionKey) {
    await ensureSession(conv)
    sessionKey = sessionKeyMap.value.get(conv.id)
  }
  if (!sessionKey) return

  isSending.value = true
  isStreaming.value = true
  streamContent.value = ''

  // 构建消息
  let messageToSend = content
  if (conv.type === 'group') {
    const groupConv = conv as GroupConversation
    const participantInfo = groupConv.participants
      .filter(p => p.enabled)
      .map(p => `- ${p.name}(${p.agentId})`)
      .join('\n')

    messageToSend = `【群聊上下文】
主持人：${groupConv.hostAgentName}
参与者：
${participantInfo}

【用户问题】
${content}

请根据问题决定需要哪些 Agent 参与，并使用 sessions_send 工具与他们讨论。`
  }

  try {
    await client.request('chat.send', {
      sessionKey,
      message: messageToSend,
      deliver: false,
      idempotencyKey: crypto.randomUUID()
    })
  } catch (err: any) {
    console.error('Failed to send message:', err)
    isStreaming.value = false
    ElMessage.error('发送失败: ' + err.message)
  } finally {
    isSending.value = false
  }
}

// ==================== 接收消息 ====================

function onChatEvent(evt: any) {
  if (evt.event !== 'chat') return

  const payload = evt.payload as any
  const sessionKey = payload.sessionKey

  // 找到对应的会话
  let convId: string | null = null
  for (const [id, key] of sessionKeyMap.value.entries()) {
    if (key === sessionKey) {
      convId = id
      break
    }
  }

  if (!convId) return

  if (payload.state === 'delta') {
    const next = extractText(payload.message)
    if (typeof next === 'string') {
      streamContent.value = next
    }
  } else if (payload.state === 'final') {
    const text = extractText(payload.message) || streamContent.value
    if (text?.trim()) {
      // 添加助手消息
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: [{ type: 'text', text }],
        timestamp: Date.now()
      }

      const messages = messagesMap.value.get(convId) || []
      messages.push(assistantMessage)
      messagesMap.value.set(convId, [...messages])

      if (convId === selectedConversationId.value) {
        currentMessages.value = [...messages]
      }

      // 更新会话最后消息
      const singleConv = singleConversations.value.find(c => c.id === convId)
      if (singleConv) {
        singleConv.lastMessage = text.slice(0, 30)
        singleConv.lastMessageTime = Date.now()
      }

      const groupConv = groupConversations.value.find(c => c.id === convId)
      if (groupConv) {
        groupConv.lastMessage = text.slice(0, 30)
        groupConv.lastMessageTime = Date.now()
      }
    }
    streamContent.value = ''
    isStreaming.value = false

    // 保存到 localStorage
    saveConversationsToStorage()
  } else if (payload.state === 'error') {
    streamContent.value = ''
    isStreaming.value = false
    ElMessage.error(payload.errorMessage || '发生错误')
  }
}

// ==================== 新建群聊 ====================

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
    return {
      agentId: id,
      name: agent?.name || id,
      enabled: true
    }
  })

  const groupConv: GroupConversation = {
    id: `group-${crypto.randomUUID()}`,
    type: 'group',
    name: newGroupName.value || `${host?.name || '群聊'}的群`,
    hostAgentId: newGroupHost.value,
    hostAgentName: host?.name || newGroupHost.value,
    participants,
    sessionKey: '',
    lastMessage: '',
    lastMessageTime: 0
  }

  groupConversations.value.unshift(groupConv)

  // 重置表单
  showCreateGroupDialog.value = false
  newGroupName.value = ''
  newGroupHost.value = ''
  newGroupParticipants.value = []

  // 选中新群聊
  selectedConversationId.value = groupConv.id
  currentMessages.value = []

  ElMessage.success('群聊创建成功')

  // 保存
  saveConversationsToStorage()
}

// ==================== 持久化 ====================

const STORAGE_KEY = 'chat_conversations'

interface SavedConversation {
  id: string
  type: 'single' | 'group'
  name?: string
  hostAgentId?: string
  hostAgentName?: string
  participants?: Participant[]
  messages: Message[]
  lastMessage?: string
  lastMessageTime?: number
}

function saveConversationsToStorage() {
  const data: SavedConversation[] = []

  // 保存群聊（单聊不需要保存，每次从 agents 初始化）
  for (const conv of groupConversations.value) {
    const messages = messagesMap.value.get(conv.id) || []
    data.push({
      id: conv.id,
      type: 'group',
      name: conv.name,
      hostAgentId: conv.hostAgentId,
      hostAgentName: conv.hostAgentName,
      participants: conv.participants,
      messages: messages.slice(-50),
      lastMessage: conv.lastMessage,
      lastMessageTime: conv.lastMessageTime
    })
  }

  // 也保存单聊的消息
  for (const conv of singleConversations.value) {
    const messages = messagesMap.value.get(conv.id) || []
    if (messages.length > 0) {
      data.push({
        id: conv.id,
        type: 'single',
        messages: messages.slice(-50),
        lastMessage: conv.lastMessage,
        lastMessageTime: conv.lastMessageTime
      })
    }
  }

  localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
}

function loadConversationsFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return

    const data = JSON.parse(raw) as SavedConversation[]

    for (const saved of data) {
      if (saved.type === 'group') {
        groupConversations.value.push({
          id: saved.id,
          type: 'group',
          name: saved.name || '群聊',
          hostAgentId: saved.hostAgentId || '',
          hostAgentName: saved.hostAgentName || '',
          participants: saved.participants || [],
          sessionKey: '',
          lastMessage: saved.lastMessage,
          lastMessageTime: saved.lastMessageTime
        })
      }

      // 恢复消息
      if (saved.messages?.length > 0) {
        messagesMap.value.set(saved.id, saved.messages)
      }
    }
  } catch (err) {
    console.error('Failed to load conversations:', err)
  }
}
</script>

<style scoped>
.chat-page {
  height: 100%;
  display: flex;
  background: #f5f5f5;
}

/* 新建群聊弹窗 */
.create-group-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-item label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
}

.agent-option {
  display: flex;
  align-items: center;
  gap: 10px;
}

.agent-option .agent-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}

.agent-option .agent-info {
  display: flex;
  flex-direction: column;
}

.agent-option .name {
  font-size: 14px;
  color: #333;
}

.agent-option .model {
  font-size: 11px;
  color: #999;
}

.participant-select {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.participant-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px;
  border-radius: 12px;
  border: 2px solid #f0f0f0;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  min-width: 80px;
}

.participant-card:hover {
  border-color: #667eea;
  background: rgba(102, 126, 234, 0.05);
}

.participant-card.selected {
  border-color: #667eea;
  background: rgba(102, 126, 234, 0.1);
}

.participant-card .agent-avatar {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

.participant-card .name {
  font-size: 13px;
  color: #333;
}

.participant-card .check-icon {
  position: absolute;
  top: 6px;
  right: 6px;
  color: #667eea;
  font-size: 16px;
}
</style>