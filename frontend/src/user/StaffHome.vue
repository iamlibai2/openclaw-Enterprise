<template>
  <div class="staff-home">
    <!-- 顶部栏 -->
    <header class="staff-header">
      <div class="header-logo">
        <div class="logo-icon">O</div>
        <span class="logo-text">OpenClaw</span>
      </div>
      <div class="header-user">
        <span class="user-name">{{ userStore.user?.display_name || userStore.user?.username }}</span>
        <el-dropdown trigger="click">
          <div class="user-avatar">
            {{ (userStore.user?.display_name || userStore.user?.username)?.charAt(0) }}
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="showProfile = true">个人资料</el-dropdown-item>
              <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <!-- 主内容区：三栏布局 -->
    <div class="staff-main">
      <!-- 左栏：Agent 和群聊列表 -->
      <div class="left-panel">
        <div class="panel-section">
          <div class="section-header">
            <span>我的助手</span>
          </div>
          <div class="agent-list">
            <div
              v-for="agent in agents"
              :key="agent.id"
              :class="['agent-item', { active: selectedAgent?.id === agent.id && !selectedGroup }]"
              @click="selectAgent(agent)"
            >
              <div class="agent-avatar" :style="getAvatarStyle(agent.id)">
                {{ agent.name?.charAt(0) || '?' }}
              </div>
              <div class="agent-info">
                <div class="agent-name">{{ agent.name }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="panel-section">
          <div class="section-header">
            <span>群聊</span>
          </div>
          <div class="group-list">
            <div
              v-for="group in groups"
              :key="group.id"
              :class="['group-item', { active: selectedGroup?.id === group.id }]"
              @click="selectGroup(group)"
            >
              <div class="group-avatar">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                  <circle cx="9" cy="7" r="4"></circle>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                  <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                </svg>
              </div>
              <div class="group-info">
                <div class="group-name">{{ group.name }}</div>
                <div class="group-members">{{ group.participants?.length || 0 }} 人</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 中栏：聊天区域 -->
      <div class="chat-panel">
        <template v-if="selectedAgent || selectedGroup">
          <!-- 聊天头部 -->
          <div class="chat-header">
            <div class="header-left">
              <div v-if="selectedAgent" class="header-avatar" :style="getAvatarStyle(selectedAgent.id)">
                {{ selectedAgent.name?.charAt(0) }}
              </div>
              <div v-else class="header-avatar group">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                  <circle cx="9" cy="7" r="4"></circle>
                </svg>
              </div>
              <div class="header-info">
                <div class="header-name">{{ selectedAgent?.name || selectedGroup?.name }}</div>
                <div class="header-status" v-if="selectedAgent">
                  <span class="status-dot online"></span>在线
                </div>
                <div class="header-status" v-else>
                  {{ selectedGroup?.participants?.map((p: any) => p.name).join('、') }}
                </div>
              </div>
            </div>
            <div class="header-right">
              <button class="header-btn" @click="showHistory = true" title="对话历史">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
              </button>
              <button class="header-btn" @click="showMemory = true" title="记忆">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                </svg>
              </button>
            </div>
          </div>

          <!-- 消息区域 -->
          <div class="messages-area" ref="messagesRef">
            <div v-if="messages.length === 0" class="welcome">
              <div v-if="selectedAgent" class="welcome-avatar" :style="getAvatarStyle(selectedAgent.id)">
                {{ selectedAgent.name?.charAt(0) }}
              </div>
              <div v-else class="welcome-avatar group">#</div>
              <div class="welcome-title">{{ selectedAgent?.name || selectedGroup?.name }}</div>
              <div class="welcome-desc">发送消息开始对话</div>
            </div>

            <div v-for="msg in messages" :key="msg.id" :class="['message-row', msg.role]">
              <div class="msg-avatar" :style="getAvatarStyle(msg.role === 'user' ? 'user' : (msg.sourceAgent || selectedAgent?.id))">
                {{ msg.role === 'user' ? (userStore.user?.display_name?.charAt(0) || '我') : (msg.senderName?.charAt(0) || selectedAgent?.name?.charAt(0)) }}
              </div>
              <div class="msg-content">
                <div class="msg-header">
                  <span class="msg-sender">{{ msg.role === 'user' ? (userStore.user?.display_name || '我') : (msg.senderName || selectedAgent?.name) }}</span>
                  <span class="msg-time">{{ formatTime(msg.timestamp) }}</span>
                </div>
                <div class="msg-text" v-html="renderMarkdown(msg.content)"></div>
              </div>
            </div>

            <div v-if="isStreaming && streamContent" class="message-row assistant">
              <div class="msg-avatar" :style="getAvatarStyle(selectedAgent?.id)">
                {{ selectedAgent?.name?.charAt(0) }}
              </div>
              <div class="msg-content">
                <div class="msg-header">
                  <span class="msg-sender">{{ selectedAgent?.name }}</span>
                </div>
                <div class="msg-text streaming" v-html="renderMarkdown(streamContent)"></div>
              </div>
            </div>

            <div ref="bottomRef"></div>
          </div>

          <!-- 输入区域 -->
          <div class="input-area">
            <textarea
              v-model="inputText"
              placeholder="输入消息..."
              @keydown.enter.exact.prevent="sendMessage"
              :disabled="isStreaming"
              rows="1"
            ></textarea>
            <button class="send-btn" @click="sendMessage" :disabled="!inputText.trim() || isStreaming">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </button>
          </div>
        </template>

        <div v-else class="no-selection">
          <div class="empty-icon">💬</div>
          <p>选择助手或群聊开始对话</p>
        </div>
      </div>

      <!-- 右栏：工作区 -->
      <div class="right-panel">
        <div class="panel-section">
          <div class="section-header">
            <span>工作状态</span>
          </div>
          <div class="work-status">
            <div class="status-card">
              <div class="status-icon pending">📋</div>
              <div class="status-info">
                <div class="status-value">{{ tasks.pending }}</div>
                <div class="status-label">待处理</div>
              </div>
            </div>
            <div class="status-card">
              <div class="status-icon progress">🔄</div>
              <div class="status-info">
                <div class="status-value">{{ tasks.inProgress }}</div>
                <div class="status-label">进行中</div>
              </div>
            </div>
            <div class="status-card">
              <div class="status-icon done">✅</div>
              <div class="status-info">
                <div class="status-value">{{ tasks.completed }}</div>
                <div class="status-label">已完成</div>
              </div>
            </div>
          </div>
        </div>

        <div class="panel-section">
          <div class="section-header">
            <span>最近成果</span>
          </div>
          <div class="deliverables">
            <div v-for="item in deliverables" :key="item.id" class="deliverable-item">
              <div class="deliverable-icon">📄</div>
              <div class="deliverable-info">
                <div class="deliverable-title">{{ item.title }}</div>
                <div class="deliverable-time">{{ formatTime(item.time) }}</div>
              </div>
            </div>
            <div v-if="deliverables.length === 0" class="empty-tip">暂无工作成果</div>
          </div>
        </div>

        <div class="panel-section">
          <div class="section-header">
            <span>今日动态</span>
          </div>
          <div class="activities">
            <div v-for="act in activities" :key="act.id" class="activity-item">
              <div class="activity-dot"></div>
              <div class="activity-content">
                <div class="activity-text">{{ act.text }}</div>
                <div class="activity-time">{{ formatTime(act.time) }}</div>
              </div>
            </div>
            <div v-if="activities.length === 0" class="empty-tip">暂无动态</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 对话历史弹窗 -->
    <el-dialog v-model="showHistory" title="对话历史" width="500px">
      <div class="history-list" v-loading="loadingHistory">
        <div v-for="session in sessions" :key="session.sessionId" class="history-item" @click="loadSession(session.sessionId)">
          <div class="history-title">{{ session.title || '未命名对话' }}</div>
          <div class="history-time">{{ formatTime(session.updatedAt || session.createdAt) }}</div>
        </div>
        <div v-if="sessions.length === 0" class="empty-tip">暂无对话记录</div>
      </div>
    </el-dialog>

    <!-- 记忆弹窗 -->
    <el-dialog v-model="showMemory" title="记忆" width="500px">
      <div class="memory-list" v-loading="loadingMemory">
        <div v-for="item in memories" :key="item.date" class="memory-item">
          <div class="memory-date">{{ item.date }}</div>
          <div class="memory-content">{{ item.summary }}</div>
        </div>
        <div v-if="memories.length === 0" class="empty-tip">暂无记忆</div>
      </div>
    </el-dialog>

    <!-- 个人资料弹窗 -->
    <el-dialog v-model="showProfile" title="个人资料" width="360px">
      <div class="profile-info">
        <div class="profile-row">
          <span class="label">姓名</span>
          <span class="value">{{ userStore.user?.display_name }}</span>
        </div>
        <div class="profile-row">
          <span class="label">邮箱</span>
          <span class="value">{{ userStore.user?.email }}</span>
        </div>
        <div class="profile-row">
          <span class="label">部门</span>
          <span class="value">{{ userStore.employee?.department_name || '-' }}</span>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from './stores'
import { agentApi, sessionApi, memoryApi } from '../api'
import { marked } from 'marked'

const router = useRouter()
const userStore = useUserStore()

const agents = ref<any[]>([])
const groups = ref<any[]>([])
const selectedAgent = ref<any>(null)
const selectedGroup = ref<any>(null)
const messages = ref<any[]>([])
const inputText = ref('')
const isStreaming = ref(false)
const streamContent = ref('')
const messagesRef = ref<HTMLElement>()
const bottomRef = ref<HTMLElement>()

const showHistory = ref(false)
const showMemory = ref(false)
const showProfile = ref(false)
const sessions = ref<any[]>([])
const memories = ref<any[]>([])
const loadingHistory = ref(false)
const loadingMemory = ref(false)

// 工作区数据
const tasks = ref({ pending: 3, inProgress: 1, completed: 12 })
const deliverables = ref<any[]>([
  { id: 1, title: '周报文档.docx', time: new Date().toISOString() },
  { id: 2, title: '数据分析报告.xlsx', time: new Date(Date.now() - 3600000).toISOString() }
])
const activities = ref<any[]>([
  { id: 1, text: '小美 完成了周报撰写', time: new Date().toISOString() },
  { id: 2, text: '收到新任务提醒', time: new Date(Date.now() - 1800000).toISOString() }
])

const avatarColors: Record<string, string> = {}

function getAvatarStyle(id: string) {
  if (!avatarColors[id]) {
    const colors = [
      'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
      'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
      'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
      'linear-gradient(135deg, #fa709a 0%, #fee140 100%)'
    ]
    avatarColors[id] = colors[Object.keys(avatarColors).length % colors.length]
  }
  return { background: avatarColors[id] }
}

function formatTime(timestamp: string) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return date.toLocaleDateString()
}

