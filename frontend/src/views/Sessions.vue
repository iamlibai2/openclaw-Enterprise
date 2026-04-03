<template>
  <div class="sessions-page">
    <!-- 三栏布局 -->
    <div class="sessions-layout">
      <!-- 左侧：Agent 选择 -->
      <div class="agent-panel">
        <div class="panel-header">
          <h3>Agent</h3>
        </div>
        <div class="agent-list">
          <div
            class="agent-item"
            v-for="agent in agents"
            :key="agent.id"
            :class="{ active: selectedAgent?.id === agent.id }"
            @click="selectAgent(agent)"
          >
            <div class="agent-avatar">{{ agent.name.charAt(0) }}</div>
            <div class="agent-info">
              <div class="agent-name">{{ agent.name }}</div>
              <div class="agent-count">{{ agent.sessionCount }} 个会话</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 中间：会话/记忆列表 -->
      <div class="session-panel">
        <div class="panel-header">
          <h3>{{ viewMode === 'sessions' ? '会话列表' : '记忆文件' }}</h3>
          <el-radio-group v-model="viewMode" size="small">
            <el-radio-button label="sessions">会话</el-radio-button>
            <el-radio-button label="memory">记忆</el-radio-button>
          </el-radio-group>
        </div>

        <!-- 搜索框 -->
        <div class="search-box">
          <el-input
            v-model="searchKeyword"
            :placeholder="viewMode === 'sessions' ? '搜索会话内容...' : '搜索记忆内容...'"
            clearable
            @keyup.enter="doSearch"
            @clear="clearSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
            <template #append>
              <el-button @click="doSearch" :loading="searching">搜索</el-button>
            </template>
          </el-input>
        </div>

        <!-- 搜索结果 -->
        <div class="search-results" v-if="showSearchResults" v-loading="searching">
          <div class="search-header">
            <span>搜索 "{{ searchKeyword }}" 结果：{{ searchResults.length }} 条</span>
            <el-button size="small" link @click="clearSearch">清除</el-button>
          </div>
          <div class="result-list">
            <div
              class="result-item"
              v-for="(result, idx) in searchResults"
              :key="idx"
              @click="jumpToResult(result)"
            >
              <div class="result-title">
                <el-icon><Document /></el-icon>
                <span v-if="viewMode === 'sessions'">{{ result.updatedAt }}</span>
                <span v-else>{{ result.date }}</span>
                <el-tag size="small" type="info">{{ result.matchCount }} 处匹配</el-tag>
              </div>
              <div class="result-matches">
                <div class="match-item" v-for="(m, i) in result.matches.slice(0, 2)" :key="i">
                  <el-tag size="small" effect="plain">{{ m.role || '内容' }}</el-tag>
                  <span class="match-context" v-html="highlightKeyword(m.context)"></span>
                </div>
              </div>
            </div>
          </div>
          <div class="empty-tip" v-if="!searching && searchResults.length === 0">
            未找到匹配内容
          </div>
        </div>

        <!-- 会话列表 -->
        <div class="session-list" v-loading="loadingSessions" v-if="!showSearchResults && viewMode === 'sessions'">
          <div
            class="session-item"
            v-for="session in sessions"
            :key="session.sessionId + (session.isReset ? '-reset' : '')"
            :class="{ active: selectedSession?.sessionId === session.sessionId, reset: session.isReset }"
            @click="selectSession(session)"
          >
            <div class="session-channel">
              <el-tag size="small" effect="plain">{{ session.channel }}</el-tag>
              <el-tag size="small" :type="session.status === 'running' ? 'warning' : session.isReset ? 'info' : 'success'">
                {{ session.isReset ? '归档' : session.status }}
              </el-tag>
            </div>
            <div class="session-info">
              <div class="session-time">{{ session.updatedAt }}</div>
              <div class="session-model" v-if="session.model && !session.isReset">{{ session.model }}</div>
              <div class="session-reset-info" v-if="session.isReset && session.resetAt">
                <el-icon><Clock /></el-icon>
                {{ formatResetTime(session.resetAt) }}
              </div>
            </div>
          </div>
          <div class="empty-tip" v-if="!loadingSessions && sessions.length === 0">
            {{ selectedAgent ? '暂无会话记录' : '请先选择 Agent' }}
          </div>
        </div>

        <!-- 记忆文件列表 -->
        <div class="memory-list" v-loading="loadingMemory" v-if="!showSearchResults && viewMode === 'memory'">
          <div
            class="memory-item"
            v-for="mem in memories"
            :key="mem.date"
            :class="{ active: selectedMemory?.date === mem.date }"
            @click="selectMemory(mem)"
          >
            <div class="memory-icon">📝</div>
            <div class="memory-info">
              <div class="memory-date">{{ mem.date }}</div>
              <div class="memory-meta">{{ formatSize(mem.size) }}</div>
            </div>
          </div>
          <div class="empty-tip" v-if="!loadingMemory && memories.length === 0">
            {{ selectedAgent ? '暂无记忆文件' : '请先选择 Agent' }}
          </div>
        </div>
      </div>

      <!-- 右侧：详情面板 -->
      <div class="chat-panel">
        <!-- 会话详情 -->
        <template v-if="viewMode === 'sessions'">
          <div class="panel-header">
            <h3>对话记录</h3>
            <div class="header-actions">
              <span v-if="selectedSession">{{ selectedSession.updatedAt }}</span>
              <el-button
                v-if="selectedSession && !selectedSession.isReset"
                size="small"
                :type="focusStatus?.enabled ? 'warning' : 'default'"
                @click="showFocusDialog"
              >
                {{ focusStatus?.enabled ? '专注模式已启用' : '专注模式' }}
              </el-button>
            </div>
          </div>
          <div class="chat-messages" v-loading="loadingMessages" ref="messagesRef">
            <template v-for="msg in messages" :key="msg.id">
              <!-- 用户消息：右侧蓝色 -->
              <div class="message-row user" v-if="msg.role === 'user' && msg.text">
                <div class="message-bubble user-bubble">
                  <div class="message-text">{{ msg.text }}</div>
                  <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
                </div>
              </div>

              <!-- 助手消息：左侧绿色 -->
              <div class="message-row assistant" v-if="msg.role === 'assistant'">
                <div class="assistant-avatar" v-if="selectedAgent">
                  {{ selectedAgent.name.charAt(0) }}
                </div>
                <div class="message-bubble assistant-bubble">
                  <div class="assistant-name">{{ selectedAgent?.name || 'Assistant' }}</div>
                  <div class="thinking-block" v-if="msg.thinking">
                    <el-collapse>
                      <el-collapse-item title="思考过程">
                        <pre>{{ msg.thinking }}</pre>
                      </el-collapse-item>
                    </el-collapse>
                  </div>
                  <div class="message-text" v-if="msg.text">{{ msg.text }}</div>
                  <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
                </div>
              </div>

              <!-- 工具结果 -->
              <div class="message-row tool" v-if="msg.role === 'toolResult'">
                <div class="tool-result">
                  <el-tag size="small" type="info">{{ msg.toolName }}</el-tag>
                  <el-collapse v-if="msg.text">
                    <el-collapse-item title="查看结果">
                      <pre class="tool-content">{{ msg.text }}</pre>
                    </el-collapse-item>
                  </el-collapse>
                </div>
              </div>
            </template>
            <div class="empty-tip" v-if="!loadingMessages && messages.length === 0">
              {{ selectedSession ? '暂无消息' : '请选择会话查看' }}
            </div>
          </div>
        </template>

        <!-- 记忆内容 -->
        <template v-else>
          <div class="panel-header">
            <h3>记忆内容</h3>
            <span v-if="selectedMemory">{{ selectedMemory.date }}</span>
          </div>
          <div class="memory-content" v-loading="loadingMemoryContent">
            <div class="markdown-body" v-if="memoryContent" v-html="renderedMemory"></div>
            <div class="empty-tip" v-else>
              {{ selectedMemory ? '加载中...' : '请选择记忆文件查看' }}
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- 专注模式对话框 -->
    <el-dialog
      v-model="focusDialogVisible"
      title="专注模式"
      width="500px"
    >
      <div class="focus-dialog-content">
        <div class="focus-status-card" v-if="focusStatus?.enabled">
          <el-alert type="success" :closable="false">
            <template #title>
              <div class="status-header">
                <span>专注模式已启用</span>
                <el-tag size="small" effect="plain">{{ focusStatus.keywords?.length || 0 }} 个关键词</el-tag>
              </div>
            </template>
            <div class="status-details">
              <div v-if="focusStatus.taskDescription">
                <strong>任务：</strong>{{ focusStatus.taskDescription }}
              </div>
              <div v-if="focusStatus.startedAt">
                <strong>开始：</strong>{{ formatTime(focusStatus.startedAt) }}
              </div>
              <div v-if="focusStatus.messagesRemoved">
                <strong>已清理：</strong>{{ focusStatus.messagesRemoved }} 条消息
              </div>
              <div v-if="focusStatus.tokensSaved">
                <strong>节省：</strong>{{ focusStatus.tokensSaved }} tokens
              </div>
            </div>
          </el-alert>
        </div>

        <div class="focus-form" v-if="!focusStatus?.enabled">
          <el-form label-width="100px">
            <el-form-item label="任务描述">
              <el-input
                v-model="focusTaskDescription"
                type="textarea"
                :rows="3"
                placeholder="描述当前任务，系统会自动提取关键词..."
              />
            </el-form-item>
            <el-form-item label="关键词">
              <el-select
                v-model="focusKeywords"
                multiple
                filterable
                allow-create
                placeholder="自定义关键词（可选）"
              />
            </el-form-item>
            <el-form-item label="立即压缩">
              <el-switch v-model="focusCompactNow" />
              <span class="form-tip">启用后立即清理无关上下文</span>
            </el-form-item>
          </el-form>
        </div>

        <div class="focus-actions">
          <el-button v-if="focusStatus?.enabled" type="danger" @click="clearFocus">
            清除专注模式
          </el-button>
          <el-button v-if="focusStatus?.enabled && !focusCompactNow" type="primary" @click="compactNow">
            执行压缩
          </el-button>
          <el-button v-if="!focusStatus?.enabled" type="primary" @click="enableFocus" :loading="focusLoading">
            启用专注模式
          </el-button>
          <el-button @click="focusDialogVisible = false">关闭</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Document, Clock } from '@element-plus/icons-vue'
