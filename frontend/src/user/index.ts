/**
 * 用户模块
 *
 * 包含：登录、注册、用户状态管理、权限控制
 */
export { default as Login } from './Login.vue'
export { default as Register } from './Register.vue'
export { default as StaffHome } from './StaffHome.vue'
export { useUserStore } from './stores'
export { userApi } from './api'
export type { UserInfo, EmployeeInfo, LoginData, RegisterParams, RegisterData } from './types'