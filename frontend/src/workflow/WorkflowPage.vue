<template>
  <div class="workflow-page">
    <!-- 左侧：编排 Agent 对话 -->
    <div class="chat-panel">
      <!-- 顶部栏 -->
      <div class="chat-header">
        <div class="header-left">
          <div class="header-avatar">
            <div class="avatar-ring"></div>
            <span class="avatar-letter">P</span>
          </div>
          <div class="header-info">
            <div class="header-name">Prometheus</div>
            <div class="header-desc">工作流编排引擎</div>
          </div>
        </div>
        <div class="header-right">
          <div class="connection-badge" :class="{ active: gatewayConnected }">
            <span class="badge-dot"></span>
            <span class="badge-text">{{ gatewayConnected ? 'READY' : 'OFFLINE' }}</span>
          </div>
        </div>
      </div>

      <!-- 消息区域 -->
      <div class="messages-area" ref="messagesRef">
        <!-- 欢迎状态 -->
        <div v-if="messages.length === 0 && !thinking" class="welcome-state">
          <div class="welcome-brand">
            <div class="brand-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"></path>
              </svg>
            </div>
            <div class="brand-title">工作流编排系统</div>
            <div class="brand-subtitle">自然语言驱动的自动化流程</div>
          </div>
          <div class="welcome-prompts">
            <div class="prompts-label">快速开始</div>
            <div class="prompt-card" @click="quickPrompt('创建一个每天早上搜索AI新闻并发送简报的工作流')">
              <div class="prompt-number">01</div>
              <div class="prompt-content">
                <div class="prompt-title">定时新闻简报</div>
                <div class="prompt-desc">搜索 → 整理 → 发送</div>
              </div>
            </div>
            <div class="prompt-card" @click="quickPrompt('创建一个数据分析报告工作流')">
              <div class="prompt-number">02</div>
              <div class="prompt-content">
                <div class="prompt-title">数据分析报告</div>
                <div class="prompt-desc">采集 → 分析 → 输出</div>
              </div>
            </div>
            <div class="prompt-card" @click="quickPrompt('查看所有工作流')">
              <div class="prompt-number">03</div>
              <div class="prompt-content">
                <div class="prompt-title">管理工作流</div>
                <div class="prompt-desc">查看、修改、删除</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 消息列表 -->
        <div v-for="(msg, idx) in messages" :key="msg.id" class="message-block" :class="msg.role">
          <div class="message-gutter">
            <div class="gutter-avatar" :class="msg.role">
              <span v-if="msg.role === 'assistant'" class="avatar-system">P</span>
              <span v-else class="avatar-user">{{ userInitial }}</span>
            </div>
          </div>
          <div class="message-body">
            <div class="message-header">
              <span class="sender-name">{{ msg.role === 'assistant' ? 'Prometheus' : userName }}</span>
              <span class="send-time">{{ msg.time }}</span>
            </div>
            <div class="message-content" v-html="renderMessageContent(msg.content)"></div>
          </div>
        </div>

        <!-- Reading 状态：收到消息正在思考 -->
        <div v-if="thinking && !streamContent" class="message-block assistant reading">
          <div class="message-gutter">
            <div class="gutter-avatar assistant">
              <span class="avatar-system">P</span>
            </div>
          </div>
          <div class="message-body">
            <div class="message-header">
              <span class="sender-name">Prometheus</span>
              <span class="status-badge reading">
                <span class="status-dot"></span>
                <span class="status-text">Processing</span>
              </span>
            </div>
            <div class="reading-indicator">
              <span class="pulse-bar"></span>
              <span class="pulse-bar"></span>
              <span class="pulse-bar"></span>
            </div>
          </div>
        </div>

        <!-- Streaming 状态：正在输出内容 -->
        <div v-if="thinking && streamContent" class="message-block assistant streaming">
          <div class="message-gutter">
            <div class="gutter-avatar assistant">
              <span class="avatar-system">P</span>
            </div>
          </div>
          <div class="message-body">
            <div class="message-header">
              <span class="sender-name">Prometheus</span>
              <span class="status-badge streaming">
                <span class="typing-cursor"></span>
                <span class="status-text">Writing</span>
              </span>
            </div>
            <div class="message-content streaming-content" v-html="renderMessageContent(streamContent)"></div>
          </div>
        </div>
      </div>

      <!-- 当前工作流指示器 -->
      <Transition name="slide-up">
        <div v-if="currentWorkflow" class="workflow-indicator">
          <div class="indicator-left">
            <div class="indicator-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
              </svg>
            </div>
            <div class="indicator-info">
              <span class="indicator-name">{{ currentWorkflow.name }}</span>
              <span class="indicator-stats">{{ currentWorkflow.nodes?.length || 0 }} nodes · {{ currentWorkflow.edges?.length || 0 }} edges</span>
            </div>
          </div>
          <button class="indicator-close" @click="clearWorkflow">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </Transition>

      <!-- 输入区域 -->
      <div class="input-area">
        <div class="input-container" :class="{ focused: inputFocused, disabled: thinking || executing || !gatewayConnected }">
          <textarea
            ref="inputRef"
            v-model="inputText"
            placeholder="描述你想要的工作流..."
            rows="1"
            @keydown="handleKeydown"
            @input="autoResize"
            @focus="inputFocused = true"
            @blur="inputFocused = false"
            :disabled="thinking || executing || !gatewayConnected"
          ></textarea>
          <button class="submit-btn" :class="{ ready: canSubmit }" @click="sendMessage" :disabled="!canSubmit">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path>
            </svg>
          </button>
        </div>
        <div class="input-hint">
          <span v-if="!gatewayConnected" class="hint-offline">等待连接...</span>
          <span v-else-if="thinking" class="hint-processing">处理中...</span>
          <span v-else class="hint-ready">Enter 发送 · Shift+Enter 换行</span>
        </div>
      </div>
    </div>

    <!-- 右侧：工作流可视化 -->
    <div class="dag-panel">
      <!-- 有工作流时显示 DAG -->
      <div v-if="currentWorkflow" class="dag-active">
        <div class="dag-toolbar">
          <div class="toolbar-left">
            <span class="workflow-badge">
              <span class="badge-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
              </span>
              <span class="workflow-name">{{ currentWorkflow.name }}</span>
            </span>
          </div>
          <div class="toolbar-right">
            <button class="action-btn test" @click="loadTestWorkflow" style="background: #6b7280; margin-right: 8px;">
              <span class="btn-text">Test</span>
            </button>
            <button class="action-btn execute" @click="executeWorkflow" :disabled="executing || thinking">
              <span class="btn-icon">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="5 3 19 12 5 21 5 3"></polygon>
                </svg>
              </span>
              <span class="btn-text">{{ executing ? 'Running' : 'Execute' }}</span>
            </button>
          </div>
        </div>

        <div class="dag-canvas" ref="canvasRef">
          <svg class="dag-svg" :viewBox="`0 0 ${canvasWidth} ${canvasHeight}`">
            <!-- 连接线 -->
            <g class="edges-layer">
              <path
                v-for="edge in layoutEdges"
                :key="`${edge.from}-${edge.to}`"
                :d="edge.path"
                class="edge-line"
                :class="getEdgeClass(edge)"
              />
            </g>

            <!-- 节点 -->
            <g class="nodes-layer">
              <g
                v-for="node in layoutNodes"
                :key="node.id"
                :transform="`translate(${node.x}, ${node.y})`"
                class="node-group"
              >
                <foreignObject :width="nodeWidth" :height="nodeHeight" :x="0" :y="0">
                  <div class="node-card" :class="getNodeClass(node)">
                    <div class="node-type-indicator" :class="node.type"></div>
                    <div class="node-content">
                      <div class="node-label">{{ node.name }}</div>
                      <div class="node-meta">
                        <span class="node-kind">{{ node.type === 'skill' ? 'SKILL' : 'AGENT' }}</span>
                      </div>
                    </div>
                    <div class="node-state" v-if="nodeStatus[node.id]">
                      <span class="state-indicator" :class="nodeStatus[node.id]"></span>
                    </div>
                  </div>
                </foreignObject>
              </g>
            </g>
          </svg>
        </div>

        <!-- 执行进度面板 -->
        <Transition name="slide-up">
          <div v-if="executing" class="execution-panel">
            <div class="panel-header">
              <span class="panel-title">执行进度</span>
              <span class="panel-progress">{{ executionProgress }}%</span>
            </div>
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: `${executionProgress}%` }"></div>
              <div class="progress-glow"></div>
            </div>
            <div class="panel-stats">
              <span class="stats-item">{{ completedNodes }} / {{ totalNodes }} 节点完成</span>
            </div>
          </div>
        </Transition>

        <!-- 执行结果面板 -->
        <Transition name="slide-up">
          <div v-if="executionResult" class="result-panel" :class="{ success: executionResult.success, failure: !executionResult.success }">
            <div class="result-header">
              <span class="result-icon">
                <svg v-if="executionResult.success" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                  <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="15" y1="9" x2="9" y2="15"></line>
                  <line x1="9" y1="9" x2="15" y2="15"></line>
                </svg>
              </span>
              <span class="result-title">{{ executionResult.success ? '执行成功' : '执行失败' }}</span>
            </div>
            <div class="result-body" v-if="executionResult.output">
              <pre>{{ formatResult(executionResult.output) }}</pre>
            </div>
            <div class="result-error" v-if="executionResult.error">{{ executionResult.error }}</div>
          </div>
        </Transition>
      </div>

      <!-- 无工作流时显示空状态 -->
      <div v-else class="dag-empty">
        <div class="empty-visual">
          <div class="visual-grid">
            <div class="grid-node node-skill">
              <div class="node-pulse"></div>
              <span>⚡</span>
            </div>
            <div class="grid-line line-1"></div>
            <div class="grid-node node-agent">
              <div class="node-pulse"></div>
              <span>◈</span>
            </div>
            <div class="grid-line line-2"></div>
            <div class="grid-node node-skill">
              <div class="node-pulse"></div>
              <span>⚡</span>
            </div>
          </div>
        </div>
        <div class="empty-content">
          <h3 class="empty-title">工作流可视化</h3>
          <p class="empty-desc">在左侧对话中描述你的需求，工作流结构将在这里实时呈现</p>
          <button class="test-btn" @click="loadTestWorkflow">加载测试数据</button>
        </div>
      </div>
    </div>

    <!-- 执行参数弹窗 -->
    <Transition name="fade">
      <div v-if="showExecuteDialog" class="execute-dialog-overlay" @click.self="showExecuteDialog = false">
        <div class="execute-dialog">
          <div class="dialog-header">
            <span class="dialog-title">执行参数</span>
            <button class="dialog-close" @click="showExecuteDialog = false">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
          <div class="dialog-body">
            <div class="dialog-workflow-name">{{ currentWorkflow?.name }}</div>
            <div class="dialog-desc">请输入以下参数以执行工作流：</div>
            <div class="params-form">
              <div v-for="(schema, key) in currentWorkflow?.userInputSchema" :key="key" class="param-field">
                <label class="param-label">
                  <span class="param-name">{{ key }}</span>
                  <span v-if="schema.required" class="param-required">*</span>
                </label>
                <input
                  v-model="executeParams[key]"
                  type="text"
                  class="param-input"
                  :placeholder="schema.description || `请输入 ${key}`"
                />
              </div>
            </div>
          </div>
          <div class="dialog-footer">
            <button class="btn-cancel" @click="showExecuteDialog = false">取消</button>
            <button class="btn-execute" @click="submitExecution">开始执行</button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../user/stores'