import { sessionApi, memoryApi, searchApi, focusApi } from '../api'
import { marked } from 'marked'

interface SessionAgent {
  id: string
  name: string
  sessionCount: number
}

interface Session {
  sessionId: string
  sessionKey: string
  displayName: string
  channel: string
  chatType: string
  updatedAt: string
  updatedAtTs: number
  status: string
  model: string
  modelProvider: string
  runtimeMs: number
  childSessions: string[]
  isReset?: boolean
  resetAt?: string
  filename?: string
}

interface Message {
  id: string
  timestamp: string
  role: string
  text: string
  thinking: string
  toolCalls: any[]
  toolName?: string
}

interface MemoryFile {
  date: string
  filename: string
  size: number
  modified: string
}

interface SearchResult {
  sessionId?: string
  sessionKey?: string
  sessionFile?: string
  displayName?: string
  updatedAt?: string
  date?: string
  matchCount: number
  matches: Array<{
    role?: string
    context: string
    timestamp?: string
    line?: number
  }>
}

interface FocusStatus {
  enabled: boolean
  taskDescription?: string
  keywords?: string[]
  startedAt?: string
  messagesRemoved?: number
  tokensSaved?: number
}

const agents = ref<SessionAgent[]>([])
const sessions = ref<Session[]>([])
const messages = ref<Message[]>([])
const memories = ref<MemoryFile[]>([])
const memoryContent = ref('')
const searchKeyword = ref('')
const searchResults = ref<SearchResult[]>([])
const showSearchResults = ref(false)

