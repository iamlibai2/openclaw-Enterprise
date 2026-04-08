/**
 * gateway-ws.ts 单元测试
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  extractText,
  handleChatEvent,
  getGatewayClient,
  createGatewayClient,
  type ChatState
} from '@/utils/gateway-ws'

describe('extractText', () => {
  it('从 text 字段提取', () => {
    expect(extractText({ text: 'hello world' })).toBe('hello world')
  })

  it('从 content 数组提取', () => {
    expect(extractText({
      content: [
        { type: 'text', text: 'array content' },
        { type: 'image', url: 'http://example.com' }
      ]
    })).toBe('array content')
  })

  it('从 content 字符串提取', () => {
    expect(extractText({ content: 'string content' })).toBe('string content')
  })

  it('无效输入返回 null', () => {
    expect(extractText(null)).toBe(null)
    expect(extractText(undefined)).toBe(null)
    expect(extractText('string')).toBe(null)
    expect(extractText({})).toBe(null)
    expect(extractText({ content: [] })).toBe(null)
    expect(extractText({ content: [{ type: 'image' }] })).toBe(null)
  })
})

describe('handleChatEvent', () => {
  let state: {
    chatMessages: any[]
    chatStream: string | null
    chatRunId: string | null
    lastError: string | null
    sessionKey: string
  }

  beforeEach(() => {
    state = {
      chatMessages: [],
      chatStream: null,
      chatRunId: null,
      lastError: null,
      sessionKey: 'test-session'
    }
  })

  describe('delta 状态', () => {
    it('更新 chatStream', () => {
      const payload: ChatState = {
        runId: 'run-1',
        sessionKey: 'test-session',
        state: 'delta',
        message: { text: 'hello' }
      }

      const result = handleChatEvent(state, payload)
      expect(result).toBe('delta')
      expect(state.chatStream).toBe('hello')
    })

    it('sessionKey 不匹配时忽略', () => {
      const payload: ChatState = {
        runId: 'run-1',
        sessionKey: 'other-session',
        state: 'delta',
        message: { text: 'hello' }
      }

      const result = handleChatEvent(state, payload)
      expect(result).toBe(null)
      expect(state.chatStream).toBe(null)
    })
  })

  describe('final 状态', () => {
    it('添加消息到 chatMessages', () => {
      state.chatStream = 'streaming text'

      const payload: ChatState = {
        runId: 'run-1',
        sessionKey: 'test-session',
        state: 'final',
        message: { text: 'final text' }
      }

      const result = handleChatEvent(state, payload)
      expect(result).toBe('final')
      expect(state.chatMessages.length).toBe(1)
      expect(state.chatMessages[0].role).toBe('assistant')
      expect(state.chatStream).toBe(null)
      expect(state.chatRunId).toBe(null)
    })

    it('使用 chatStream 作为备选', () => {
      state.chatStream = 'streaming text'

      const payload: ChatState = {
        runId: 'run-1',
        sessionKey: 'test-session',
        state: 'final',
        message: null
      }

      handleChatEvent(state, payload)
      expect(state.chatMessages[0].content[0].text).toBe('streaming text')
    })
  })

  describe('aborted 状态', () => {
    it('保存已流式传输的内容', () => {
      state.chatStream = 'partial text'

      const payload: ChatState = {
        runId: 'run-1',
        sessionKey: 'test-session',
        state: 'aborted'
      }

      const result = handleChatEvent(state, payload)
      expect(result).toBe('aborted')
      expect(state.chatMessages.length).toBe(1)
      expect(state.chatStream).toBe(null)
    })
  })

  describe('error 状态', () => {
    it('设置错误信息', () => {
      const payload: ChatState = {
        runId: 'run-1',
        sessionKey: 'test-session',
        state: 'error',
        errorMessage: 'something went wrong'
      }

      const result = handleChatEvent(state, payload)
      expect(result).toBe('error')
      expect(state.lastError).toBe('something went wrong')
      expect(state.chatStream).toBe(null)
    })

    it('使用默认错误信息', () => {
      const payload: ChatState = {
        runId: 'run-1',
        sessionKey: 'test-session',
        state: 'error'
      }

      handleChatEvent(state, payload)
      expect(state.lastError).toBe('chat error')
    })
  })

  describe('payload 为空', () => {
    it('返回 null', () => {
      expect(handleChatEvent(state, undefined)).toBe(null)
    })
  })
})

describe('单例管理', () => {
  afterEach(() => {
    // 清理单例
    const client = getGatewayClient()
    if (client) {
      client.stop()
    }
  })

  it('createGatewayClient 创建客户端', () => {
    const client = createGatewayClient({
      url: 'ws://localhost:8080/ws',
      token: 'test-token'
    })
    expect(client).toBeDefined()
    expect(getGatewayClient()).toBe(client)
  })

  it('创建新客户端时停止旧客户端', () => {
    const client1 = createGatewayClient({
      url: 'ws://localhost:8080/ws'
    })
    const client2 = createGatewayClient({
      url: 'ws://localhost:8080/ws'
    })
    expect(getGatewayClient()).toBe(client2)
    expect(getGatewayClient()).not.toBe(client1)
  })

  it('getGatewayClient 返回当前单例', () => {
    const client = createGatewayClient({
      url: 'ws://localhost:8080/ws'
    })
    expect(getGatewayClient()).toBe(client)
  })
})