import { useWorkflowStore } from './stores'
import { chatApi } from '../api'
import { createGatewayClient, getGatewayClient, extractText } from '../utils/gateway-ws'
import { renderMessageContent } from '../utils/markdown'
import axios from 'axios'

const userStore = useUserStore()
const workflowStore = useWorkflowStore()
const PROMETHEUS_AGENT_ID = 'prometheus'

// 从 store 获取状态
const messages = computed(() => workflowStore.messages)
const currentWorkflow = computed(() => workflowStore.currentWorkflow)
const nodeStatus = computed(() => workflowStore.nodeStatus)
const executionResult = computed(() => workflowStore.executionResult)
const gatewayConnected = computed(() => workflowStore.gatewayConnected)
const sessionKey = computed(() => workflowStore.sessionKey)
const pendingRequests = computed(() => workflowStore.pendingRequests)
const thinking = computed(() => workflowStore.thinking)
const streamContent = computed(() => workflowStore.streamContent)

// 本地 UI 状态（不需要持久化）
const inputText = ref('')
const inputFocused = ref(false)
const messagesRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)
const canvasRef = ref<HTMLElement | null>(null)

const executing = ref(false)
let client: ReturnType<typeof createGatewayClient> | null = null

// 执行参数弹窗
const showExecuteDialog = ref(false)
const executeParams = ref<Record<string, string>>({})

