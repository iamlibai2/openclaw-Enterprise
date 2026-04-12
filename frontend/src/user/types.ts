/**
 * 用户模块类型定义
 */

export interface EmployeeInfo {
  id: number
  name: string
  agent_ids: string[]
  department_id: number | null
  department_name: string | null
}

export interface UserInfo {
  id: number
  username: string
  display_name: string
  email?: string
  role: string
  permissions: Record<string, string[]>
  last_login?: string
  employee?: EmployeeInfo
}

export interface LoginData {
  user: UserInfo
  access_token: string
  refresh_token: string
}

export interface RegisterParams {
  name: string
  email: string
  password: string
  phone?: string
}

export interface RegisterData extends LoginData {
  employee_id: number
}