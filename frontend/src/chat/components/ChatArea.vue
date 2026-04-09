<template>
  <div class="chat-area">
    <!-- 空状态 -->
    <div v-if="!conversation" class="empty-state">
      <div class="empty-icon">
        <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
      </div>
      <p class="empty-text">选择一个会话开始聊天</p>
    </div>

    <!-- 聊天内容 -->
    <template v-else>
      <!-- 顶部信息栏 -->
      <div class="chat-header">
        <div class="header-left">
          <template v-if="conversation.type === 'single'">
            <div class="header-avatar" :style="getAvatarStyle(conversation.agentId)">
              {{ conversation.agentName?.charAt(0) || '?' }}
            </div>
            <div class="header-info">
              <span class="header-name">{{ conversation.agentName }}</span>
              <span class="header-status">
                <span class="status-dot online"></span>
                在线
              </span>
            </div>
          </template>
          <template v-else>
            <div class="group-avatars">
              <div
                v-for="(p, idx) in groupParticipants.slice(0, 3)"
                :key="p.agentId"
                class="header-avatar small"
                :style="getAvatarStyle(p.agentId)"
              >
                {{ p.name?.charAt(0) || '?' }}
              </div>
              <div v-if="groupParticipants.length > 3" class="header-avatar small more">
                +{{ groupParticipants.length - 3 }}
              </div>
            </div>
            <div class="header-info">
              <span class="header-name">{{ conversation.name || '群聊' }}</span>
              <span class="header-members">
                {{ conversation.hostAgentName }}、{{ groupParticipants.map(p => p.name).join('、') }}
              </span>
            </div>
          </template>
        </div>
        <div class="header-actions">
          <el-button text circle @click="showInfo = true">
            <el-icon><InfoFilled /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- 消息区域 -->
      <div class="messages-container" ref="messagesRef">
        <div class="messages-inner">
          <TransitionGroup name="message" tag="div" class="messages-list">
            <template v-for="(group, gIdx) in groupedMessages" :key="gIdx">
              <!-- 时间分隔 -->
              <div class="time-divider">
                <span>{{ formatGroupTime(group.timestamp) }}</span>
              </div>

              <!-- 消息 -->
              <div
                v-for="msg in group.messages"
                :key="msg.id"
                :class="['message-item', msg.role]"
              >
                <!-- 用户消息 -->
                <template v-if="msg.role === 'user'">
                  <div class="message-bubble user">
                    <div class="message-content" v-html="renderMarkdown(getMessageText(msg))"></div>
                  </div>
                </template>

                <!-- Agent 消息 -->
                <template v-else>
                  <div class="agent-avatar" :style="getAvatarStyle(msg.sourceAgent || conversation.agentId)">
                    {{ msg.sourceName?.charAt(0) || conversation.agentName?.charAt(0) || '?' }}
                  </div>
                  <div class="message-bubble agent">
                    <div v-if="msg.sourceName" class="sender-name">{{ msg.sourceName }}</div>
                    <div class="message-content" v-html="renderMarkdown(getMessageText(msg))"></div>
                  </div>
                </template>
              </div>
            </template>

            <!-- 流式输出 -->
            <div v-if="isStreaming && streamContent" class="message-item assistant streaming">
              <div class="agent-avatar" :style="getAvatarStyle(conversation.agentId)">
                {{ conversation.agentName?.charAt(0) || '?' }}
              </div>
              <div class="message-bubble agent">
                <div class="message-content" v-html="renderMarkdown(streamContent)"></div>
                <span class="typing-indicator">
                  <span></span><span></span><span></span>
                </span>
              </div>
            </div>
          </TransitionGroup>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="input-area">
        <div class="input-container">
          <div class="input-tools">
            <el-button text circle size="small" title="表情">
              <span style="font-size: 18px;">😊</span>
            </el-button>
          </div>
          <div class="input-wrapper">
            <textarea
              ref="textareaRef"
              v-model="inputMessage"
              placeholder="输入消息..."
              rows="1"
              @keydown="handleKeydown"
              @input="autoResize"
            ></textarea>
          </div>
          <div class="input-actions">
            <button
              class="send-btn"
              :class="{ active: canSend }"
              :disabled="!canSend"
              @click="sendMessage"
            >
              <svg v-if="!isSending" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
              <span v-else class="loading-spinner"></span>
            </button>
          </div>
        </div>
        <div class="input-hint">Enter 发送 · Shift+Enter 换行</div>
      </div>
    </template>

    <!-- 群聊信息抽屉 -->
    <el-drawer
      v-model="showInfo"
      title="群聊信息"
      direction="rtl"
      size="300px"
    >
      <div class="group-info">
        <div class="info-section">
          <h4>主持人</h4>
          <div class="member-card">
            <div class="avatar" :style="getAvatarStyle(conversation?.hostAgentId)">
              {{ conversation?.hostAgentName?.charAt(0) || '?' }}
            </div>
            <span class="name">{{ conversation?.hostAgentName }}</span>
            <el-tag size="small" type="warning">主持人</el-tag>
          </div>
        </div>
        <div class="info-section">
          <h4>参与者 ({{ groupParticipants.length }})</h4>
          <div
            v-for="p in groupParticipants"
            :key="p.agentId"
            class="member-card"
          >
            <div class="avatar" :style="getAvatarStyle(p.agentId)">
              {{ p.name?.charAt(0) || '?' }}
            </div>
            <span class="name">{{ p.name }}</span>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { InfoFilled } from '@element-plus/icons-vue'