// DAG layout params
const nodeWidth = 160
const nodeHeight = 56
const horizontalGap = 48
const verticalGap = 24
const canvasPadding = 32

// Computed
const userInitial = computed(() => userStore.user?.displayName?.charAt(0) || 'U')
const userName = computed(() => userStore.user?.displayName || 'User')
const canSubmit = computed(() => inputText.value.trim() && !thinking.value && !executing.value && gatewayConnected.value)

const layoutNodes = computed(() => {
  if (!currentWorkflow.value) return []
  const nodes = currentWorkflow.value.nodes || []
  const edges = currentWorkflow.value.edges || []
  const graph: Record<string, string[]> = {}
  const inDegree: Record<string, number> = {}

  nodes.forEach((n: any) => { graph[n.id] = []; inDegree[n.id] = 0 })
  edges.forEach((e: any) => { graph[e.from].push(e.to); inDegree[e.to]++ })

  const levels: Record<string, number> = {}
  let currentLevel = 0
  const queue = nodes.filter((n: any) => inDegree[n.id] === 0).map((n: any) => n.id)

  while (queue.length > 0) {
    const nextQueue: string[] = []
    queue.forEach(id => {
      levels[id] = currentLevel
      graph[id].forEach(toId => {
        inDegree[toId]--
        if (inDegree[toId] === 0) nextQueue.push(toId)
      })
    })
    queue.length = 0
    queue.push(...nextQueue)
    currentLevel++
  }

  const positions: Record<string, { x: number; y: number }> = {}
  const levelCounts: Record<number, number> = {}

  nodes.forEach((n: any) => {
    const level = levels[n.id] || 0
    levelCounts[level] = (levelCounts[level] || 0)
    positions[n.id] = {
      x: canvasPadding + level * (nodeWidth + horizontalGap),
      y: canvasPadding + levelCounts[level] * (nodeHeight + verticalGap)
    }
    levelCounts[level]++
  })

  return nodes.map((n: any) => ({
    ...n,
    x: positions[n.id]?.x || canvasPadding,
    y: positions[n.id]?.y || canvasPadding,
    level: levels[n.id] || 0
  }))
})

const layoutEdges = computed(() => {
  if (!currentWorkflow.value || !layoutNodes.value.length) return []
  const positions = layoutNodes.value.reduce((acc, n) => {
    acc[n.id] = { x: n.x, y: n.y }
    return acc
  }, {} as Record<string, { x: number; y: number }>)

  return (currentWorkflow.value.edges || []).map((e: any) => {
    const from = positions[e.from]
    const to = positions[e.to]
    if (!from || !to) return { from: e.from, to: e.to, path: '' }
    const startX = from.x + nodeWidth
    const startY = from.y + nodeHeight / 2
    const endX = to.x
    const endY = to.y + nodeHeight / 2
    const midX = (startX + endX) / 2
    return { from: e.from, to: e.to, path: `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}` }
  })
})

const canvasWidth = computed(() => {
  if (!layoutNodes.value.length) return 400
  return Math.max(Math.max(...layoutNodes.value.map(n => n.x)) + nodeWidth + canvasPadding, 400)
})

const canvasHeight = computed(() => {
  if (!layoutNodes.value.length) return 300
  return Math.max(Math.max(...layoutNodes.value.map(n => n.y)) + nodeHeight + canvasPadding, 300)
})

const totalNodes = computed(() => currentWorkflow.value?.nodes?.length || 0)
const completedNodes = computed(() => Object.values(nodeStatus.value).filter(s => s === 'completed').length)
const executionProgress = computed(() => totalNodes.value === 0 ? 0 : Math.round((completedNodes.value / totalNodes.value) * 100))

