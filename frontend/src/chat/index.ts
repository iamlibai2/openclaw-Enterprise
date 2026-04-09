/**
 * Chat 模块入口
 */

// Discord 风格聊天页面
export { default as DiscordChat } from './DiscordChat.vue'

// 飞书风格聊天页面
export { default as FeishuChat } from './FeishuChat.vue'

// 原版聊天页面
export { default as ChatPage } from './Chat.vue'

// 微信风格聊天页面
export { default as ChatPageNew } from './ChatPage.vue'

// 类型
export * from './types'

// 工具
export { InputHistory } from './utils/input-history'
export { exportChatMarkdown, buildChatMarkdown } from './utils/chat-export'
export { getOrCreateSessionCacheValue, SessionCache, MAX_CACHED_CHAT_SESSIONS } from './utils/session-cache'
export { SLASH_COMMANDS, parseSlashCommand, getSlashCommandCompletions, isLocalCommand } from './utils/slash-commands'
export { extractText, extractTextCached, clearTextCache } from './utils/message-extract'