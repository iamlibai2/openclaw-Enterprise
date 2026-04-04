/**
 * Agent Profile 模块入口
 *
 * 将 Agent 视为"人"而非配置集合
 * 包含：灵魂、身份、记忆、技能、工具等组件
 */

// 导出组件
export { default as AgentProfilePage } from './AgentProfile.vue'
export { default as AgentGalleryPage } from './AgentGallery.vue'

// 导出类型
export * from './types'

// 导出 API
export * from './api'