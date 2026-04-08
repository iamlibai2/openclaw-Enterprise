/**
 * SSE 客户端
 *
 * 提供与后端 SSE 端点的连接能力
 */

export interface SSEEvent {
  type: string
  timestamp: string
  data: any
}

export type SSEEventCallback = (data: any) => void

export class SSEClient {
  private eventSource: EventSource | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private listeners: Map<string, Set<SSEEventCallback>> = new Map()
  private statusListeners: Set<(connected: boolean) => void> = new Set()
  private connected = false
  private getToken: () => string | null

  constructor(url: string, getToken: () => string | null = () => localStorage.getItem('access_token')) {
    this.url = url
    this.getToken = getToken
  }

  /**
   * 建立 SSE 连接
   */
  connect(): void {
    if (this.eventSource) {
      this.disconnect()
    }

    try {
      // EventSource 不支持自定义 header，通过 URL 参数传递 token
      const token = this.getToken()
      if (!token) {
        console.error('[SSE] No token available')
        return
      }

      const urlWithToken = `${this.url}?token=${encodeURIComponent(token)}`
      this.eventSource = new EventSource(urlWithToken)

      this.eventSource.onopen = () => {
        console.log('[SSE] Connected')
        this.connected = true
        this.reconnectAttempts = 0
        this.notifyStatusChange(true)
      }

      this.eventSource.onmessage = (event) => {
        try {
          const message: SSEEvent = JSON.parse(event.data)
          this.dispatch(message.type, message.data)
        } catch (e) {
          // 心跳消息或其他非 JSON 消息，忽略
        }
      }

      this.eventSource.onerror = (error) => {
        console.error('[SSE] Connection error:', error)
        this.connected = false
        this.notifyStatusChange(false)
        this.reconnect()
      }
    } catch (error) {
      console.error('[SSE] Failed to create EventSource:', error)
      this.reconnect()
    }
  }

  /**
   * 断开 SSE 连接
   */
  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
    }
    this.connected = false
    this.notifyStatusChange(false)
    console.log('[SSE] Disconnected')
  }

  /**
   * 监听事件
   */
  on(eventType: string, callback: SSEEventCallback): void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set())
    }
    this.listeners.get(eventType)!.add(callback)
  }

  /**
   * 取消监听
   */
  off(eventType: string, callback: SSEEventCallback): void {
    this.listeners.get(eventType)?.delete(callback)
  }

  /**
   * 监听连接状态变化
   */
  onStatusChange(callback: (connected: boolean) => void): void {
    this.statusListeners.add(callback)
  }

  /**
   * 取消状态监听
   */
  offStatusChange(callback: (connected: boolean) => void): void {
    this.statusListeners.delete(callback)
  }

  /**
   * 获取连接状态
   */
  isConnected(): boolean {
    return this.connected
  }

  /**
   * 分发事件
   */
  private dispatch(type: string, data: any): void {
    const callbacks = this.listeners.get(type)
    if (callbacks) {
      callbacks.forEach(cb => {
        try {
          cb(data)
        } catch (e) {
          console.error(`[SSE] Callback error for ${type}:`, e)
        }
      })
    }
  }

  /**
   * 通知状态变化
   */
  private notifyStatusChange(connected: boolean): void {
    this.statusListeners.forEach(cb => {
      try {
        cb(connected)
      } catch (e) {
        console.error('[SSE] Status callback error:', e)
      }
    })
  }

  /**
   * 重连
   */
  private reconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[SSE] Max reconnect attempts reached')
      return
    }

    this.reconnectAttempts++
    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000)

    console.log(`[SSE] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})...`)

    setTimeout(() => {
      if (!this.connected) {
        this.connect()
      }
    }, delay)
  }
}

/**
 * 事件类型定义
 */
export const SSEEventTypes = {
  // 任务相关
  TASK_STARTED: 'task_started',
  TASK_RESULT: 'task_result',
  TASK_FAILED: 'task_failed',

  // 系统相关
  SYSTEM_NOTICE: 'system_notice',
  SYSTEM_ALERT: 'system_alert',

  // Gateway 相关
  GATEWAY_CONNECTED: 'gateway_connected',
  GATEWAY_DISCONNECTED: 'gateway_disconnect'
} as const

// 全局单例
let globalSSEClient: SSEClient | null = null

export function getSSEClient(): SSEClient {
  if (!globalSSEClient) {
    globalSSEClient = new SSEClient('/api/events/stream')
  }
  return globalSSEClient
}