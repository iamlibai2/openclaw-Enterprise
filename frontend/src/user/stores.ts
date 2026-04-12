/**
 * 用户状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo, EmployeeInfo, LoginData } from './types'

export const useUserStore = defineStore('user', () => {
  const user = ref<UserInfo | null>(null)
  const accessToken = ref<string>('')
  const refreshToken = ref<string>('')

  // 计算属性
  const isLoggedIn = computed(() => !!user.value && !!accessToken.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isOperator = computed(() => user.value?.role === 'operator' || user.value?.role === 'admin')
  const isStaff = computed(() => user.value?.role === 'staff')
  const employee = computed(() => user.value?.employee)
  const boundAgentIds = computed(() => user.value?.employee?.agent_ids || [])

  /**
   * 设置用户信息
   */
  function setUser(userInfo: UserInfo) {
    user.value = userInfo
    localStorage.setItem('user_info', JSON.stringify(userInfo))
  }

  /**
   * 设置 Token
   */
  function setTokens(access: string, refresh: string) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  /**
   * 设置登录数据（一次性设置所有登录信息）
   */
  function setLoginData(data: LoginData) {
    user.value = data.user
    accessToken.value = data.access_token
    refreshToken.value = data.refresh_token
    localStorage.setItem('user_info', JSON.stringify(data.user))
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
  }

  /**
   * 从 localStorage 恢复状态
   */
  function loadFromStorage() {
    const storedUser = localStorage.getItem('user_info')
    const storedAccess = localStorage.getItem('access_token')
    const storedRefresh = localStorage.getItem('refresh_token')

    if (storedUser && storedAccess) {
      try {
        user.value = JSON.parse(storedUser)
        accessToken.value = storedAccess
        refreshToken.value = storedRefresh || ''
      } catch {
        clear()
      }
    }
  }

  /**
   * 清除所有登录状态
   */
  function clear() {
    user.value = null
    accessToken.value = ''
    refreshToken.value = ''
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_info')
  }

  /**
   * 检查是否有指定权限
   */
  function hasPermission(resource: string, action: string): boolean {
    if (!user.value) return false
    if (user.value.role === 'admin') return true
    const perms = user.value.permissions[resource] || []
    return perms.includes(action)
  }

  return {
    // 状态
    user,
    accessToken,
    refreshToken,
    // 计算属性
    isLoggedIn,
    isAdmin,
    isOperator,
    isStaff,
    employee,
    boundAgentIds,
    // 方法
    setUser,
    setTokens,
    setLoginData,
    loadFromStorage,
    clear,
    hasPermission
  }
})