const selectedAgent = ref<SessionAgent | null>(null)
const selectedSession = ref<Session | null>(null)
const selectedMemory = ref<MemoryFile | null>(null)

const viewMode = ref<'sessions' | 'memory'>('sessions')

const loadingSessions = ref(false)
const loadingMessages = ref(false)
const loadingMemory = ref(false)
const loadingMemoryContent = ref(false)
const searching = ref(false)
const messagesRef = ref<HTMLElement | null>(null)

// Focus Mode 相关
const focusDialogVisible = ref(false)
const focusStatus = ref<FocusStatus | null>(null)
const focusTaskDescription = ref('')
const focusKeywords = ref<string[]>([])
const focusCompactNow = ref(true)
const focusLoading = ref(false)

const renderedMemory = computed(() => {
  if (!memoryContent.value) return ''
  return marked(memoryContent.value)
})

watch(viewMode, async () => {
  selectedSession.value = null
  selectedMemory.value = null
  messages.value = []
  memoryContent.value = ''
  clearSearch()

  // 如果已选择 Agent，自动加载对应列表
  if (selectedAgent.value) {
    if (viewMode.value === 'sessions') {
      await loadSessions()
    } else {
      await loadMemories()
    }
  }
})

async function loadAgents() {
  try {
    const res = await sessionApi.agents()
    if (res.data.success) {
      agents.value = res.data.data
    }
  } catch (e: any) {
    ElMessage.error('加载 Agent 列表失败')
  }
}

