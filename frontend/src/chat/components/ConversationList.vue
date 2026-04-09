<template>
  <div class="conversation-list">
    <!-- 搜索栏 -->
    <div class="search-bar">
      <el-input
        v-model="searchQuery"
        placeholder="搜索"
        prefix-icon="Search"
        clearable
        size="default"
      />
    </div>

    <!-- 标签页切换 -->
    <div class="tabs">
      <div
        :class="['tab', { active: activeTab === 'single' }]"
        @click="activeTab = 'single'"
      >
        <el-icon><User /></el-icon>
        <span>单聊</span>
      </div>
      <div
        :class="['tab', { active: activeTab === 'group' }]"
        @click="activeTab = 'group'"
      >
        <el-icon><ChatDotRound /></el-icon>
        <span>群聊</span>
      </div>
    </div>

    <!-- 会话列表 -->
    <div class="list-container">
      <TransitionGroup name="list" tag="div" class="list">
        <!-- 单聊列表 -->
        <template v-if="activeTab === 'single'">
          <div
            v-for="conv in filteredSingleConversations"
            :key="conv.id"
            :class="['conversation-item', { active: selectedId === conv.id }]"
            @click="selectConversation(conv)"
          >
            <div class="avatar" :style="getAvatarStyle(conv.agentId)">
              {{ conv.agentName?.charAt(0) || '?' }}
            </div>
            <div class="info">
              <div class="name-row">
                <span class="name">{{ conv.agentName }}</span>
                <span class="time" v-if="conv.lastMessageTime">{{ formatTime(conv.lastMessageTime) }}</span>
              </div>
              <div class="preview">{{ conv.lastMessage || '开始聊天吧' }}</div>
            </div>
            <div class="unread-badge" v-if="conv.unread && conv.unread > 0">
              {{ conv.unread > 99 ? '99+' : conv.unread }}
            </div>
          </div>
        </template>

        <!-- 群聊列表 -->
        <template v-else>
          <!-- 新建群聊 -->
          <div class="conversation-item create-group" @click="$emit('createGroup')">
            <div class="avatar create">
              <el-icon><Plus /></el-icon>
            </div>
            <div class="info">
              <span class="name">新建群聊</span>
            </div>
          </div>

          <div
            v-for="conv in filteredGroupConversations"
            :key="conv.id"
            :class="['conversation-item', { active: selectedId === conv.id }]"
            @click="selectConversation(conv)"
          >
            <div class="avatar group">
              <div class="group-avatars">
                <span v-for="(p, idx) in conv.participants.slice(0, 2)" :key="p.agentId" :style="{ zIndex: 2 - idx }">
                  {{ p.name?.charAt(0) || '?' }}
                </span>
              </div>
            </div>
            <div class="info">
              <div class="name-row">
                <span class="name">{{ conv.name || '群聊' }}</span>
                <span class="time" v-if="conv.lastMessageTime">{{ formatTime(conv.lastMessageTime) }}</span>
              </div>
              <div class="preview">{{ conv.lastMessage || `${conv.participants.length} 人` }}</div>
            </div>
            <div class="unread-badge" v-if="conv.unread && conv.unread > 0">
              {{ conv.unread > 99 ? '99+' : conv.unread }}
            </div>
          </div>

          <!-- 空状态 -->
          <div v-if="filteredGroupConversations.length === 0" class="empty-tip">
            点击上方"新建群聊"开始
          </div>
        </template>
      </TransitionGroup>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { User, ChatDotRound, Plus } from '@element-plus/icons-vue'
import type { SingleConversation, GroupConversation, Conversation, Agent, Participant } from '../types'

// ==================== Props & Emits ====================

const props = defineProps<{
  agents: Agent[]
  selectedId?: string
  singleConversations: SingleConversation[]
  groupConversations: GroupConversation[]
}>()

const emit = defineEmits<{
  (e: 'select', conv: Conversation): void
  (e: 'createGroup'): void
}>()

// ==================== State ====================

