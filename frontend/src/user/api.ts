/**
 * 用户相关 API
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

// 请求拦截器：添加 Token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：处理 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (originalRequest.url?.includes('/auth/login') || originalRequest.url?.includes('/auth/register')) {
      return Promise.reject(error)
    }

    if (window.location.pathname === '/login' || window.location.pathname === '/register') {
      return Promise.reject(error)
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user_info')
      window.location.href = '/login'
      return Promise.reject(error)
    }

    return Promise.reject(error)
  }
)

export const userApi = {
  /**
   * 用户登录
   */
  login(username: string, password: string) {
    return api.post('/auth/login', { username, password })
  },

  /**
   * 员工注册
   */
  register(data: { name: string; email: string; password: string; phone?: string }) {
    return api.post('/auth/register', data)
  },

  /**
   * 用户登出
   */
  logout() {
    return api.post('/auth/logout')
  },

  /**
   * 获取当前用户信息
   */
  me() {
    return api.get('/auth/me')
  },

  /**
   * 刷新 Token
   */
  refresh(refreshToken: string) {
    return api.post('/auth/refresh', { refresh_token: refreshToken })
  },

  /**
   * 修改密码
   */
  changePassword(old_password: string, new_password: string) {
    return api.post('/auth/change-password', { old_password, new_password })
  }
}

export default api