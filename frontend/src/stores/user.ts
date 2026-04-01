import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface UserInfo {
  id: number
  username: string
  display_name: string
  role: string
  permissions: Record<string, string[]>
}

export const useUserStore = defineStore('user', () => {
  const user = ref<UserInfo | null>(null)
  const accessToken = ref<string>('')
  const refreshToken = ref<string>('')

  const isLoggedIn = computed(() => !!user.value && !!accessToken.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isOperator = computed(() => user.value?.role === 'operator' || user.value?.role === 'admin')

  function setUser(userInfo: UserInfo) {
    user.value = userInfo
    localStorage.setItem('user_info', JSON.stringify(userInfo))
  }

  function setTokens(access: string, refresh: string) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  function setLoginData(data: { user: UserInfo; access_token: string; refresh_token: string }) {
    user.value = data.user
    accessToken.value = data.access_token
    refreshToken.value = data.refresh_token
    localStorage.setItem('user_info', JSON.stringify(data.user))
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
  }

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
        // 解析失败，清除所有
        clear()
      }
    }
  }

  function clear() {
    user.value = null
    accessToken.value = ''
    refreshToken.value = ''
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_info')
  }

  function hasPermission(resource: string, action: string): boolean {
    if (!user.value) return false
    // admin 拥有所有权限
    if (user.value.role === 'admin') return true
    const perms = user.value.permissions[resource] || []
    return perms.includes(action)
  }

  return {
    user,
    accessToken,
    refreshToken,
    isLoggedIn,
    isAdmin,
    isOperator,
    setUser,
    setTokens,
    setLoginData,
    loadFromStorage,
    clear,
    hasPermission
  }
})