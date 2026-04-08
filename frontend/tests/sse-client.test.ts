/**
 * sse-client.ts 单元测试
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { SSEClient, SSEEventTypes, getSSEClient } from '@/utils/sse-client'

// Mock EventSource 类
class MockEventSource {
  static instances: MockEventSource[] = []
  url: string
  onopen: ((ev: Event) => void) | null = null
  onmessage: ((ev: MessageEvent) => void) | null = null
  onerror: ((ev: Event) => void) | null = null
  readyState: number = 0

  constructor(url: string) {
    this.url = url
    MockEventSource.instances.push(this)
  }

  close() {
    this.readyState = 2
  }
}

describe('SSEClient', () => {
  let client: SSEClient
  let lastMock: MockEventSource | null

  beforeEach(() => {
    vi.useFakeTimers()
    MockEventSource.instances = []
    lastMock = null

    // Mock EventSource
    vi.stubGlobal('EventSource', MockEventSource)

    client = new SSEClient('http://localhost:5001/api/events/stream', () => 'test-token')
  })

  afterEach(() => {
    client.disconnect()
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  function getLatestMock(): MockEventSource | undefined {
    return MockEventSource.instances[MockEventSource.instances.length - 1]
  }

  describe('构造函数', () => {
    it('使用自定义 getToken 函数', () => {
      const customClient = new SSEClient('http://test', () => 'custom-token')
      expect(customClient).toBeDefined()
    })
  })

  describe('connect', () => {
    it('无 token 时不连接', () => {
      const noTokenClient = new SSEClient('http://test', () => null)
      noTokenClient.connect()
      expect(noTokenClient.isConnected()).toBe(false)
    })

    it('有 token 时创建 EventSource', () => {
      client.connect()
      const mock = getLatestMock()
      expect(mock).toBeDefined()
      expect(mock!.url).toContain('token=')
    })

    it('连接成功后更新状态', () => {
      client.connect()
      const mock = getLatestMock()
      expect(mock).toBeDefined()

      // 模拟连接成功
      mock!.onopen!(new Event('open'))

      expect(client.isConnected()).toBe(true)
    })

    it('重连前断开现有连接', () => {
      client.connect()
      const mock1 = getLatestMock()
      mock1!.onopen!(new Event('open'))

      // 再次连接
      client.connect()

      // 原来的 EventSource 应该被关闭
      expect(mock1!.readyState).toBe(2)
      // 新的 EventSource 应该被创建
      expect(MockEventSource.instances.length).toBe(2)
    })
  })

  describe('disconnect', () => {
    it('断开连接并更新状态', () => {
      client.connect()
      const mock = getLatestMock()
      mock!.onopen!(new Event('open'))
      expect(client.isConnected()).toBe(true)

      client.disconnect()

      expect(mock!.readyState).toBe(2)
      expect(client.isConnected()).toBe(false)
    })
  })

  describe('on / off', () => {
    it('监听事件', () => {
      const callback = vi.fn()
      client.on('test_event', callback)

      client.connect()
      const mock = getLatestMock()
      mock!.onopen!(new Event('open'))

      // 模拟收到消息
      const messageEvent = new MessageEvent('message', {
        data: JSON.stringify({ type: 'test_event', timestamp: '2024-01-01', data: { msg: 'hello' } })
      })
      mock!.onmessage!(messageEvent)

      expect(callback).toHaveBeenCalledWith({ msg: 'hello' })
    })

    it('取消监听', () => {
      const callback = vi.fn()
      client.on('test_event', callback)
      client.off('test_event', callback)

      client.connect()
      const mock = getLatestMock()
      mock!.onopen!(new Event('open'))

      const messageEvent = new MessageEvent('message', {
        data: JSON.stringify({ type: 'test_event', timestamp: '2024-01-01', data: {} })
      })
      mock!.onmessage!(messageEvent)

      expect(callback).not.toHaveBeenCalled()
    })
  })

  describe('onStatusChange / offStatusChange', () => {
    it('监听状态变化', () => {
      const callback = vi.fn()
      client.onStatusChange(callback)

      client.connect()
      const mock = getLatestMock()
      mock!.onopen!(new Event('open'))

      expect(callback).toHaveBeenCalledWith(true)
    })

    it('取消状态监听', () => {
      const callback = vi.fn()
      client.onStatusChange(callback)
      client.offStatusChange(callback)

      client.connect()
      const mock = getLatestMock()
      mock!.onopen!(new Event('open'))

      expect(callback).not.toHaveBeenCalled()
    })
  })

  describe('isConnected', () => {
    it('初始为 false', () => {
      expect(client.isConnected()).toBe(false)
    })

    it('连接后为 true', () => {
      client.connect()
      const mock = getLatestMock()
      mock!.onopen!(new Event('open'))
      expect(client.isConnected()).toBe(true)
    })
  })

  describe('reconnect', () => {
    it('错误后触发重连', () => {
      client.connect()
      const mock = getLatestMock()
      mock!.onopen!(new Event('open'))

      // 模拟错误
      mock!.onerror!(new Event('error'))
      expect(client.isConnected()).toBe(false)

      // 快进时间
      vi.advanceTimersByTime(2000)

      // 应该尝试重连（创建新的 EventSource）
      expect(MockEventSource.instances.length).toBe(2)
    })
  })
})

describe('SSEEventTypes', () => {
  it('定义事件类型常量', () => {
    expect(SSEEventTypes.TASK_STARTED).toBe('task_started')
    expect(SSEEventTypes.TASK_RESULT).toBe('task_result')
    expect(SSEEventTypes.TASK_FAILED).toBe('task_failed')
    expect(SSEEventTypes.SYSTEM_NOTICE).toBe('system_notice')
    expect(SSEEventTypes.GATEWAY_CONNECTED).toBe('gateway_connected')
  })
})

describe('getSSEClient', () => {
  it('返回全局单例', () => {
    const client1 = getSSEClient()
    const client2 = getSSEClient()
    expect(client1).toBe(client2)
  })
})