function renderMarkdown(text: string) {
  if (!text) return ''
  return marked.parse(text) as string
}

async function loadAgents() {
  try {
    const res = await agentApi.list()
    if (res.data.success) {
      agents.value = res.data.data || []
    }
  } catch (e) {
    ElMessage.error('加载助手列表失败')
  }
}

async function loadGroups() {
  // TODO: 加载群聊列表
  groups.value = []
}

function selectAgent(agent: any) {
  selectedAgent.value = agent
  selectedGroup.value = null
  messages.value = []
}

function selectGroup(group: any) {
  selectedGroup.value = group
  selectedAgent.value = null
  messages.value = []
}

async function sendMessage() {
  if (!inputText.value.trim() || isStreaming.value || !selectedAgent.value) return

  const text = inputText.value.trim()
  inputText.value = ''

  messages.value.push({
    id: Date.now().toString(),
    role: 'user',
    content: text,
    timestamp: new Date().toISOString()
  })

  scrollToBottom()
  isStreaming.value = true
  streamContent.value = ''

  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userStore.accessToken}`
      },
      body: JSON.stringify({
        agentId: selectedAgent.value.id,
        message: text
      })
    })

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    while (reader) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') {
            messages.value.push({
              id: Date.now().toString(),
              role: 'assistant',
              content: streamContent.value,
              timestamp: new Date().toISOString()
            })
            streamContent.value = ''
            break
          }
          try {
            const json = JSON.parse(data)
            if (json.content) streamContent.value += json.content
          } catch {}
        }
      }
      scrollToBottom()
    }
  } catch (e: any) {
    ElMessage.error('发送失败：' + e.message)
  } finally {
    isStreaming.value = false
    scrollToBottom()
  }
}

function scrollToBottom() {
  nextTick(() => {
    bottomRef.value?.scrollIntoView({ behavior: 'smooth' })
  })
}

watch(showHistory, (val) => {
  if (val && selectedAgent.value) {
    loadingHistory.value = true
    sessionApi.list(selectedAgent.value.id).then(res => {
      if (res.data.success) sessions.value = res.data.data || []
    }).finally(() => loadingHistory.value = false)
  }
})

watch(showMemory, (val) => {
  if (val && selectedAgent.value) {
    loadingMemory.value = true
    memoryApi.list(selectedAgent.value.id).then(res => {
      if (res.data.success) memories.value = res.data.data || []
    }).finally(() => loadingMemory.value = false)
  }
})

async function handleLogout() {
  await userStore.clear()
  router.push('/login')
}

onMounted(() => {
  loadAgents()
  loadGroups()
})
</script>

<style scoped>
.staff-home {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #fff;
}

/* 顶部栏 */
.staff-header {
  height: 52px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  flex-shrink: 0;
}

.header-logo {
  display: flex;
  align-items: center;
  gap: 8px;
}

.logo-icon {
  width: 28px;
  height: 28px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 600;
  font-size: 14px;
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.header-user {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.user-name {
  font-size: 13px;
  color: #606266;
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 12px;
}

/* 三栏布局 - 黄金分割 */
.staff-main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* 左栏 */
.left-panel {
  width: 200px;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow-y: auto;
}

/* 中栏 */
.chat-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  background: #fff;
}

/* 右栏 */
.right-panel {
  width: calc((100vw - 200px) * 0.382);
  max-width: 420px;
  min-width: 280px;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow-y: auto;
}

.panel-section {
  padding: 12px;
}

.section-header {
  font-size: 12px;
  font-weight: 600;
  color: #909399;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Agent 列表 */
.agent-item, .group-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}

.agent-item:hover, .group-item:hover {
  background: #f0f0f0;
}

.agent-item.active, .group-item.active {
  background: #e6f7ff;
}

.agent-avatar, .group-avatar {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  flex-shrink: 0;
}

.group-avatar {
  background: #909399;
}

.agent-name, .group-name {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.agent-item.active .agent-name,
.group-item.active .group-name {
  color: #1890ff;
}

.group-members {
  font-size: 12px;
  color: #909399;
}

.agent-item.active .group-members,
.group-item.active .group-members {
  color: #69c0ff;
}

.group-members {
  font-size: 12px;
  color: var(--warm-600);
}

.agent-item.active .group-members,
.group-item.active .group-members {
  color: rgba(255, 255, 255, 0.8);
}

/* 聊天区域 */
.chat-header {
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  flex-shrink: 0;
  background: #fff;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-avatar {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
}

.header-avatar.group {
  background: #909399;
}

.header-name {
  font-size: 15px;
  font-weight: 500;
  color: #303133;
}

.header-status {
  font-size: 12px;
  color: #909399;
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #909399;
}

.status-dot.online {
  background: #52c41a;
}

.header-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: #f5f5f5;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #606266;
  transition: all 0.2s;
}

.header-btn:hover {
  background: #e8e8e8;
  color: #303133;
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
}

.welcome-avatar {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 24px;
  margin-bottom: 12px;
}

.welcome-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.message-row {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.message-row.user {
  flex-direction: row-reverse;
}

.msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 12px;
  flex-shrink: 0;
}

.msg-content {
  max-width: 70%;
}

.msg-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 2px;
}

.message-row.user .msg-header {
  flex-direction: row-reverse;
}

.msg-sender {
  font-size: 12px;
  font-weight: 500;
  color: #303133;
}

.msg-time {
  font-size: 11px;
  color: #909399;
}

.msg-text {
  background: #f5f5f5;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.5;
  color: #303133;
}

.message-row.user .msg-text {
  background: #e6f7ff;
}

.msg-text.streaming::after {
  content: '▋';
  animation: blink 1s infinite;
  color: #1890ff;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.input-area {
  padding: 12px 16px;
  display: flex;
  gap: 10px;
  flex-shrink: 0;
  background: #fff;
}

.input-area textarea {
  flex: 1;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 14px;
  resize: none;
  outline: none;
}

.input-area textarea:focus {
  border-color: #40a9ff;
}

.send-btn {
  width: 40px;
  height: 40px;
  border: none;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  transition: transform 0.2s, box-shadow 0.2s;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.no-selection {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.empty-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

/* 工作区 */
.work-status {
  display: flex;
  gap: 8px;
}

.status-card {
  flex: 1;
  background: #fff;
  border-radius: 8px;
  padding: 10px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.status-icon {
  font-size: 20px;
  margin-bottom: 4px;
}

.status-value {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.status-label {
  font-size: 11px;
  color: #909399;
}

.deliverable-item, .activity-item {
  display: flex;
  gap: 8px;
  padding: 8px 0;
}

.deliverable-icon {
  font-size: 18px;
}

.deliverable-title {
  font-size: 13px;
  color: #303133;
}

.deliverable-time {
  font-size: 11px;
  color: #909399;
}

.activity-item {
  position: relative;
  padding-left: 16px;
}

.activity-dot {
  position: absolute;
  left: 0;
  top: 12px;
  width: 6px;
  height: 6px;
  background: #1890ff;
  border-radius: 50%;
}

.activity-text {
  font-size: 13px;
  color: #606266;
}

.activity-time {
  font-size: 11px;
  color: #909399;
}

.empty-tip {
  text-align: center;
  padding: 20px;
  color: #909399;
  font-size: 13px;
}

/* 弹窗 */
.history-item, .memory-item {
  padding: 10px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
}

.history-item:hover {
  background: #f5f5f5;
}

.history-title, .memory-content {
  font-size: 14px;
  color: #303133;
}

.history-time, .memory-date {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.memory-date {
  color: #1890ff;
}

.profile-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.profile-row {
  display: flex;
  align-items: center;
}

.profile-row .label {
  width: 60px;
  color: #909399;
  font-size: 13px;
}

.profile-row .value {
  flex: 1;
  font-size: 13px;
  color: #303133;
}
</style>