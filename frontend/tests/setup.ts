/**
 * Vitest 测试配置
 */

import { config } from '@vue/test-utils'
import { vi } from 'vitest'

// 全局存根 Element Plus 组件
config.global.stubs = {
  'el-button': true,
  'el-input': true,
  'el-select': true,
  'el-option': true,
  'el-table': true,
  'el-table-column': true,
  'el-form': true,
  'el-form-item': true,
  'el-dialog': true,
  'el-message': true,
  'el-pagination': true,
  'el-dropdown': true,
  'el-dropdown-menu': true,
  'el-dropdown-item': true,
  'el-menu': true,
  'el-menu-item': true,
  'el-sub-menu': true,
  'el-tag': true,
  'el-tooltip': true,
  'el-switch': true,
  'el-checkbox': true,
  'el-radio': true,
  'el-radio-group': true,
  'el-date-picker': true,
  'el-time-picker': true,
  'el-icon': true,
  'el-badge': true,
  'el-card': true,
  'el-tabs': true,
  'el-tab-pane': true,
  'el-collapse': true,
  'el-collapse-item': true,
  'el-descriptions': true,
  'el-descriptions-item': true,
  'el-progress': true,
  'el-steps': true,
  'el-step': true,
  'el-empty': true,
  'el-skeleton': true,
  'el-loading': true,
  'el-alert': true,
  'el-notification': true,
}

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
}

Object.defineProperty(global, 'localStorage', {
  value: localStorageMock,
})

// Mock sessionStorage
Object.defineProperty(global, 'sessionStorage', {
  value: localStorageMock,
})

// Mock window.location
const originalLocation = window.location
delete (window as any).location
;(window as any).location = {
  ...originalLocation,
  href: 'http://localhost:5000/',
  origin: 'http://localhost:5000',
  pathname: '/',
  search: '',
  hash: '',
  reload: vi.fn(),
  assign: vi.fn(),
  replace: vi.fn(),
}