import { renderMessageContent } from '../../utils/markdown'
import type { Conversation, Message, Participant } from '../types'

// ==================== Props & Emits ====================

const props = defineProps<{
  conversation: Conversation | null
  messages: Message[]
  isStreaming: boolean
  streamContent: string
  isSending: boolean
}>()

const emit = defineEmits<{
  (e: 'send', message: string): void
}>()

// ==================== State ====================

const inputMessage = ref('')
const messagesRef = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const showInfo = ref(false)

// ==================== Computed ====================

const groupParticipants = computed((): Participant[] => {
  if (!props.conversation || props.conversation.type !== 'group') return []
  return props.conversation.participants.filter(p => p.enabled)
})

const canSend = computed(() => {
  return inputMessage.value.trim() && !props.isSending
})

// 消息分组（按时间）
const groupedMessages = computed(() => {
  const groups: { timestamp: number; messages: Message[] }[] = []

  for (const msg of props.messages) {
    const timestamp = msg.timestamp || Date.now()
    // 5分钟内的消息分为一组
    const groupTimestamp = Math.floor(timestamp / 300000) * 300000

    let group = groups.find(g => g.timestamp === groupTimestamp)
    if (!group) {
      group = { timestamp: groupTimestamp, messages: [] }
      groups.push(group)
    }
    group.messages.push(msg)
  }

  return groups
})

// ==================== Methods ====================

const avatarColors: Record<string, string> = {}
const colorPalette = [
  'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
]

function getAvatarStyle(agentId?: string): Record<string, string> {
  if (!agentId) return { background: colorPalette[0] }
  if (!avatarColors[agentId]) {
    const idx = Object.keys(avatarColors).length
    avatarColors[agentId] = colorPalette[idx % colorPalette.length]
  }
  return { background: avatarColors[agentId] }
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

function formatGroupTime(timestamp: number): string {
  const date = new Date(timestamp)
  const now = new Date()
  const isToday = date.toDateString() === now.toDateString()

  if (isToday) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }

  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  if (date.toDateString() === yesterday.toDateString()) {
    return '昨天 ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
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
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px'
  }
}

function sendMessage() {
  if (!canSend.value) return
  const content = inputMessage.value.trim()
  inputMessage.value = ''
  autoResize()
  emit('send', content)
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

// 监听消息变化，自动滚动
watch(() => props.messages.length, () => {
  scrollToBottom()
})

watch(() => props.streamContent, () => {
  scrollToBottom()
})

// 切换会话时滚动到底部
watch(() => props.conversation, () => {
  nextTick(() => {
    scrollToBottom(false)
  })
})

onMounted(() => {
  scrollToBottom(false)
})
</script>

<style scoped>
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
  height: 100%;
  overflow: hidden;
}

