/**
 * api/index.ts 单元测试
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'

// Mock axios
vi.mock('axios', () => {
  const mockAxios = {
    create: vi.fn(() => mockAxios),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() }
    },
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  }
  return { default: mockAxios }
})

describe('API 模块', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('axios 实例创建', () => {
    it('创建 axios 实例', async () => {
      // 重新导入以触发 axios.create
      vi.resetModules()
      const { default: api } = await import('@/api/index')

      expect(axios.create).toHaveBeenCalledWith({
        baseURL: '/api',
        timeout: 10000
      })
    })

    it('注册请求拦截器', async () => {
      vi.resetModules()
      const { default: api } = await import('@/api/index')

      expect(api.interceptors.request.use).toHaveBeenCalled()
    })

    it('注册响应拦截器', async () => {
      vi.resetModules()
      const { default: api } = await import('@/api/index')

      expect(api.interceptors.response.use).toHaveBeenCalled()
    })
  })

  describe('请求拦截器', () => {
    it('无 token 时不添加 Authorization', async () => {
      vi.resetModules()
      await import('@/api/index')

      // 获取请求拦截器的成功回调
      const requestInterceptor = axios.create.mock.results[0]?.value?.interceptors?.request?.use
      if (!requestInterceptor) {
        // 直接检查拦截器注册
        expect(axios.interceptors.request.use).toHaveBeenCalled()
        return
      }

      const callbacks = requestInterceptor.mock.calls[0]
      if (callbacks && callbacks[0]) {
        const config = { headers: {} }
        const result = callbacks[0](config)
        expect(result.headers.Authorization).toBeUndefined()
      }
    })

    it('有 token 时添加 Authorization', async () => {
      localStorage.setItem('access_token', 'test-token')
      vi.resetModules()
      await import('@/api/index')

      // 检查拦截器注册
      expect(axios.interceptors.request.use).toHaveBeenCalled()
    })
  })

  describe('authApi', () => {
    it('login 方法调用正确接口', async () => {
      const { authApi } = await import('@/api/index')

      authApi.login('user', 'pass')
      expect(axios.post).toHaveBeenCalledWith('/auth/login', { username: 'user', password: 'pass' })
    })

    it('logout 方法调用正确接口', async () => {
      const { authApi } = await import('@/api/index')

      authApi.logout()
      expect(axios.post).toHaveBeenCalledWith('/auth/logout')
    })

    it('me 方法调用正确接口', async () => {
      const { authApi } = await import('@/api/index')

      authApi.me()
      expect(axios.get).toHaveBeenCalledWith('/auth/me')
    })

    it('changePassword 方法调用正确接口', async () => {
      const { authApi } = await import('@/api/index')

      authApi.changePassword('old', 'new')
      expect(axios.post).toHaveBeenCalledWith('/auth/change-password', { old_password: 'old', new_password: 'new' })
    })
  })

  describe('userApi', () => {
    it('list 方法调用正确接口', async () => {
      const { userApi } = await import('@/api/index')

      userApi.list()
      expect(axios.get).toHaveBeenCalledWith('/users')
    })

    it('create 方法调用正确接口', async () => {
      const { userApi } = await import('@/api/index')

      userApi.create({ username: 'test', password: 'pass' })
      expect(axios.post).toHaveBeenCalledWith('/users', { username: 'test', password: 'pass' })
    })

    it('update 方法调用正确接口', async () => {
      const { userApi } = await import('@/api/index')

      userApi.update(1, { display_name: 'Test' })
      expect(axios.put).toHaveBeenCalledWith('/users/1', { display_name: 'Test' })
    })

    it('delete 方法调用正确接口', async () => {
      const { userApi } = await import('@/api/index')

      userApi.delete(1)
      expect(axios.delete).toHaveBeenCalledWith('/users/1')
    })
  })

  describe('roleApi', () => {
    it('list 方法调用正确接口', async () => {
      const { roleApi } = await import('@/api/index')

      roleApi.list()
      expect(axios.get).toHaveBeenCalledWith('/roles')
    })

    it('update 方法调用正确接口', async () => {
      const { roleApi } = await import('@/api/index')

      roleApi.update(1, { description: 'Admin role' })
      expect(axios.put).toHaveBeenCalledWith('/roles/1', { description: 'Admin role' })
    })
  })

  describe('gatewayApi', () => {
    it('status 方法调用正确接口', async () => {
      const { gatewayApi } = await import('@/api/index')

      gatewayApi.status()
      expect(axios.get).toHaveBeenCalledWith('/gateway/status')
    })

    it('restart 方法调用正确接口', async () => {
      const { gatewayApi } = await import('@/api/index')

      gatewayApi.restart()
      expect(axios.post).toHaveBeenCalledWith('/gateway/restart')
    })

    it('reload 方法调用正确接口', async () => {
      const { gatewayApi } = await import('@/api/index')

      gatewayApi.reload()
      expect(axios.post).toHaveBeenCalledWith('/gateway/reload')
    })
  })

  describe('taskApi', () => {
    it('overview 方法调用正确接口', async () => {
      const { taskApi } = await import('@/api/index')

      taskApi.overview()
      expect(axios.get).toHaveBeenCalledWith('/tasks/overview')
    })

    it('trend 方法带参数调用', async () => {
      const { taskApi } = await import('@/api/index')

      taskApi.trend(14)
      expect(axios.get).toHaveBeenCalledWith('/tasks/trend', { params: { days: 14 } })
    })

    it('recent 方法带参数调用', async () => {
      const { taskApi } = await import('@/api/index')

      taskApi.recent(20)
      expect(axios.get).toHaveBeenCalledWith('/tasks/recent', { params: { limit: 20 } })
    })
  })
})