// Methods
function getTime(): string {
  const now = new Date()
  return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`
}

/**
 * 转换节点 ID：后端 node_1 → 前端 node-0
 * 后端格式: node_1, node_2, ...
 * 前端格式: node-0, node-1, ...
 */
function convertNodeId(backendNodeId: string): string {
  // node_1 → node-0 (减1因为后端从1开始，前端从0开始)
  const match = backendNodeId.match(/node_(\d+)/)
  if (match) {
    const index = parseInt(match[1]) - 1
    return `node-${index}`
  }
  // 如果已经是前端格式，直接返回
  if (backendNodeId.startsWith('node-')) {
    return backendNodeId
  }
  return backendNodeId
}

function formatResult(output: any): string {
  if (typeof output === 'string') return output
  return JSON.stringify(output, null, 2)
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTo({ top: messagesRef.value.scrollHeight, behavior: 'smooth' })
    }
  })
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function autoResize() {
  nextTick(() => {
    if (inputRef.value) {
      inputRef.value.style.height = 'auto'
      inputRef.value.style.height = Math.min(inputRef.value.scrollHeight, 120) + 'px'
    }
  })
}

function getNodeClass(node: any): string {
  const status = nodeStatus.value[node.id]
  if (status === 'running') return 'running'
  if (status === 'completed') return 'completed'
  if (status === 'failed') return 'failed'
  return ''
}

function getEdgeClass(edge: any): string {
  const fromStatus = nodeStatus.value[edge.from]
  const toStatus = nodeStatus.value[edge.to]
  if (fromStatus === 'completed' && toStatus === 'running') return 'active flowing'
  if (fromStatus === 'completed' && toStatus === 'completed') return 'active'
  return ''
}

async function sendMessage() {
  if (!canSubmit.value || !client) return
  const text = inputText.value.trim()
  inputText.value = ''
  autoResize()

  // 生成 requestId，用于关联 workflow 创建
  const requestId = crypto.randomUUID().slice(0, 8) // 短 ID，便于命名
  const messageWithRequestId = `${text}\n\n[REQUEST_ID: ${requestId}]`

  // 存储 pending request
  workflowStore.addPendingRequest(requestId)

  workflowStore.addMessage({ id: crypto.randomUUID(), role: 'user', content: text, time: getTime() })
  scrollToBottom()

  workflowStore.setStreaming(true, '')

  try {
    await client.request('chat.send', {
      sessionKey: sessionKey.value,
      message: messageWithRequestId,
      deliver: false,
      idempotencyKey: crypto.randomUUID()
    })
    console.log('[WorkflowPage] Sent message with requestId:', requestId)
  } catch (e: any) {
    workflowStore.setStreaming(false)
    workflowStore.removePendingRequest(requestId)
    workflowStore.addMessage({ id: crypto.randomUUID(), role: 'assistant', content: `❌ 请求失败: ${e.message}`, time: getTime() })
    scrollToBottom()
  }
}

async function onChatEvent(evt: any) {
  if (evt.event !== 'chat') return
  const payload = evt.payload
  if (payload.sessionKey !== sessionKey.value) return

  if (payload.state === 'delta') {
    const text = extractText(payload.message)
    if (typeof text === 'string') {
      workflowStore.setStreaming(true, text)
      scrollToBottom()
    }
  } else if (payload.state === 'final') {
    const text = extractText(payload.message) || streamContent.value
    if (text?.trim()) {
      await parseWorkflowResponse(text)
      workflowStore.addMessage({ id: crypto.randomUUID(), role: 'assistant', content: text, time: getTime() })
    }
    workflowStore.setStreaming(false)
    scrollToBottom()
  } else if (payload.state === 'error') {
    workflowStore.setStreaming(false)
    workflowStore.addMessage({ id: crypto.randomUUID(), role: 'assistant', content: `❌ ${payload.errorMessage || '错误'}`, time: getTime() })
    scrollToBottom()
  }
}

async function parseWorkflowResponse(text: string) {
  console.log('[WorkflowPage] parseWorkflowResponse called, text:', text.substring(0, 500))

  // 解析节点状态标记，实时更新 DAG
  // 格式: [NODE_START: node_1] 或 [NODE_COMPLETE: node_1] 或 [NODE_ERROR: node_1]
  const nodeStartMatches = text.matchAll(/\[NODE_START:\s+(\S+)\]/g)
  const nodeCompleteMatches = text.matchAll(/\[NODE_COMPLETE:\s+(\S+)\]/g)
  const nodeErrorMatches = text.matchAll(/\[NODE_ERROR:\s+(\S+)\]/g)

  for (const match of nodeStartMatches) {
    const nodeId = match[1]
    // 将后端的 node_1 格式转换为前端的 node-0 格式
    const frontendNodeId = convertNodeId(nodeId)
    console.log('[WorkflowPage] Node started:', frontendNodeId)
    workflowStore.updateNodeStatus(frontendNodeId, 'running')
  }

  for (const match of nodeCompleteMatches) {
    const nodeId = match[1]
    if (nodeId === 'final') continue // 忽略 final 标记
    const frontendNodeId = convertNodeId(nodeId)
    console.log('[WorkflowPage] Node completed:', frontendNodeId)
    workflowStore.updateNodeStatus(frontendNodeId, 'completed')
  }

  for (const match of nodeErrorMatches) {
    const nodeId = match[1]
    const frontendNodeId = convertNodeId(nodeId)
    console.log('[WorkflowPage] Node error:', frontendNodeId)
    workflowStore.updateNodeStatus(frontendNodeId, 'failed')
  }

  // 解析工作流开始标记
  const workflowStartMatch = text.match(/\[WORKFLOW_START:\s+(\S+)\]/)
  if (workflowStartMatch) {
    console.log('[WorkflowPage] Workflow started:', workflowStartMatch[1])
    // 清除之前的执行状态
    currentWorkflow.value?.nodes?.forEach((n: any) => {
      workflowStore.updateNodeStatus(n.id, 'pending')
    })
    workflowStore.setExecutionResult(null)
  }

  // 检查执行完成标记
  const executionCompleteMatch = text.match(/\[EXECUTION_COMPLETE:\s+(\S+)\]/)
  if (executionCompleteMatch) {
    const workflowName = executionCompleteMatch[1]
    console.log('[WorkflowPage] Found execution complete marker:', workflowName)

    // 标记所有节点完成
    currentWorkflow.value?.nodes?.forEach((n: any) => {
      workflowStore.updateNodeStatus(n.id, 'completed')
    })
    workflowStore.setExecutionResult({ success: true, output: text })
    workflowStore.addMessage({
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '✅ 工作流执行完成！',
      time: getTime()
    })
    scrollToBottom()
    return
  }

  // 检查执行失败标记
  const executionErrorMatch = text.match(/\[EXECUTION_ERROR:\s+(.+)\]/)
  if (executionErrorMatch) {
    const errorMsg = executionErrorMatch[1]
    console.log('[WorkflowPage] Found execution error marker:', errorMsg)

    workflowStore.setExecutionResult({ success: false, error: errorMsg })
    workflowStore.addMessage({
      id: crypto.randomUUID(),
      role: 'assistant',
      content: `❌ 执行失败: ${errorMsg}`,
      time: getTime()
    })
    scrollToBottom()
    return
  }

  // 检查是否有 pending requests（最近 2 分钟内发送的）
  const now = new Date()
  const recentRequests = Array.from(pendingRequests.value.entries())
    .filter(([id, req]) => {
      const sentAt = new Date(req.sentAt)
      return (now.getTime() - sentAt.getTime()) < 120000
    })
    .sort((a, b) => new Date(b[1].sentAt).getTime() - new Date(a[1].sentAt).getTime())

  // 方式1：匹配约定的标记格式（最可靠）
  const markerMatch = text.match(/\[WORKFLOW_CREATED:\s+(\S+)\]/)
  if (markerMatch) {
    const workflowName = markerMatch[1]
    console.log('[WorkflowPage] Found workflow marker:', workflowName)

    if (recentRequests.length > 0) {
      const [requestId] = recentRequests[0]
      workflowStore.removePendingRequest(requestId)
    }

    await fetchWorkflowFromApi(workflowName)
    return
  }

  // 方式2：匹配表格中的工作流名称（更灵活）
  // 支持格式：| 名称 | workflow-name | 或 | 名称 | workflow-name |
  const tableNameMatch = text.match(/\|\s*名称\s*\|\s*([^\s|]+)\s*\|/)
  if (tableNameMatch) {
    const workflowName = tableNameMatch[1].trim()
    console.log('[WorkflowPage] Found workflow name from table:', workflowName)

    if (recentRequests.length > 0) {
      const [requestId] = recentRequests[0]
      workflowStore.removePendingRequest(requestId)
    }

    await fetchWorkflowFromApi(workflowName)
    return
  }

  // 方式3：匹配 "工作流创建成功" 后面的名称
  const successNameMatch = text.match(/工作流创建成功[^\n]*\n[^\n]*?(\S+)/)
  if (successNameMatch) {
    const workflowName = successNameMatch[1]
    console.log('[WorkflowPage] Found workflow name after success:', workflowName)

    if (recentRequests.length > 0) {
      const [requestId] = recentRequests[0]
      workflowStore.removePendingRequest(requestId)
    }

    await fetchWorkflowFromApi(workflowName)
    return
  }

  // 方式4：如果有 requestId，从 workflow list 中查找
  if (recentRequests.length > 0) {
    const [requestId] = recentRequests[0]
    console.log('[WorkflowPage] Searching workflow with requestId:', requestId)

    try {
      const res = await axios.get('/api/workflow/list')
      if (res.data?.success && res.data?.data) {
        const matched = res.data.data.find(w => w.name.includes(requestId))
        if (matched) {
          console.log('[WorkflowPage] Found workflow by requestId in list:', matched.name)
          workflowStore.removePendingRequest(requestId)
          await fetchWorkflowFromApi(matched.name)
          return
        }
      }
    } catch (e) {
      console.log('[WorkflowPage] Failed to search by requestId:', e)
    }
  }

  // 方式5：检测成功关键词，fetch 最新
  if (text.includes('工作流创建成功') || text.includes('创建成功') || text.includes('✅')) {
    console.log('[WorkflowPage] Detected workflow creation success, fetching latest')
    await fetchLatestWorkflow()
  }
}

async function fetchLatestWorkflow() {
  try {
    const res = await axios.get('/api/workflow/list')
    if (res.data?.success && res.data?.data?.length > 0) {
      // 按时间降序，取最新的（排除测试用的）
      const recent = res.data.data.filter(w => !w.name.startsWith('test'))
      if (recent.length > 0) {
        // 检查是否是最近 60 秒内创建的
        const now = new Date()
        const latest = recent[0]
        const createdTime = new Date(latest.created_at)
        const diffSeconds = (now.getTime() - createdTime.getTime()) / 1000

        if (diffSeconds < 60) {
          console.log('[WorkflowPage] Found recent workflow:', latest.name)
          await fetchWorkflowFromApi(latest.name)
        } else {
          console.log('[WorkflowPage] No workflow created in last 60 seconds')
        }
      }
    }
  } catch (e: any) {
    console.error('[WorkflowPage] Failed to fetch workflow list:', e)
  }
}

async function fetchWorkflowFromApi(name: string) {
  console.log('[WorkflowPage] fetchWorkflowFromApi:', name)
  try {
    const res = await axios.get(`/api/workflow/${name}`)
    console.log('[WorkflowPage] API response:', res.data)

    if (res.data?.success && res.data?.data?.workflow) {
      const workflow = res.data.data.workflow
      console.log('[WorkflowPage] workflow data:', workflow)
      // 将后端的 node_1, node_2 格式转换为前端 node-0, node-1 格式
      const nodes = workflow.nodes.map((n: any, i: number) => ({
        id: `node-${i}`,
        originalId: n.id,  // 保存原始 ID 用于变量绑定
        name: n.name,
        type: n.type,
        skill: n.skill,
        agent_id: n.agent_id,
        input: n.input
      }))
      // 转换边
      const edges = workflow.edges.map((e: any) => {
        const fromIdx = workflow.nodes.findIndex((n: any) => n.id === e.from)
        const toIdx = workflow.nodes.findIndex((n: any) => n.id === e.to)
        return { from: `node-${fromIdx}`, to: `node-${toIdx}` }
      })

      console.log('[WorkflowPage] Setting currentWorkflow:', { nodes, edges })
      workflowStore.setWorkflow({
        name: workflow.name,
        description: workflow.description,
        nodes,
        edges,
        userInputSchema: workflow.userInputSchema
      })
    } else {
      // 精确匹配失败，获取最新创建的工作流
      console.log('[WorkflowPage] Exact match failed, fetching latest workflow')
      await fetchLatestWorkflow()
    }
  } catch (e: any) {
    console.error('[WorkflowPage] Failed to fetch workflow:', e)
    // 失败时获取最新工作流
    await fetchLatestWorkflow()
  }
}

async function quickPrompt(text: string) {
  inputText.value = text
  await sendMessage()
}

function loadTestWorkflow() {
  console.log('[WorkflowPage] Loading test workflow')
  workflowStore.setWorkflow({
    name: 'test-workflow',
    description: '测试工作流',
    nodes: [
      { id: 'node-0', name: '搜索资料', type: 'skill', skill: 'baidu-search' },
      { id: 'node-1', name: '生成文章', type: 'agent', agent_id: 'writer' },
      { id: 'node-2', name: '发布内容', type: 'skill', skill: 'wordpress-publish' }
    ],
    edges: [
      { from: 'node-0', to: 'node-1' },
      { from: 'node-1', to: 'node-2' }
    ]
  })
  console.log('[WorkflowPage] Test workflow loaded:', currentWorkflow.value)
}

async function executeWorkflow() {
  if (!currentWorkflow.value || executing.value || thinking.value) return

  // 检查是否有需要用户输入的参数
  const schema = currentWorkflow.value.userInputSchema || {}
  // API 返回的 schema 没有 required 字段，没有 default 的字段就是必需的
  const requiredParams = Object.entries(schema)
    .filter(([key, val]) => !val?.default)
    .map(([key]) => key)

  console.log('[WorkflowPage] executeWorkflow - schema:', schema)
  console.log('[WorkflowPage] executeWorkflow - requiredParams:', requiredParams)

  if (requiredParams.length > 0) {
    // 初始化参数表单
    executeParams.value = {}
    Object.keys(schema).forEach(key => {
      executeParams.value[key] = schema[key]?.default || ''
    })
    showExecuteDialog.value = true
  } else {
    // 无需参数，直接执行
    workflowStore.addMessage({
      id: crypto.randomUUID(),
      role: 'user',
      content: `执行工作流「${currentWorkflow.value.name}」`,
      time: getTime()
    })
    scrollToBottom()
    await sendExecutionRequest({})
  }
}

async function submitExecution() {
  showExecuteDialog.value = false

  const schema = currentWorkflow.value?.userInputSchema || {}
  const missingParams = Object.entries(schema)
    .filter(([key, val]) => val?.required && !executeParams.value[key])
    .map(([key]) => key)

  if (missingParams.length > 0) {
    ElMessage.warning(`请填写必填参数：${missingParams.join(', ')}`)
    return
  }

  // 构建执行消息
  const paramsStr = Object.entries(executeParams.value)
    .filter(([key, val]) => val)
    .map(([key, val]) => `${key}: ${val}`)
    .join('\n')

  workflowStore.addMessage({
    id: crypto.randomUUID(),
    role: 'user',
    content: `执行工作流「${currentWorkflow.value?.name}」\n${paramsStr}`,
    time: getTime()
  })
  scrollToBottom()

  await sendExecutionRequest(executeParams.value)
}

async function sendExecutionRequest(userInput: Record<string, string>) {
  if (!client || !sessionKey.value || !currentWorkflow.value) {
    ElMessage.error('无法执行：连接或工作流信息缺失')
    return
  }

  // 清除之前的执行状态
  workflowStore.setExecutionResult(null)
  currentWorkflow.value.nodes?.forEach((n: any) => {
    workflowStore.updateNodeStatus(n.id, 'pending')
  })

  workflowStore.setStreaming(true, '')
  workflowStore.addMessage({
    id: crypto.randomUUID(),
    role: 'assistant',
    content: '⚡ 正在执行工作流...',
    time: getTime()
  })
  scrollToBottom()

  // 构建执行请求消息
  const executionMessage = `执行工作流 ${currentWorkflow.value.name}
${Object.entries(userInput).length > 0 ? '参数：\n' + Object.entries(userInput).map(([k, v]) => `- ${k}: ${v}`).join('\n') : ''}`

  try {
    await client.request('chat.send', {
      sessionKey: sessionKey.value,
      message: executionMessage,
      deliver: false,
      idempotencyKey: crypto.randomUUID()
    })
    console.log('[WorkflowPage] Execution request sent:', currentWorkflow.value.name)
  } catch (e: any) {
    workflowStore.setStreaming(false)
    workflowStore.addMessage({
      id: crypto.randomUUID(),
      role: 'assistant',
      content: `❌ 执行请求失败: ${e.message}`,
      time: getTime()
    })
    scrollToBottom()
  }
}


function clearWorkflow() {
  workflowStore.clearWorkflow()
}

async function initGateway() {
  const existingClient = getGatewayClient()
  if (existingClient && existingClient.connected) {
    console.log('[WorkflowPage] Reusing existing Gateway connection')
    client = existingClient
    // 更新事件回调
    ;(client as any).opts.onEvent = onChatEvent
    workflowStore.setSession(sessionKey.value, true)

    // 如果已有 sessionKey，重新订阅；否则创建新的
    if (sessionKey.value) {
      try {
        await client.request('sessions.subscribe', { keys: [sessionKey.value] })
        console.log('[WorkflowPage] Session re-subscribed:', sessionKey.value)
      } catch (e) {
        console.error('[WorkflowPage] Re-subscribe failed:', e)
        // 如果订阅失败，可能需要创建新 session
        await initSession()
      }
    } else {
      await initSession()
    }
    return
  }

  try {
    const res = await chatApi.getConfig()
    if (res.data.success) {
      const { gatewayUrl, gatewayToken } = res.data.data
      await new Promise<void>((resolve) => {
        client = createGatewayClient({
          url: gatewayUrl,
          token: gatewayToken,
          onHello: () => { workflowStore.setSession(sessionKey.value, true); resolve() },
          onEvent: onChatEvent,
          onClose: () => { workflowStore.setSession(sessionKey.value, false) }
        })
        client.start()
        setTimeout(() => resolve(), 3000)
      })
      await initSession()
    }
  } catch (e) {
    console.error('Connect gateway failed:', e)
    ElMessage.error('连接 Gateway 失败')
  }
}

async function initSession() {
  if (!client) return
  // 如果已有 sessionKey，不创建新的（可能正在 streaming）
  if (sessionKey.value) {
    console.log('[WorkflowPage] Using existing session:', sessionKey.value)
    return
  }

  const sessionId = crypto.randomUUID()
  const newSessionKey = `agent:${PROMETHEUS_AGENT_ID}:webchat:${sessionId}`
  workflowStore.setSession(newSessionKey, gatewayConnected.value)
  try {
    await client.request('sessions.subscribe', { keys: [newSessionKey] })
    console.log('[WorkflowPage] Session subscribed:', newSessionKey)
  } catch (e) {
    console.error('Subscribe session failed:', e)
  }
}

onMounted(async () => {
  // 从 sessionStorage 恢复状态
  workflowStore.loadFromStorage()
  await initGateway()
  if (inputRef.value) inputRef.value.focus()
})

onUnmounted(() => {
  // 保存状态（已在 store 的各个方法中自动保存）
  // 不停止 Gateway 连接，让其他组件复用
})
</script>

<style scoped>
.workflow-page {
  --bg-page: #f7f8fa;
  --bg-card: #ffffff;
  --bg-hover: #f0f2f5;
  --bg-active: #e8f4ff;
  --border-subtle: rgba(0, 0, 0, 0.06);
  --border-light: rgba(0, 0, 0, 0.08);
  --text-primary: #1a1a1a;
  --text-secondary: #5c5c5c;
  --text-tertiary: #8c8c8c;
  --text-placeholder: #b3b3b3;
  --accent: #3370ff;
  --accent-soft: rgba(51, 112, 255, 0.08);
  --accent-medium: rgba(51, 112, 255, 0.15);
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04);
  --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 4px 16px rgba(0, 0, 0, 0.08);
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;

  display: flex;
  height: calc(100vh - 60px);
  background: var(--bg-page);
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
}

/* ==================== 左侧对话面板 ==================== */
.chat-panel {
  width: 38%;
  min-width: 380px;
  max-width: 440px;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border-right: 1px solid var(--border-light);
}

/* Header */
.chat-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--bg-card);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-avatar {
  width: 40px;
  height: 40px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #3370ff 0%, #2b5ce6 100%);
  border-radius: var(--radius-md);
}

.avatar-ring {
  position: absolute;
  inset: -2px;
  border-radius: 12px;
  border: 2px solid var(--accent-soft);
  animation: ring-pulse 2s ease-in-out infinite;
}

@keyframes ring-pulse {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.02); }
}

.avatar-letter {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.header-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.header-desc {
  font-size: 12px;
  color: var(--text-tertiary);
}

.connection-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: var(--radius-sm);
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
}

.connection-badge.active {
  background: var(--accent-soft);
  border-color: var(--accent-medium);
}

.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-tertiary);
}

.connection-badge.active .badge-dot {
  background: var(--accent);
  animation: dot-blink 1s ease-in-out infinite;
}

@keyframes dot-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.badge-text {
  font-size: 11px;
  color: var(--text-tertiary);
}

.connection-badge.active .badge-text {
  color: var(--accent);
}

/* Messages Area */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  scrollbar-width: thin;
  scrollbar-color: var(--border-light) transparent;
}

.messages-area::-webkit-scrollbar {
  width: 6px;
}

.messages-area::-webkit-scrollbar-track {
  background: transparent;
}

.messages-area::-webkit-scrollbar-thumb {
  background: var(--border-light);
  border-radius: 3px;
}

/* Welcome State */
.welcome-state {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding-top: 20px;
}

.welcome-brand {
  text-align: center;
  padding: 24px 0;
}

.brand-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto 12px;
  color: var(--accent);
}

.brand-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.brand-subtitle {
  font-size: 13px;
  color: var(--text-tertiary);
}

.welcome-prompts {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.prompts-label {
  font-size: 12px;
  color: var(--text-tertiary);
  padding-left: 4px;
  margin-bottom: 4px;
}

.prompt-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s ease;
}

.prompt-card:hover {
  background: var(--bg-hover);
  border-color: var(--accent);
  box-shadow: var(--shadow-sm);
}

.prompt-number {
  font-size: 12px;
  font-weight: 600;
  color: var(--accent);
  opacity: 0.7;
}

.prompt-content {
  flex: 1;
}

.prompt-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.prompt-desc {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

/* Message Block */
.message-block {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.message-block.user {
  flex-direction: row-reverse;
}

.message-gutter {
  flex-shrink: 0;
}

.gutter-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
}

.gutter-avatar.assistant {
  background: linear-gradient(135deg, #3370ff 0%, #2b5ce6 100%);
}

.gutter-avatar.user {
  background: var(--bg-hover);
}

.avatar-system {
  font-size: 13px;
  font-weight: 600;
  color: #ffffff;
}

.avatar-user {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.message-body {
  flex: 1;
  max-width: 85%;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.sender-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.send-time {
  font-size: 11px;
  color: var(--text-tertiary);
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--bg-hover);
}

.status-badge.reading {
  background: var(--accent-soft);
}

.status-badge.streaming {
  background: var(--accent-medium);
}

.status-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
  animation: status-pulse 1s ease-in-out infinite;
}

@keyframes status-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.8); }
}

.status-text {
  font-size: 10px;
  color: var(--accent);
}

.typing-cursor {
  width: 2px;
  height: 10px;
  background: var(--accent);
  animation: cursor-blink 0.8s step-end infinite;
}

@keyframes cursor-blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.message-content {
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--bg-hover);
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary);
}

.message-content :deep(.markdown-body) {
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif;
  font-size: 14px;
  line-height: 1.6;
}

.message-content :deep(.markdown-body p) {
  margin: 0;
}

.message-content :deep(.markdown-body ul),
.message-content :deep(.markdown-body ol) {
  margin: 8px 0;
  padding-left: 20px;
}

.message-content :deep(.markdown-body code) {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 13px;
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 4px;
  border-radius: 4px;
}

.message-block.user .message-content :deep(.markdown-body code) {
  background: rgba(255, 255, 255, 0.2);
}

.message-content :deep(.markdown-body table) {
  margin: 8px 0;
  border-collapse: collapse;
  font-size: 13px;
}

.message-content :deep(.markdown-body th),
.message-content :deep(.markdown-body td) {
  padding: 6px 10px;
  border: 1px solid var(--border-light);
}

.message-block.user .message-content :deep(.markdown-body th),
.message-block.user .message-content :deep(.markdown-body td) {
  border-color: rgba(255, 255, 255, 0.2);
}

.message-block.user .message-content {
  background: var(--accent);
  color: #ffffff;
}

.streaming-content {
  background: var(--bg-active);
  border: 1px solid var(--accent-soft);
}

/* Reading Indicator */
.reading-indicator {
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 10px 12px;
  background: var(--bg-active);
  border: 1px solid var(--accent-soft);
  border-radius: var(--radius-md);
}

.pulse-bar {
  width: 3px;
  height: 14px;
  background: var(--accent);
  border-radius: 2px;
  animation: bar-pulse 1.2s ease-in-out infinite;
}

.pulse-bar:nth-child(1) { animation-delay: 0s; }
.pulse-bar:nth-child(2) { animation-delay: 0.2s; }
.pulse-bar:nth-child(3) { animation-delay: 0.4s; }

@keyframes bar-pulse {
  0%, 100% { transform: scaleY(0.4); opacity: 0.4; }
  50% { transform: scaleY(1); opacity: 1; }
}

/* Workflow Indicator */
.workflow-indicator {
  padding: 10px 20px;
  background: var(--accent-soft);
  border-top: 1px solid var(--accent-medium);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.indicator-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.indicator-icon {
  width: 18px;
  height: 18px;
  color: var(--accent);
}

.indicator-info {
  display: flex;
  flex-direction: column;
}

.indicator-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--accent);
}

.indicator-stats {
  font-size: 11px;
  color: var(--text-tertiary);
}

.indicator-close {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all 0.2s;
}

.indicator-close:hover {
  color: #f56c6c;
  background: rgba(245, 108, 108, 0.1);
}

/* Input Area */
.input-area {
  padding: 14px 20px 10px;
  background: var(--bg-card);
  border-top: 1px solid var(--border-subtle);
}

.input-container {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  transition: all 0.2s ease;
}

.input-container.focused {
  background: var(--bg-card);
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.input-container.disabled {
  opacity: 0.5;
  background: var(--bg-hover);
}

.input-container textarea {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-primary);
  resize: none;
  min-height: 20px;
  max-height: 80px;
  outline: none;
  font-family: inherit;
  padding: 0;
  margin: 0;
  vertical-align: middle;
}

.input-container textarea::placeholder {
  color: var(--text-placeholder);
}

.submit-btn {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  border: none;
  background: var(--bg-hover);
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.submit-btn.ready {
  background: var(--accent);
  color: #ffffff;
}

.submit-btn.ready:hover {
  background: #2b5ce6;
  transform: translateY(-1px);
}

.submit-btn:disabled {
  cursor: not-allowed;
}

.input-hint {
  display: flex;
  justify-content: center;
  padding-top: 6px;
  font-size: 11px;
  color: var(--text-tertiary);
}

.hint-offline { color: #f56c6c; }
.hint-processing { color: var(--accent); }

/* ==================== 右侧 DAG 面板 ==================== */
.dag-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg-page);
  overflow: hidden;
}

/* DAG Active */
.dag-active {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 20px;
}

.dag-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
}

.workflow-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.badge-icon {
  width: 16px;
  height: 16px;
  color: var(--accent);
}

.workflow-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  border: none;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn.execute {
  background: var(--accent);
  color: #ffffff;
}

.action-btn.execute:hover:not(:disabled) {
  background: #2b5ce6;
  transform: translateY(-1px);
}

.action-btn.test {
  background: var(--bg-hover);
  color: var(--text-secondary);
}

.action-btn.test:hover {
  background: var(--bg-active);
}

.action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-icon {
  width: 14px;
  height: 14px;
}

.btn-text {
  font-weight: 500;
}

/* DAG Canvas */
.dag-canvas {
  flex: 1;
  overflow: auto;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.dag-svg {
  width: 100%;
  height: 100%;
}

.edge-line {
  fill: none;
  stroke: var(--border-light);
  stroke-width: 2;
  stroke-dasharray: 6 4;
  transition: all 0.3s;
}

.edge-line.active {
  stroke: var(--accent);
  stroke-dasharray: none;
}

.edge-line.flowing {
  animation: flow-dash 1s linear infinite;
}

@keyframes flow-dash {
  from { stroke-dashoffset: 10; }
  to { stroke-dashoffset: 0; }
}

/* Node Card */
.node-card {
  width: 100%;
  height: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  transition: all 0.3s;
  box-shadow: var(--shadow-sm);
}

.node-card:hover {
  border-color: var(--accent-soft);
  box-shadow: var(--shadow-md);
}

.node-card.running {
  border-color: var(--accent);
  background: var(--bg-active);
}

.node-card.completed {
  border-color: #52c41a;
  background: rgba(82, 196, 26, 0.06);
}

.node-card.failed {
  border-color: #f56c6c;
  background: rgba(245, 108, 108, 0.06);
}

.node-type-indicator {
  width: 6px;
  height: 100%;
  border-radius: 3px;
  flex-shrink: 0;
}

.node-type-indicator.skill {
  background: #52c41a;
}

.node-type-indicator.agent {
  background: #fa8c16;
}

.node-content {
  flex: 1;
}

.node-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.node-meta {
  margin-top: 1px;
}

.node-kind {
  font-size: 10px;
  color: var(--text-tertiary);
}

.node-state {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.state-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-tertiary);
}

.state-indicator.running {
  background: var(--accent);
  animation: state-spin 1s linear infinite;
}

@keyframes state-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.state-indicator.completed {
  background: #52c41a;
}

.state-indicator.failed {
  background: #f56c6c;
}

/* Execution Panel */
.execution-panel {
  margin-top: 12px;
  padding: 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.panel-title {
  font-size: 12px;
  color: var(--text-tertiary);
}

.panel-progress {
  font-size: 14px;
  font-weight: 600;
  color: var(--accent);
}

.progress-track {
  height: 4px;
  background: var(--bg-hover);
  border-radius: 2px;
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 2px;
  transition: width 0.3s;
}

.progress-glow {
  position: absolute;
  right: 0;
  top: -2px;
  bottom: -2px;
  width: 16px;
  background: linear-gradient(90deg, transparent, rgba(51, 112, 255, 0.4));
  animation: glow-move 1s ease-in-out infinite;
}

@keyframes glow-move {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}

.panel-stats {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

/* Result Panel */
.result-panel {
  margin-top: 12px;
  padding: 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.result-panel.success {
  border-color: rgba(82, 196, 26, 0.3);
}

.result-panel.failure {
  border-color: rgba(245, 108, 108, 0.3);
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.result-icon {
  width: 16px;
  height: 16px;
}

.result-panel.success .result-icon { color: #52c41a; }
.result-panel.failure .result-icon { color: #f56c6c; }

.result-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.result-body pre {
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-hover);
  padding: 10px;
  border-radius: var(--radius-sm);
  overflow-x: auto;
  margin: 0;
}

.result-error {
  font-size: 12px;
  color: #f56c6c;
}

/* DAG Empty */
.dag-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.empty-visual {
  margin-bottom: 24px;
}

.visual-grid {
  display: flex;
  align-items: center;
  gap: 40px;
  position: relative;
}

.grid-node {
  width: 48px;
  height: 48px;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  opacity: 0.8;
  box-shadow: var(--shadow-sm);
}

.node-skill { color: #52c41a; font-size: 18px; }
.node-agent { color: #fa8c16; font-size: 18px; }

.node-pulse {
  position: absolute;
  inset: -3px;
  border-radius: var(--radius-lg);
  border: 1px solid;
  animation: node-ring 2s ease-in-out infinite;
}

.node-skill .node-pulse { border-color: rgba(82, 196, 26, 0.2); }
.node-agent .node-pulse { border-color: rgba(250, 140, 22, 0.2); }

@keyframes node-ring {
  0%, 100% { opacity: 0; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.08); }
}

.grid-line {
  position: absolute;
  height: 2px;
  background: var(--border-light);
}

.line-1 { width: 28px; left: 60px; top: 23px; }
.line-2 { width: 28px; left: 140px; top: 23px; }

.empty-content {
  text-align: center;
}

.empty-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 6px;
}

.empty-desc {
  font-size: 13px;
  color: var(--text-tertiary);
  margin: 0;
  max-width: 260px;
}

.test-btn {
  margin-top: 14px;
  padding: 8px 18px;
  background: var(--accent);
  color: #ffffff;
  border: none;
  border-radius: var(--radius-md);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.test-btn:hover {
  background: #2b5ce6;
  transform: translateY(-1px);
}

/* Transitions */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.25s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

/* Execute Dialog */
.execute-dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.execute-dialog {
  width: 420px;
  max-width: 90vw;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  animation: dialog-enter 0.2s ease;
}

@keyframes dialog-enter {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-subtle);
}

.dialog-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.dialog-close {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all 0.2s;
}

.dialog-close:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.dialog-close svg {
  width: 16px;
  height: 16px;
}

.dialog-body {
  padding: 16px 18px;
}

.dialog-workflow-name {
  font-size: 13px;
  color: var(--accent);
  font-weight: 500;
  margin-bottom: 4px;
}

.dialog-desc {
  font-size: 13px;
  color: var(--text-tertiary);
  margin-bottom: 14px;
}

.params-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.param-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.param-label {
  display: flex;
  align-items: center;
  gap: 4px;
}

.param-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.param-required {
  font-size: 11px;
  color: #f56c6c;
}

.param-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  font-size: 14px;
  color: var(--text-primary);
  background: var(--bg-card);
  transition: all 0.2s;
}

.param-input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.param-input::placeholder {
  color: var(--text-placeholder);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 18px;
  border-top: 1px solid var(--border-subtle);
}

.btn-cancel {
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-light);
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.btn-execute {
  padding: 8px 20px;
  border-radius: var(--radius-sm);
  border: none;
  background: var(--accent);
  color: #ffffff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-execute:hover {
  background: #2b5ce6;
  transform: translateY(-1px);
}

/* Fade transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