/* 空状态 */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #ccc;
}

.empty-icon {
  margin-bottom: 16px;
}

.empty-text {
  font-size: 15px;
  color: #999;
}

/* 顶部栏 */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-avatar {
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

.header-avatar.small {
  width: 32px;
  height: 32px;
  font-size: 13px;
  border-radius: 8px;
  margin-left: -8px;
  border: 2px solid #fff;
}

.header-avatar.more {
  background: #e0e0e0 !important;
  color: #666;
  font-size: 11px;
}

.group-avatars {
  display: flex;
}

.header-info {
  display: flex;
  flex-direction: column;
}

.header-name {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #999;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-dot.online {
  background: #52c41a;
}

.header-members {
  font-size: 12px;
  color: #999;
}

/* 消息区域 */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

.messages-inner {
  max-width: 900px;
  margin: 0 auto;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 时间分隔 */
.time-divider {
  text-align: center;
  padding: 16px 0;
}

.time-divider span {
  font-size: 12px;
  color: #999;
  background: #f5f5f5;
  padding: 4px 12px;
  border-radius: 12px;
}

/* 消息项 */
.message-item {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  animation: fadeIn 0.3s ease;
}

.message-item.user {
  flex-direction: row-reverse;
}

.agent-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  flex-shrink: 0;
}

.message-bubble {
  max-width: 70%;
  padding: 10px 14px;
  border-radius: 16px;
  position: relative;
}

.message-bubble.user {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message-bubble.agent {
  background: #fff;
  color: #333;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.sender-name {
  font-size: 12px;
  color: #667eea;
  font-weight: 500;
  margin-bottom: 4px;
}

.message-content {
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

/* 流式输出 */
.message-item.streaming .message-bubble {
  animation: pulse 1.5s ease infinite;
}

.typing-indicator {
  display: inline-flex;
  gap: 4px;
  margin-left: 8px;
}

.typing-indicator span {
  width: 6px;
  height: 6px;
  background: #999;
  border-radius: 50%;
  animation: typing 1s ease infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

/* 输入区域 */
.input-area {
  padding: 12px 20px;
  background: #fff;
  border-top: 1px solid #f0f0f0;
}

.input-container {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 8px 12px;
  background: #f5f5f5;
  border-radius: 20px;
}

.input-tools {
  display: flex;
  gap: 4px;
}

.input-wrapper {
  flex: 1;
}

.input-wrapper textarea {
  width: 100%;
  border: none;
  background: transparent;
  resize: none;
  font-size: 14px;
  line-height: 1.5;
  color: #333;
  font-family: inherit;
  outline: none;
  min-height: 24px;
  max-height: 120px;
}

.input-wrapper textarea::placeholder {
  color: #999;
}

.input-actions {
  display: flex;
  gap: 4px;
}

.send-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: #e0e0e0;
  color: #999;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.send-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}

.send-btn.active:hover {
  transform: scale(1.05);
}

.send-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.input-hint {
  text-align: center;
  font-size: 11px;
  color: #bbb;
  margin-top: 6px;
}

/* 群聊信息 */
.group-info {
  padding: 0 16px;
}

.info-section {
  margin-bottom: 24px;
}

.info-section h4 {
  font-size: 13px;
  color: #999;
  margin: 0 0 12px;
}

.member-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
}

.member-card .avatar {
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

.member-card .name {
  flex: 1;
  font-size: 14px;
  color: #333;
}

/* 动画 */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  }
  50% {
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
  }
}

@keyframes typing {
  0%, 100% {
    transform: translateY(0);
    opacity: 0.5;
  }
  50% {
    transform: translateY(-4px);
    opacity: 1;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 消息过渡 */
.message-enter-active {
  transition: all 0.3s ease;
}

.message-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

/* 滚动条 */
.messages-container::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-thumb {
  background: #ddd;
  border-radius: 3px;
}

.messages-container::-webkit-scrollbar-thumb:hover {
  background: #ccc;
}
</style>