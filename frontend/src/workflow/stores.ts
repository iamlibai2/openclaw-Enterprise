/**
 * Workflow 页面状态管理
 * 用于保持页面切换后的状态
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  time: string
}

interface Workflow {
  name: string
  description?: string
  nodes: any[]
  edges: any[]
  userInputSchema?: any
}

interface PendingRequest {
  requestId: string
  sentAt: string // ISO string for serialization
  expectedName: string
}

export const useWorkflowStore = defineStore('workflow', () => {
  // 对话历史
  const messages = ref<Message[]>([])

  // 当前 workflow
  const currentWorkflow = ref<Workflow | null>(null)

  // 节点状态
  const nodeStatus = ref<Record<string, string>>({})

  // 执行结果
  const executionResult = ref<any>(null)

  // pending requests（requestId 关联）
  const pendingRequests = ref<Map<string, PendingRequest>>(new Map())

  // session 信息
  const sessionKey = ref<string>('')
  const gatewayConnected = ref<boolean>(false)

  // streaming 状态（正在进行的对话）
  const thinking = ref<boolean>(false)
  const streamContent = ref<string>('')

  /**
   * 从 sessionStorage 恢复状态
   */
  function loadFromStorage() {
    try {
      const stored = sessionStorage.getItem('workflow_state')
      if (stored) {
        const data = JSON.parse(stored)
        messages.value = data.messages || []
        currentWorkflow.value = data.currentWorkflow || null
        nodeStatus.value = data.nodeStatus || {}
        executionResult.value = data.executionResult || null
        sessionKey.value = data.sessionKey || ''
        gatewayConnected.value = data.gatewayConnected || false
        thinking.value = data.thinking || false
        streamContent.value = data.streamContent || ''

        // 恢复 pendingRequests Map
        if (data.pendingRequests) {
          pendingRequests.value = new Map(Object.entries(data.pendingRequests))
        }
      }
    } catch (e) {
      console.error('[WorkflowStore] Failed to load from storage:', e)
    }
  }

  /**
   * 保存状态到 sessionStorage
   */
  function saveToStorage() {
    try {
      const data = {
        messages: messages.value,
        currentWorkflow: currentWorkflow.value,
        nodeStatus: nodeStatus.value,
        executionResult: executionResult.value,
        sessionKey: sessionKey.value,
        gatewayConnected: gatewayConnected.value,
        pendingRequests: Object.fromEntries(pendingRequests.value),
        thinking: thinking.value,
        streamContent: streamContent.value
      }
      sessionStorage.setItem('workflow_state', JSON.stringify(data))
    } catch (e) {
      console.error('[WorkflowStore] Failed to save to storage:', e)
    }
  }

  /**
   * 添加消息
   */
  function addMessage(msg: Message) {
    messages.value.push(msg)
    saveToStorage()
  }

  /**
   * 设置当前 workflow
   */
  function setWorkflow(workflow: Workflow | null) {
    currentWorkflow.value = workflow
    if (workflow) {
      nodeStatus.value = {}
    }
    saveToStorage()
  }

  /**
   * 清除 workflow
   */
  function clearWorkflow() {
    currentWorkflow.value = null
    nodeStatus.value = {}
    executionResult.value = null
    saveToStorage()
  }

  /**
   * 更新节点状态
   */
  function updateNodeStatus(nodeId: string, status: string) {
    nodeStatus.value[nodeId] = status
    saveToStorage()
  }

  /**
   * 设置执行结果
   */
  function setExecutionResult(result: any) {
    executionResult.value = result
    saveToStorage()
  }

  /**
   * 添加 pending request
   */
  function addPendingRequest(requestId: string) {
    pendingRequests.value.set(requestId, {
      requestId,
      sentAt: new Date().toISOString(),
      expectedName: ''
    })
    saveToStorage()
  }

  /**
   * 移除 pending request
   */
  function removePendingRequest(requestId: string) {
    pendingRequests.value.delete(requestId)
    saveToStorage()
  }

  /**
   * 设置 session
   */
  function setSession(key: string, connected: boolean) {
    sessionKey.value = key
    gatewayConnected.value = connected
    saveToStorage()
  }

  /**
   * 清除所有状态
   */
  function clearAll() {
    messages.value = []
    currentWorkflow.value = null
    nodeStatus.value = {}
    executionResult.value = null
    pendingRequests.value = new Map()
    thinking.value = false
    streamContent.value = ''
    saveToStorage()
  }

  /**
   * 设置 streaming 状态
   */
  function setStreaming(isThinking: boolean, content: string = '') {
    thinking.value = isThinking
    streamContent.value = content
    saveToStorage()
  }

  return {
    // 状态
    messages,
    currentWorkflow,
    nodeStatus,
    executionResult,
    pendingRequests,
    sessionKey,
    gatewayConnected,
    thinking,
    streamContent,
    // 方法
    loadFromStorage,
    saveToStorage,
    addMessage,
    setWorkflow,
    clearWorkflow,
    updateNodeStatus,
    setExecutionResult,
    addPendingRequest,
    removePendingRequest,
    setSession,
    clearAll,
    setStreaming
  }
})