const searchQuery = ref('')
const activeTab = ref<'single' | 'group'>('single')

// ==================== Computed ====================

const filteredSingleConversations = computed(() => {
  if (!searchQuery.value) return props.singleConversations
  const query = searchQuery.value.toLowerCase()
  return props.singleConversations.filter(c =>
    c.agentName.toLowerCase().includes(query)
  )
})

const filteredGroupConversations = computed(() => {
  if (!searchQuery.value) return props.groupConversations
  const query = searchQuery.value.toLowerCase()
  return props.groupConversations.filter(c =>
    c.name?.toLowerCase().includes(query)
  )
})

// ==================== Methods ====================

const avatarColors: Record<string, string> = {}
const colorPalette = [
  'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
  'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)',
]

function getAvatarStyle(agentId: string): Record<string, string> {
  if (!avatarColors[agentId]) {
    const idx = Object.keys(avatarColors).length
    avatarColors[agentId] = colorPalette[idx % colorPalette.length]
  }
  return { background: avatarColors[agentId] }
}

function selectConversation(conv: Conversation) {
  emit('select', conv)
}

function formatTime(timestamp?: number): string {
  if (!timestamp) return ''
  const now = Date.now()
  const diff = now - timestamp
  const date = new Date(timestamp)

  // 今天
  if (diff < 86400000 && date.getDate() === new Date().getDate()) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  // 昨天
  if (diff < 172800000) {
    return '昨天'
  }
  // 一周内
  if (diff < 604800000) {
    const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
    return days[date.getDay()]
  }
  // 更早
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}
</script>

<style scoped>
.conversation-list {
  width: 280px;
  height: 100%;
  background: #fff;
  border-right: 1px solid #e5e5e5;
  display: flex;
  flex-direction: column;
}

/* 搜索栏 */
.search-bar {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.search-bar :deep(.el-input__wrapper) {
  border-radius: 20px;
  background: #f5f5f5;
  box-shadow: none;
}

/* 标签页 */
.tabs {
  display: flex;
  padding: 8px 12px;
  gap: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  transition: all 0.2s ease;
}

.tab:hover {
  background: #f5f5f5;
}

.tab.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}

/* 列表容器 */
.list-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.list {
  padding: 8px;
}

/* 会话项 */
.conversation-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.conversation-item:hover {
  background: #f5f5f5;
}

.conversation-item.active {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
}

/* 头像 */
.avatar {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  flex-shrink: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.avatar.group {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.avatar.create {
  background: #f0f0f0;
  color: #999;
  border: 2px dashed #ddd;
}

.group-avatars {
  display: flex;
  font-size: 14px;
}

.group-avatars span {
  margin-left: -8px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: 2px solid #fff;
}

.group-avatars span:first-child {
  margin-left: 0;
}

/* 信息区 */
.info {
  flex: 1;
  min-width: 0;
}

.name-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.name {
  font-size: 15px;
  font-weight: 500;
  color: #333;
}

.time {
  font-size: 12px;
  color: #999;
}

.preview {
  font-size: 13px;
  color: #999;
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 未读徽章 */
.unread-badge {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: #ff4d4f;
  color: #fff;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 新建群聊 */
.create-group {
  border: 1px dashed #ddd;
  margin-bottom: 8px;
}

.create-group:hover {
  border-color: #667eea;
  background: rgba(102, 126, 234, 0.05);
}

.create-group .name {
  color: #667eea;
}

/* 空状态 */
.empty-tip {
  text-align: center;
  padding: 40px 20px;
  color: #999;
  font-size: 13px;
}

/* 列表动画 */
.list-enter-active,
.list-leave-active {
  transition: all 0.3s ease;
}

.list-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}

.list-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

/* 滚动条 */
.list-container::-webkit-scrollbar {
  width: 6px;
}

.list-container::-webkit-scrollbar-thumb {
  background: #ddd;
  border-radius: 3px;
}

.list-container::-webkit-scrollbar-thumb:hover {
  background: #ccc;
}
</style>