async function selectAgent(agent: SessionAgent) {
  selectedAgent.value = agent
  selectedSession.value = null
  selectedMemory.value = null
  messages.value = []
  memoryContent.value = ''
  clearSearch()

  if (viewMode.value === 'sessions') {
    await loadSessions()
  } else {
    await loadMemories()
  }
}

async function loadSessions() {
  if (!selectedAgent.value) return

  loadingSessions.value = true
  try {
    const res = await sessionApi.list(selectedAgent.value.id)
    if (res.data.success) {
      sessions.value = res.data.data
    }
  } catch (e: any) {
    ElMessage.error('加载会话列表失败')
  } finally {
    loadingSessions.value = false
  }
}

async function loadMemories() {
  if (!selectedAgent.value) return

  loadingMemory.value = true
  try {
    const res = await memoryApi.list(selectedAgent.value.id)
    if (res.data.success) {
      memories.value = res.data.data
    }
  } catch (e: any) {
    ElMessage.error('加载记忆列表失败')
  } finally {
    loadingMemory.value = false
  }
}

async function selectSession(session: Session) {
  selectedSession.value = session
  messages.value = []
  focusStatus.value = null

  if (!selectedAgent.value) return

  // 加载 Focus 状态（只有活跃会话才有）
  if (!session.isReset) {
    loadFocusStatus(session.sessionKey)
  }

  loadingMessages.value = true
  try {
    // 根据会话类型调用不同的 API
    const res = await sessionApi.messages(
      selectedAgent.value.id,
      session.sessionId,
      session.isReset ? {
        isReset: true,
        filename: session.filename
      } : undefined
    )

    if (res.data.success) {
      messages.value = res.data.data
      await nextTick()
      if (messagesRef.value) {
        messagesRef.value.scrollTop = messagesRef.value.scrollHeight
      }
    } else {
      ElMessage.error(res.data.error || '加载消息失败')
    }
  } catch (e: any) {
    const errorMsg = e.response?.data?.error || e.message || '加载消息失败'
    console.error('加载消息失败:', errorMsg, 'agent:', selectedAgent.value.id, 'session:', session.sessionId)
    ElMessage.error(errorMsg)
  } finally {
    loadingMessages.value = false
  }
}

async function selectMemory(mem: MemoryFile) {
  selectedMemory.value = mem
  memoryContent.value = ''

  if (!selectedAgent.value) return

  loadingMemoryContent.value = true
  try {
    const res = await memoryApi.get(selectedAgent.value.id, mem.date)
    if (res.data.success) {
      memoryContent.value = res.data.data.content
    }
  } catch (e: any) {
    ElMessage.error('加载记忆内容失败')
  } finally {
    loadingMemoryContent.value = false
  }
}

async function doSearch() {
  if (!searchKeyword.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  if (!selectedAgent.value) {
    ElMessage.warning('请先选择 Agent')
    return
  }

  searching.value = true
  showSearchResults.value = true
  searchResults.value = []

  try {
    if (viewMode.value === 'sessions') {
      const res = await searchApi.sessions(selectedAgent.value.id, searchKeyword.value.trim())
      if (res.data.success) {
        searchResults.value = res.data.data
      }
    } else {
      const res = await searchApi.memory(selectedAgent.value.id, searchKeyword.value.trim())
      if (res.data.success) {
        searchResults.value = res.data.data
      }
    }
  } catch (e: any) {
    ElMessage.error('搜索失败')
  } finally {
    searching.value = false
  }
}

function clearSearch() {
  searchKeyword.value = ''
  searchResults.value = []
  showSearchResults.value = false
}

async function jumpToResult(result: SearchResult) {
  if (viewMode.value === 'sessions') {
    // 跳转到会话
    const session = sessions.value.find(s => s.sessionId === result.sessionId)
    if (session) {
      await selectSession(session)
    }
  } else {
    // 跳转到记忆
    const mem = memories.value.find(m => m.date === result.date)
    if (mem) {
      await selectMemory(mem)
    }
  }
}

function highlightKeyword(text: string): string {
  if (!searchKeyword.value || !text) return text
  const regex = new RegExp(`(${escapeRegex(searchKeyword.value)})`, 'gi')
  return text.replace(regex, '<mark>$1</mark>')
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function formatTime(timestamp: string): string {
  if (!timestamp) return ''
  try {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return timestamp
  }
}

function formatSize(size: number): string {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

function formatResetTime(resetAt: string): string {
  if (!resetAt) return ''
  try {
    const date = new Date(resetAt)
    return `归档于 ${date.toLocaleDateString('zh-CN')} ${date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`
  } catch {
    return resetAt
  }
}

// ==================== Focus Mode 相关 ====================

async function loadFocusStatus(sessionKey: string) {
  try {
    const res = await focusApi.getStatus(sessionKey)
    if (res.data.success) {
      focusStatus.value = res.data.data
    }
  } catch (e: any) {
    console.error('获取专注模式状态失败:', e)
  }
}

function showFocusDialog() {
  if (!selectedSession.value) return

  focusTaskDescription.value = ''
  focusKeywords.value = []
  focusCompactNow.value = true
  focusDialogVisible.value = true

  // 加载当前状态
  loadFocusStatus(selectedSession.value.sessionKey)
}

async function enableFocus() {
  if (!selectedSession.value) return

  focusLoading.value = true
  try {
    const res = await focusApi.enable(
      selectedSession.value.sessionKey,
      {
        taskDescription: focusTaskDescription.value,
        keywords: focusKeywords.value,
        compactNow: focusCompactNow.value
      }
    )

    if (res.data.success) {
      ElMessage.success(res.data.message || '专注模式已启用')
      focusStatus.value = res.data.data

      // 如果执行了压缩，刷新消息列表
      if (focusCompactNow.value && selectedAgent.value) {
        await loadSessions()
        if (selectedSession.value) {
          await selectSession(selectedSession.value)
        }
      }
    } else {
      ElMessage.error(res.data.error || '启用失败')
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || '启用专注模式失败')
  } finally {
    focusLoading.value = false
  }
}

async function compactNow() {
  if (!selectedSession.value) return

  focusLoading.value = true
  try {
    const res = await focusApi.compact(
      selectedSession.value.sessionKey,
      {
        taskDescription: focusTaskDescription.value,
        keywords: focusKeywords.value
      }
    )

    if (res.data.success && res.data.compacted) {
      const result = res.data.data
      ElMessage.success(`已清理 ${result.details.messagesRemoved} 条消息，节省 ${result.tokensBefore - result.tokensAfter} tokens`)

      // 更新状态
      if (selectedSession.value) {
        await loadFocusStatus(selectedSession.value.sessionKey)
        // 刷新消息列表
        if (selectedAgent.value) {
          await loadSessions()
          if (selectedSession.value) {
            await selectSession(selectedSession.value)
          }
        }
      }
    } else {
      ElMessage.info('无需压缩或压缩失败')
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || '压缩失败')
  } finally {
    focusLoading.value = false
  }
}

async function clearFocus() {
  if (!selectedSession.value) return

  focusLoading.value = true
  try {
    const res = await focusApi.clear(selectedSession.value.sessionKey)

    if (res.data.success) {
      ElMessage.success('专注模式已清除')
      focusStatus.value = null
      focusDialogVisible.value = false
    } else {
      ElMessage.error(res.data.error || '清除失败')
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || '清除专注模式失败')
  } finally {
    focusLoading.value = false
  }
}

onMounted(() => {
  loadAgents()
})
</script>

<style scoped>
.sessions-page {
  height: calc(100vh - 96px);
}

.sessions-layout {
  display: flex;
  height: 100%;
  gap: 16px;
}

/* 面板通用 */
.agent-panel,
.session-panel,
.chat-panel {
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
}

.panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.panel-header span {
  font-size: 13px;
  color: #909399;
}

/* Agent 面板 */
.agent-panel {
  width: 200px;
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
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.agent-item:hover {
  background: #f5f5f5;
}

.agent-item.active {
  background: #e6f7ff;
}

.agent-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1890ff, #36cfc9);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 500;
}

.agent-info {
  flex: 1;
}

.agent-name {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.agent-count {
  font-size: 12px;
  color: #909399;
}

/* 会话面板 */
.session-panel {
  width: 300px;
}

/* 搜索框 */
.search-box {
  padding: 12px;
  border-bottom: 1px solid #e8e8e8;
}

/* 搜索结果 */
.search-results {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.search-header {
  padding: 8px 12px;
  background: #fafafa;
  font-size: 13px;
  color: #666;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.result-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.result-item {
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
  margin-bottom: 8px;
  background: #fafafa;
}

.result-item:hover {
  background: #f0f0f0;
}

.result-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
  color: #303133;
}

.result-matches {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.match-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
}

.match-context {
  flex: 1;
  color: #666;
  line-height: 1.5;
  word-break: break-all;
}

.match-context :deep(mark) {
  background: #ffe58f;
  padding: 0 2px;
  border-radius: 2px;
}

.session-list,
.memory-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.session-item,
.memory-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.session-item:hover,
.memory-item:hover {
  background: #f5f5f5;
}

.session-item.active {
  background: #f6ffed;
}

.session-item.reset {
  background: #f5f5f5;
  opacity: 0.85;
}

.session-item.reset.active {
  background: #e6e6e6;
}

.memory-item.active {
  background: #fff7e6;
}

.session-info,
.memory-info {
  flex: 1;
}

.session-time,
.memory-date {
  font-size: 13px;
  color: #303133;
}

.session-count,
.session-model,
.session-reset-info,
.memory-meta {
  font-size: 12px;
  color: #909399;
}

.session-reset-info {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #c0c4cc;
}

.session-channel {
  display: flex;
  gap: 4px;
  margin-bottom: 4px;
}

.memory-icon {
  font-size: 20px;
}

/* 聊天面板 */
.chat-panel {
  flex: 1;
  min-width: 400px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 消息行 */
.message-row {
  display: flex;
  gap: 8px;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.message-row.tool {
  justify-content: center;
}

/* 消息气泡 */
.message-bubble {
  max-width: 70%;
  padding: 10px 14px;
  border-radius: 8px;
}

.user-bubble {
  background: #1890ff;
  color: #fff;
}

.user-bubble .message-time {
  color: rgba(255, 255, 255, 0.7);
}

.assistant-bubble {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
}

.assistant-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #52c41a, #73d13d);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 500;
  align-self: flex-end;
}

.assistant-name {
  font-size: 12px;
  color: #52c41a;
  font-weight: 500;
  margin-bottom: 4px;
}

.assistant-bubble .message-time {
  color: #909399;
}

.message-text {
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-time {
  font-size: 11px;
  margin-top: 6px;
  text-align: right;
}

.thinking-block {
  margin-bottom: 8px;
}

.thinking-block pre {
  font-size: 12px;
  color: #666;
  white-space: pre-wrap;
  background: #fafafa;
  padding: 8px;
  border-radius: 4px;
}

.tool-result {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #f5f5f5;
  border-radius: 6px;
}

.tool-content {
  font-size: 12px;
  color: #666;
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
}

/* 记忆内容 */
.memory-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.markdown-body {
  font-size: 14px;
  line-height: 1.8;
  color: #303133;
}

.markdown-body :deep(h1) {
  font-size: 20px;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e8e8e8;
}

.markdown-body :deep(h2) {
  font-size: 18px;
  margin: 20px 0 12px;
  color: #1890ff;
}

.markdown-body :deep(h3) {
  font-size: 16px;
  margin: 16px 0 10px;
  color: #52c41a;
}

.markdown-body :deep(p) {
  margin-bottom: 12px;
}

.markdown-body :deep(pre) {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 13px;
}

.markdown-body :deep(code) {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 13px;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 20px;
  margin-bottom: 12px;
}

.markdown-body :deep(li) {
  margin-bottom: 6px;
}

.markdown-body :deep(strong) {
  color: #303133;
}

.markdown-body :deep(blockquote) {
  border-left: 4px solid #1890ff;
  padding-left: 12px;
  margin: 12px 0;
  color: #666;
}

/* 空状态 */
.empty-tip {
  text-align: center;
  color: #c0c4cc;
  padding: 40px 0;
  font-size: 13px;
}

/* 折叠面板样式 */
:deep(.el-collapse) {
  border: none;
}

:deep(.el-collapse-item__header) {
  font-size: 12px;
  color: #909399;
  height: 28px;
  line-height: 28px;
  background: transparent;
}

:deep(.el-collapse-item__content) {
  padding-bottom: 8px;
}

/* Focus Mode 样式 */
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.focus-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.focus-status-card {
  margin-bottom: 16px;
}

.status-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-details {
  margin-top: 12px;
  font-size: 13px;
  line-height: 1.8;
}

.status-details div {
  margin-bottom: 6px;
}

.focus-form {
  padding: 16px 0;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}

.focus-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 16px;
  border-top: 1px solid #e8e8e8;
}
</style>